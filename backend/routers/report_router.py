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
    
    students = db.query(User).filter(User.role == "student").all()
    return students

@router.post("/generate", response_model=models.ReportOut)
async def generate_report(report_in: models.ReportCreate, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate content using Gemini
    student = db.query(User).filter(User.id == report_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    generated_content = await chat_service.analyze_performance(student.username, report_in.subject)
    
    # Save Report
    new_report = Report(
        student_id=report_in.student_id,
        subject=report_in.subject,
        content=generated_content
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report

@router.get("/student/{student_id}", response_model=List[models.ReportOut])
def get_student_reports(student_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # Students can view their own reports, Teachers can view all
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    reports = db.query(Report).filter(Report.student_id == student_id).all()
    return reports
