import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from ..database import get_mongo_db

logger = logging.getLogger("teaching_platform.session")

def get_now():
    return datetime.now(timezone.utc)

def create_session(username: str, subject: str, topics: list[str]) -> str:
    """Creates a new learning chat session document in MongoDB."""
    db = get_mongo_db()
    title = f"{subject} - {', '.join(topics)}" if topics else f"{subject} - General"
    now = get_now()
    
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

def get_user_sessions(username: str) -> list[dict]:
    """Retrieves all chat sessions for a specific user, sorted by last updated."""
    db = get_mongo_db()
    cursor = db.chat_sessions.find({"username": username}).sort("last_updated", -1)
    sessions = []
    for doc in cursor:
        subject = doc.get("subject", "General")
        topics = doc.get("topics", [])
        title = doc.get("title")
        if not title:
            title = f"{subject} - {', '.join(topics)}" if topics else f"{subject} - General"
        sessions.append({
            "session_id": str(doc["_id"]),
            "title": title,
            "created_at": doc.get("created_at"),
            "subject": subject,
            "topics": topics
        })
    return sessions

def get_session_history(session_id: str) -> dict:
    """Retrieves message history and structured learning plan for a session ID."""
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
    except (InvalidId, Exception) as e:
        logger.warning(f"Invalid session ID format: {session_id} ({e})")
        return {"messages": [], "learning_plan": {}}
    
    session = db.chat_sessions.find_one({"_id": oid})
    if session:
        subject = session.get("subject", "General")
        topics = session.get("topics", [])
        title = session.get("title")
        if not title:
            title = f"{subject} - {', '.join(topics)}" if topics else f"{subject} - General"
        return {
            "messages": session.get("messages", []),
            "learning_plan": session.get("learning_plan", {}),
            "subject": subject,
            "topics": topics,
            "title": title
        }
    return {"messages": [], "learning_plan": {}}

def save_message_to_session(session_id: str, role: str, content: str, author: str = None, visible_to_student: bool = True):
    """Persists a new message turn into a MongoDB session document."""
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
    except (InvalidId, Exception) as e:
        logger.error(f"Cannot save message with invalid ObjectId {session_id}: {e}")
        return

    now = get_now()
    message = {
        "role": role,
        "parts": [content],
        "timestamp": now,
        "visible_to_student": visible_to_student
    }
    if author:
        message["author"] = author
        
    db.chat_sessions.update_one(
        {"_id": oid},
        {
            "$push": {"messages": message},
            "$set": {"last_updated": now}
        }
    )
