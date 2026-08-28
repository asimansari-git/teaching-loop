from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

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
    role = Column(String)  # "student" or "teacher"
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", back_populates="users")
    reports = relationship("Report", back_populates="student")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    topics = Column(JSON)  # List of strings

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    difficulty = Column(String)  # easy, mid, hard
    questions = Column(JSON)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="reports")

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content_type = Column(String)
    status = Column(String, default="processed")  # processed, verified
    teacher_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("ContentChunk", back_populates="item")

class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(Integer, ForeignKey("content_items.id"))
    text = Column(String)
    topics = Column(JSON)  # List of extracted topics
    status = Column(String, default="pending")  # pending, approved, rejected
    index_id = Column(String, nullable=True)  # Chroma ID

    item = relationship("ContentItem", back_populates="chunks")
