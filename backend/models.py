from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from .database import Base

# --- SQLAlchemy Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # "student" or "teacher"
    
    reports = relationship("Report", back_populates="student")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    content = Column(Text) # Storing report as JSON string or text
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="reports")

# --- Pydantic Schemas ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str

class UserOut(UserBase):
    id: int
    role: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class ReportCreate(BaseModel):
    student_id: int
    session_id: str
    subject: Optional[str] = None # Can be inferred
    content: Optional[str] = ""

class ReportOut(ReportCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class CreateSessionRequest(BaseModel):
    subject: str
    topics: List[str]

class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    subject: str
