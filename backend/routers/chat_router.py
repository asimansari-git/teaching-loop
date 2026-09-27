from fastapi import APIRouter, Depends, HTTPException
from .. import auth, models, chat_service, database
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from bson import ObjectId

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

def verify_session_access(session: dict, current_user: models.User, db: Session):
    """Verifies that current_user has permission to read or write to this chat session."""
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "student":
        if session.get("username") != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
    elif current_user.role == "teacher":
        session_username = session.get("username")
        student = db.query(models.User).filter(models.User.username == session_username).first()
        if not student or student.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to access student session outside your organization")
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

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
async def send_message(
    session_id: str,
    request: MessageRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")
    
    verify_session_access(session, current_user, db)

    try:
        response_text = await chat_service.generate_response(
            session_id=session_id,
            prompt=request.prompt,
            role=current_user.role
        )
        return {"response": response_text}
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
async def create_learning_plan(
    request: models.LearningPlanCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    subject = session.get("subject", "General")
    topics = session.get("topics", [])
    
    try:
        plan_data = await chat_service.generate_learning_plan_from_llm(subject, topics)
        mongo_db.chat_sessions.update_one(
            {"_id": ObjectId(request.session_id)},
            {"$set": {"learning_plan": plan_data}}
        )
        return plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/generate")
async def generate_quiz(
    request: models.QuizCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    subject = session.get("subject", "General")
    learning_plan = session.get("learning_plan", {})
    
    # Check if a valid quiz already exists for this session and difficulty
    quizzes = db.query(models.Quiz).filter(models.Quiz.session_id == str(request.session_id)).all()
    for quiz in quizzes:
        if quiz.difficulty == request.difficulty:
            if quiz.questions and len(quiz.questions) > 0:
                safe_questions = []
                for q in quiz.questions:
                    q_copy = dict(q)
                    q_copy.pop("correct_option_index", None)
                    safe_questions.append(q_copy)
                return {
                    "db_id": quiz.id,
                    "difficulty": quiz.difficulty,
                    "questions": safe_questions,
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
    
    # Save Quiz to DB with full answers
    new_quiz = models.Quiz(
        session_id=str(request.session_id),
        difficulty=request.difficulty,
        questions=questions
    )

    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    
    # Strip answers before returning to client
    client_quiz_data = chat_service.strip_answers(quiz_data)
    client_quiz_data["db_id"] = new_quiz.id
    client_quiz_data["difficulty"] = request.difficulty
    
    return client_quiz_data

@router.post("/quiz/submit")
async def submit_quiz(
    request: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    user_answers = request.get("user_answers") or {}
    quiz_id = request.get("quiz_id")
    quiz_data = request.get("quiz_data") or {}
    
    if not quiz_id and isinstance(quiz_data, dict):
        quiz_id = quiz_data.get("db_id") or quiz_data.get("id")
        
    quiz_record = None
    if quiz_id:
        try:
            quiz_record = db.query(models.Quiz).filter(models.Quiz.id == int(quiz_id)).first()
        except (ValueError, TypeError):
            quiz_record = None

    if quiz_record:
        mongo_db = chat_service.get_mongo_db()
        try:
            session = mongo_db.chat_sessions.find_one({"_id": ObjectId(quiz_record.session_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Session ID format")
            
        verify_session_access(session, current_user, db)
        # Server-side authoritative grading using database record questions containing answer keys
        eval_data = {"questions": quiz_record.questions}
    elif quiz_data and "questions" in quiz_data:
        # Fallback if no DB record found (e.g. isolated mocks)
        eval_data = quiz_data
    else:
        raise HTTPException(status_code=400, detail="Quiz ID or valid questions required")

    result = await chat_service.evaluate_quiz_from_llm(eval_data, user_answers)
    
    # Update DB if record exists
    if quiz_record:
        quiz_record.score = result["percentage"]
        quiz_record.passed = result["passed"]
        db.commit()
            
    return result

@router.get("/{session_id}/history")
async def get_history(
    session_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    messages = session.get("messages", [])
    if current_user.role == "student":
        filtered_messages = []
        skip_next_model = False
        for msg in messages:
            author = msg.get("author")
            visible = msg.get("visible_to_student", True)
            if not visible or author in ["teacher", "teacher_model", "teacher_assistant", "model_to_teacher"]:
                if author == "teacher":
                    skip_next_model = True
                continue
            if skip_next_model and msg.get("role") != "user":
                skip_next_model = False
                continue
            skip_next_model = False
            filtered_messages.append(msg)
        messages = filtered_messages

    return {
        "messages": messages,
        "learning_plan": session.get("learning_plan", {}),
        "subject": session.get("subject", "General")
    }
