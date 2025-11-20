import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from fastapi_otp_auth.auth_router import router
from fastapi_otp_auth.email import get_email_service
from fastapi_otp_auth.dependencies import get_current_user

# Create test app
app = FastAPI()
app.include_router(router)


@app.get("/protected")
async def protected_route(user: str = Depends(get_current_user)):
    return {"user": user}


# Mock EmailService
mock_email_service = AsyncMock()
mock_email_service.send_email.return_value = {
    "status": "success",
    "message": "Email sent",
}

# Override dependency
app.dependency_overrides[get_email_service] = lambda: mock_email_service

client = TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch("fastapi_otp_auth.auth_router.get_redis_client"):
        # Create a mock Redis instance
        mock_redis_instance = AsyncMock()
        # We need to override the dependency, not patch the module level redis_client which doesn't exist anymore in the same way
        # But wait, the router uses Depends(get_redis_client).
        # So we should override the dependency in the app.
        pass

    # Better way to mock redis for the app
    mock_redis_instance = AsyncMock()
    app.dependency_overrides["fastapi_otp_auth.auth_router.get_redis_client"] = (
        lambda: mock_redis_instance
    )
    # Actually, we need to override the function itself in the app overrides
    from fastapi_otp_auth.auth_router import get_redis_client

    app.dependency_overrides[get_redis_client] = lambda: mock_redis_instance

    # Default exists to 0 (not blacklisted)
    mock_redis_instance.exists.return_value = 0

    yield mock_redis_instance

    # Clean up
    app.dependency_overrides = {}
    # Restore email service override as it was global for the module but cleared here
    app.dependency_overrides[get_email_service] = lambda: mock_email_service


@pytest.fixture
def test_email():
    return "test@example.com"


@pytest.fixture
def test_otp():
    return "123456"


def test_request_otp_success(mock_redis, test_email):
    """Test successful OTP request"""
    response = client.post("/request-otp", json={"email": test_email})

    assert response.status_code == 200
    assert response.json() == {"message": "OTP sent successfully"}

    # Verify email was sent
    mock_email_service.send_email.assert_called()


def test_request_otp_email_failure(mock_redis, test_email):
    """Test OTP request when email sending fails"""
    # Setup mock to fail
    mock_email_service.send_email.return_value = {
        "status": "error",
        "message": "SMTP Error",
    }

    response = client.post("/request-otp", json={"email": test_email})

    assert response.status_code == 500
    assert "Failed to send OTP email" in response.json()["detail"]

    # Reset mock
    mock_email_service.send_email.return_value = {
        "status": "success",
        "message": "Email sent",
    }


def test_request_otp_invalid_email():
    """Test OTP request with invalid email"""
    response = client.post("/request-otp", json={"email": "invalid-email"})

    assert response.status_code == 422


def test_verify_otp_success(mock_redis, test_email, test_otp):
    """Test successful OTP verification"""
    # Mock the Redis get to return our test OTP
    mock_redis.get.return_value = test_otp

    response = client.post("/verify-otp", json={"email": test_email, "otp": test_otp})

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "OTP verified successfully!"
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"

    # Verify cookie
    assert "refresh_token" in response.cookies

    # Verify that the OTP was deleted from Redis
    mock_redis.delete.assert_called_once_with(f"otp_{test_email}")


def test_verify_otp_expired(mock_redis, test_email):
    """Test OTP verification with expired OTP"""
    # Mock the Redis get to return None (expired)
    mock_redis.get.return_value = None

    response = client.post("/verify-otp", json={"email": test_email, "otp": "123456"})

    assert response.status_code == 400
    assert "OTP expired or not requested" in response.json()["detail"]


def test_verify_otp_invalid(mock_redis, test_email, test_otp):
    """Test OTP verification with invalid OTP"""
    # Mock the Redis get to return a different OTP
    mock_redis.get.return_value = "654321"

    response = client.post("/verify-otp", json={"email": test_email, "otp": test_otp})

    assert response.status_code == 400
    assert "Invalid OTP provided" in response.json()["detail"]


def test_verify_otp_invalid_email():
    """Test OTP verification with invalid email"""
    response = client.post(
        "/verify-otp", json={"email": "invalid-email", "otp": "123456"}
    )

    assert response.status_code == 422


def test_refresh_token_success(mock_redis, test_email, test_otp):
    """Test successful token refresh"""
    # First get a valid refresh token by verifying OTP
    mock_redis.get.return_value = test_otp
    verify_response = client.post(
        "/verify-otp", json={"email": test_email, "otp": test_otp}
    )
    refresh_token = verify_response.cookies["refresh_token"]

    # Now use the refresh token to get a new access token
    response = client.post("/refresh", cookies={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_refresh_token_missing():
    """Test refresh with missing cookie"""
    response = client.post("/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token missing"


def test_refresh_token_invalid():
    """Test refresh with invalid token"""
    response = client.post("/refresh", cookies={"refresh_token": "invalid.token.here"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


def test_protected_route_success(mock_redis, test_email, test_otp):
    """Test accessing a protected route with valid access token"""
    # Get access token
    mock_redis.get.return_value = test_otp
    verify_response = client.post(
        "/verify-otp", json={"email": test_email, "otp": test_otp}
    )
    access_token = verify_response.json()["access_token"]

    # Access protected route
    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"user": test_email}


def test_protected_route_unauthorized():
    """Test accessing a protected route without token"""
    response = client.get("/protected")
    assert response.status_code == 401


def test_logout_success(mock_redis, test_email, test_otp):
    """Test successful logout"""
    # Get tokens
    mock_redis.get.return_value = test_otp
    verify_response = client.post(
        "/verify-otp", json={"email": test_email, "otp": test_otp}
    )
    access_token = verify_response.json()["access_token"]
    refresh_token = verify_response.cookies["refresh_token"]

    # Logout
    response = client.post(
        "/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}

    # Verify cookie cleared
    assert (
        'refresh_token=""' in response.headers["set-cookie"]
        or "refresh_token=;" in response.headers["set-cookie"]
    )


def test_access_revoked_token(mock_redis, test_email, test_otp):
    """Test accessing protected route with revoked token"""
    # Get tokens
    mock_redis.get.return_value = test_otp
    verify_response = client.post(
        "/verify-otp", json={"email": test_email, "otp": test_otp}
    )
    access_token = verify_response.json()["access_token"]

    # Mock blacklist check to return True (revoked)
    # We need to mock the redis.exists call which is used by is_token_blacklisted
    mock_redis.exists.return_value = 1

    # Access protected route
    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked"


def test_refresh_revoked_token(mock_redis, test_email, test_otp):
    """Test refreshing with revoked refresh token"""
    # Get tokens
    mock_redis.get.return_value = test_otp
    verify_response = client.post(
        "/verify-otp", json={"email": test_email, "otp": test_otp}
    )
    refresh_token = verify_response.cookies["refresh_token"]

    # Mock blacklist check to return True (revoked)
    mock_redis.exists.return_value = 1

    # Try to refresh
    response = client.post("/refresh", cookies={"refresh_token": refresh_token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token has been revoked"
