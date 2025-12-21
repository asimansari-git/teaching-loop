from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, database, auth, chat_service
from ..models import User, Report

router = APIRouter(
    prefix="/reports",
    tags=["reports"]
)

@router.get("/students", response_model=List[models.UserOut])
def get_students(current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Filter students by the same organization as the teacher
    students = db.query(User).filter(
        User.role == "student",
        User.organization_id == current_user.organization_id
    ).all()
    return students

@router.post("/generate", response_model=models.ReportOut)
async def generate_report(report_in: models.ReportCreate, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    print("Generating report for student: ", report_in.student_id)
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate content using Gemini
    student = db.query(User).filter(User.id == report_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Authorize: Teacher can only generate reports for students in their org
    if student.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this student")

    print("Passed db query")
    generated_content = await chat_service.analyze_performance(report_in.session_id)
    print("Generated content: ", generated_content)
    if(generated_content.startswith("ERROR")):
        raise HTTPException(status_code=500, detail=generated_content)
    # We might need to fetch the session to get the subject if it wasn't passed?
    # For now, let's assume subject is passed or we can fetch it?
    # Simple fix: Let's fetch session details if subject is missing
    subject = report_in.subject
    if not subject:
         # Small hack: we can parse from analyze_performance or just fetch from mongo
         # Better to fetch from mongo in chat_service or here. 
         # For speed, let's just default to "Session Report" if not provided, 
         # but ideally frontend passes it.
         subject = "Session Report" 

    # Save Report
    new_report = Report(
        student_id=report_in.student_id,
        subject=subject,
        content=generated_content
    )
    print("New report: ", new_report)
    db.add(new_report)
    print("Added to db")
    db.commit()
    print("Committed to db")
    db.refresh(new_report)
    print("Refreshed")
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
