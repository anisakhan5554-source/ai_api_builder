import os
from dotenv import load_dotenv
import redis

load_dotenv()

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL")
        _redis_client = redis.from_url(redis_url,)
    return _redis_client