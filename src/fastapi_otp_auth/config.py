from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"

    # Email settings
    smtp_server: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = "user@example.com"
    smtp_password: str = "password"
    mail_from_name: str = "FastAPI App"

    # OTP settings
    otp_expiry_seconds: int = 300  # 5 minutes
    otp_key_prefix: str = "otp_"
    otp_rate_limit_per_minute: int = 5
    otp_max_verify_attempts: int = 5
    blacklist_key_prefix: str = "blacklist_"

    # Local Auth Bypass
    disable_local_auth: bool = False

    # Cookie settings
    cookie_secure: bool = True

    # JWT settings
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_days: int = 7  # 7 days

    model_config = SettingsConfigDict(env_prefix="FASTAPI_OTP_AUTH_")


settings = Settings()
