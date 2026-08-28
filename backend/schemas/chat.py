from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any

class CreateSessionRequest(BaseModel):
    subject: str
    topics: List[str]

class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    subject: str

class SubjectBase(BaseModel):
    name: str
    topics: List[str]

class SubjectOut(SubjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LearningPlanCreate(BaseModel):
    session_id: str
    plan_content: dict

class QuizCreate(BaseModel):
    session_id: str
    difficulty: str
    questions: Optional[Any] = None
