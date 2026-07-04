import os
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        url = os.environ.get("REDIS_URL")
        token = os.environ.get("REDIS_TOKEN")
        _redis_client = Redis(url=url, token=token)
    return _redis_client