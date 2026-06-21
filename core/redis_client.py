import os
from upstash_redis import Redis

REDIS_URL = os.environ.get("REDIS_URL")
REDIS_TOKEN = os.environ.get("REDIS_TOKEN")

print("RAILWAY REDIS_URL:", repr(REDIS_URL))
print("RAILWAY REDIS_TOKEN:", repr(REDIS_TOKEN))

redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
