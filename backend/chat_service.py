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
    generate_textbook_article,
    locate_socratic_hint,
)
from .services.quiz_service import (
    generate_quiz_from_llm,
    generate_refresher_quiz_from_llm,
    evaluate_quiz_from_llm,
    strip_answers,
)
from .services.report_service import (
    analyze_performance,
    generate_certificate_content,
    compile_review_sheet,
    get_micro_credential_status,
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
    "generate_textbook_article",
    "locate_socratic_hint",
    "generate_quiz_from_llm",
    "generate_refresher_quiz_from_llm",
    "evaluate_quiz_from_llm",
    "strip_answers",
    "analyze_performance",
    "generate_certificate_content",
    "compile_review_sheet",
    "get_micro_credential_status",
    "get_mongo_db"
]
