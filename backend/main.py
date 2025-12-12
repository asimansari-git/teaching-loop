from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth_router, chat_router, report_router
from .database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Teaching Platform API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(report_router.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Teaching Platform API"}
