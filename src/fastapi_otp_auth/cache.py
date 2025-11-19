import os
import redis.asyncio as redis

from fastapi_otp_auth.config import settings

async def get_redis_client() -> redis.Redis:
    return await redis.from_url(settings.redis_url, decode_responses=True)
