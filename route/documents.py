from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from dependencies.auth import get_current_user
import os
import io
from core.vector_store import store_document ,search_documents
from core.ai_factory import get_ai_provider

router = APIRouter(tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def extract_text(contents: bytes, file_ext: str) -> str:
    try:
        if file_ext == ".pdf":
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text

        elif file_ext == ".docx":
            import docx
            doc = docx.Document(io.BytesIO(contents))
            return "\n".join([para.text for para in doc.paragraphs])

        elif file_ext in {".txt", ".md"}:
            return contents.decode("utf-8")

        else:
            return ""
    except Exception as e:
        return f"Error extracting text: {str(e)}"

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}"
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )

    file_path = f"{UPLOAD_DIR}/{current_user.id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(contents)

    extracted_text = extract_text(contents, file_ext)
    text_preview = extracted_text[:500] if extracted_text else ""

    return {
        "status": "success",
        "filename": file.filename,
        "file_path": file_path,
        "file_size": len(contents),
        "file_type": file_ext,
        "uploaded_by": current_user.id,
        "text_extracted": bool(extracted_text),
        "text_preview": text_preview,
        "total_characters": len(extracted_text)
    }

@router.post("/documents/extract/{filename}")
async def extract_document_text(
    filename: str,
    current_user = Depends(get_current_user)
):
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    with open(file_path, "rb") as f:
        contents = f.read()

    file_ext = os.path.splitext(filename)[1].lower()
    extracted_text = extract_text(contents, file_ext)

    return {
        "status": "success",
        "filename": filename,
        "extracted_text": extracted_text,
        "total_characters": len(extracted_text)
    }

@router.get("/documents")
async def get_documents(
    current_user = Depends(get_current_user)
):
    user_files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(f"{current_user.id}_"):
                file_path = os.path.join(UPLOAD_DIR, filename)
                user_files.append({
                    "filename": filename.replace(f"{current_user.id}_", ""),
                    "file_path": file_path,
                    "file_size": os.path.getsize(file_path)
                })

    return {
        "status": "success",
        "count": len(user_files),
        "documents": user_files
    }

@router.post("/documents/process/{filename}")
async def process_document(
    filename: str,
    current_user = Depends(get_current_user)
):
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    with open(file_path, "rb") as f:
        contents = f.read()

    file_ext = os.path.splitext(filename)[1].lower()
    extracted_text = extract_text(contents, file_ext)

    if not extracted_text:
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    chunks_stored = store_document(
        document_id=f"{current_user.id}_{filename}",
        text=extracted_text,
        metadata={
            "user_id": str(current_user.id),
            "filename": filename
        }
    )

    return {
        "status": "success",
        "filename": filename,
        "chunks_stored": chunks_stored,
        "message": f"Document processed and stored {chunks_stored} chunks in vector database"
    }


@router.post("/documents/search")
async def search_documents_endpoint(
    current_user = Depends(get_current_user),
    query: str = None,
    n_results: int = 3
):
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    results = search_documents(
        query=query,
        n_results=n_results,
        user_id=current_user.id
    )

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return {
        "status": "success",
        "query": query,
        "results": [
            {
                "text": doc,
                "relevance_score": round(1 - dist, 3),
                "metadata": meta
            }
            for doc, dist, meta in zip(documents, distances, metadatas)
        ]
    }


@router.post("/documents/chat")
async def chat_with_document(
    current_user = Depends(get_current_user),
    query: str = None,
    provider: str = "groq"
):
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    # Step 1 — retrieve relevant chunks
    results = search_documents(
        query=query,
        n_results=3,
        user_id=current_user.id
    )

    documents = results.get("documents", [[]])[0]

    if not documents:
        raise HTTPException(status_code=404, detail="No relevant documents found")

    # Step 2 — build context from chunks
    context = "\n\n".join(documents)

    # Step 3 — ask AI with context
    prompt = f"""You are a helpful assistant. Answer the question based on the context provided.

Context from documents:
{context}

Question: {query}

Answer based only on the context above. If the answer is not in the context, say so."""

    try:
        ai_provider = get_ai_provider(provider)
        answer = await ai_provider.generate(prompt)
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "query": query,
        "answer": answer,
        "sources_used": len(documents)
    }

@router.post("/documents/analyze")
async def analyze_requirements(
    filename: str,
    current_user = Depends(get_current_user),
    provider: str = "groq"
):
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    with open(file_path, "rb") as f:
        contents = f.read()

    file_ext = os.path.splitext(filename)[1].lower()
    extracted_text = extract_text(contents, file_ext)

    prompt = f"""Analyze this software requirements document and extract:

1. KEY FEATURES: List the main features needed
2. DATABASE TABLES: Suggest database tables needed
3. API ENDPOINTS: List the main API endpoints needed
4. TECH STACK: Recommend a tech stack
5. COMPLEXITY: Rate complexity (Low/Medium/High)

Document:
{extracted_text[:3000]}

Provide a structured analysis."""

    try:
        ai_provider = get_ai_provider(provider)
        analysis = await ai_provider.generate(prompt)
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "filename": filename,
        "analysis": analysis
    }