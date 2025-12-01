from fastapi import HTTPException, status, Depends
import redis.asyncio as redis
from fastapi_otp_auth.cache import get_redis_client
from fastapi_otp_auth.config import settings


class OtpRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check(self, email: str):
        rate_limit_key = f"rate_limit:{email}"
        current_requests = await self.redis.incr(rate_limit_key)
        if current_requests == 1:
            await self.redis.expire(rate_limit_key, 60)  # Reset every minute

        if current_requests > settings.otp_rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please try again later.",
            )


async def get_otp_rate_limiter(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> OtpRateLimiter:
    return OtpRateLimiter(redis_client)
