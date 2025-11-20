import redis.asyncio as redis
from fastapi_otp_auth.config import settings


async def blacklist_token(redis_client: redis.Redis, jti: str, expires_in: int):
    """
    Blacklist a token by its JTI.
    expires_in: Time in seconds until the token expires.
    """
    key = f"{settings.blacklist_key_prefix}{jti}"
    await redis_client.setex(key, expires_in, "blacklisted")


async def is_token_blacklisted(redis_client: redis.Redis, jti: str) -> bool:
    """
    Check if a token JTI is blacklisted.
    """
    key = f"{settings.blacklist_key_prefix}{jti}"
    return await redis_client.exists(key) > 0
