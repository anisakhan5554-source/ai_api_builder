from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from dependencies.auth import get_current_user
import os
import shutil

router = APIRouter(tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {ALLOWED_EXTENSIONS}"
        )

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )

    # Save file
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(contents)

    return {
        "status": "success",
        "filename": file.filename,
        "file_path": file_path,
        "file_size": len(contents),
        "file_type": file_ext,
        "uploaded_by": current_user.id
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