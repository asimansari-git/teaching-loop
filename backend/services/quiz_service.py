import os
import json
import logging
from google import genai
from google.genai import types

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
            model="gemini-flash-latest",
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
    """Scores student responses locally against question answer keys and computes percentage and pass threshold."""
    score = 0
    questions = quiz_data.get("questions", []) if isinstance(quiz_data, dict) else []
    total = len(questions)
    
    for q in questions:
        qid = str(q.get("id"))
        if qid in user_answers and user_answers[qid] == q.get("correct_option_index"):
            score += 1
            
    percentage = (score / total) * 100 if total > 0 else 0
    passed = percentage >= 70
    
    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": passed
    }
