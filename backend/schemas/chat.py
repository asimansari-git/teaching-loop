from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any, Dict

class CreateSessionRequest(BaseModel):
    subject: str
    topics: List[str]

class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    subject: str
    topics: List[str] = []

class SubjectBase(BaseModel):
    name: str
    topics: List[str]

class SubjectOut(SubjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LearningPlanCreate(BaseModel):
    session_id: str
    plan_content: Optional[Dict[str, Any]] = None

class QuizCreate(BaseModel):
    session_id: str
    difficulty: str
    questions: Optional[Any] = None

class QuizSubmit(BaseModel):
    quiz_id: Optional[int] = None
    quiz_data: Optional[Dict[str, Any]] = None
    user_answers: Dict[str, Any]

class TextbookGenerateRequest(BaseModel):
    session_id: str
    topic_override: Optional[str] = None

class TextbookArticleOut(BaseModel):
    session_id: str
    title: str
    topics: List[str]
    markdown_content: str
    generated_at: Optional[datetime] = None

class SocraticHintRequest(BaseModel):
    session_id: str
    question: str
    article_text: Optional[str] = None

class SocraticHintOut(BaseModel):
    target_element_id: str
    highlight_quote: str
    context_scope: str
    socratic_hint: str

class HighlightCreate(BaseModel):
    element_id: Optional[str] = "selection"
    quoted_text: str
    question: Optional[str] = None
    tag: str = "Note"  # "Tough", "Rewind", "Note", "Ask Doubt", "Hint"

class HighlightOut(BaseModel):
    element_id: Optional[str] = "selection"
    quoted_text: str
    question: Optional[str] = None
    tag: str = "Note"
    created_at: datetime

class RefresherQuizRequest(BaseModel):
    session_id: str
