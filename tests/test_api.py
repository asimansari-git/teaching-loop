from fastapi.testclient import TestClient
from backend.main import app
from backend import models, chat_service
from frontend.utils import decode_jwt_payload
import os
from unittest.mock import MagicMock
from bson import ObjectId

# In-memory MongoDB Mock for isolated unit tests
class MockMongoCollection:
    def __init__(self):
        self.docs = {}

    def insert_one(self, doc):
        oid = ObjectId()
        item = dict(doc)
        item["_id"] = oid
        self.docs[str(oid)] = item
        res = MagicMock()
        res.inserted_id = oid
        return res

    def find_one(self, query):
        if "_id" in query:
            return self.docs.get(str(query["_id"]))
        for doc in self.docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    def find(self, query):
        results = [doc for doc in self.docs.values() if all(doc.get(k) == v for k, v in query.items())]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = results
        return mock_cursor

    def update_one(self, query, update):
        doc = self.find_one(query)
        if doc:
            if "$set" in update:
                doc.update(update["$set"])
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k not in doc:
                        doc[k] = []
                    doc[k].append(v)

class MockMongoDB:
    def __init__(self):
        self.chat_sessions = MockMongoCollection()

mock_db_instance = MockMongoDB()
from backend import database
from backend.services import session_service, ai_service, report_service
database.get_mongo_db = lambda: mock_db_instance
session_service.get_mongo_db = lambda: mock_db_instance
ai_service.get_mongo_db = lambda: mock_db_instance
chat_service.get_mongo_db = lambda: mock_db_instance
report_service.get_mongo_db = lambda: mock_db_instance

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Teaching Platform API"}

def test_register_teacher():
    response = client.post(
        "/auth/register",
        json={"username": "testteacher", "password": "password123", "role": "teacher", "new_organization_name": "TestOrg"},
    )
    assert response.status_code in [200, 400]

