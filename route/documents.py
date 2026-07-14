from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from dependencies.auth import get_current_user
import os
import io
from core.vector_store import store_document ,search_documents
from core.ai_factory import get_ai_provider
from pydantic import  BaseModel

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



@router.post("/documents/generate-backend")
async def generate_backend_from_document(
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

    prompt = f"""You are an expert FastAPI backend developer.

Based on these software requirements, generate a complete FastAPI backend including:

1. models.py - SQLAlchemy database models
2. schemas.py - Pydantic schemas
3. main.py - FastAPI app with all routes
4. Key API endpoints with full implementation

Requirements Document:
{extracted_text[:3000]}

Generate production-ready FastAPI code with proper error handling, authentication where needed, and clear comments."""

    try:
        ai_provider = get_ai_provider(provider)
        generated_backend = await ai_provider.generate(prompt)
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "filename": filename,
        "generated_backend": generated_backend,
        "message": "Complete FastAPI backend generated from your requirements"
    }


@router.post("/documents/generate-api-spec")
async def generate_api_specification(
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

    prompt = f"""You are an API architect. Based on these requirements, generate a complete OpenAPI 3.0 specification in JSON format.

Include:
- All necessary endpoints (GET, POST, PUT, DELETE)
- Request/response schemas
- Authentication requirements
- Error responses
- Proper HTTP status codes

Requirements:
{extracted_text[:3000]}

Return only valid OpenAPI 3.0 JSON, no explanation."""

    try:
        ai_provider = get_ai_provider(provider)
        api_spec = await ai_provider.generate(prompt)
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "filename": filename,
        "api_specification": api_spec,
        "message": "OpenAPI specification generated from requirements"
    }

class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    provider: str = "groq"

from pydantic import BaseModel

class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    provider: str = "groq"



@router.post("/documents/review-code")
async def review_code(
    review_request: CodeReviewRequest,
    current_user = Depends(get_current_user)
):
    prompt = f"""You are an expert code reviewer. Review this {review_request.language} code and provide:

1. BUGS: Any bugs or errors found
2. SECURITY: Security vulnerabilities
3. PERFORMANCE: Performance issues
4. BEST PRACTICES: Violations of best practices
5. IMPROVEMENTS: Specific improvement suggestions
6. RATING: Overall code quality rating (1-10)

Code to review:
{review_request.code}

Provide a detailed, constructive review."""

    try:
        ai_provider = get_ai_provider(review_request.provider)
        review = await ai_provider.generate(prompt)
    except Exception as e:
        print(f"AI provider error:{str(e)}")
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "language": review_request.language,
        "review": review
    }

class DatabaseDesignRequest(BaseModel):
    description: str
    provider: str = "groq"

@router.post("/documents/design-database")
async def design_database(
    db_request: DatabaseDesignRequest,
    current_user = Depends(get_current_user)
):
    prompt = f"""You are an expert database architect. Design a complete database schema for:

{db_request.description}

Provide:
1. TABLES: All tables with columns and data types
2. PRIMARY KEYS: For each table
3. FOREIGN KEYS: Relationships between tables
4. INDEXES: Recommended indexes for performance
5. SQLAlchemy MODELS: Complete Python SQLAlchemy model code
6. ERD DESCRIPTION: Text description of the entity relationship diagram

Make it production-ready with proper normalization."""

    try:
        ai_provider = get_ai_provider(db_request.provider)
        design = await ai_provider.generate(prompt)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "description": db_request.description,
        "database_design": design
    }



import httpx

class GitHubAnalysisRequest(BaseModel):
    repo_url: str
    provider: str = "groq"

@router.post("/documents/analyze-github")
async def analyze_github_repo(
    github_request: GitHubAnalysisRequest,
    current_user = Depends(get_current_user)
):
    # Extract owner and repo from URL
    try:
        parts = github_request.repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL format")

    # Fetch repo info from GitHub API
    try:
        async with httpx.AsyncClient() as client:
            repo_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            readme_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/readme",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            files_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not fetch GitHub repository")

    repo_data = repo_response.json()
    files_data = files_response.json() if files_response.status_code == 200 else []

    file_list = [f["name"] for f in files_data if isinstance(files_data, list)]

    prompt = f"""Analyze this GitHub repository and provide:

1. PROJECT OVERVIEW: What does this project do?
2. TECH STACK: Technologies used based on files
3. CODE QUALITY: Assessment based on structure
4. MISSING FEATURES: What's missing?
5. IMPROVEMENTS: Specific recommendations
6. DOCUMENTATION: Is it well documented?

Repository Info:
Name: {repo_data.get('name', 'Unknown')}
Description: {repo_data.get('description', 'No description')}
Language: {repo_data.get('language', 'Unknown')}
Stars: {repo_data.get('stargazers_count', 0)}
Files: {', '.join(file_list[:20])}

Provide a detailed technical analysis."""

    try:
        ai_provider = get_ai_provider(github_request.provider)
        analysis = await ai_provider.generate(prompt)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "repo_url": github_request.repo_url,
        "repo_name": repo_data.get("name"),
        "language": repo_data.get("language"),
        "stars": repo_data.get("stargazers_count"),
        "analysis": analysis
    }

class ReadmeRequest(BaseModel):
    repo_url: str = None
    project_description: str = None
    tech_stack: str = None
    provider: str = "groq"

@router.post("/documents/generate-readme")
async def generate_readme(
    readme_request: ReadmeRequest,
    current_user = Depends(get_current_user)
):
    context = ""

    if readme_request.repo_url:
        try:
            parts = readme_request.repo_url.rstrip("/").split("/")
            owner = parts[-2]
            repo = parts[-1]

            async with httpx.AsyncClient() as client:
                repo_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
                files_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contents",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )

            repo_data = repo_response.json()
            files_data = files_response.json() if files_response.status_code == 200 else []
            file_list = [f["name"] for f in files_data if isinstance(files_data, list)]

            context = f"""
Repository: {repo_data.get('name')}
Description: {repo_data.get('description', 'No description')}
Language: {repo_data.get('language')}
Files: {', '.join(file_list[:20])}
"""
        except Exception:
            pass

    if readme_request.project_description:
        context += f"\nProject Description: {readme_request.project_description}"

    if readme_request.tech_stack:
        context += f"\nTech Stack: {readme_request.tech_stack}"

    prompt = f"""Generate a professional, comprehensive README.md for this project:

{context}

Include:
1. Project title and badges
2. Description
3. Features list
4. Tech stack
5. Installation instructions
6. Usage examples
7. API endpoints (if applicable)
8. Contributing guidelines
9. License section

Use proper Markdown formatting. Make it professional and impressive."""

    try:
        ai_provider = get_ai_provider(readme_request.provider)
        readme = await ai_provider.generate(prompt)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=503, detail="AI provider unavailable")

    return {
        "status": "success",
        "readme": readme,
        "message": "README.md generated successfully"
    }


