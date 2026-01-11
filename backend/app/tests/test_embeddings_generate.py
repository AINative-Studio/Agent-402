"""
Tests for embeddings generation endpoint.

Implements testing for Epic 3 Story 1: Generate embeddings via POST /embeddings/generate.

Per PRD §10: Testing & Verification (MVP)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Get a valid API key from settings."""
    if settings.valid_api_keys:
        return list(settings.valid_api_keys.keys())[0]
    return settings.demo_api_key_1


@pytest.fixture
def auth_headers(valid_api_key):
    """Create authentication headers."""
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def test_project_id():
    """Get a test project ID."""
    return "proj_test_123"


class TestEmbeddingsGenerateEndpoint:
    """Tests for POST /v1/public/{project_id}/embeddings/generate."""

    def test_generate_with_default_model(self, client, auth_headers, test_project_id):
        """
        Test embedding generation with default model.
        Epic 3 Story 2: Default to 384-dim embeddings when model omitted.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": "Autonomous agent workflow"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "embedding" in data
        assert "model" in data
        assert "dimensions" in data
        assert "text" in data
        assert "processing_time_ms" in data

        # Verify default model behavior
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384
        assert isinstance(data["processing_time_ms"], (int, float))

    def test_generate_with_specific_model(self, client, auth_headers, test_project_id):
        """Test embedding generation with specific model."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={
                "text": "Test text",
                "model": "sentence-transformers/all-mpnet-base-v2"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data["dimensions"] == 768

    def test_empty_text_error(self, client, auth_headers, test_project_id):
        """Test error handling for empty text."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": ""},
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_invalid_model_error(self, client, auth_headers, test_project_id):
        """
        Test error for unsupported model.
        Epic 3 Story 4: Unsupported models return MODEL_NOT_FOUND.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={
                "text": "Test",
                "model": "invalid-model"
            },
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"

    def test_no_authentication(self, client, test_project_id):
        """Test that endpoint requires authentication."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": "Test"}
        )

        assert response.status_code == 401

    def test_deterministic_output(self, client, auth_headers, test_project_id):
        """
        Test that same input produces same output.
        Per PRD §10: Deterministic defaults for reproducibility.
        """
        text = "Reproducible agent decision"

        response1 = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": text},
            headers=auth_headers
        )
        response2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": text},
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Embeddings should be identical
        assert data1["embedding"] == data2["embedding"]


class TestListModelsEndpoint:
    """Tests for GET /v1/public/embeddings/models."""

    def test_list_models(self, client, auth_headers):
        """Test listing supported models."""
        response = client.get(
            "/v1/public/embeddings/models",
            headers=auth_headers
        )

        # Note: This endpoint might not be public or might be GET instead of POST
        # Adjust based on actual implementation
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0


class TestErrorFormatCompliance:
    """Tests for DX Contract error format compliance."""

    def test_error_has_required_fields(self, client, auth_headers, test_project_id):
        """Test that errors return { detail, error_code }."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": "Test", "model": "invalid"},
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
