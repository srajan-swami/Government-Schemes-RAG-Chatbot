import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ragchatbot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ChromaDB
CHROMA_PERSIST_DIR = "./chroma_db"
