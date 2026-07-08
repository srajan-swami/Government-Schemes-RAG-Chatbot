"""
Database module for PostgreSQL connection and user management.
Handles user registration, authentication, and document tracking.
"""
import psycopg2
import psycopg2.extras
import bcrypt
from datetime import datetime
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def get_connection():
    """Get a PostgreSQL database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cur = conn.cursor()

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create documents table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(500) NOT NULL,
            filepath VARCHAR(1000) NOT NULL,
            file_size BIGINT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'uploaded',
            summary TEXT,
            chunk_count INTEGER DEFAULT 0,
            uploaded_by INTEGER REFERENCES users(id),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ingested_at TIMESTAMP
        );
    """)

    # Create conversations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create chat_history table if not exists (with conversation_id)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            username TEXT,
            role TEXT,
            message TEXT,
            conversation_id INTEGER REFERENCES conversations(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Add conversation_id column if it doesn't exist (for existing tables)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'chat_history' AND column_name = 'conversation_id'
            ) THEN
                ALTER TABLE chat_history
                ADD COLUMN conversation_id INTEGER REFERENCES conversations(id);
            END IF;
        END $$;
    """)

    conn.commit()
    cur.close()
    conn.close()


def create_user(email: str, password: str) -> dict:
    """Create a new user with hashed password."""
    # Hash the password with bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at",
            (email, password_hash)
        )
        user = dict(cur.fetchone())
        conn.commit()
        return user
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError("Email already registered")
    finally:
        cur.close()
        conn.close()


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate user by email and password."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        raise ValueError("Invalid email or password")

    # Verify password with bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise ValueError("Invalid email or password")

    return {"id": user["id"], "email": user["email"]}


def add_document(filename: str, filepath: str, file_size: int, user_id: int) -> dict:
    """Add a document record to the database."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """INSERT INTO documents (filename, filepath, file_size, uploaded_by) 
           VALUES (%s, %s, %s, %s) 
           RETURNING id, filename, filepath, file_size, status, summary, chunk_count, uploaded_at""",
        (filename, filepath, file_size, user_id)
    )
    doc = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    return doc


def update_document_status(doc_id: int, status: str, summary: str = None, chunk_count: int = 0):
    """Update document status after ingestion."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """UPDATE documents 
           SET status = %s, summary = %s, chunk_count = %s, ingested_at = %s
           WHERE id = %s""",
        (status, summary, chunk_count, datetime.now(), doc_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_documents() -> list:
    """Get all documents."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """SELECT id, filename, file_size, status, summary, chunk_count, uploaded_at, ingested_at 
           FROM documents ORDER BY uploaded_at DESC"""
    )
    docs = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return docs


def get_document_by_id(doc_id: int) -> dict:
    """Get a single document by ID."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    cur.close()
    conn.close()
    return dict(doc) if doc else None

def save_chat_message(username, role, message, conversation_id=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO chat_history
        (username, role, message, conversation_id)
        VALUES (%s, %s, %s, %s)
    """, (username, role, message, conversation_id))

    conn.commit()
    cur.close()
    conn.close()

def get_chat_history(username, limit=10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (message)
            role,
            message,
            created_at
        FROM chat_history
        WHERE username = %s
          AND role = 'user'
        ORDER BY message, created_at DESC
        LIMIT %s
    """, (username, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "role": role,
            "content": message,
            "created_at": str(created_at)
        }
        for role, message, created_at in rows
    ]


def create_conversation(user_email, title):
    """Create a new conversation and return its id."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO conversations (user_email, title)
        VALUES (%s, %s)
        RETURNING id
    """, (user_email, title))

    conversation_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return conversation_id


def get_user_conversations(user_email):
    """Get all conversations for a user, most recent first."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_email = %s
        ORDER BY updated_at DESC
    """, (user_email,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "created_at": str(row[2]),
            "updated_at": str(row[3])
        }
        for row in rows
    ]


def get_conversation_messages(conversation_id):
    """Get all messages for a conversation in chronological order."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT role, message
        FROM chat_history
        WHERE conversation_id = %s
        ORDER BY created_at ASC
    """, (conversation_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"role": row[0], "content": row[1]}
        for row in rows
    ]


def update_conversation_timestamp(conversation_id):
    """Update the updated_at timestamp of a conversation."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE conversations
        SET updated_at = %s
        WHERE id = %s
    """, (datetime.now(), conversation_id))

    conn.commit()
    cur.close()
    conn.close()