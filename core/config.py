
from dotenv import load_dotenv
import os


load_dotenv()

SECRET_KEY=os.getenv("SECRET_KEY","fallback_secret")
DATABASE_URL = os.getenv("DATABASE_URL")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
)