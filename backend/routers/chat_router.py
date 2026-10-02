from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from .. import auth, models, chat_service, database
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone

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

async def _generate_and_save_learning_plan(session_id: str, subject: str, topics: list):
    try:
        plan_data = await chat_service.generate_learning_plan_from_llm(subject, topics)
        if plan_data and plan_data.get("modules"):
            mongo_db = chat_service.get_mongo_db()
            mongo_db.chat_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"learning_plan": plan_data}}
            )
    except Exception as e:
        import logging
        logging.getLogger("teaching_platform.chat").warning(f"Background plan generation failed: {e}")

@router.post("/start")
async def start_session(
    request: models.CreateSessionRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(auth.get_current_user)
):
    session_id = chat_service.create_session(
        username=current_user.username,
        subject=request.subject,
        topics=request.topics
    )
    # Eagerly generate learning path in background so it's ready immediately
    background_tasks.add_task(
        _generate_and_save_learning_plan,
        session_id=session_id,
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

@router.post("/textbook/generate", response_model=models.TextbookArticleOut)
async def generate_textbook_article_endpoint(
    request: models.TextbookGenerateRequest,
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

    if not request.topic_override and session.get("textbook_article"):
        cached = session["textbook_article"]
        return {
            "session_id": request.session_id,
            "title": cached.get("title", subject),
            "topics": cached.get("topics", topics),
            "markdown_content": cached.get("markdown_content", ""),
            "generated_at": cached.get("generated_at")
        }

    try:
        article_result = await chat_service.generate_textbook_article(
            subject=subject,
            topics=topics,
            topic_override=request.topic_override
        )
        now_utc = datetime.now(timezone.utc)
        article_data = {
            "title": article_result["title"],
            "topics": article_result["topics"],
            "markdown_content": article_result["markdown_content"],
            "generated_at": now_utc
        }
        mongo_db.chat_sessions.update_one(
            {"_id": ObjectId(request.session_id)},
            {"$set": {"textbook_article": article_data, "last_updated": now_utc}}
        )
        return {
            "session_id": request.session_id,
            "title": article_result["title"],
            "topics": article_result["topics"],
            "markdown_content": article_result["markdown_content"],
            "generated_at": now_utc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/highlight", response_model=models.HighlightOut)
async def add_highlight_endpoint(
    session_id: str,
    request: models.HighlightCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    now_utc = datetime.now(timezone.utc)
    highlight_doc = {
        "element_id": request.element_id,
        "quoted_text": request.quoted_text,
        "question": request.question or "",
        "tag": request.tag,
        "created_at": now_utc
    }

    mongo_db.chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"highlights": highlight_doc}}
    )

    return highlight_doc

@router.get("/{session_id}/highlights", response_model=List[models.HighlightOut])
async def get_highlights_endpoint(
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

    highlights = session.get("highlights", [])
    return highlights

@router.delete("/{session_id}/highlight/{index}")
async def delete_highlight_endpoint(
    session_id: str,
    index: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    highlights = session.get("highlights", [])
    if 0 <= index < len(highlights):
        highlights.pop(index)
        mongo_db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"highlights": highlights}}
        )
        return {"status": "success", "remaining_count": len(highlights)}
    raise HTTPException(status_code=404, detail="Highlight index not found")

@router.post("/quiz/refresher")
async def generate_refresher_quiz_endpoint(
    request: models.RefresherQuizRequest,
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
    highlights = session.get("highlights", [])
    tough_highlights = [h for h in highlights if h.get("tag") == "Tough"]

    quiz_data = await chat_service.generate_refresher_quiz_from_llm(subject, tough_highlights)
    questions = quiz_data.get("questions") if quiz_data else []

    if not questions:
        raise HTTPException(status_code=500, detail="Failed to generate refresher quiz questions.")

    new_quiz = models.Quiz(
        session_id=str(request.session_id),
        difficulty="refresher",
        questions=questions
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    client_quiz_data = chat_service.strip_answers(quiz_data)
    client_quiz_data["db_id"] = new_quiz.id
    client_quiz_data["difficulty"] = "refresher"

    return client_quiz_data

@router.post("/textbook/socratic-hint", response_model=models.SocraticHintOut)
async def locate_socratic_hint_endpoint(
    request: models.SocraticHintRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    mongo_db = chat_service.get_mongo_db()
    try:
        session = mongo_db.chat_sessions.find_one({"_id": ObjectId(request.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Session ID format")

    verify_session_access(session, current_user, db)

    article_text = request.article_text
    if not article_text:
        textbook_article = session.get("textbook_article") or {}
        article_text = textbook_article.get("markdown_content", "")

    if not article_text:
        raise HTTPException(status_code=400, detail="No textbook article text available for socratic hint calculation. Please generate a textbook article first.")

    try:
        hint_result = await chat_service.locate_socratic_hint(
            question=request.question,
            article_text=article_text
        )
        return hint_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

    existing_plan = session.get("learning_plan")
    if existing_plan and isinstance(existing_plan, dict) and existing_plan.get("modules"):
        return existing_plan

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

    normalized_messages = []
    for msg in messages:
        m = dict(msg)
        if "content" not in m or not m["content"]:
            parts = m.get("parts", [])
            if isinstance(parts, list) and len(parts) > 0:
                m["content"] = str(parts[0])
            elif isinstance(parts, str):
                m["content"] = parts
            else:
                m["content"] = ""
        # Map timestamp to ISO string if datetime
        if isinstance(m.get("timestamp"), datetime):
            m["timestamp"] = m["timestamp"].isoformat()
        normalized_messages.append(m)

    subject = session.get("subject", "General")
    topics = session.get("topics", [])
    title = session.get("title")
    if not title:
        title = f"{subject} - {', '.join(topics)}" if topics else f"{subject} - General"

    return {
        "messages": normalized_messages,
        "learning_plan": session.get("learning_plan", {}),
        "highlights": session.get("highlights", []),
        "subject": subject,
        "topics": topics,
        "title": title
    }
