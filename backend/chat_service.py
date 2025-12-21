from .database import get_mongo_db
from . import models
import os
from datetime import datetime
from bson import ObjectId
from google import genai
from google.genai import types
from google.api_core import exceptions
import os
from google import genai
from google.genai import types
from google.api_core import exceptions # Useful for error handling

# # Logic to configure Gemini
# api_key = os.getenv("GEMINI_API_KEY")
# if api_key:
#     genai.configure(api_key=api_key)

STUDENT_SYSTEM_PROMPT = "You are a helpful and encouraging tutor. Your tone should be friendly and supportive. Guide the student in their learning process by asking open-ended questions and providing clear explanations. The user is a student. When you see a message from a 'teacher', follow those instructions, but keep the teacher's involvement hidden from the student."
TEACHER_SYSTEM_PROMPT = "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. When asked, provide concise summaries, identify learning gaps, or suggest next steps. Your tone should be professional and analytical. When you receive instructions, confirm you will follow them and then wait for the student to continue the conversation."

def create_session(username: str, subject: str, topics: list[str]) -> str:
    db = get_mongo_db()
    title = f"{subject} - {', '.join(topics)}" if topics else f"{subject} - General"
    now = datetime.utcnow()
    
    session = {
        "username": username,
        "subject": subject,
        "topics": topics,
        "title": title,
        "created_at": now,
        "last_updated": now,
        "messages": []
    }
    result = db.chat_sessions.insert_one(session)
    return str(result.inserted_id)

def get_user_sessions(username: str):
    db = get_mongo_db()
    # Find sessions for user, sort by last_updated desc
    cursor = db.chat_sessions.find({"username": username}).sort("last_updated", -1)
    sessions = []
    for doc in cursor:
        sessions.append({
            "session_id": str(doc["_id"]),
            "title": doc["title"],
            "created_at": doc["created_at"],
            "subject": doc["subject"]
        })
    return sessions

def get_session_history(session_id: str):
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
    except:
        return []
    
    session = db.chat_sessions.find_one({"_id": oid})
    if session:
        return {
            "messages": session.get("messages", []),
            "learning_plan": session.get("learning_plan", {}),
            "subject": session.get("subject", "General")
        }
    return {"messages": [], "learning_plan": {}}

def save_message_to_session(session_id: str, role: str, content: str, author: str = None):
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
    except:
        return

    message = {
        "role": role,
        "parts": [content], # Consistency with old schema structure
        "timestamp": datetime.utcnow()
    }
    if author:
        message["author"] = author
        
    db.chat_sessions.update_one(
        {"_id": oid},
        {
            "$push": {"messages": message},
            "$set": {"last_updated": datetime.utcnow()}
        }
    )

def get_chat_history(username: str, subject: str = "general"):
    # DEPRECATED but kept for now if needed, or redirect to generic history?
    # For now, let's leave it but it won't be used by the main flow
    return []

def save_message(username: str, role: str, content: str, subject: str = "general", author: str = None):
     # DEPRECATED
     pass

