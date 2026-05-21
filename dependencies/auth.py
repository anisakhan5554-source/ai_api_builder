from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from database import get_db
from models import User

from core.config import SECRET_KEY

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):

    try:

        token = credentials.credentials

        decoded = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        current_user = db.query(User).filter(
            User.email == decoded["email"]
        ).first()

        if not current_user:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return current_user

    except ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )