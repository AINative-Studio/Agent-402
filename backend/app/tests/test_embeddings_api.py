"""
Tests for embeddings API endpoints.

Implements testing for Epic 3 (Embeddings: Generate).

Test Coverage:
- POST /v1/public/embeddings/generate
- GET /v1/public/embeddings/models
- GET /v1/public/embeddings/models/{model_name}

Per PRD §10: Testing & Verification (MVP)
Per Epic 3: All user stories for embeddings generation
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
    # Use first API key from settings
    if settings.valid_api_keys:
        return list(settings.valid_api_keys.keys())[0]
    return "test_api_key_abc123"


@pytest.fixture
def auth_headers(valid_api_key):
    """Create authentication headers."""
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def test_project_id():
    """Get a test project ID."""
    return "proj_test_abc123"


class TestEmbeddingsGenerate:
    """Tests for POST /v1/public/embeddings/generate endpoint."""

    def test_generate_embeddings_success_default_model(self, client, auth_headers, test_project_id):
        """
        Test successful embedding generation with default model.

        Epic 3 Story 2: Default to 384-dim embeddings when model is omitted.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={"text": "Test autonomous agent workflow"},
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert "embedding" in data
        assert "model" in data
        assert "dimensions" in data
        assert "text" in data
        assert "processing_time_ms" in data

        # Verify default model is used
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384
        assert data["text"] == "Test autonomous agent workflow"
        assert data["processing_time_ms"] >= 0

    def test_generate_embeddings_with_specific_model(self, client, auth_headers, test_project_id):
        """
        Test embedding generation with specific model.

        Epic 3 Story 3: Support multiple models with correct dimensions.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/generate",
            json={
                "text": "Fintech compliance check",
                "model": "sentence-transformers/all-mpnet-base-v2"
            },
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data["dimensions"] == 768
        assert len(data["embedding"]) == 768

    def test_generate_embeddings_empty_text(self, client, auth_headers):
        """
        Test error handling for empty text input.

        Per Epic 3: Proper error handling for invalid input.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": ""},
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_generate_embeddings_whitespace_only(self, client, auth_headers):
        """Test error handling for whitespace-only text."""
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "   "},
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_generate_embeddings_invalid_model(self, client, auth_headers):
        """
        Test error handling for unsupported model.

        Epic 3 Story 4: Unsupported models return MODEL_NOT_FOUND.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={
                "text": "Test text",
                "model": "invalid-model-xyz"
            },
            headers=auth_headers
        )

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"
        assert "invalid-model-xyz" in data["detail"]

    def test_generate_embeddings_missing_text(self, client, auth_headers):
        """Test error handling when text field is missing."""
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"model": "BAAI/bge-small-en-v1.5"},
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_generate_embeddings_no_auth(self, client):
        """
        Test authentication requirement.

        Epic 2 Story 1: All public endpoints require X-API-Key.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test text"}
        )

        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_generate_embeddings_invalid_api_key(self, client):
        """
        Test invalid API key handling.

        Epic 2 Story 2: Invalid API keys return 401 INVALID_API_KEY.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test text"},
            headers={"X-API-Key": "invalid_key_xyz"}
        )

        assert response.status_code == 401

    def test_generate_embeddings_long_text(self, client, auth_headers):
        """Test embedding generation with long text input."""
        long_text = " ".join(["Autonomous agent workflow"] * 100)

        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": long_text},
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384

    def test_generate_embeddings_special_characters(self, client, auth_headers):
        """Test embedding generation with special characters."""
        text_with_special_chars = "Agent: $10,000 transaction @fintech #compliance"

        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": text_with_special_chars},
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert data["text"] == text_with_special_chars

    def test_generate_embeddings_unicode(self, client, auth_headers):
        """Test embedding generation with Unicode characters."""
        unicode_text = "Agent workflow 🤖 with émojis and spëcial çharacters"

        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": unicode_text},
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_generate_embeddings_deterministic(self, client, auth_headers):
        """
        Test that same input produces same output (determinism).

        Per PRD §10: Deterministic defaults for demo reproducibility.
        """
        text = "Reproducible agent decision"

        # Generate embedding twice
        response1 = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": text},
            headers=auth_headers
        )
        response2 = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": text},
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Embeddings should be identical for same input
        assert data1["embedding"] == data2["embedding"]
        assert data1["model"] == data2["model"]
        assert data1["dimensions"] == data2["dimensions"]


class TestListModels:
    """Tests for GET /v1/public/embeddings/models endpoint."""

    def test_list_models_success(self, client, auth_headers):
        """Test successful retrieval of supported models list."""
        response = client.post(
            "/v1/public/embeddings/models",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert "default_model" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

        # Verify default model is in the list
        assert data["default_model"] == "BAAI/bge-small-en-v1.5"

    def test_list_models_no_auth(self, client):
        """Test that models endpoint requires authentication."""
        response = client.get("/v1/public/embeddings/models")

        assert response.status_code == 401


class TestGetModelInfo:
    """Tests for GET /v1/public/embeddings/models/{model_name} endpoint."""

    def test_get_model_info_success(self, client, auth_headers):
        """Test successful retrieval of specific model info."""
        response = client.get(
            "/v1/public/embeddings/models/BAAI/bge-small-en-v1.5",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "dimensions" in data
        assert "description" in data
        assert "is_default" in data

        assert data["name"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert data["is_default"] is True

    def test_get_model_info_not_found(self, client, auth_headers):
        """Test error handling for non-existent model."""
        response = client.get(
            "/v1/public/embeddings/models/non-existent-model",
            headers=auth_headers
        )

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"


class TestEmbeddingDimensions:
    """Tests for dimension validation across different models."""

    @pytest.mark.parametrize("model,expected_dims", [
        ("BAAI/bge-small-en-v1.5", 384),
        ("sentence-transformers/all-MiniLM-L6-v2", 384),
        ("sentence-transformers/all-MiniLM-L12-v2", 384),
        ("sentence-transformers/all-mpnet-base-v2", 768),
    ])
    def test_model_dimensions(self, client, auth_headers, model, expected_dims):
        """
        Test that each model returns correct dimensions.

        Epic 3 Story 3: Support multiple models with correct dimensions.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test text", "model": model},
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert data["dimensions"] == expected_dims
        assert len(data["embedding"]) == expected_dims


class TestErrorFormat:
    """Tests for consistent error format per DX Contract."""

    def test_error_format_missing_api_key(self, client):
        """
        Test error format compliance.

        Per DX Contract §7: All errors return { detail, error_code }.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test"}
        )

        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_error_format_invalid_model(self, client, auth_headers):
        """Test error format for invalid model."""
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test", "model": "invalid"},
            headers=auth_headers
        )

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"


class TestProcessingTime:
    """Tests for processing time metadata."""

    def test_processing_time_included(self, client, auth_headers):
        """
        Test that processing_time_ms is included in response.

        Epic 3 Story 5: Responses include processing_time_ms.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test performance"},
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] >= 0
