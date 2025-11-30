import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_otp_auth.auth_router import router
from fastapi_otp_auth.email import get_email_service
from fastapi_otp_auth.config import settings

# Create test app
app = FastAPI()
app.include_router(router)

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
    mock_redis_instance = AsyncMock()
    from fastapi_otp_auth.auth_router import get_redis_client
    app.dependency_overrides[get_redis_client] = lambda: mock_redis_instance
    
    # Defaults
    mock_redis_instance.incr.return_value = 1
    
    yield mock_redis_instance
    
    app.dependency_overrides = {}
    app.dependency_overrides[get_email_service] = lambda: mock_email_service

def test_magic_otp_flow(mock_redis):
    """Test the entire Magic OTP flow"""
    email = "magic@example.com"
    
    # Enable Magic OTP
    with patch.object(settings, 'disable_local_auth', True):
        # 1. Request OTP
        response = client.post("/request-otp", json={"email": email})
        
        assert response.status_code == 200
        assert response.json() == {"message": "OTP sent successfully"}
        
        # Verify email was NOT called
        mock_email_service.send_email.assert_not_called()
        
        # Verify 000000 was stored in Redis
        # Note: The code stores "000000" in Redis
        mock_redis.setex.assert_called_with(
            name=f"otp_{email}",
            time=300,
            value="000000"
        )
        
        # 2. Verify OTP
        # Mock Redis get to return "000000"
        def side_effect(key):
            if "otp_" in key:
                return "000000"
            return None
        mock_redis.get.side_effect = side_effect
        
        response = client.post("/verify-otp", json={"email": email, "otp": "000000"})
        
        assert response.status_code == 200
        assert response.json()["message"] == "OTP verified successfully!"

def test_magic_otp_disabled(mock_redis):
    """Test that Magic OTP doesn't work when disabled"""
    email = "normal@example.com"
    
    # Ensure disabled (default)
    with patch.object(settings, 'disable_local_auth', False):
        response = client.post("/request-otp", json={"email": email})
        
        assert response.status_code == 200
        
        # Verify email WAS called
        mock_email_service.send_email.assert_called()
        
        # Verify random OTP was stored (not 000000)
        args, kwargs = mock_redis.setex.call_args
        stored_otp = kwargs['value']
        assert stored_otp != "000000"
        assert len(stored_otp) == 6
