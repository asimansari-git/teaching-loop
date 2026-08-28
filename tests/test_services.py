import asyncio
import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from backend.services.quiz_service import evaluate_quiz_from_llm, get_fallback_quiz
from backend.services import session_service
from backend.schemas.chat import CreateSessionRequest, QuizCreate
from backend.schemas.auth import UserCreate

def test_evaluate_quiz_full_score():
    quiz_data = {
        "questions": [
            {"id": 1, "text": "Q1", "options": ["A", "B", "C", "D"], "correct_option_index": 0},
            {"id": 2, "text": "Q2", "options": ["A", "B", "C", "D"], "correct_option_index": 2},
            {"id": 3, "text": "Q3", "options": ["A", "B", "C", "D"], "correct_option_index": 1}
        ]
    }
    answers = {"1": 0, "2": 2, "3": 1}
    result = asyncio.run(evaluate_quiz_from_llm(quiz_data, answers))
    
    assert result["score"] == 3
    assert result["total"] == 3
    assert result["percentage"] == 100.0
    assert result["passed"] is True

def test_evaluate_quiz_partial_fail():
    quiz_data = {
        "questions": [
            {"id": 1, "text": "Q1", "options": ["A", "B", "C", "D"], "correct_option_index": 0},
            {"id": 2, "text": "Q2", "options": ["A", "B", "C", "D"], "correct_option_index": 2},
            {"id": 3, "text": "Q3", "options": ["A", "B", "C", "D"], "correct_option_index": 1}
        ]
    }
    # Only 1 of 3 correct = 33.3% -> Failed (< 70%)
    answers = {"1": 0, "2": 0, "3": 0}
    result = asyncio.run(evaluate_quiz_from_llm(quiz_data, answers))
    
    assert result["score"] == 1
    assert result["total"] == 3
    assert result["passed"] is False

def test_fallback_quiz_structure():
    quiz = get_fallback_quiz("Python", "easy")
    assert "questions" in quiz
    assert len(quiz["questions"]) >= 3
    for q in quiz["questions"]:
        assert "id" in q
        assert "text" in q
        assert "options" in q
        assert len(q["options"]) == 4
        assert "correct_option_index" in q
        assert 0 <= q["correct_option_index"] <= 3

def test_schemas_validation():
    # Chat request schema
    req = CreateSessionRequest(subject="Computer Science", topics=["Algorithms", "Data Structures"])
    assert req.subject == "Computer Science"
    assert len(req.topics) == 2

    # User create schema
    user_req = UserCreate(username="newuser", password="secretpassword", role="student")
    assert user_req.username == "newuser"
    assert user_req.role == "student"

    # Quiz create schema
    quiz_req = QuizCreate(session_id="60d5ec49f1b2c8b1f8e4e1a1", difficulty="hard")
    assert quiz_req.difficulty == "hard"
