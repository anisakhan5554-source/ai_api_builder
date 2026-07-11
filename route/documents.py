from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from dependencies.auth import get_current_user
import os
import io

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