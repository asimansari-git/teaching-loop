import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("teaching_platform.database")

# Database Setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./teaching_platform.db")

def init_engine(url: str):
    """Initializes SQLAlchemy engine with graceful local SQLite fallback if target DB is offline."""
    try:
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}
        eng = create_engine(url, connect_args=connect_args)
        # Test connection immediately
        with eng.connect() as conn:
            pass
        return eng, url
    except Exception as e:
        if "sqlite" not in url:
            logger.warning(
                f"Database connection to '{url}' failed ({e}). "
                "Falling back to local SQLite database: 'sqlite:///./teaching_platform.db'"
            )
            fallback_url = "sqlite:///./teaching_platform.db"
            fallback_eng = create_engine(fallback_url, connect_args={"check_same_thread": False})
            return fallback_eng, fallback_url
        raise e

engine, SQLALCHEMY_DATABASE_URL = init_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["teaching_platform"]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongo_db():
    return mongo_db