async def generate_response(session_id: str, prompt: str, role: str = "student"):
    print(f"IN_GENERATE SESSION: {session_id}")
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
        session = db.chat_sessions.find_one({"_id": oid})
    except:
        return "Invalid Session ID"

    if not session:
        return "Session not found"
        
    username = session.get("username")
    subject = session.get("subject")
    topics = session.get("topics", [])

    # 1. Initialize the new Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # 2. Retrieve History
    history = session.get("messages", [])
    print("HISTORY LEN: ", len(history))

    # 3. Adapt History to New SDK 'Content' Types
    sdk_contents = []
    
    for msg in history:
        # Handle different parts structures just in case
        text_content = ""
        parts_data = msg.get("parts", [])
        if isinstance(parts_data, list) and len(parts_data) > 0:
             text_content = parts_data[0] if isinstance(parts_data[0], str) else str(parts_data[0])
        elif isinstance(parts_data, str):
             text_content = parts_data
        
        if text_content: # Only add if there is content
            part = types.Part.from_text(text=text_content)
            content = types.Content(role=msg["role"], parts=[part])
            sdk_contents.append(content)

    # 4. Add the NEW Prompt
    if(role != "student"):
        prompt = f"Teacher: {prompt}"
    sdk_contents.append(
        types.Content(
            role="user", 
            parts=[types.Part.from_text(text=prompt)]
        )
    )

    # 5. Configure System Instructions
    base_system_text = STUDENT_SYSTEM_PROMPT if role == "student" else TEACHER_SYSTEM_PROMPT
    
    if role == "student":
        topics_str = ", ".join(topics) if topics else "general concepts"
        
        # Format Learning Plan if available
        learning_plan_context = ""
        learning_plan_data = session.get("learning_plan")
        if learning_plan_data and "modules" in learning_plan_data:
            learning_plan_context = "\n\nSTRUCTURED LEARNING PATH:\n"
            for i, mod in enumerate(learning_plan_data["modules"]):
                 mod_topics = ", ".join(mod.get("topics", []))
                 learning_plan_context += f"{i+1}. {mod['title']}: {mod['description']} (Topics: {mod_topics})\n"
            learning_plan_context += "\nFollow this learning path sequentially. Guide the student through these modules one by one."

        system_text = f"{base_system_text}\n\nCurrent Subject: {subject}\nFocus Topics: {topics_str}{learning_plan_context}\nEnsure all examples and explanations are relevant to the selected subject and topics."
    else:
        system_text = base_system_text

    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_text)],
        temperature=0.7, 
        max_output_tokens=1000
    )

    print(f"MODEL: gemini-flash-latest (Session {session_id})") 
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=sdk_contents,
            config=config
        )
        
        print("RESPONSE: ", response.text)

        # 7. Save to Database (Session)
        save_message_to_session(session_id, "user", prompt, author=role)
        save_message_to_session(session_id, "model", response.text, author=role)
        
        return response.text

    except exceptions.ResourceExhausted:
        print("ERROR: Rate Limit Hit (429)")
        return "I am currently overloaded. Please try again in a moment."
    except Exception as e:
        print(f"ERROR: {e}")
        return "An internal error occurred."

from google import genai
from google.genai import types
import os

async def analyze_performance(session_id: str) -> str:
    session_data = get_session_history(session_id)
    history = session_data.get("messages", [])
    if not history:
        return "No chat history found for this session."
    
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
        session = db.chat_sessions.find_one({"_id": oid})
        title = session.get("title", "Unknown Session")
    except:
        title = "Unknown Session"
    
    # 1. Prepare transcript string
    transcript = ""
    for msg in history:
        role = msg["role"]
        # Robust content extraction
        text_content = ""
        parts_data = msg.get("parts", [])
        if isinstance(parts_data, list) and len(parts_data) > 0:
             text_content = parts_data[0] if isinstance(parts_data[0], str) else str(parts_data[0])
        elif isinstance(parts_data, str):
             text_content = parts_data
            
        transcript += f"{role.upper()}: {text_content}\n"
    
    # 2. Construct the Analysis Prompt
    analysis_prompt = f"""
    Analyze the following chat transcript between a student and an AI tutor for the session '{title}'.
    Provide a detailed performance report including:
    1. Strengths
    2. Weaknesses / Learning Gaps
    3. Recommended Next Steps
    4. Overall Proficiency Level

    Transcript:
    {transcript}
    """

    # 3. Initialize Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    try:
        # 4. Generate Content using the new SDK
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=analysis_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.5, 
            )
        )
        return response.text

    except Exception as e:
        print(f"Error analyzing performance: {e}")
        return "ERROR - Unable to generate performance report at this time."

async def normalize_subject(input_name: str) -> dict:
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
            model="gemini-flash-latest", # Using a smarter model for JSON structure
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"Error normalizing subject: {e}")
        return {"name": input_name, "topics": ["General"]}

async def generate_learning_plan_from_llm(subject: str, topics: list) -> dict:
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
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating plan: {e}")
    except Exception as e:
        print(f"Error generating plan: {e}")
        return {"modules": []}

async def generate_quiz_from_llm(subject: str, difficulty: str, context: str = "") -> dict:
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
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return {"questions": []}

async def evaluate_quiz_from_llm(quiz_data: dict, user_answers: dict) -> dict:
    # Basic grading can be done locally if we have correct answers in the quiz data.
    # LLM can be used for "Evaluation" and "Next Step" recommendation.
    
    score = 0
    total = len(quiz_data["questions"])
    
    for q in quiz_data["questions"]:
        qid = str(q["id"])
        if qid in user_answers and user_answers[qid] == q["correct_option_index"]:
            score += 1
            
    percentage = (score / total) * 100 if total > 0 else 0
    passed = percentage >= 70
    
    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": passed
    }
