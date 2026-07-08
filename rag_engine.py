"""
RAG Engine module.
Handles PDF processing, text chunking, vector storage, and retrieval-augmented generation.
"""
import os
import PyPDF2
import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_EMBED_MODEL, CHROMA_PERSIST_DIR


# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
collection = chroma_client.get_or_create_collection(
    name="government_schemes",
    metadata={"hnsw:space": "cosine"}
)

# Initialize Ollama client
ollama_client = ollama.Client(host=OLLAMA_BASE_URL)

# Text splitter for chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]
)


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text content from a PDF file."""
    text = ""
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def get_embeddings(text: str) -> list:
    """Get embeddings from Ollama."""
    response = ollama_client.embeddings(
        model=OLLAMA_EMBED_MODEL,
        prompt=text
    )
    return response["embedding"]


def ingest_pdf(filepath: str, doc_id: int, filename: str) -> dict:
    """
    Process a PDF: extract text, chunk it, generate embeddings, and store in ChromaDB.
    Returns summary and chunk count.
    """
    # Extract text
    full_text = extract_text_from_pdf(filepath)

    if not full_text:
        raise ValueError("Could not extract any text from the PDF")

    # Split into chunks
    chunks = text_splitter.split_text(full_text)

    # Generate embeddings and store in ChromaDB
    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"doc_{doc_id}_chunk_{i}"
        embedding = get_embeddings(chunk)

        ids.append(chunk_id)
        documents.append(chunk)
        embeddings.append(embedding)
        metadatas.append({
            "doc_id": str(doc_id),
            "filename": filename,
            "chunk_index": i
        })

    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    # Generate summary using Ollama
    summary_prompt = f"""You are a government policy analyst. Provide a concise summary (3-5 sentences) of the following government scheme document. 
Focus on: what the scheme is, who it benefits, and key eligibility criteria.

Document: {full_text[:3000]}

Summary:"""

    summary_response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    summary = summary_response["message"]["content"]

    return {
        "summary": summary,
        "chunk_count": len(chunks)
    }


def query_rag(question: str, chat_history: list = None) -> str:
    """
    Perform RAG query: find relevant chunks and generate an answer.
    Uses conversation history for context-aware retrieval and response.
    """
    # Build context-aware search query for better ChromaDB retrieval
    search_query = question
    if chat_history and len(chat_history) > 0:
        # Combine recent conversation context with current question
        # so embeddings capture the topic being discussed
        history_context_parts = []
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Truncate long assistant responses to keep search query focused
            if role == "assistant":
                content = content[:200]
            history_context_parts.append(f"{role}: {content}")

        search_query = (
            "Conversation:\n"
            + "\n".join(history_context_parts)
            + f"\n\nCurrent Question: {question}"
        )

    # Get query embeddings using context-aware search query
    query_embedding = get_embeddings(search_query)

    # Search ChromaDB for relevant chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas","distances"]
    )

    # Build context from retrieved chunks
    context_parts = []
    sources = set()

    if results["documents"] and results["documents"][0]:
        THRESHOLD = 0.4

        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            if distance < THRESHOLD:
                context_parts.append(doc)
                sources.add(meta.get("filename", "Unknown"))

    context = "\n\n---\n\n".join(context_parts)

    if not context_parts:
        return "I could not find relevant information in the uploaded documents."

    # Build chat messages with conversational context
    system_prompt = """You are a helpful and conversational Government Schemes Advisor chatbot for India.
Your role is to help citizens understand and find government schemes that are relevant to them.

INSTRUCTIONS:
- Use ONLY the provided context to answer questions
- If the context doesn't contain relevant information, say so honestly
- Be specific about eligibility criteria, benefits, and application processes
- Provide scheme names and relevant details
- Be helpful and empathetic
- If asked about multiple schemes, compare them clearly
- Always mention the source document when possible

CONVERSATIONAL CONTEXT:
- You must use previous conversation history to understand references and follow-up questions
- Resolve pronouns and references such as: "it", "this scheme", "the scheme", "eligibility", "benefits", "apply for it", "compare it", "how much", "what about"
- Always interpret these references using the previous messages in the conversation
- If the user asks a follow-up question, relate it to the scheme or topic discussed earlier"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history so the LLM can understand follow-up references
    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})

    # Add the current question with context
    user_message = f"""Based on the following context from government scheme documents, please answer the user's question.

CONTEXT:
{context}

SOURCES: {', '.join(sources) if sources else 'No relevant documents found'}

USER QUESTION: {question}

Please provide a helpful and accurate answer based on the context above."""

    messages.append({"role": "user", "content": user_message})

    # Generate response using Ollama
    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=messages
    )

    answer = response["message"]["content"]

    # Append source information
    if sources:
        answer += f"\n\n📄 **Sources:** {', '.join(sources)}"

    return answer

