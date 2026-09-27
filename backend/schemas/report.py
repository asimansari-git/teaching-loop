from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

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
