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
chat_service.get_mongo_db = lambda: mock_db_instance

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
