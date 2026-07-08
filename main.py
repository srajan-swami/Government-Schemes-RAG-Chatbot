"""
FastAPI main application.
Government Schemes RAG Chatbot API server.
"""
import os
import shutil
from typing import Optional
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, UPLOAD_DIR
from database import init_db, create_user, authenticate_user, add_document, update_document_status, get_all_documents, get_document_by_id
from rag_engine import ingest_pdf, query_rag
from database import (
    save_chat_message,
    get_chat_history,
    create_conversation,
    get_user_conversations,
    get_conversation_messages,
    update_conversation_timestamp
)

# Initialize FastAPI app
app = FastAPI(title="Government Schemes RAG Chatbot", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


# ==================== Pydantic Models ====================

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ChatMessage(BaseModel):
    message: str
    history: list = []
    conversation_id: Optional[int] = None


# ==================== Auth Helpers ====================

def create_token(user_data: dict) -> str:
    """Create a JWT token."""
    payload = {
        "sub": str(user_data["id"]),
        "email": user_data["email"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify a JWT token and return user data."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"id": int(payload["sub"]), "email": payload["email"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ==================== Page Routes ====================

@app.get("/")
async def serve_login():
    return FileResponse("static/login.html")

@app.get("/database")
async def serve_database():
    return FileResponse("static/database.html")

@app.get("/chat")
async def serve_chat():
    return FileResponse("static/chat.html")


# ==================== Auth API ====================

@app.post("/api/register")
async def register(user: UserRegister):
    try:
        new_user = create_user(user.email, user.password)
        token = create_token(new_user)
        return {"success": True, "token": token, "email": new_user["email"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/login")
async def login(user: UserLogin):
    try:
        auth_user = authenticate_user(user.email, user.password)
        token = create_token(auth_user)
        return {"success": True, "token": token, "email": auth_user["email"]}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ==================== Document API ====================

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), token: str = ""):
    """Upload a PDF file."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = verify_token(token)

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save the file
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(filepath)
    doc = add_document(file.filename, filepath, file_size, user["id"])

    return {"success": True, "document": doc}


@app.post("/api/ingest/{doc_id}")
async def ingest_document(doc_id: int, token: str = ""):
    """Ingest a PDF into the vector store and generate summary."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    verify_token(token)
    doc = get_document_by_id(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        update_document_status(doc_id, "processing")
        result = ingest_pdf(doc["filepath"], doc_id, doc["filename"])
        update_document_status(doc_id, "ingested", result["summary"], result["chunk_count"])
        return {
            "success": True,
            "summary": result["summary"],
            "chunk_count": result["chunk_count"]
        }
    except Exception as e:
        update_document_status(doc_id, "error")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/api/documents")
async def list_documents(token: str = ""):
    """List all uploaded documents."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    verify_token(token)
    docs = get_all_documents()

    # Convert datetime objects to strings for JSON serialization
    for doc in docs:
        for key in ["uploaded_at", "ingested_at"]:
            if doc.get(key) and isinstance(doc[key], datetime):
                doc[key] = doc[key].isoformat()

    return {"success": True, "documents": docs}


# ==================== Chat API ====================
@app.post("/api/chat")
async def chat(msg: ChatMessage, token: str = ""):

    if not token:
        raise HTTPException(status_code=401)

    user = verify_token(token)
    username = user["email"]

    conversation_id = msg.conversation_id

    # If no conversation_id, create a new conversation
    if conversation_id is None:
        # Generate title from first user message (first 50 chars)
        title = msg.message[:50].strip()
        if len(msg.message) > 50:
            title += "..."
        conversation_id = create_conversation(username, title)

    # Save user message with conversation_id
    save_chat_message(
        username,
        "user",
        msg.message,
        conversation_id
    )

    # Fetch conversation history for context (last 3 pairs = 6 messages)
    conversation_history = get_conversation_messages(conversation_id)
    # Keep only the last 6 messages for context
    recent_history = conversation_history[-6:]

    response = query_rag(
        msg.message,
        recent_history
    )

    # Save assistant message with conversation_id
    save_chat_message(
        username,
        "assistant",
        response,
        conversation_id
    )

    # Update conversation timestamp
    update_conversation_timestamp(conversation_id)

    return {
        "success": True,
        "response": response,
        "conversation_id": conversation_id
    }


@app.get("/api/history")
async def history(token: str = ""):

    if not token:
        raise HTTPException(status_code=401)

    user = verify_token(token)

    history = get_chat_history(
        user["email"],
        10
    )

    return {
        "success": True,
        "history": history
    }


@app.get("/api/conversations")
async def list_conversations(token: str = ""):
    """Get all conversations for the authenticated user."""
    if not token:
        raise HTTPException(status_code=401)

    user = verify_token(token)
    conversations = get_user_conversations(user["email"])

    return {
        "success": True,
        "conversations": conversations
    }


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, token: str = ""):
    """Get all messages for a specific conversation."""
    if not token:
        raise HTTPException(status_code=401)

    verify_token(token)
    messages = get_conversation_messages(conversation_id)

    return {
        "success": True,
        "messages": messages
    }
