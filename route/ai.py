from  core.limiter import limiter
from fastapi import Request
from datetime import datetime,date
from fastapi import HTTPException
from fastapi.responses import  Response
from fastapi import APIRouter, Depends , BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.ai_factory import get_ai_provider
from dependencies.auth import get_current_user
from database import get_db
from models import GeneratedAPI
from typing import Optional
from core.redis_client import get_redis_client
import os
from sqlalchemy import  func,or_, text
from models import GeneratedAPI,AIUsageLog
router = APIRouter(tags=["AI"])


class AIRequest(BaseModel):
    description: str
    provider: str = "groq"
    parent_id: Optional[int] = None

@router.get("/ai/versions/{generation_id}")
async def get_versions(
    generation_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    original = db.query(GeneratedAPI).filter(
        GeneratedAPI.id == generation_id,
        GeneratedAPI.user_id == current_user.id
    ).first()

    if not original:
        raise HTTPException(status_code=404, detail="Generation not found")

    versions = db.query(GeneratedAPI).filter(
        GeneratedAPI.parent_id == generation_id,
        GeneratedAPI.user_id == current_user.id
    ).all()

    return {
        "original": {
            "id": original.id,
            "prompt": original.prompt,
            "created_at": original.created_at
        },
        "versions": [
            {
                "id": v.id,
                "prompt": v.prompt,
                "created_at": v.created_at
            }
            for v in versions
        ]
    }

@router.post("/ai/generate")
@limiter.limit("5/minute")
async def generate_api(
    request: Request,
    ai_request: AIRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import time
    start_time = time.time()

    cache_key = f"ai_generate:{ai_request.provider}:{ai_request.description}"

    try:
        cached_result = get_redis_client().get(cache_key)
    except Exception:
        cached_result = None

    if cached_result:
        response_time = time.time() - start_time

        def log_cache_hit():
            log = AIUsageLog(
                user_id=current_user.id,
                provider=ai_request.provider,
                prompt=ai_request.description,
                response_time=response_time,
                from_cache=True
            )
            db.add(log)
            db.commit()

        background_tasks.add_task(log_cache_hit)

        return {
            "status": "success",
            "provider": ai_request.provider,
            "generated_code": cached_result,
            "from_cache": True
        }

    try:
        provider = get_ai_provider(ai_request.provider)
        result = await provider.generate_code(ai_request.description)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "provider": ai_request.provider,
                "message": "AI provider temporarily unavailable. Please try again later."
            }
        )

    response_time = time.time() - start_time

    try:
        get_redis_client().set(cache_key, result)
    except Exception:
        pass

    def save_to_db():
        saved_record = GeneratedAPI(
            user_id=current_user.id,
            prompt=ai_request.description,
            generated_code=result,
            provider=ai_request.provider,
            parent_id=ai_request.parent_id
        )
        db.add(saved_record)
        db.commit()
        db.refresh(saved_record)

        log = AIUsageLog(
            user_id=current_user.id,
            provider=ai_request.provider,
            prompt=ai_request.description,
            response_time=response_time,
            from_cache=False
        )
        db.add(log)
        db.commit()

    background_tasks.add_task(save_to_db)

    return {
        "status": "success",
        "provider": ai_request.provider,
        "generated_code": result,
        "from_cache": False,
        "message": "Generation complete, saving in background"
    }


@router.post("/ai/schema")
async def generate_schema(
    request: AIRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        provider = get_ai_provider(request.provider)
        result = await provider.generate_api_schema(request.description)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "provider": request.provider,
                "message": "AI provider temporarily unavailable. Please try again later."
            }
        )

    saved_record = GeneratedAPI(
        user_id=current_user.id,
        prompt=request.description,
        generated_code=result.get("openapi_spec", ""),
        provider=request.provider
    )
    db.add(saved_record)
    db.commit()
    db.refresh(saved_record)

    return {
        "status": "success",
        "provider": request.provider,
        "openapi_spec": result.get("openapi_spec"),
        "saved_id": saved_record.id
    }

@router.get("/ai/history")
async def get_history(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 10,
    search: str = None
):
    query = db.query(GeneratedAPI).filter(
        GeneratedAPI.user_id == current_user.id,
        or_(GeneratedAPI.is_deleted == False, GeneratedAPI.is_deleted == None)
    )

    if search:
        query = query.filter(
            GeneratedAPI.prompt.ilike(f"%{search}%")
        )

    total = query.count()
    records = query.order_by(GeneratedAPI.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit,
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
@router.delete("/ai/history/{generation_id}")
async def delete_generation(
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

    record.is_deleted = True
    db.commit()

    return {
        "status": "success",
        "message": f"Generation {generation_id} deleted"
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


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check Redis
    try:
        get_redis_client().ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
        "ai_provider": "groq"
    }


@router.get("/ai/usage")
async def get_usage(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(AIUsageLog).filter(
        AIUsageLog.user_id == current_user.id
    ).all()

    total_requests = len(logs)
    cache_hits = sum(1 for log in logs if log.from_cache)
    avg_response_time = sum(log.response_time for log in logs) / total_requests if total_requests > 0 else 0

    provider_usage = {}
    for log in logs:
        provider_usage[log.provider] = provider_usage.get(log.provider, 0) + 1

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_miss": total_requests - cache_hits,
        "avg_response_time": round(avg_response_time, 3),
        "provider_usage": provider_usage
    }

class EditRequest(BaseModel):
    generation_id: int
    instruction: str
    provider: str = "groq"

@router.post("/ai/edit")
async def edit_generated_api(
    edit_request: EditRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    original = db.query(GeneratedAPI).filter(
        GeneratedAPI.id == edit_request.generation_id,
        GeneratedAPI.user_id == current_user.id
    ).first()

    if not original:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Build conversation history by walking up the version chain
    history = []
    current = original
    while current:
        history.insert(0, current)
        if current.parent_id:
            current = db.query(GeneratedAPI).filter(
                GeneratedAPI.id == current.parent_id
            ).first()
        else:
            break

    # Build context from history
    context = ""
    for i, record in enumerate(history):
        if i == 0:
            context += f"Original code:\n{record.generated_code}\n\n"
        else:
            instruction = record.prompt.replace("EDIT: ", "")
            context += f"After edit '{instruction}':\n{record.generated_code}\n\n"

    try:
        provider = get_ai_provider(edit_request.provider)
        prompt = f"""Here is the complete history of this API and all its edits:

{context}

Now apply this new instruction to the LATEST version: {edit_request.instruction}

Return only the modified Python code, no explanation."""

        result = await provider.generate(prompt)
    except Exception as e:
        print(f"AI provider error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "provider": edit_request.provider,
                "message": "AI provider temporarily unavailable. Please try again later."
            }
        )

    def save_edited():
        edited_record = GeneratedAPI(
            user_id=current_user.id,
            prompt=f"EDIT: {edit_request.instruction}",
            generated_code=result,
            provider=edit_request.provider,
            parent_id=edit_request.generation_id
        )
        db.add(edited_record)
        db.commit()

    background_tasks.add_task(save_edited)

    return {
        "status": "success",
        "provider": edit_request.provider,
        "original_id": edit_request.generation_id,
        "instruction": edit_request.instruction,
        "edited_code": result,
        "context_versions": len(history),
        "message": "Edit complete with full conversation memory"
    }

