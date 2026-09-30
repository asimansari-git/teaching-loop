from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class ReviewHighlightItem(BaseModel):
    element_id: str
    quoted_text: str
    question: str
    tag: Optional[str] = None

class ReviewSheetRequest(BaseModel):
    session_id: str
    student_id: Optional[int] = None
    highlights: List[ReviewHighlightItem]

class ReviewItem(BaseModel):
    element_id: str
    quoted_text: str
    question: str
    tag: Optional[str] = None
    pedagogical_answer: str

class ReviewSheetOut(BaseModel):
    id: int
    student_id: int
    session_id: str
    review_items: List[ReviewItem]
    markdown_report: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReportCreate(BaseModel):
    student_id: int
    session_id: str
    subject: Optional[str] = None
    content: Optional[str] = ""

class ReportOut(ReportCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CertificateCreate(BaseModel):
    session_id: str
    subject: Optional[str] = None

class CertificateOut(BaseModel):
    id: int
    student_id: int
    session_id: str
    subject: str
    verification_hash: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MicroCredentialOut(BaseModel):
    session_id: str
    subject: str
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    days_remaining: int
    status: str  # "Active", "Renewal Required", "Locked"
    tough_count: int
    tough_topics: List[str]
