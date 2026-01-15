"""
Pytest configuration and fixtures for testing.
"""
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.tests.fixtures.zerodb_mock import MockZeroDBClient
from unittest.mock import patch

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


@pytest.fixture
def mock_zerodb_client():
    """
    Provide a fresh MockZeroDBClient instance for each test.

    The client is reset before each test to ensure isolation.
    """
    client = MockZeroDBClient()
    client.reset()
    return client


@pytest.fixture(autouse=True)
def override_zerodb_client(monkeypatch, mock_zerodb_client):
    """
    Automatically override get_zerodb_client() for all tests.

    This ensures that all service instances use the mock client
    instead of attempting to connect to the real ZeroDB API.

    autouse=True means this fixture runs for every test automatically.
    """
    # Patch the get_zerodb_client function in the zerodb_client module
    monkeypatch.setattr(
        "app.services.zerodb_client.get_zerodb_client",
        lambda: mock_zerodb_client
    )

    # Also patch it in service modules that import it directly
    monkeypatch.setattr(
        "app.services.agent_memory_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.agent_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.compliance_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.x402_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.event_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.table_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )
    monkeypatch.setattr(
        "app.services.row_service.get_zerodb_client",
        lambda: mock_zerodb_client
    )

    return mock_zerodb_client


@pytest.fixture
def sample_embedding_384():
    """
    Sample 384-dimensional embedding vector.

    Issue #79: Default model BAAI/bge-small-en-v1.5 produces 384 dimensions.
    Use this fixture for all embedding tests.
    """
    return [0.1] * 384


@pytest.fixture
def sample_embeddings_384():
    """
    Sample list of 384-dimensional embedding vectors.

    Issue #79: For batch embedding tests with 384-dim default model.
    """
    return [[0.1] * 384, [0.2] * 384, [0.3] * 384]


@pytest.fixture
def sample_embedding_768():
    """
    Sample 768-dimensional embedding vector.

    For testing models like BAAI/bge-base-en-v1.5 or all-mpnet-base-v2.
    """
    return [0.1] * 768


@pytest.fixture
def sample_embedding_1536():
    """
    Sample 1536-dimensional embedding vector.

    For testing OpenAI text-embedding-ada-002 compatibility.
    """
    return [0.1] * 1536
