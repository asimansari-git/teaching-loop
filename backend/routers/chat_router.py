from fastapi import APIRouter, Depends, HTTPException
from .. import auth, models, chat_service
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ChatRequest(BaseModel):
    prompt: str
    subject: str = "general"
    topics: List[str] = []

class ChatResponse(BaseModel):
    response: str

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: models.User = Depends(auth.get_current_user)):
    print("IN_CHAT")
    try:
        response_text = await chat_service.generate_response(
            username=current_user.username,
            prompt=request.prompt,
            subject=request.subject,
            topics=request.topics,
            role=current_user.role
        )
        print("IN_TRY")
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history(subject: str = "general", current_user: models.User = Depends(auth.get_current_user)):
    return chat_service.get_chat_history(current_user.username, subject)
