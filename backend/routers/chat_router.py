from fastapi import APIRouter, Depends, HTTPException
from .. import auth, models, chat_service, database
from sqlalchemy.orm import Session
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

@router.get("/subjects", response_model=List[models.SubjectOut])
async def get_subjects(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    subjects = db.query(models.Subject).all()
    return subjects

@router.post("/subjects/validate", response_model=models.SubjectOut)
async def validate_subject(request: models.SubjectBase, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    normalized_data = await chat_service.normalize_subject(request.name)
    
    # Check if subject exists
    existing_subject = db.query(models.Subject).filter(models.Subject.name == normalized_data["name"]).first()
    if existing_subject:
        return existing_subject
    
    # Create new subject
    new_subject = models.Subject(
        name=normalized_data["name"],
        topics=normalized_data["topics"]
    )
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    
    return new_subject

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
async def generate_quiz(request: models.QuizCreate, db: Session = Depends(database.get_db)):
    # Fetch session context
    subject = "General"
    learning_plan = {}
    try:
        from bson import ObjectId
        mongo_db = chat_service.get_mongo_db()
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
        if session:
            subject = session.get("subject", "General")
            learning_plan = session.get("learning_plan", {})
    except Exception as e:
        print(f"Error fetching session context for quiz: {e}")

    print(f"SESSION ID: {request.session_id}")
    print(f"DIFFICULTY: {request.difficulty}")
    
    # Check if a valid quiz already exists
    quizzes = db.query(models.Quiz).filter(models.Quiz.session_id == str(request.session_id)).all()
    for quiz in quizzes:
        if quiz.difficulty == request.difficulty:
            if quiz.questions and len(quiz.questions) > 0:
                return {
                    "db_id": quiz.id,
                    "difficulty": quiz.difficulty,
                    "questions": quiz.questions,
                    "score": quiz.score,
                    "passed": quiz.passed
                }
            else:
                db.delete(quiz)
                db.commit()
    
    # Generate new quiz
    quiz_data = await chat_service.generate_quiz_from_llm(subject, request.difficulty, learning_plan)
    questions = quiz_data.get("questions") if quiz_data else []
    
    if not questions:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz questions from AI service. Please try again."
        )
    
    # Save Quiz to DB
    new_quiz = models.Quiz(
        session_id=str(request.session_id),
        difficulty=request.difficulty,
        questions=questions
    )

    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    # Inject ID so frontend can submit answers with it
    quiz_data["db_id"] = new_quiz.id
    quiz_data["difficulty"] = request.difficulty
    
    return quiz_data

@router.post("/quiz/submit")
async def submit_quiz(request: dict, db: Session = Depends(database.get_db)): # Simplified request
    # Expects { "quiz_data": ..., "user_answers": ... }
    quiz_data = request.get("quiz_data") or {}
    user_answers = request.get("user_answers") or {}
    result = await chat_service.evaluate_quiz_from_llm(quiz_data, user_answers)
    
    # Update DB if ID exists
    db_id = quiz_data.get("db_id") or quiz_data.get("id")
    if db_id:
        quiz_record = db.query(models.Quiz).filter(models.Quiz.id == int(db_id)).first()
        if quiz_record:
            quiz_record.score = result["percentage"]
            quiz_record.passed = result["passed"]
            db.commit()
            
    return result

@router.get("/{session_id}/history")
async def get_history(session_id: str, current_user: models.User = Depends(auth.get_current_user)):
    # Verify ownership? For now, we assume if you have ID you can read, 
    # but ideally check if session belongs to user or if user is teacher.
    # We will trust internal logic for now or add a quick check if needed.
    return chat_service.get_session_history(session_id)
