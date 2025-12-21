from fastapi import APIRouter, Depends, HTTPException
from .. import auth, models, chat_service
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/start")
async def start_session(request: models.CreateSessionRequest, current_user: models.User = Depends(auth.get_current_user)):
    session_id = chat_service.create_session(
        username=current_user.username,
        subject=request.subject,
        topics=request.topics
    )
    return {"session_id": session_id}

@router.get("/sessions", response_model=List[models.SessionSummary])
async def get_sessions(current_user: models.User = Depends(auth.get_current_user)):
    return chat_service.get_user_sessions(current_user.username)

class MessageRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    response: str

@router.post("/{session_id}", response_model=ChatResponse)
async def send_message(session_id: str, request: MessageRequest, current_user: models.User = Depends(auth.get_current_user)):
    print(f"SESSION ID: {session_id}")
    try:
        response_text = await chat_service.generate_response(
            session_id=session_id,
            prompt=request.prompt,
            role=current_user.role
        )
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subjects/validate")
async def validate_subject(request: models.SubjectBase, current_user: models.User = Depends(auth.get_current_user)):
    normalized_data = await chat_service.normalize_subject(request.name)
    # Check if subject exists data
    # Ideally logic to merge user provided topics vs LLM topics
    return normalized_data

@router.post("/learning/plan")
async def create_learning_plan(request: models.LearningPlanCreate):
    # Retrieve session to get subject/topics if needed, or pass them in request? 
    # Request has session_id, we can fetch from Mongo
    session_history = chat_service.get_session_history(request.session_id)
    # Actually we just need subject/topics. fetch from db is safer.
    import pymongo
    db = chat_service.get_mongo_db() # Should expose this or add a getter
    from bson import ObjectId
    try:
        session = db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        subject = session.get("subject")
        topics = session.get("topics", [])
        
        plan_data = await chat_service.generate_learning_plan_from_llm(subject, topics)
        
        # Save Plan to SQL DB
        # ... We need DB session here. 
        # For simplicity in this step, let's just return the plan JSON. 
        # The frontend can store it in session_state or we save it to Mongo session doc?
        # Let's save to Mongo session doc for now as it bounds to the chat session tightly.
        
        db.chat_sessions.update_one(
            {"_id": ObjectId(request.session_id)},
            {"$set": {"learning_plan": plan_data}}
        )
        return plan_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/generate")
async def generate_quiz(request: models.QuizCreate):
    # Fetch session context
    import pymongo
    db = chat_service.get_mongo_db()
    from bson import ObjectId
    session = db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    subject = session.get("subject", "General") if session else "General"
    learning_plan = session.get("learning_plan", {})
    
    quiz_data = await chat_service.generate_quiz_from_llm(subject, request.difficulty, learning_plan)
    return quiz_data

@router.post("/quiz/submit")
async def submit_quiz(request: dict): # Simplified request
    # Expects { "quiz_data": ..., "user_answers": ... }
    result = await chat_service.evaluate_quiz_from_llm(request.get("quiz_data"), request.get("user_answers"))
    return result

@router.get("/{session_id}/history")
async def get_history(session_id: str, current_user: models.User = Depends(auth.get_current_user)):
    # Verify ownership? For now, we assume if you have ID you can read, 
    # but ideally check if session belongs to user or if user is teacher.
    # We will trust internal logic for now or add a quick check if needed.
    return chat_service.get_session_history(session_id)
