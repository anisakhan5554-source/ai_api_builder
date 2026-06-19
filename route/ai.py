from  core.limiter import limiter
from fastapi import Request
from datetime import datetime,date
from sqlalchemy import  func
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
@limiter.limit("5/minute")
async def generate_api(
    request: Request,
    ai_request: AIRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    provider = get_ai_provider(ai_request.provider)
    result = await provider.generate_code(ai_request.description)

    saved_record = GeneratedAPI(
        user_id=current_user.id,
        prompt=ai_request.description,
        generated_code=result,
        provider=ai_request.provider
    )
    db.add(saved_record)
    db.commit()
    db.refresh(saved_record)

    return {
        "status": "success",
        "provider": ai_request.provider,
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

@router.get("/ai/stats")
async def get_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total_generations = db.query(GeneratedAPI).filter(
        GeneratedAPI.user_id == current_user.id
    ).count()

    today = date.today()
    generated_today = db.query(GeneratedAPI).filter(
        GeneratedAPI.user_id == current_user.id,
        func.date(GeneratedAPI.created_at) == today
    ).count()

    favorite_provider_result = db.query(
        GeneratedAPI.provider,
        func.count(GeneratedAPI.provider).label("count")
    ).filter(
        GeneratedAPI.user_id == current_user.id
    ).group_by(GeneratedAPI.provider).order_by(func.count(GeneratedAPI.provider).desc()).first()

    favorite_provider = favorite_provider_result[0] if favorite_provider_result else None

    return {
        "total_generations": total_generations,
        "generated_today": generated_today,
        "favorite_provider": favorite_provider
    }

@router.get("/ai/templates")
async def get_templates():
    templates = [
        {"name": "CRUD API", "description": "Create a CRUD API for managing items with create, read, update, and delete endpoints"},
        {"name": "Authentication API", "description": "Create a user authentication API with register, login, and JWT token endpoints"},
        {"name": "E-commerce API", "description": "Create an e-commerce API with product listing, cart, and order endpoints"},
        {"name": "Blog API", "description": "Create a blog API with endpoints for posts, comments, and categories"}
    ]
    return {"templates": templates}