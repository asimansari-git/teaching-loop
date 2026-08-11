from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from .database import Base

# --- SQLAlchemy Models ---

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # "student" or "teacher"
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True) # Check if we want nullable, for now yes
    
    organization = relationship("Organization", back_populates="users")
    reports = relationship("Report", back_populates="student")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    topics = Column(JSON) # List of strings

class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True) # MongoDB Session ID
    plan_content = Column(JSON) # Structured curriculum
    status = Column(String, default="active") # active, completed
    created_at = Column(DateTime, default=datetime.utcnow)

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    difficulty = Column(String) # easy, mid, hard
    questions = Column(JSON)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    content = Column(Text) # Storing report as JSON string or text
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="reports")

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content_type = Column(String)
    status = Column(String, default="processed") # processed, verified
    teacher_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chunks = relationship("ContentChunk", back_populates="item")

class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(Integer, ForeignKey("content_items.id"))
    text = Column(String)
    topics = Column(JSON) # List of extracted topics
    status = Column(String, default="pending") # pending, approved, rejected
    index_id = Column(String, nullable=True) # Chroma ID
    
    item = relationship("ContentItem", back_populates="chunks")

# --- Pydantic Schemas ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str
    organization_id: Optional[int] = None
    new_organization_name: Optional[str] = None # For creating new org

class UserOut(UserBase):
    id: int
    role: str
    organization_id: Optional[int] = None
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
    
class ContentChunkOut(BaseModel):
    id: int
    text: str
    topics: list
    status: str
    
class ContentItemOut(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime
    chunks: List[ContentChunkOut] = []
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
class OrganizationOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class SubjectBase(BaseModel):
    name: str
    topics: List[str]

class SubjectOut(SubjectBase):
    id: int
    class Config:
        from_attributes = True

class LearningPlanCreate(BaseModel):
    session_id: str
    plan_content: dict

class QuizCreate(BaseModel):
    session_id: str
    difficulty: str
    questions: dict
