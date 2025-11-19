from fastapi_otp_auth.auth_router import router as auth_router
from fastapi_otp_auth.dependencies import get_current_user
from fastapi_otp_auth.config import settings, Settings
from fastapi_otp_auth.email import EmailService

__all__ = ["auth_router", "get_current_user", "settings", "Settings", "EmailService"]