def test_login_teacher():
    response = client.post(
        "/auth/token",
        data={"username": "testteacher", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_jwt_payload(token)
    assert payload.get("role") == "teacher"
    assert payload.get("sub") == "testteacher"

def test_register_student():
    org_res = client.get("/auth/organizations")
    org_id = org_res.json()[0]["id"] if org_res.json() else 1
    response = client.post(
        "/auth/register",
        json={"username": "teststudent", "password": "password123", "role": "student", "organization_id": org_id},
    )
    assert response.status_code in [200, 400]

def test_login_student():
    response = client.post(
        "/auth/token",
        data={"username": "teststudent", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_jwt_payload(token)
    assert payload.get("role") == "student"
    assert payload.get("sub") == "teststudent"

def test_get_students_as_teacher():
    login_res = client.post(
        "/auth/token",
        data={"username": "testteacher", "password": "password123"},
    )
    token = login_res.json()["access_token"]
    response = client.get(
        "/reports/students",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_unauthenticated_endpoints_return_401():
    # POST /chat/learning/plan without auth
    res_plan = client.post("/chat/learning/plan", json={"session_id": "507f1f77bcf86cd799439011", "plan_content": {}})
    assert res_plan.status_code == 401

    # POST /chat/quiz/submit without auth
    res_quiz_submit = client.post("/chat/quiz/submit", json={"quiz_data": {}, "user_answers": {}})
    assert res_quiz_submit.status_code == 401

    # POST /chat/quiz/generate without auth
    res_quiz_gen = client.post("/chat/quiz/generate", json={"session_id": "507f1f77bcf86cd799439011", "difficulty": "easy"})
    assert res_quiz_gen.status_code == 401

    # GET /chat/{session_id}/history without auth
    res_history = client.get("/chat/507f1f77bcf86cd799439011/history")
    assert res_history.status_code == 401

def test_idor_session_history_protection():
    # 1. Register a second student
    org_res = client.get("/auth/organizations")
    org_id = org_res.json()[0]["id"] if org_res.json() else 1
    client.post(
        "/auth/register",
        json={"username": "otherstudent", "password": "password123", "role": "student", "organization_id": org_id},
    )

    # 2. Login as student 1 and create a session
    login_res_1 = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    token_1 = login_res_1.json()["access_token"]
    session_res = client.post(
        "/chat/start",
        json={"subject": "Math", "topics": ["Calculus"]},
        headers={"Authorization": f"Bearer {token_1}"}
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["session_id"]

    # 3. Student 1 accesses own session -> 200
    res_own = client.get(
        f"/chat/{session_id}/history",
        headers={"Authorization": f"Bearer {token_1}"}
    )
    assert res_own.status_code == 200

    # 4. Login as student 2 (attacker)
    login_res_2 = client.post("/auth/token", data={"username": "otherstudent", "password": "password123"})
    token_2 = login_res_2.json()["access_token"]

    # 5. Student 2 attempts to read Student 1's session -> Must be 403 Forbidden
    res_unauthorized = client.get(
        f"/chat/{session_id}/history",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert res_unauthorized.status_code == 403
    assert "Not authorized" in res_unauthorized.json()["detail"]

def test_teacher_intervention_hidden_from_student_history():
    # 1. Login as student and create a session
    login_res_s = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    student_token = login_res_s.json()["access_token"]
    
    session_res = client.post(
        "/chat/start",
        json={"subject": "Python", "topics": ["Loops"]},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    session_id = session_res.json()["session_id"]
    
    # 2. Add messages: student msg, model reply, teacher intervention, model confirmation
    session_service.save_message_to_session(session_id, "user", "How do for loops work?", author="student", visible_to_student=True)
    session_service.save_message_to_session(session_id, "model", "A for loop iterates over a sequence.", author="model", visible_to_student=True)
    session_service.save_message_to_session(session_id, "user", "Focus on while loops next.", author="teacher", visible_to_student=False)
    session_service.save_message_to_session(session_id, "model", "I confirm I will guide the student to while loops.", author="teacher_model", visible_to_student=False)
    
    # 3. Student requests history -> should only receive the 2 student/tutor messages
    res_student = client.get(f"/chat/{session_id}/history", headers={"Authorization": f"Bearer {student_token}"})
    assert res_student.status_code == 200
    student_messages = res_student.json()["messages"]
    assert len(student_messages) == 2
    assert student_messages[0]["parts"] == ["How do for loops work?"]
    assert student_messages[1]["parts"] == ["A for loop iterates over a sequence."]
    
    # 4. Teacher requests history -> should receive all 4 messages
    login_res_t = client.post("/auth/token", data={"username": "testteacher", "password": "password123"})
    teacher_token = login_res_t.json()["access_token"]
    res_teacher = client.get(f"/chat/{session_id}/history", headers={"Authorization": f"Bearer {teacher_token}"})
    assert res_teacher.status_code == 200
    teacher_messages = res_teacher.json()["messages"]
    assert len(teacher_messages) == 4

def test_quiz_answers_stripped_and_server_graded():
    # 1. Login student and start session
    login_res = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    token = login_res.json()["access_token"]
    session_res = client.post(
        "/chat/start",
        json={"subject": "Python", "topics": ["Functions"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_res.json()["session_id"]

    # 2. Generate quiz
    gen_res = client.post(
        "/chat/quiz/generate",
        json={"session_id": session_id, "difficulty": "easy"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert gen_res.status_code == 200
    quiz_data = gen_res.json()
    assert "db_id" in quiz_data
    assert "questions" in quiz_data
    assert len(quiz_data["questions"]) > 0

    # Verify no correct_option_index is leaked to client
    for q in quiz_data["questions"]:
        assert "correct_option_index" not in q
        assert "id" in q
        assert "text" in q
        assert len(q["options"]) == 4

    # 3. Submit quiz with quiz_id
    quiz_id = quiz_data["db_id"]
    submit_res = client.post(
        "/chat/quiz/submit",
        json={"quiz_id": quiz_id, "user_answers": {"1": 0, "2": 0, "3": 0}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert submit_res.status_code == 200
    res = submit_res.json()
    assert "score" in res
    assert "total" in res
    assert "percentage" in res
    assert "passed" in res
    assert "review" in res
    assert len(res["review"]) == len(quiz_data["questions"])
    assert res["review"][0]["correct_option_index"] is not None

def test_certificate_ownership_and_tier_prerequisites():
    login_res = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    student_token = login_res.json()["access_token"]
    session_res = client.post(
        "/chat/start",
        json={"subject": "Data Science", "topics": ["Pandas"]},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    session_id = session_res.json()["session_id"]

    # 1. Calling certificate before passing all quizzes -> 400 Bad Request
    res_no_quiz = client.post(
        "/reports/certificate",
        json={"session_id": session_id, "subject": "Data Science", "student_id": 0, "content": ""},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert res_no_quiz.status_code == 400
    assert "No quiz assessments found" in res_no_quiz.json()["detail"]

    # 1b. Add only easy quiz -> 400 Bad Request indicating missing levels
    from backend.database import SessionLocal
    from backend.models import Quiz
    db = SessionLocal()
    try:
        db.add(Quiz(session_id=session_id, difficulty="easy", questions=[], score=100.0, passed=True))
        db.commit()
    finally:
        db.close()

    res_partial_quiz = client.post(
        "/reports/certificate",
        json={"session_id": session_id, "subject": "Data Science", "student_id": 0, "content": ""},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert res_partial_quiz.status_code == 400
    assert "Must complete and pass all quiz levels" in res_partial_quiz.json()["detail"]

    # 2. Another student calling certificate for this session -> 403 Forbidden
    login_other = client.post("/auth/token", data={"username": "otherstudent", "password": "password123"})
    other_token = login_other.json()["access_token"]
    res_forbidden = client.post(
        "/reports/certificate",
        json={"session_id": session_id, "subject": "Data Science", "student_id": 0, "content": ""},
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert res_forbidden.status_code == 403
    assert "Not authorized" in res_forbidden.json()["detail"]

    # 3. Simulate passing Easy, Mid, and Hard in DB
    from backend.database import SessionLocal
    from backend.models import Quiz
    db = SessionLocal()
    try:
        db.add(Quiz(session_id=session_id, difficulty="easy", questions=[], score=100.0, passed=True))
        db.add(Quiz(session_id=session_id, difficulty="mid", questions=[], score=85.0, passed=True))
        db.add(Quiz(session_id=session_id, difficulty="hard", questions=[], score=90.0, passed=True))
        db.commit()
    finally:
        db.close()

    # 4. Now generate certificate -> 200 OK with persistence
    res_cert = client.post(
        "/reports/certificate",
        json={"session_id": session_id, "subject": "Data Science", "student_id": 0, "content": ""},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert res_cert.status_code == 200
    cert_data = res_cert.json()
    assert "content" in cert_data
    assert "verification_hash" in cert_data
    assert len(cert_data["verification_hash"]) == 16

def test_content_curation_organization_authorization():
    # 1. Register Teacher 2 in a new organization
    client.post(
        "/auth/register",
        json={"username": "otherorgteacher", "password": "password123", "role": "teacher", "new_organization_name": "SecondOrg"}
    )
    login_t2 = client.post("/auth/token", data={"username": "otherorgteacher", "password": "password123"})
    token_t2 = login_t2.json()["access_token"]

    login_t1 = client.post("/auth/token", data={"username": "testteacher", "password": "password123"})
    token_t1 = login_t1.json()["access_token"]

    # 2. Teacher 1 creates ContentItem and Chunk
    from backend.database import SessionLocal
    from backend.models import ContentItem, ContentChunk, User
    db = SessionLocal()
    try:
        t1_user = db.query(User).filter(User.username == "testteacher").first()
        item = ContentItem(
            filename="intro.pdf",
            content_type="application/pdf",
            teacher_id=t1_user.id,
            organization_id=t1_user.organization_id,
            status="processed"
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        chunk = ContentChunk(content_item_id=item.id, text="Variables store data.", topics=["variables"], status="pending")
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        chunk_id = chunk.id
        item_id = item.id
    finally:
        db.close()

    # 3. Teacher 2 (different org) attempts to update chunk -> 403 Forbidden
    res_update_forbidden = client.post(
        f"/content/chunk/{chunk_id}",
        json={"text": "Tampered text"},
        headers={"Authorization": f"Bearer {token_t2}"}
    )
    assert res_update_forbidden.status_code == 403

    # 4. Teacher 2 attempts to verify item -> 403 Forbidden
    res_verify_forbidden = client.post(
        f"/content/verify/{item_id}",
        headers={"Authorization": f"Bearer {token_t2}"}
    )
    assert res_verify_forbidden.status_code == 403

    # 5. Teacher 1 (same org) updates chunk and verifies item -> 200 OK
    res_update_ok = client.post(
        f"/content/chunk/{chunk_id}",
        json={"text": "Legitimate update"},
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    assert res_update_ok.status_code == 200

def test_textbook_generation_and_socratic_hint_api():
    # 1. Login student
    login_res = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    token = login_res.json()["access_token"]

    # 2. Start a session
    session_res = client.post(
        "/chat/start",
        json={"subject": "Computer Science", "topics": ["Algorithms"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_res.json()["session_id"]

    # 3. Generate textbook article
    tb_res = client.post(
        "/chat/textbook/generate",
        json={"session_id": session_id, "topic_override": "Sorting Algorithms"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert tb_res.status_code == 200
    tb_data = tb_res.json()
    assert tb_data["session_id"] == session_id
    assert "title" in tb_data
    assert "markdown_content" in tb_data

    # 4. Request Socratic hint
    hint_res = client.post(
        "/chat/textbook/socratic-hint",
        json={"session_id": session_id, "question": "How does quicksort partition work?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert hint_res.status_code == 200
    hint_data = hint_res.json()
    assert "target_element_id" in hint_data
    assert "highlight_quote" in hint_data
    assert "socratic_hint" in hint_data

    # 5. Unauthorized student accessing socratic hint -> 403 Forbidden
    login_other = client.post("/auth/token", data={"username": "otherstudent", "password": "password123"})
    other_token = login_other.json()["access_token"]
    res_forbidden = client.post(
        "/chat/textbook/socratic-hint",
        json={"session_id": session_id, "question": "What is time complexity?"},
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert res_forbidden.status_code == 403

def test_review_sheet_compiler_api():
    # 1. Login student
    login_res = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    token = login_res.json()["access_token"]

    # 2. Start a session
    session_res = client.post(
        "/chat/start",
        json={"subject": "Database Systems", "topics": ["Indexing"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_res.json()["session_id"]

    # 3. Post review sheet compilation request
    highlights = [
        {
            "element_id": "s-1-1",
            "quoted_text": "B-Trees maintain balanced search trees.",
            "question": "How does node splitting work during insertion?",
            "tag": "Tough"
        }
    ]
    rs_res = client.post(
        "/reports/review-sheet",
        json={"session_id": session_id, "highlights": highlights},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert rs_res.status_code == 200
    rs_data = rs_res.json()
    assert "id" in rs_data
    assert rs_data["session_id"] == session_id
    assert len(rs_data["review_items"]) == 1
    assert "pedagogical_answer" in rs_data["review_items"][0]
    assert "markdown_report" in rs_data

    # 4. Unauthorized student submitting review sheet for another student's session -> 403
    login_other = client.post("/auth/token", data={"username": "otherstudent", "password": "password123"})
    other_token = login_other.json()["access_token"]
    res_unauth = client.post(
        "/reports/review-sheet",
        json={"session_id": session_id, "highlights": highlights},
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert res_unauth.status_code == 403

def test_highlights_telemetry_and_micro_credential_api():
    login_res = client.post("/auth/token", data={"username": "teststudent", "password": "password123"})
    token = login_res.json()["access_token"]

    session_res = client.post(
        "/chat/start",
        json={"subject": "Machine Learning", "topics": ["Neural Networks"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_res.json()["session_id"]

    # 1. Post a highlight tagged as "Tough"
    hl_res = client.post(
        f"/chat/{session_id}/highlight",
        json={
            "element_id": "s-2-1",
            "quoted_text": "Backpropagation computes gradients via chain rule.",
            "question": "How do vanishing gradients happen?",
            "tag": "Tough"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert hl_res.status_code == 200
    hl_data = hl_res.json()
    assert hl_data["element_id"] == "s-2-1"
    assert hl_data["tag"] == "Tough"

    # 2. Retrieve highlights
    get_hl_res = client.get(
        f"/chat/{session_id}/highlights",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_hl_res.status_code == 200
    highlights_list = get_hl_res.json()
    assert len(highlights_list) == 1

    # 3. Request micro-credential status
    mc_res = client.get(
        f"/reports/micro-credential/{session_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert mc_res.status_code == 200
    mc_data = mc_res.json()
    assert mc_data["session_id"] == session_id
    assert mc_data["tough_count"] == 1
    assert "Backpropagation" in mc_data["tough_topics"][0]

    # 4. Generate targeted refresher quiz
    ref_res = client.post(
        "/chat/quiz/refresher",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert ref_data["difficulty"] == "refresher"
    assert "db_id" in ref_data
    assert len(ref_data["questions"]) > 0
