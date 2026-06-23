import os
from dotenv import  load_dotenv
from upstash_redis import Redis

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL")
REDIS_TOKEN = os.environ.get("REDIS_TOKEN")



redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
