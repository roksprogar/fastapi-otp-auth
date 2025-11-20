import secrets
import logging
import redis.asyncio as redis
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordBearer

from pydantic import BaseModel, EmailStr

from fastapi_otp_auth.cache import get_redis_client
from fastapi_otp_auth.email import EmailService, get_email_service
from fastapi_otp_auth.config import settings
from fastapi_otp_auth.utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from fastapi_otp_auth.blacklist import blacklist_token, is_token_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestOtpRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


router = APIRouter()


@router.post("/request-otp")
async def request_otp(
    payload: RequestOtpRequest,
    redis: redis.Redis = Depends(get_redis_client),
    email_service: EmailService = Depends(get_email_service),
):
    email = payload.email

    # Rate Limiting
    rate_limit_key = f"rate_limit:{email}"
    current_requests = await redis.incr(rate_limit_key)
    if current_requests == 1:
        await redis.expire(rate_limit_key, 60)  # Reset every minute

    if current_requests > settings.otp_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again later.",
        )

    # Generate 6-digit cryptographically secure OTP
    otp = "".join([str(secrets.choice("0123456789")) for _ in range(6)])

    # Store OTP in Redis with expiry from settings
    redis_key = f"{settings.otp_key_prefix}{email}"
    await redis.setex(name=redis_key, time=settings.otp_expiry_seconds, value=otp)

    logger.info(f"OTP generated for {email}")

    # Send OTP via email
    result = await email_service.send_email(
        email,
        "Your verification code",
        f"Your verification code is: {otp}",
    )

    if result.get("status") == "error":
        logger.error(f"Failed to send email to {email}: {result.get('message')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email.",
        )

    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
async def verify_otp(
    payload: VerifyOTPRequest,
    response: Response,
    redis: redis.Redis = Depends(get_redis_client),
):
    email = payload.email
    otp = payload.otp

    # Verify OTP
    redis_key = f"{settings.otp_key_prefix}{email}"
    stored_otp = await redis.get(redis_key)

    # Check for max attempts
    attempts_key = f"attempts:{email}"
    current_attempts = await redis.get(attempts_key)
    if current_attempts and int(current_attempts) >= settings.otp_max_verify_attempts:
        await redis.delete(redis_key)
        await redis.delete(attempts_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. OTP has been invalidated.",
        )

    if stored_otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired or not requested. Please request a new one.",
        )

    if stored_otp == otp:
        # Delete the OTP from Redis immediately after successful verification
        await redis.delete(redis_key)
        await redis.delete(attempts_key)

        # Generate tokens
        access_token = create_access_token(data={"sub": email})
        refresh_token = create_refresh_token(data={"sub": email})

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        )

        return {
            "message": "OTP verified successfully!",
            "access_token": access_token,
            "token_type": "bearer",
        }

    # Invalid OTP
    await redis.incr(attempts_key)
    await redis.expire(attempts_key, settings.otp_expiry_seconds)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP provided."
    )


@router.post("/logout")
async def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    refresh_token: Optional[str] = Cookie(None),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    # Blacklist access token
    payload = verify_token(token, "access")
    if payload:
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                await blacklist_token(redis_client, jti, ttl)

    # Blacklist refresh token
    if refresh_token:
        payload = verify_token(refresh_token, "refresh")
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                now = datetime.now(timezone.utc).timestamp()
                ttl = int(exp - now)
                if ttl > 0:
                    await blacklist_token(redis_client, jti, ttl)

    # Clear cookie
    response.delete_cookie("refresh_token")

    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(
    refresh_token: Optional[str] = Cookie(None),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(redis_client, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    email = payload.get("sub")
    access_token = create_access_token(data={"sub": email})

    return {"access_token": access_token, "token_type": "bearer"}
