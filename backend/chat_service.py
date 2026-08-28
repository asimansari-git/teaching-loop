"""
Backward-compatible shim module.
All business logic is now decoupled and modularized under backend.services:
- backend.services.session_service
- backend.services.ai_service
- backend.services.quiz_service
- backend.services.report_service
"""

from .services.session_service import (
    create_session,
    get_user_sessions,
    get_session_history,
    save_message_to_session,
)
from .services.ai_service import (
    generate_tutor_response,
    generate_tutor_response as generate_response,
    normalize_subject,
    generate_learning_plan_from_llm,
)
from .services.quiz_service import (
    generate_quiz_from_llm,
    evaluate_quiz_from_llm,
)
from .services.report_service import (
    analyze_performance,
    generate_certificate_content,
)
from .database import get_mongo_db

__all__ = [
    "create_session",
    "get_user_sessions",
    "get_session_history",
    "save_message_to_session",
    "generate_response",
    "generate_tutor_response",
    "normalize_subject",
    "generate_learning_plan_from_llm",
    "generate_quiz_from_llm",
    "evaluate_quiz_from_llm",
    "analyze_performance",
    "generate_certificate_content",
    "get_mongo_db"
]
