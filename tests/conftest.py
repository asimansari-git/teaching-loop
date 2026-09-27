import os
import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set required environment variables before any module imports
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-purposes-123456"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:8501,http://127.0.0.1:8501"

from backend.database import Base, get_db
import backend.database as database

# Configure in-memory SQLite with StaticPool for test isolation
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create tables in memory
Base.metadata.create_all(bind=test_engine)

# In-memory MongoDB Mock Collection
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

# Patch database and services to use test fixtures
database.engine = test_engine
database.SessionLocal = TestingSessionLocal
database.get_mongo_db = lambda: mock_db_instance

from backend.services import session_service, ai_service, report_service
from backend import chat_service
session_service.get_mongo_db = lambda: mock_db_instance
ai_service.get_mongo_db = lambda: mock_db_instance
report_service.get_mongo_db = lambda: mock_db_instance
chat_service.get_mongo_db = lambda: mock_db_instance

# Override FastAPI get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

from backend.main import app
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def test_db():
    return TestingSessionLocal()

@pytest.fixture(scope="session")
def mock_mongo():
    return mock_db_instance
