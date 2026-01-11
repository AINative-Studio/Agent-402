"""
Pytest configuration and fixtures for testing.
"""
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings

# Import the simple version for testing
# Avoids complex middleware that interferes with dependency-based auth
try:
    from app.main_simple import app
except ImportError:
    from app.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture
def valid_api_key_user1():
    """Valid API key for user 1."""
    return settings.demo_api_key_1


@pytest.fixture
def valid_api_key_user2():
    """Valid API key for user 2."""
    return settings.demo_api_key_2


@pytest.fixture
def invalid_api_key():
    """Invalid API key for testing authentication failures."""
    return "invalid_key_xyz"


@pytest.fixture
def auth_headers_user1(valid_api_key_user1):
    """Authentication headers for user 1."""
    return {"X-API-Key": valid_api_key_user1}


@pytest.fixture
def auth_headers_user2(valid_api_key_user2):
    """Authentication headers for user 2."""
    return {"X-API-Key": valid_api_key_user2}


@pytest.fixture
def invalid_auth_headers(invalid_api_key):
    """Invalid authentication headers."""
    return {"X-API-Key": invalid_api_key}
