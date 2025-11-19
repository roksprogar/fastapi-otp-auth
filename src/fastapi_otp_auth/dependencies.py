from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

import redis.asyncio as redis
from fastapi_otp_auth.utils import verify_token
from fastapi_otp_auth.cache import get_redis_client
from fastapi_otp_auth.blacklist import is_token_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> str:
    payload = verify_token(token, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(redis_client, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return email
