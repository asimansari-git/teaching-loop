import logging
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from ..database import get_mongo_db

logger = logging.getLogger("teaching_platform.session")

def create_session(username: str, subject: str, topics: list[str]) -> str:
    """Creates a new learning chat session document in MongoDB."""
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

def get_user_sessions(username: str) -> list[dict]:
    """Retrieves all chat sessions for a specific user, sorted by last updated."""
    db = get_mongo_db()
    cursor = db.chat_sessions.find({"username": username}).sort("last_updated", -1)
    sessions = []
    for doc in cursor:
        sessions.append({
            "session_id": str(doc["_id"]),
            "title": doc.get("title", "Untitled Session"),
            "created_at": doc.get("created_at"),
            "subject": doc.get("subject", "General")
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
        return {
            "messages": session.get("messages", []),
            "learning_plan": session.get("learning_plan", {}),
            "subject": session.get("subject", "General")
        }
    return {"messages": [], "learning_plan": {}}

def save_message_to_session(session_id: str, role: str, content: str, author: str = None):
    """Persists a new message turn into a MongoDB session document."""
    db = get_mongo_db()
    try:
        oid = ObjectId(session_id)
    except (InvalidId, Exception) as e:
        logger.error(f"Cannot save message with invalid ObjectId {session_id}: {e}")
        return

    message = {
        "role": role,
        "parts": [content],
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
