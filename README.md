# FastAPI OTP Auth

[![PyPI version](https://badge.fury.io/py/fastapi-otp-auth.svg)](https://badge.fury.io/py/fastapi-otp-auth)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


A simple and robust OTP (One-Time Password) authentication library for FastAPI, backed by Redis and Email.

## Features

- 🔐 **Secure OTP Generation**: Cryptographically secure 6-digit codes.
- 🎫 **JWT Support**: Auto-generates Access and Refresh tokens upon verification.
- 🍪 **HttpOnly Cookies**: Securely stores refresh tokens in HttpOnly cookies.
- ⚡ **Redis-Backed**: Fast and reliable storage for OTPs with automatic expiration.
- 📧 **Email Delivery**: Integrated email sending using `fastapi-mail`.
- 🔌 **Easy Integration**: Drop-in `APIRouter` for quick setup.
- ⚙️ **Configurable**: Fully customizable via environment variables.
- 🚫 **Token Blacklisting**: Secure logout and immediate token revocation.

## Installation

```bash
pip install fastapi-otp-auth
```

Or using Poetry:

```bash
poetry add fastapi-otp-auth
```

## Configuration

The library is configured using environment variables. The prefix for all variables is `FASTAPI_OTP_AUTH_`.

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTAPI_OTP_AUTH_REDIS_URL` | Connection string for Redis | `redis://localhost:6379/0` |
| `FASTAPI_OTP_AUTH_SMTP_SERVER` | SMTP server hostname | `127.0.0.1` |
| `FASTAPI_OTP_AUTH_SMTP_PORT` | SMTP server port | `1025` |
| `FASTAPI_OTP_AUTH_SMTP_USERNAME` | SMTP username | `user@example.com` |
| `FASTAPI_OTP_AUTH_SMTP_PASSWORD` | SMTP password | `password` |
| `FASTAPI_OTP_AUTH_MAIL_FROM_NAME` | Sender name for emails | `FastAPI App` |
| `FASTAPI_OTP_AUTH_OTP_EXPIRY_SECONDS` | OTP validity duration in seconds | `300` (5 minutes) |
| `FASTAPI_OTP_AUTH_OTP_KEY_PREFIX` | Prefix for Redis keys | `otp_` |
| `FASTAPI_OTP_AUTH_JWT_SECRET` | Secret key for signing JWTs | `change-me-in-production` |
| `FASTAPI_OTP_AUTH_JWT_ALGORITHM` | Algorithm for JWTs | `HS256` |
| `FASTAPI_OTP_AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `60` (1 hour) |
| `FASTAPI_OTP_AUTH_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` (7 days) |
| `FASTAPI_OTP_AUTH_BLACKLIST_KEY_PREFIX` | Prefix for blacklisted tokens in Redis | `blacklist_` |

## Usage

Import the `auth_router` and include it in your FastAPI application:

```python
from fastapi import FastAPI
from fastapi_otp_auth.auth_router import router as auth_router

app = FastAPI()

# Include the router
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# The following endpoints will be available:
# POST /auth/request-otp - Request a new OTP
# POST /auth/verify-otp  - Verify a received OTP
# POST /auth/logout      - Logout and blacklist tokens

```

### Requesting an OTP

Send a POST request to `/auth/request-otp`:

```json
{
  "email": "user@example.com"
}
```

### Verifying an OTP

Send a POST request to `/auth/verify-otp`:

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

On success, the response will contain the access token, and the refresh token will be set as an `HttpOnly` cookie:

```json
{
  "message": "OTP verified successfully!",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Protecting Routes

Use the `get_current_user` dependency to protect routes. This will verify the access token and return the user's email.

```python
from fastapi import Depends
from fastapi_otp_auth.dependencies import get_current_user

@app.get("/protected")
async def protected_route(user: str = Depends(get_current_user)):
    return {"message": f"Hello, {user}!"}
```

### Refreshing Tokens

To get a new access token using the `HttpOnly` refresh token cookie, send a POST request to `/auth/refresh`. The browser will automatically include the cookie.

```bash
POST /auth/refresh
```

Response:

```json
{
  "access_token": "new_access_token_here",
  "token_type": "bearer"
}
```

```

### Logging Out

To logout, send a POST request to `/auth/logout`. This will blacklist both the access token (provided in the Authorization header) and the refresh token (provided in the cookie).

```bash
POST /auth/logout
Authorization: Bearer <access_token>
Cookie: refresh_token=<refresh_token>
```

Response:

```json
{
  "message": "Successfully logged out"
}
```

## Development

To run tests locally using Docker (no local environment needed):

```bash
make test
```

This will spin up a Redis container and run the test suite in an isolated environment.

### Running Checks

To run linting checks (ruff) using Docker:

```bash
docker-compose -f docker-compose.test.yml run --rm app-test ruff check .
```

### Pre-commit Hooks

To automatically run checks before every commit, install the pre-commit hooks:

```bash
poetry run pre-commit install
```

You can also run the hooks manually against all files:

```bash
poetry run pre-commit run --all-files
```
