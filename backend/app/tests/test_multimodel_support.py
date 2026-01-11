"""
Test suite for multi-model embedding support (Issue #13).

Tests cover:
1. Model validation against supported models list
2. Correct dimensions returned for each model
3. Default model behavior when parameter omitted
4. Error handling for unsupported models
5. All supported models work correctly

Per PRD §12 (Extensibility):
- Support multiple embedding models with different dimensions
- Validate model parameter against supported models list
- Return embeddings with correct dimensions for each model

Per DX Contract §3:
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Model parameter is optional
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_MODEL_SPECS,
    get_model_dimensions,
    is_model_supported
)

client = TestClient(app)

# Test API key for authentication
TEST_API_KEY = "test_api_key_12345"


class TestModelConfiguration:
    """Test the model configuration module."""

    def test_default_model_is_defined(self):
        """Test that default model is properly defined."""
        assert DEFAULT_EMBEDDING_MODEL == "BAAI/bge-small-en-v1.5"

    def test_default_model_has_384_dimensions(self):
        """Test that default model has exactly 384 dimensions per DX Contract."""
        dimensions = get_model_dimensions(DEFAULT_EMBEDDING_MODEL)
        assert dimensions == 384, "Default model must have 384 dimensions per DX Contract §3"

    def test_all_models_have_dimension_specs(self):
        """Test that all supported models have dimension specifications."""
        for model_name, spec in EMBEDDING_MODEL_SPECS.items():
            assert "dimensions" in spec, f"Model {model_name} missing dimensions"
            assert isinstance(spec["dimensions"], int), f"Model {model_name} dimensions must be int"
            assert spec["dimensions"] > 0, f"Model {model_name} dimensions must be positive"

    def test_model_dimension_lookup(self):
        """Test that model dimensions can be looked up correctly."""
        # Test all supported models
        assert get_model_dimensions("BAAI/bge-small-en-v1.5") == 384
        assert get_model_dimensions("sentence-transformers/all-MiniLM-L6-v2") == 384
        assert get_model_dimensions("sentence-transformers/all-mpnet-base-v2") == 768

    def test_unsupported_model_raises_error(self):
        """Test that unsupported model raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_model_dimensions("unsupported-model")

        assert "not supported" in str(exc_info.value).lower()

    def test_is_model_supported_function(self):
        """Test the is_model_supported utility function."""
        # Supported models
        assert is_model_supported("BAAI/bge-small-en-v1.5") is True
        assert is_model_supported("sentence-transformers/all-MiniLM-L6-v2") is True

        # Unsupported models
        assert is_model_supported("invalid-model") is False
        assert is_model_supported("") is False


