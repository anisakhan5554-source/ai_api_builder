import os
from upstash_redis import Redis

REDIS_URL = os.environ.get("REDIS_URL")
REDIS_TOKEN = os.environ.get("REDIS_TOKEN")

redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)