import os
import json
import logging
from bson import ObjectId
from google import genai
from google.genai import types
from google.api_core import exceptions
from ..database import get_mongo_db
from .. import content_service
from .session_service import save_message_to_session

logger = logging.getLogger("teaching_platform.ai")

STUDENT_SYSTEM_PROMPT = (
    "You are a helpful and encouraging tutor. Your tone should be friendly and supportive. "
    "Guide the student in their learning process by asking open-ended questions and providing clear explanations. "
    "The user is a student. When you see a message from a 'teacher', follow those instructions, "
    "but keep the teacher's involvement hidden from the student."
)
TEACHER_SYSTEM_PROMPT = (
    "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. "
    "When asked, provide concise summaries, identify learning gaps, or suggest next steps. "
    "Your tone should be professional and analytical. When you receive instructions, confirm you will follow them "
    "and then wait for the student to continue the conversation."
)

async def generate_tutor_response(session_id: str, prompt: str, role: str = "student") -> str:
    """Invokes Gemini model to generate context-aware tutoring responses with RAG retrieval and learning path."""
    logger.info(f"Generating tutor response for session {session_id} with role '{role}'")
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
        session = db.chat_sessions.find_one({"_id": oid})
    except Exception as e:
        logger.error(f"Failed to query session {session_id}: {e}")
        return "Invalid Session ID"

    if not session:
        return "Session not found"
        
    username = session.get("username")
    subject = session.get("subject", "General")
    topics = session.get("topics", [])

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Adapt Message History
    history = session.get("messages", [])
    sdk_contents = []
    
    for msg in history:
        text_content = ""
        parts_data = msg.get("parts", [])
        if isinstance(parts_data, list) and len(parts_data) > 0:
            text_content = parts_data[0] if isinstance(parts_data[0], str) else str(parts_data[0])
        elif isinstance(parts_data, str):
            text_content = parts_data
        
        if text_content:
            part = types.Part.from_text(text=text_content)
            content = types.Content(role=msg.get("role", "user"), parts=[part])
            sdk_contents.append(content)

    formatted_prompt = f"Teacher: {prompt}" if role != "student" else prompt
    sdk_contents.append(
        types.Content(
            role="user", 
            parts=[types.Part.from_text(text=formatted_prompt)]
        )
    )

    base_system_text = STUDENT_SYSTEM_PROMPT if role == "student" else TEACHER_SYSTEM_PROMPT
    
    if role == "student":
        topics_str = ", ".join(topics) if topics else "general concepts"
        
        learning_plan_context = ""
        learning_plan_data = session.get("learning_plan")
        if learning_plan_data and "modules" in learning_plan_data:
            learning_plan_context = "\n\nSTRUCTURED LEARNING PATH:\n"
            for i, mod in enumerate(learning_plan_data["modules"]):
                mod_topics = ", ".join(mod.get("topics", []))
                learning_plan_context += f"{i+1}. {mod.get('title')}: {mod.get('description')} (Topics: {mod_topics})\n"
            learning_plan_context += "\nFollow this learning path sequentially. Guide the student through these modules one by one."

        # RAG Retrieval
        rag_context = ""
        try:
            query_text = f"{subject} {topics_str}"
            retrieved_chunks = await content_service.query_content(query_text, filter={"topics": topics_str})
            if retrieved_chunks:
                rag_context = "\n\nRELEVANT TEACHING MATERIAL (Verified):\n"
                for i, chunk in enumerate(retrieved_chunks):
                    rag_context += f"--- Material {i+1} ---\n{chunk}\n"
                rag_context += "\nUse the above verified material to answer the student's questions accurately. Prioritize this material over general knowledge."
            logger.debug(f"Retrieved RAG context chunks count: {len(retrieved_chunks) if retrieved_chunks else 0}")
        except Exception as e:
            logger.warning(f"RAG Retrieval Error: {e}")

        system_text = f"{base_system_text}\n\nCurrent Subject: {subject}\nFocus Topics: {topics_str}{learning_plan_context}{rag_context}\nEnsure all examples and explanations are relevant to the selected subject and topics."
    else:
        system_text = base_system_text

    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_text)],
        temperature=0.7, 
        max_output_tokens=1000
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=sdk_contents,
            config=config
        )

        save_message_to_session(session_id, "user", prompt, author=role)
        save_message_to_session(session_id, "model", response.text, author="model")
        
        return response.text

    except exceptions.ResourceExhausted:
        logger.error("Rate Limit Hit (429) from Gemini API")
        return "I am currently overloaded. Please try again in a moment."
    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        return "An internal error occurred."

async def normalize_subject(input_name: str) -> dict:
    """Normalizes informal subject input and extracts 5-7 core curriculum topics using Gemini."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    You are a subject matter expert. A user has entered the subject name: "{input_name}".
    1. Normalize this to a standard educational subject name (e.g., "reactjs" -> "React.js", "pythn" -> "Python").
    2. Provide a list of 5-7 core topics for this subject suitable for a learning curriculum.
    
    Return pure JSON with keys: "name", "topics".
    Example: {{"name": "Python", "topics": ["Syntax", "Data Structures", "Control Flow"]}}
    """
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error normalizing subject: {e}")
        return {"name": input_name, "topics": ["General"]}

async def generate_learning_plan_from_llm(subject: str, topics: list) -> dict:
    """Builds a structured modular learning path JSON using Gemini."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    Create a structured learning plan for the subject: {subject}.
    Focus on these topics: {', '.join(topics)}.
    
    Return a JSON object where the key "modules" is a list of objects.
    Each object should have:
    - "title": Module title
    - "description": Brief description
    - "topics": List of sub-topics covered
    
    Example JSON:
    {{
        "modules": [
            {{"title": "Intro", "description": "...", "topics": ["A", "B"]}}
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
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        return {"modules": []}