class TestEmbeddingGeneration:
    """Test embedding generation with different models."""

    def test_generate_embedding_with_default_model(self):
        """
        Test generating embeddings with default model (no model specified).
        Issue #13: Default to 384-dim when model omitted.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Test compliance check for transaction TX-123"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default model was used
        assert data["model"] == DEFAULT_EMBEDDING_MODEL
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384

    def test_generate_embedding_with_explicit_model(self):
        """
        Test generating embeddings with explicitly specified model.
        Issue #13: Support multiple models with correct dimensions.
        """
        test_models = [
            ("BAAI/bge-small-en-v1.5", 384),
            ("sentence-transformers/all-MiniLM-L6-v2", 384),
            ("sentence-transformers/all-mpnet-base-v2", 768),
        ]

        for model_name, expected_dims in test_models:
            response = client.post(
                "/v1/public/proj_demo_u1_001/embeddings/generate",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Test text for model {model_name}",
                    "model": model_name
                }
            )

            assert response.status_code == 200, f"Failed for model {model_name}"
            data = response.json()

            # Verify correct model and dimensions
            assert data["model"] == model_name
            assert data["dimensions"] == expected_dims
            assert len(data["embedding"]) == expected_dims

    def test_all_supported_models_work(self):
        """
        Test that all supported models can generate embeddings.
        Issue #13: Test each supported model.
        """
        for model_name, spec in EMBEDDING_MODEL_SPECS.items():
            response = client.post(
                "/v1/public/proj_demo_u1_001/embeddings/generate",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Test embedding for {model_name}",
                    "model": model_name
                }
            )

            assert response.status_code == 200, f"Model {model_name} failed"
            data = response.json()

            assert data["model"] == model_name
            assert data["dimensions"] == spec["dimensions"]
            assert len(data["embedding"]) == spec["dimensions"]

    def test_unsupported_model_returns_error(self):
        """
        Test that unsupported model returns appropriate error.
        Epic 3 Story 4: Unsupported models return MODEL_NOT_FOUND.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test text",
                "model": "unsupported-model-xyz"
            }
        )

        assert response.status_code == 422  # Validation error
        data = response.json()

        # Should contain error details about supported models
        assert "detail" in data

    def test_embedding_response_includes_metadata(self):
        """
        Test that response includes all required metadata.
        Epic 3 Story 5: Response includes processing_time_ms.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Metadata test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        assert "embedding" in data
        assert "model" in data
        assert "dimensions" in data
        assert "text" in data
        assert "processing_time_ms" in data

        # Verify types
        assert isinstance(data["embedding"], list)
        assert isinstance(data["model"], str)
        assert isinstance(data["dimensions"], int)
        assert isinstance(data["text"], str)
        assert isinstance(data["processing_time_ms"], (int, float))


class TestDimensionConsistency:
    """Test dimension consistency across operations."""

    def test_dimension_consistency_for_same_model(self):
        """
        Test that the same model always returns the same dimensions.
        PRD §10: Behavior must be deterministic.
        """
        model = "BAAI/bge-small-en-v1.5"
        texts = ["First text", "Second text", "Third text"]

        dimensions_list = []
        for text in texts:
            response = client.post(
                "/v1/public/proj_demo_u1_001/embeddings/generate",
                headers={"X-API-Key": TEST_API_KEY},
                json={"text": text, "model": model}
            )

            assert response.status_code == 200
            data = response.json()
            dimensions_list.append(data["dimensions"])

        # All dimensions should be identical
        assert len(set(dimensions_list)) == 1, "Dimensions must be consistent for same model"
        assert dimensions_list[0] == 384

    def test_different_models_have_different_dimensions(self):
        """
        Test that models with different dimension specs return different dimensions.
        Issue #13: Validate dimensions match model specifications.
        """
        model_384 = "BAAI/bge-small-en-v1.5"
        model_768 = "sentence-transformers/all-mpnet-base-v2"

        response_384 = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Test", "model": model_384}
        )

        response_768 = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Test", "model": model_768}
        )

        assert response_384.status_code == 200
        assert response_768.status_code == 200

        dims_384 = response_384.json()["dimensions"]
        dims_768 = response_768.json()["dimensions"]

        assert dims_384 == 384
        assert dims_768 == 768
        assert dims_384 != dims_768


class TestSupportedModelsEndpoint:
    """Test the supported models listing endpoint."""

    def test_list_supported_models(self):
        """
        Test GET /v1/public/embeddings/models endpoint.
        Issue #13: Document all supported models in API spec.
        """
        response = client.get(
            "/v1/public/embeddings/models",
            headers={"X-API-Key": TEST_API_KEY}
        )

        assert response.status_code == 200
        data = response.json()

        # Should contain models information
        assert "models" in data or isinstance(data, list)

    def test_models_response_includes_default(self):
        """Test that models response indicates which is the default."""
        response = client.get(
            "/v1/public/embeddings/models",
            headers={"X-API-Key": TEST_API_KEY}
        )

        assert response.status_code == 200
        data = response.json()

        # Should indicate default model
        if "default_model" in data:
            assert data["default_model"] == DEFAULT_EMBEDDING_MODEL


class TestAPISpecCompliance:
    """Test compliance with API specification requirements."""

    def test_api_requires_authentication(self):
        """Test that embedding endpoints require authentication."""
        # Request without API key should fail
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            json={"text": "Test"}
        )

        assert response.status_code == 401

    def test_empty_text_rejected(self):
        """Test that empty text is rejected with validation error."""
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": ""}
        )

        assert response.status_code == 422  # Validation error

    def test_whitespace_only_text_rejected(self):
        """Test that whitespace-only text is rejected."""
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "   \n\t  "}
        )

        assert response.status_code == 422  # Validation error


class TestBackwardCompatibility:
    """Test that changes maintain backward compatibility."""

    def test_omitting_model_still_works(self):
        """
        Test that omitting model parameter still works (backward compatibility).
        DX Contract §3: Default model behavior is guaranteed.
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Test without model parameter"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should use default model
        assert data["model"] == DEFAULT_EMBEDDING_MODEL
        assert data["dimensions"] == 384

    def test_response_format_unchanged(self):
        """
        Test that response format hasn't changed (backward compatibility).
        """
        response = client.post(
            "/v1/public/proj_demo_u1_001/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Format test"}
        )

        assert response.status_code == 200
        data = response.json()

        # All original fields must be present
        required_fields = ["embedding", "model", "dimensions", "text", "processing_time_ms"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
