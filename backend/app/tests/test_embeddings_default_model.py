"""
Tests for Issue #12: Default 384-dim embeddings when model is omitted.

These tests verify that:
1. When model parameter is omitted, the API uses the default model
2. Default model generates exactly 384 dimensions
3. Behavior is deterministic and consistent
4. Response indicates which model was used
5. Unsupported models return appropriate errors

Per PRD §10: Demo must fail loudly and clearly if behavior changes.
"""
import pytest
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_MODEL_SPECS
)


@pytest.fixture
def project_id():
    """Standard project ID for tests."""
    return "proj_test123"


class TestDefaultModelBehavior:
    """
    Test suite for Issue #12: Default model behavior.

    DX Contract Guarantee:
    - Default model is BAAI/bge-small-en-v1.5 (384 dimensions)
    - This will not change without a version bump
    """

    def test_generate_embedding_without_model_uses_default(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test that omitting model parameter uses the default model.

        Issue #12 Story Point 1:
        - When model parameter is omitted, use default model
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test embedding generation"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default model was used
        assert data["model"] == DEFAULT_EMBEDDING_MODEL
        assert data["model"] == "BAAI/bge-small-en-v1.5"

    def test_generate_embedding_without_model_returns_384_dimensions(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test that default model generates exactly 384 dimensions.

        Issue #12 Story Point 2:
        - Default model must generate 384-dimension embeddings
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test embedding dimensions"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify exactly 384 dimensions
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384

    def test_generate_embedding_response_indicates_model_used(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test that response indicates which model was used.

        Issue #12 Technical Details:
        - Response must indicate which model was used (for determinism)
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Model indication test"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Response must have model field
        assert "model" in data
        assert data["model"] is not None
        assert len(data["model"]) > 0

    def test_generate_embedding_is_deterministic(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test that same input produces same output (determinism).

        Issue #12 PRD §10:
        - Behavior must be deterministic and consistent
        """
        test_text = "Determinism test text"

        # Generate embedding twice with same input
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": test_text}
        )

        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": test_text}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Same text should produce same embedding
        assert data1["embedding"] == data2["embedding"]
        assert data1["model"] == data2["model"]
        assert data1["dimensions"] == data2["dimensions"]

    def test_generate_embedding_with_explicit_default_model(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test explicitly specifying the default model produces same result.

        Issue #12:
        - Explicit model=DEFAULT_EMBEDDING_MODEL should behave identically to omitting it
        """
        test_text = "Explicit default model test"

        # Test without model parameter
        response_implicit = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": test_text}
        )

        # Test with explicit default model
        response_explicit = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": test_text,
                "model": DEFAULT_EMBEDDING_MODEL
            }
        )

        assert response_implicit.status_code == 200
        assert response_explicit.status_code == 200

        # Should produce identical results
        data_implicit = response_implicit.json()
        data_explicit = response_explicit.json()

        assert data_implicit["model"] == data_explicit["model"]
        assert data_implicit["dimensions"] == data_explicit["dimensions"]
        assert data_implicit["embedding"] == data_explicit["embedding"]


class TestSupportedModels:
    """
    Test suite for supported embedding models.

    Issue #12 Story Point 3:
    - Support multiple models with correct dimensions
    """

    def test_all_supported_models_work(
        self, client, auth_headers_user1, project_id
    ):
        """Test that all declared supported models can be used."""
        test_text = "Supported models test"

        # Get model names as strings
        for model_enum, spec in EMBEDDING_MODEL_SPECS.items():
            model_name = model_enum.value if hasattr(model_enum, 'value') else str(model_enum)
            expected_dims = spec["dimensions"]
            
            response = client.post(
                f"/v1/public/{project_id}/embeddings/generate",
                headers=auth_headers_user1,
                json={
                    "text": test_text,
                    "model": model_name
                }
            )

            assert response.status_code == 200, f"Model {model_name} failed"
            data = response.json()

            assert data["model"] == model_name
            assert data["dimensions"] == expected_dims
            assert len(data["embedding"]) == expected_dims

    def test_unsupported_model_returns_error(
        self, client, auth_headers_user1, project_id
    ):
        """
        Test that unsupported models return clear error.

        Issue #12 Story Point 4 (Epic 3):
        - Unsupported models return MODEL_NOT_FOUND
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text",
                "model": "unsupported-model-xyz"
            }
        )

        # Model validation happens at Pydantic level now, so it returns 422
        # But the error should still be clear
        assert response.status_code in (404, 422)
        data = response.json()
        assert "detail" in data


class TestResponseFormat:
    """
    Test suite for response format compliance.

    Issue #12 Story Point 5 (Epic 3):
    - Responses include processing_time_ms
    """

    def test_response_includes_processing_time(
        self, client, auth_headers_user1, project_id
    ):
        """Test that response includes processing_time_ms field."""
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": "Processing time test"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)
        assert data["processing_time_ms"] >= 0

    def test_response_includes_all_required_fields(
        self, client, auth_headers_user1, project_id
    ):
        """Test that response includes all required fields."""
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": "Complete response test"}
        )

        assert response.status_code == 200
        data = response.json()

        # All required fields per schema
        required_fields = ["embedding", "model", "dimensions", "text", "processing_time_ms"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_response_embedding_is_list_of_floats(
        self, client, auth_headers_user1, project_id
    ):
        """Test that embedding is a list of float values."""
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": "Embedding format test"}
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) > 0
        assert all(isinstance(v, (int, float)) for v in data["embedding"])


class TestInputValidation:
    """Test input validation per DX Contract."""

    def test_empty_text_returns_validation_error(
        self, client, auth_headers_user1, project_id
    ):
        """Test that empty text is rejected."""
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": ""}
        )

        assert response.status_code == 422

    def test_whitespace_only_text_returns_validation_error(
        self, client, auth_headers_user1, project_id
    ):
        """Test that whitespace-only text is rejected."""
        response = client.post(
            f"/v1/public/{project_id}/embeddings/generate",
            headers=auth_headers_user1,
            json={"text": "   "}
        )

        assert response.status_code == 422


class TestListModels:
    """Test the models listing endpoint."""

    def test_list_models_returns_supported_models(self, client, auth_headers_user1):
        """Test that /embeddings/models returns all supported models."""
        response = client.get(
            "/v1/public/embeddings/models",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        models = response.json()

        assert isinstance(models, list)
        assert len(models) == len(EMBEDDING_MODEL_SPECS)

        # Verify each model in EMBEDDING_MODEL_SPECS is returned
        model_names = [m["name"] for m in models]
        for model_enum in EMBEDDING_MODEL_SPECS.keys():
            model_name = model_enum.value if hasattr(model_enum, 'value') else str(model_enum)
            assert model_name in model_names

    def test_list_models_indicates_default(self, client, auth_headers_user1):
        """Test that default model is marked as is_default=True."""
        response = client.get(
            "/v1/public/embeddings/models",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        models = response.json()

        # Find the default model
        default_models = [m for m in models if m["is_default"]]

        assert len(default_models) == 1
        assert default_models[0]["name"] == DEFAULT_EMBEDDING_MODEL
        assert default_models[0]["dimensions"] == 384
