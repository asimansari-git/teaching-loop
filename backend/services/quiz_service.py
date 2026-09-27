import os
import json
import logging
from google import genai
from google.genai import types

MODEL = os.environ.get("GEMINI_MODEL")

logger = logging.getLogger("teaching_platform.quiz")

def get_fallback_quiz(subject: str, difficulty: str) -> dict:
    """Provides deterministic high-quality fallback questions if LLM fails or hits rate limits."""
    return {
        "questions": [
            {
                "id": 1,
                "text": f"What is a fundamental concept when learning {subject}?",
                "options": [
                    f"Understanding core principles and syntax of {subject}",
                    "Memorizing code without understanding logic",
                    "Avoiding problem breakdown and debugging",
                    "Skipping documentation completely"
                ],
                "correct_option_index": 0
            },
            {
                "id": 2,
                "text": f"Which of the following represents a best practice in {subject}?",
                "options": [
                    "Writing modular, readable, and testable code",
                    "Hardcoding secrets in source files",
                    "Ignoring error messages and stack traces",
                    "Disabling version control"
                ],
                "correct_option_index": 0
            },
            {
                "id": 3,
                "text": f"At {difficulty} level in {subject}, how should complex problems be approached?",
                "options": [
                    "Decompose into smaller sub-problems step by step",
                    "Guess solutions randomly until one works",
                    "Skip tests and deploy directly to production",
                    "Ignore edge cases"
                ],
                "correct_option_index": 0
            }
        ]
    }

def strip_answers(quiz_data: dict) -> dict:
    """Strips correct_option_index from quiz questions before sending to client."""
    if not isinstance(quiz_data, dict):
        return quiz_data
    safe_data = dict(quiz_data)
    questions = quiz_data.get("questions", [])
    safe_questions = []
    for q in questions:
        q_copy = dict(q)
        q_copy.pop("correct_option_index", None)
        safe_questions.append(q_copy)
    safe_data["questions"] = safe_questions
    return safe_data

async def generate_quiz_from_llm(subject: str, difficulty: str, context: str = "") -> dict:
    """Generates an adaptive multiple-choice quiz using Gemini with automatic JSON parsing."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    Create a {difficulty} level quiz for {subject}.
    Context: {context} (If any).

    Return a JSON object with:
    "questions": List of objects:
        - "id": int
        - "text": question text
        - "options": list of 4 options
        - "correct_option_index": int (0-3)

    Example:
    {{
        "questions": [
           {{"id": 1, "text": "Q1", "options": ["A","B","C","D"], "correct_option_index": 0}}
        ]
    }}
    """
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict) and "questions" in parsed and len(parsed["questions"]) > 0:
            return parsed
        elif isinstance(parsed, list) and len(parsed) > 0:
            return {"questions": parsed}
    except Exception as e:
        logger.error(f"Error generating quiz from LLM: {e}")

    return get_fallback_quiz(subject, difficulty)

async def evaluate_quiz_from_llm(quiz_data: dict, user_answers: dict) -> dict:
    """Scores student responses locally against question answer keys and computes percentage, pass threshold, and question review."""
    score = 0
    questions = quiz_data.get("questions", []) if isinstance(quiz_data, dict) else []
    total = len(questions)
    review = []
    
    for q in questions:
        qid = str(q.get("id"))
        correct_idx = q.get("correct_option_index")
        user_choice_raw = user_answers.get(qid)
        try:
            user_choice_idx = int(user_choice_raw) if user_choice_raw is not None else None
        except (ValueError, TypeError):
            user_choice_idx = None

        is_correct = (user_choice_idx is not None and user_choice_idx == correct_idx)
        if is_correct:
            score += 1
            
        options = q.get("options", [])
        user_choice_text = options[user_choice_idx] if (user_choice_idx is not None and 0 <= user_choice_idx < len(options)) else None
        correct_choice_text = options[correct_idx] if (correct_idx is not None and 0 <= correct_idx < len(options)) else None

        review.append({
            "id": q.get("id"),
            "text": q.get("text"),
            "options": options,
            "user_choice_index": user_choice_idx,
            "user_choice_text": user_choice_text,
            "correct_option_index": correct_idx,
            "correct_option_text": correct_choice_text,
            "is_correct": is_correct
        })
            
    percentage = (score / total) * 100 if total > 0 else 0
    passed = percentage >= 70
    
    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": passed,
        "review": review
    }
