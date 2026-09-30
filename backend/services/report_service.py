import os
import logging
import json
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from google import genai
from google.genai import types
from ..database import get_mongo_db
from .session_service import get_session_history

MODEL = os.environ.get("GEMINI_MODEL")
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
        author = msg.get("author")
        parts_data = msg.get("parts", [])
        if isinstance(parts_data, list) and len(parts_data) > 0:
            text_content = parts_data[0] if isinstance(parts_data[0], str) else str(parts_data[0])
        elif isinstance(parts_data, str):
            text_content = parts_data
        else:
            text_content = ""
            
        if not text_content:
            continue

        if author == "teacher":
            transcript += f"TEACHER INTERVENTION (HIDDEN FROM STUDENT): {text_content}\n"
        elif author in ["teacher_model", "teacher_assistant", "model_to_teacher"]:
            transcript += f"AI TUTOR CONFIRMATION TO TEACHER: {text_content}\n"
        elif role == "user":
            transcript += f"STUDENT: {text_content}\n"
        else:
            transcript += f"AI TUTOR: {text_content}\n"
    
    learning_plan_info = ""
    if learning_plan:
        learning_plan_info = f"Learning Plan Status: {learning_plan.get('status', 'Active')}\nModules: {len(learning_plan.get('modules', []))}\n"

    analysis_prompt = f"""
    Analyze the following chat transcript between a student and an AI tutor for the session '{title}'.
    
    Context Information:
    {learning_plan_info}
    {extra_context}

    Note on Guidance: Lines labeled 'TEACHER INTERVENTION (HIDDEN FROM STUDENT)' represent pedagogical instructions provided discreetly by the teacher to guide the tutor. Evaluate how the student adapted to redirected concepts, but do NOT attribute teacher instructions to the student.

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
            model=MODEL,
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
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        return "Certificate Generation Failed."

async def compile_review_sheet(
    session_id: str,
    student_id: int,
    highlights: list,
    db_session
) -> dict:
    """Compiles an array of student highlights and doubt notes into a structured Q&A review sheet, saves a Report to SQL DB, and returns structured review sheet output."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    mongo_db = get_mongo_db()
    subject = "General"
    try:
        oid = ObjectId(session_id)
        session = mongo_db.chat_sessions.find_one({"_id": oid})
        if session:
            subject = session.get("subject", "General")
    except Exception as e:
        logger.warning(f"Error fetching session for review sheet compilation: {e}")

    highlights_summary = ""
    for i, item in enumerate(highlights):
        elem_id = item.get("element_id", "")
        quote = item.get("quoted_text", "")
        q = item.get("question", "")
        tag = item.get("tag", "Note")
        highlights_summary += f"{i+1}. [Tag: {tag}] [ID: {elem_id}] Quote: \"{quote}\" | Student Question: \"{q}\"\n"

    prompt = f"""
    You are an expert pedagogical AI tutor compiling a Review Sheet for a student on subject "{subject}".

    The student highlighted the following passages and raised questions/doubts:
    {highlights_summary}

    Instructions:
    1. For EACH highlighted item, generate a concise, targeted, authoritative pedagogical answer explaining the concept and answering the student's question.
    2. Synthesize a complete Markdown Review Sheet report with clear section headings, student quotes, questions, and pedagogical explanations.

    Return pure JSON with keys:
    - "answers": A list of strings, where answers[i] is the pedagogical answer corresponding to highlight item i.
    - "markdown_report": A formatted Markdown document containing the entire synthesized review sheet.
    """

    review_items = []
    markdown_report = ""

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
        data = json.loads(text.strip())
        answers = data.get("answers", [])
        markdown_report = data.get("markdown_report", "")

        for i, item in enumerate(highlights):
            ans = answers[i] if i < len(answers) else "Review the highlighted material for context."
            review_items.append({
                "element_id": item.get("element_id", ""),
                "quoted_text": item.get("quoted_text", ""),
                "question": item.get("question", ""),
                "tag": item.get("tag"),
                "pedagogical_answer": ans
            })
    except Exception as e:
        logger.error(f"Error generating review sheet with Gemini: {e}")
        markdown_report = f"# Review Sheet: {subject}\n\n"
        for i, item in enumerate(highlights):
            ans = "Review the highlighted text and discuss with your tutor."
            review_items.append({
                "element_id": item.get("element_id", ""),
                "quoted_text": item.get("quoted_text", ""),
                "question": item.get("question", ""),
                "tag": item.get("tag"),
                "pedagogical_answer": ans
            })
            markdown_report += f"### Passage {i+1} ({item.get('tag', 'Note')})\n> {item.get('quoted_text')}\n\n**Question:** {item.get('question')}\n\n**Answer:** {ans}\n\n"

    from ..models import Report
    report_subject = f"{subject} - Q&A Review Sheet"
    new_report = Report(
        student_id=student_id,
        subject=report_subject,
        content=markdown_report
    )
    db_session.add(new_report)
    db_session.commit()
    db_session.refresh(new_report)

    return {
        "id": new_report.id,
        "student_id": student_id,
        "session_id": session_id,
        "review_items": review_items,
        "markdown_report": markdown_report,
        "created_at": new_report.created_at
    }

async def get_micro_credential_status(session_id: str, student_id: int, db_session) -> dict:
    """Calculates living micro-credential status with 3-month expiration countdown and Tough telemetry flags."""
    from ..models import Certificate, Quiz

    mongo_db = get_mongo_db()
    subject = "General"
    highlights = []
    try:
        oid = ObjectId(session_id)
        session = mongo_db.chat_sessions.find_one({"_id": oid})
        if session:
            subject = session.get("subject", "General")
            highlights = session.get("highlights", [])
    except Exception as e:
        logger.warning(f"Error fetching session for micro-credential status: {e}")

    # Tough telemetry analysis
    tough_highlights = [h for h in highlights if h.get("tag") == "Tough"]
    tough_count = len(tough_highlights)
    tough_topics = [h.get("quoted_text", "") for h in tough_highlights if h.get("quoted_text")]

    # Check Certificate or Quiz Completion in SQL DB
    cert = db_session.query(Certificate).filter(
        Certificate.student_id == student_id,
        Certificate.session_id == str(session_id)
    ).first()

    issued_at = None
    if cert:
        issued_at = cert.created_at
    else:
        # Check if hard quiz was passed
        hard_quiz = db_session.query(Quiz).filter(
            Quiz.session_id == str(session_id),
            Quiz.difficulty == "hard",
            Quiz.passed == True
        ).first()
        if hard_quiz:
            issued_at = hard_quiz.created_at

    now = datetime.now(timezone.utc)
    if issued_at:
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        expires_at = issued_at + timedelta(days=90)  # 3 months renewal cycle
        days_remaining = max(0, (expires_at - now).days)
        status = "Active" if days_remaining > 0 else "Renewal Required"
    else:
        expires_at = None
        days_remaining = 0
        status = "Locked"

    return {
        "session_id": session_id,
        "subject": subject,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "days_remaining": days_remaining,
        "status": status,
        "tough_count": tough_count,
        "tough_topics": tough_topics
    }
