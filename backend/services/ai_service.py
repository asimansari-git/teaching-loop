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

MODEL = os.environ.get("GEMINI_MODEL")

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
            model=MODEL, 
            contents=sdk_contents,
            config=config
        )

        if role == "teacher":
            save_message_to_session(session_id, "user", prompt, author="teacher", visible_to_student=False)
            save_message_to_session(session_id, "model", response.text, author="teacher_model", visible_to_student=False)
        else:
            save_message_to_session(session_id, "user", prompt, author="student", visible_to_student=True)
            save_message_to_session(session_id, "model", response.text, author="model", visible_to_student=True)
        
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
            model=MODEL,
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
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        return {"modules": []}

async def generate_textbook_article(subject: str, topics: list, topic_override: str = None) -> dict:
    """Generates a structured Socratic living textbook article with stable paragraph (p-X) and sentence (s-X-Y) DOM IDs using Gemini."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    target_topics = [topic_override] if topic_override else topics
    topics_str = ", ".join(target_topics) if target_topics else "General"

    prompt = f"""
    You are an expert educational textbook author.
    Write a comprehensive living textbook article for subject: "{subject}" focusing on: {topics_str}.

    Requirements for output JSON:
    Return a pure JSON object with the following fields:
    - "title": A clear article title string
    - "topics": List of string topics covered
    - "markdown_content": Clean Markdown text where:
      1. Headings use standard Markdown (e.g. # Header, ## Subheader).
      2. EVERY paragraph is wrapped with an HTML paragraph element having a stable ID like <p id="p-1">...</p>, <p id="p-2">...</p>, etc.
      3. EVERY sentence inside each paragraph is wrapped with a span element having a sentence ID like <span id="s-1-1">Sentence text...</span> <span id="s-1-2">Second sentence...</span>.
         Example: <p id="p-1"><span id="s-1-1">Python is a dynamic programming language.</span> <span id="s-1-2">It supports multiple paradigms.</span></p>

    Example JSON response structure:
    {{
      "title": "Introduction to Python Programming",
      "topics": ["Syntax", "Variables"],
      "markdown_content": "# Introduction\\n\\n<p id=\\"p-1\\"><span id=\\"s-1-1\\">Python is easy to learn.</span> <span id=\\"s-1-2\\">It is widely used in AI.</span></p>\\n\\n## Variables\\n\\n<p id=\\"p-2\\"><span id=\\"s-2-1\\">Variables store data.</span> <span id=\\"s-2-2\\">They do not need type declarations.</span></p>"
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
        data = json.loads(text.strip())
        return {
            "title": data.get("title", f"{subject} Textbook Article"),
            "topics": data.get("topics", target_topics),
            "markdown_content": data.get("markdown_content", "")
        }
    except Exception as e:
        logger.error(f"Error generating textbook article: {e}")
        fallback_content = f"# {subject}\n\n<p id=\"p-1\"><span id=\"s-1-1\">Welcome to {subject}.</span> <span id=\"s-1-2\">This article covers {topics_str}.</span></p>"
        return {
            "title": f"{subject} Article",
            "topics": target_topics,
            "markdown_content": fallback_content
        }

async def locate_socratic_hint(question: str, article_text: str) -> dict:
    """Evaluates a student's question against textbook article text and returns target DOM ID, quote, parent context, and Socratic reasoning hint without spoiling direct answers."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    prompt = f"""
    You are a Socratic tutor analyzing a student's question regarding a textbook article.

    Student Question / Doubt:
    "{question}"

    Textbook Article Content (with element IDs):
    {article_text[:30000]}

    Instructions:
    1. Locate the specific sentence or paragraph in the article that addresses or provides context for the student's question.
    2. Identify its exact element ID (e.g. "s-2-1" for a sentence span, or "p-2" for a paragraph).
    3. Identify the parent context paragraph ID (e.g. "p-2").
    4. Extract the exact sentence/passage text as "highlight_quote".
    5. Formulate a "socratic_hint": A concise 1-2 sentence directional reasoning hint that steers the learner's attention to think about the concept, WITHOUT giving away or spoiling the direct answer.

    Return a pure JSON object with keys:
    - "target_element_id": string (e.g., "s-2-1")
    - "highlight_quote": string (exact quoted text)
    - "context_scope": string (parent paragraph ID e.g. "p-2")
    - "socratic_hint": string (directional hint)
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
        data = json.loads(text.strip())
        return {
            "target_element_id": data.get("target_element_id", "p-1"),
            "highlight_quote": data.get("highlight_quote", ""),
            "context_scope": data.get("context_scope", "p-1"),
            "socratic_hint": data.get("socratic_hint", "Consider re-reading the highlighted section to find the core concept.")
        }
    except Exception as e:
        logger.error(f"Error locating socratic hint: {e}")
        return {
            "target_element_id": "p-1",
            "highlight_quote": "",
            "context_scope": "p-1",
            "socratic_hint": "Review the highlighted paragraph carefully and reflect on how it connects to your question."
        }
