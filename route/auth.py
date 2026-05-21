from fastapi import APIRouter, Depends
from jose import jwt
from datetime import datetime, timedelta, timezone
from database import get_db
from schemas import UserLogin
from models import User
from passlib.context import CryptContext
from core.config import SECRET_KEY
from dependencies.auth import get_current_user
from logs.logger_config import logger
from fastapi import Request
from core.limiter import limiter
from sqlalchemy.orm import Session


router = APIRouter()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

@router.post("/login")
@limiter.limit("5/minute")
def login(
        request:Request,
         data: UserLogin,
    db:Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if user and pwd_context.verify(
        data.password,
        user.password
    ):

        token = jwt.encode(
            {
                "email": data.email,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            },
            SECRET_KEY,
            algorithm="HS256"
        )

        logger.info(
            f"User logged in: {user.email}"
        )

        return {
            "status": "success",
            "message": "Login successful",
            "token": token
        }

    return {
        "status": "failed",
        "message": "Invalid credentials"
    }


@router.get("/profile")
def profile(
    current_user: User = Depends(get_current_user)
):

    return {
        "status": "success",
        "message": "Protected route accessed",
        "user_email": current_user.email
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):

    return {
        "status": "success",
        "name": current_user.name,
        "email": current_user.email
    }

