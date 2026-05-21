from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter
from database import engine
from models import Base
from route.users import router as users_router
from route.auth import router as auth_router

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Base.metadata.create_all(bind=engine)

app.include_router(users_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "AI API Builder is running!"}