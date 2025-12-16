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
    try:
        response_text = await chat_service.generate_response(
            session_id=session_id,
            prompt=request.prompt,
            role=current_user.role
        )
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/history")
async def get_history(session_id: str, current_user: models.User = Depends(auth.get_current_user)):
    # Verify ownership? For now, we assume if you have ID you can read, 
    # but ideally check if session belongs to user or if user is teacher.
    # We will trust internal logic for now or add a quick check if needed.
    return chat_service.get_session_history(session_id)
