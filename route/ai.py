from fastapi import HTTPException
from fastapi.responses import  Response
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.ai_factory import get_ai_provider
from dependencies.auth import get_current_user
from database import get_db
from models import GeneratedAPI

router = APIRouter(tags=["AI"])

class AIRequest(BaseModel):
    description: str
    provider: str = "groq"

@router.post("/ai/generate")
async def generate_api(
    request: AIRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    provider = get_ai_provider(request.provider)
    result = await provider.generate_code(request.description)

    saved_record = GeneratedAPI(
        user_id=current_user.id,
        prompt=request.description,
        generated_code=result,
        provider=request.provider
    )
    db.add(saved_record)
    db.commit()
    db.refresh(saved_record)

    return {
        "status": "success",
        "provider": request.provider,
        "generated_code": result,
        "saved_id": saved_record.id
    }

@router.post("/ai/schema")
async def generate_schema(
    request: AIRequest,
    current_user = Depends(get_current_user)
):
    provider = get_ai_provider(request.provider)
    result = await provider.generate_api_schema(request.description)
    return {
        "status": "success",
        "provider": request.provider,
        "schema": result
    }

@router.get("/ai/history")
async def get_history(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(GeneratedAPI).filter(GeneratedAPI.user_id == current_user.id).all()
    return {
        "status": "success",
        "count": len(records),
        "history": [
            {
                "id": r.id,
                "prompt": r.prompt,
                "provider": r.provider,
                "generated_code": r.generated_code,
                "created_at": r.created_at
            }
            for r in records
        ]
    }
@router.get("/ai/export/{generation_id}")
async def export_generated_code(
    generation_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = db.query(GeneratedAPI).filter(
        GeneratedAPI.id == generation_id,
        GeneratedAPI.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")

    return Response(
        content=record.generated_code,
        media_type="text/x-python",
        headers={
            "Content-Disposition": f"attachment; filename=generated_api_{generation_id}.py"
        }
    )