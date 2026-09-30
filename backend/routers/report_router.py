import logging
import hashlib
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, database, auth, chat_service
from ..models import User, Report, Certificate

logger = logging.getLogger("teaching_platform.report_router")

router = APIRouter(
    prefix="/reports",
    tags=["reports"]
)

@router.get("/students", response_model=List[models.UserOut])
def get_students(current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    students = db.query(User).filter(
        User.role == "student",
        User.organization_id == current_user.organization_id
    ).all()
    return students

@router.post("/generate", response_model=models.ReportOut)
async def generate_report(report_in: models.ReportCreate, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    logger.info(f"Generating report for student ID {report_in.student_id}")
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")

    student = db.query(User).filter(User.id == report_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this student")

    quizzes = db.query(models.Quiz).filter(models.Quiz.session_id == report_in.session_id).all()
    quiz_context = ""
    if quizzes:
        quiz_context = "Quiz Performance History:\n"
        for q in quizzes:
            status = "Passed" if q.passed else "Failed"
            score_display = f"{q.score:.1f}%" if q.score is not None else "N/A"
            quiz_context += f"- Level: {q.difficulty}, Score: {score_display}, Status: {status}\n"
            
    generated_content = await chat_service.analyze_performance(report_in.session_id, extra_context=quiz_context)
    if generated_content.startswith("ERROR"):
        raise HTTPException(status_code=500, detail=generated_content)

    subject = report_in.subject or "Session Report"

    new_report = Report(
        student_id=report_in.student_id,
        subject=subject,
        content=generated_content
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    report_out = models.ReportOut(
        id=new_report.id,
        session_id=report_in.session_id,    
        student_id=new_report.student_id,
        subject=new_report.subject,
        content=new_report.content,
        created_at=new_report.created_at
    )
    return report_out

@router.get("/sessions/{student_username}", response_model=List[models.SessionSummary])
async def get_student_sessions(student_username: str, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if student belongs to teacher's org
    student = db.query(User).filter(User.username == student_username).first()
    if not student or student.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this student sessions")

    return chat_service.get_user_sessions(student_username)

@router.get("/student/{student_id}", response_model=List[models.ReportOut])
def get_student_reports(student_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # Students can view their own reports, Teachers can view all
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    reports = db.query(Report).filter(Report.student_id == student_id).order_by(Report.created_at.desc()).all()
    report_out = [models.ReportOut(
        id=report.id,
        session_id="",
        student_id=student_id,
        subject=report.subject,
        content=report.content,
        created_at=report.created_at
    ) for report in reports]
    return report_out

@router.post("/certificate")
async def generate_certificate(request: models.ReportCreate, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Certificates can only be earned and requested by students.")

    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("username") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to generate certificate for another student's session")

    # Check if a certificate has already been issued for this session
    existing_cert = db.query(Certificate).filter(
        Certificate.student_id == current_user.id,
        Certificate.session_id == str(request.session_id)
    ).first()
    if existing_cert:
        return {
            "content": existing_cert.content,
            "verification_hash": existing_cert.verification_hash,
            "created_at": existing_cert.created_at
        }

    # Fetch and validate Quiz Results across all levels
    quizzes = db.query(models.Quiz).filter(models.Quiz.session_id == str(request.session_id)).all()
    if not quizzes:
        raise HTTPException(status_code=400, detail="No quiz assessments found for this session.")

    quiz_summary = ""
    passed_levels = set()
    for q in quizzes:
        status = "Passed" if q.passed else "Failed"
        score_display = f"{q.score:.1f}%" if q.score is not None else "N/A"
        quiz_summary += f"- Level: {q.difficulty.title()}, Score: {score_display}, Status: {status}\n"
        if q.passed and q.score is not None and q.score >= 70:
            passed_levels.add(q.difficulty.lower())

    required_levels = {"easy", "mid", "hard"}
    missing_levels = required_levels - passed_levels
    if missing_levels:
        missing_str = ", ".join(sorted(missing_levels)).title()
        raise HTTPException(
            status_code=400,
            detail=f"Must complete and pass all quiz levels (Easy, Mid, and Hard >= 70%) to earn a certificate. Missing: {missing_str}"
        )

    # Generate certificate content with official timestamp and hash
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    hash_seed = f"{current_user.id}:{request.session_id}:{now.timestamp()}"
    verification_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:16].upper()

    course_subject = request.subject or session.get("subject", "Adaptive Learning Course")
    content = await chat_service.generate_certificate_content(
        student_name=current_user.username,
        subject=course_subject,
        date_str=date_str,
        quiz_summary=f"{quiz_summary}\nVerification Code: `{verification_hash}`"
    )

    new_cert = Certificate(
        student_id=current_user.id,
        session_id=str(request.session_id),
        subject=course_subject,
        verification_hash=verification_hash,
        content=content,
        created_at=now
    )
    db.add(new_cert)
    db.commit()
    db.refresh(new_cert)

    return {
        "content": new_cert.content,
        "verification_hash": new_cert.verification_hash,
        "created_at": new_cert.created_at
    }

@router.get("/micro-credential/{session_id}", response_model=models.MicroCredentialOut)
async def get_micro_credential_endpoint(
    session_id: str,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_username = session.get("username")
    if current_user.role == "student":
        if session_username != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        target_student_id = current_user.id
    elif current_user.role == "teacher":
        student = db.query(User).filter(User.username == session_username).first()
        if not student or student.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to access student session outside your organization")
        target_student_id = student.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

    res = await chat_service.get_micro_credential_status(session_id, target_student_id, db)
    return res

@router.post("/review-sheet", response_model=models.ReviewSheetOut)
async def compile_review_sheet_endpoint(
    request: models.ReviewSheetRequest,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_username = session.get("username")
    if current_user.role == "student":
        if session_username != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        target_student_id = current_user.id
    elif current_user.role == "teacher":
        student = db.query(User).filter(User.username == session_username).first()
        if not student or student.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to access student session outside your organization")
        target_student_id = request.student_id or student.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

    highlights_dicts = [h.model_dump() for h in request.highlights]
    result = await chat_service.compile_review_sheet(
        session_id=request.session_id,
        student_id=target_student_id,
        highlights=highlights_dicts,
        db_session=db
    )
    return result
