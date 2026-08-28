import os
import logging
from bson import ObjectId
from google import genai
from google.genai import types
from ..database import get_mongo_db
from .session_service import get_session_history

logger = logging.getLogger("teaching_platform.report")

async def analyze_performance(session_id: str, extra_context: str = "") -> str:
    """Analyzes a full chat transcript and quiz context to generate a comprehensive student evaluation report."""
    session_data = get_session_history(session_id)
    history = session_data.get("messages", [])
    if not history:
        return "No chat history found for this session."
    
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
        session = db.chat_sessions.find_one({"_id": oid})
        title = session.get("title", "Unknown Session") if session else "Unknown Session"
        learning_plan = session.get("learning_plan", {}) if session else {}
    except Exception as e:
        logger.warning(f"Error querying session for analysis: {e}")
        title = "Unknown Session"
        learning_plan = {}
    
    transcript = ""
    for msg in history:
        role = msg.get("role", "user")
        parts_data = msg.get("parts", [])
        if isinstance(parts_data, list) and len(parts_data) > 0:
            text_content = parts_data[0] if isinstance(parts_data[0], str) else str(parts_data[0])
        elif isinstance(parts_data, str):
            text_content = parts_data
        else:
            text_content = ""
            
        transcript += f"{role.upper()}: {text_content}\n"
    
    learning_plan_info = ""
    if learning_plan:
        learning_plan_info = f"Learning Plan Status: {learning_plan.get('status', 'Active')}\nModules: {len(learning_plan.get('modules', []))}\n"

    analysis_prompt = f"""
    Analyze the following chat transcript between a student and an AI tutor for the session '{title}'.
    
    Context Information:
    {learning_plan_info}
    {extra_context}

    Provide a detailed performance report including:
    1. Strengths
    2. Weaknesses / Learning Gaps
    3. Quiz Performance Analysis (if available)
    4. Recommended Next Steps
    5. Overall Proficiency Level

    Transcript:
    {transcript}
    """

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=analysis_prompt)]
                )
            ],
            config=types.GenerateContentConfig(temperature=0.5)
        )
        return response.text

    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        return "ERROR - Unable to generate performance report at this time."

async def generate_certificate_content(student_name: str, subject: str, date_str: str, quiz_summary: str) -> str:
    """Generates a structured formal completion certificate in Markdown."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    Generate a formal certificate of completion for:
    Student: {student_name}
    Subject: {subject}
    Date: {date_str}
    
    Achievements:
    {quiz_summary}
    
    The output should be formatted as a beautiful Markdown certificate. 
    Use headers, bold text, and separator lines to make it look professional.
    Include a congratulatory message and a "Verified by AI Tutor" footer.
    """
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        return "Certificate Generation Failed."
