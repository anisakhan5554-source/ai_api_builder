from logs.logger_config import logger
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter
from database import engine
from models import Base
from route.users import router as users_router
from route.auth import router as auth_router
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from route.ai import router as ai_router
from contextlib import asynccontextmanager
import os
from route.projects import router as projects_router
from route.documents import router as documents_router
from route import rag

@asynccontextmanager
async def lifespan(app: FastAPI):
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "GROQ_API_KEY",
        "REDIS_URL",
        "REDIS_TOKEN"
    ]
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        logger.warning(f"Missing environment variables: {missing}")
    else:
        logger.info("All required environment variables are set")

    yield

app = FastAPI(
    lifespan=lifespan,
    title="AI API Builder",
    description="""
## AI-Powered API Generator

Generate, save, version, and export FastAPI code using AI.

### Features
- 🤖 AI code generation using Groq (Llama 3.3)
- 💾 Save and version generated APIs
- 📤 Export generated code as .py files
- 📊 Dashboard stats and history
- 🔐 JWT Authentication with RBAC
- ⚡ Redis caching for fast responses
- 🚀 Production-ready with Railway deployment
    """,
    version="1.0.0",
    contact={
        "name": "Anisa Khan",
        "url": "https://github.com/anisakhan5554-source/ai_api_builder"
    }
)

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://aiapibuilder-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Base.metadata.create_all(bind=engine)

app.include_router(users_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag.router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation failed",
            "details": str(exc.errors())
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Something went wrong"
        }
    )

@app.get("/")
def root():
    return {"message": "AI API Builder is running!"}