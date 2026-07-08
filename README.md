# 🏛️ Government Schemes RAG Chatbot

An AI-powered Government Schemes Assistant that helps users find information about Indian Government schemes by asking questions in natural language.

The chatbot uses **Retrieval-Augmented Generation (RAG)** with **ChromaDB**, **Ollama**, and **FastAPI** to retrieve relevant information from uploaded government PDF documents before generating accurate responses.

---

#  Features

-  User Authentication (JWT)
-  User Registration & Login
-  Upload Government Scheme PDFs
-  PDF Ingestion into ChromaDB
-  AI Chatbot using Ollama
-  Semantic Search using Embeddings
-  PostgreSQL Database
-  Persistent Chat History
-  Recent Search History
-  Dockerized Deployment
-  Responsive Web Interface

---

# Project Architecture

```
                User
                  │
                  ▼
          HTML/CSS/JavaScript
                  │
                  ▼
            FastAPI Backend
                  │
     ┌────────────┼────────────┐
     │            │            │
     ▼            ▼            ▼
 PostgreSQL    ChromaDB      Ollama
(User Data) (Vector Store)   (LLM)
```

---

# Tech Stack

### Backend

- FastAPI
- Python
- Uvicorn

### AI

- Ollama
- Llama 3.2
- nomic-embed-text

### Vector Database

- ChromaDB

### Database

- PostgreSQL

### Authentication

- JWT

### Frontend

- HTML
- CSS
- JavaScript

### Deployment

- Docker
- Docker Compose

---

# Project Structure

```
RAGCHATBOT/

│── main.py
│── database.py
│── rag_engine.py
│── config.py
│── requirements.txt
│── Dockerfile
│── docker-compose.yml
│── .dockerignore
│── .env

├── uploads/
├── chroma_db/
├── static/
│   ├── login.html
│   ├── chat.html
│   ├── database.html
│   ├── styles.css
│   └── utils.js
```

---

#  How It Works

## 1. User Uploads PDF

Government scheme PDFs are uploaded using the Database page.

↓

## 2. PDF Processing

The application:

- Extracts text
- Splits into chunks
- Generates embeddings
- Stores vectors in ChromaDB

↓

## 3. User Asks Question

Example:

> What is PM Kisan?

↓

## 4. RAG Retrieval

Relevant chunks are retrieved from ChromaDB using semantic similarity.

↓

## 5. LLM Response

Ollama generates a response using:

- Retrieved context
- Previous conversation (chat history)

↓

## 6. Chat History

Both user messages and AI responses are stored in PostgreSQL.

---

# 🛠️ Installation

## Clone Repository

```bash
git clone <your_repository_url>
cd RAGCHATBOT
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment

Create a `.env` file.

Example:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ragchatbot
DB_USER=postgres
DB_PASSWORD=your_password

JWT_SECRET=your_secret

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text
```

---

## Start Ollama

```bash
ollama serve
```

Download models:

```bash
ollama pull llama3.2

ollama pull nomic-embed-text
```

---

## Run FastAPI

```bash
python -m uvicorn main:app --reload
```

Open:

```
http://localhost:8000
```

---

# 🐳 Docker Deployment

Build:

```bash
docker compose build
```

Run:

```bash
docker compose up
```

Open:

```
http://localhost:8000
```

---

# 📡 API Endpoints

## Authentication

```
POST /api/register

POST /api/login
```

## Documents

```
POST /api/upload

POST /api/ingest/{id}

GET /api/documents
```

## Chat

```
POST /api/chat

GET /api/history
```

---

# Database

The project uses PostgreSQL to store:

- Users
- Uploaded Documents
- Chat History
- Conversation Metadata

---

# 🧠 AI Pipeline

```
User Question

↓

Embedding Generation

↓

ChromaDB Similarity Search

↓

Relevant Context

↓

Ollama (Llama 3.2)

↓

Generated Response
```

---

# Authentication

JWT-based authentication is used.

Protected APIs require a valid token.

---

# Current Features

- User Authentication
- PDF Upload
- PDF Ingestion
- RAG Retrieval
- AI Chatbot
- Chat History
- Docker Support
- PostgreSQL Storage

---

# Future Improvements

- ChatGPT-style Conversations
- Conversation Memory
- OCR Support for Scanned PDFs
- PDF Preview
- Source Citations with Page Numbers
- Multi-file Upload
- Streaming Responses
- Conversation Search
- Admin Dashboard

---

# Author

**Srajan Swami**

B.Tech CSE with specialisation in AI & ML

SRM Institute of Science and Technology, Kattankulathur, T.N

---

# ⭐ Acknowledgements

- FastAPI
- Ollama
- ChromaDB
- PostgreSQL
- Docker