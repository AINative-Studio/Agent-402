"""
Test model validation for embeddings API.

Implements tests for Epic 3 Story 4 (Issue #14):
- Invalid/unsupported model values must return HTTP 404
- Error response must include error_code: "MODEL_NOT_FOUND"
- Error response must include "detail" field with clear message
- Error message should list supported models
- Follow PRD §10 for clear failure modes

Per DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
"""
import pytest
from app.services.embedding_service import EmbeddingService


class TestModelValidation:
    """
    Test suite for model validation (Issue #14).

    Requirements:
    - HTTP 404 for unsupported models
    - error_code: MODEL_NOT_FOUND
    - detail field with clear message
    - List all supported models in error message
    """

    def test_unsupported_model_returns_404(self, client, auth_headers_user1):
        """
        Test that an unsupported model returns HTTP 404.

        Epic 3 Story 4 (Issue #14): Invalid/unsupported model values return 404.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding",
                "model": "unsupported-model-xyz"
            }
        )

        assert response.status_code == 404, \
            f"Expected 404 for unsupported model, got {response.status_code}"

    def test_unsupported_model_has_error_code(self, client, auth_headers_user1):
        """
        Test that error response includes error_code: MODEL_NOT_FOUND.

        Epic 3 Story 4 (Issue #14): Error response must include error_code.
        DX Contract §7: All errors return { detail, error_code }.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding",
                "model": "invalid-model"
            }
        )

        assert response.status_code == 404
        data = response.json()

        assert "error_code" in data, \
            "Response must include error_code field"
        assert data["error_code"] == "MODEL_NOT_FOUND", \
            f"Expected error_code MODEL_NOT_FOUND, got {data['error_code']}"

    def test_unsupported_model_has_detail_field(self, client, auth_headers_user1):
        """
        Test that error response includes detail field with clear message.

        Epic 3 Story 4 (Issue #14): Error response must include detail field.
        DX Contract §7: All errors return { detail, error_code }.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding",
                "model": "another-invalid-model"
            }
        )

        assert response.status_code == 404
        data = response.json()

        assert "detail" in data, \
            "Response must include detail field"
        assert isinstance(data["detail"], str), \
            "detail field must be a string"
        assert len(data["detail"]) > 0, \
            "detail field must not be empty"

    def test_error_message_lists_supported_models(self, client, auth_headers_user1):
        """
        Test that error message lists all supported models.

        Epic 3 Story 4 (Issue #14): Error message should list supported models.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding",
                "model": "wrong-model"
            }
        )

        assert response.status_code == 404
        data = response.json()
        detail = data["detail"]

        # Get list of supported models from the service
        service = EmbeddingService()
        supported_models = list(service.SUPPORTED_MODELS.keys())

        # Verify error message mentions supported models
        assert "Supported models" in detail or "supported" in detail.lower(), \
            "Error message should mention supported models"

        # Verify at least some of the supported models are listed
        models_mentioned = sum(1 for model in supported_models if model in detail)
        assert models_mentioned > 0, \
            f"Error message should list supported models. Detail: {detail}"

    def test_supported_model_succeeds(self, client, auth_headers_user1):
        """
        Test that a supported model returns 200 OK.

        This is a positive test case to ensure we're not rejecting valid models.
        """
        # Use the default model which is guaranteed to be supported
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding",
                "model": EmbeddingService.DEFAULT_MODEL
            }
        )

        assert response.status_code == 200, \
            f"Supported model should return 200, got {response.status_code}"

        data = response.json()
        assert "embedding" in data
        assert "model" in data
        assert "dimensions" in data

    def test_default_model_when_omitted(self, client, auth_headers_user1):
        """
        Test that model defaults to 384-dim when omitted.

        Epic 3 Story 2: API defaults to 384-dim embeddings when model is omitted.
        DX Contract §3: Default embedding model is 384-dim.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text for embedding"
                # No model specified
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dimensions"] == 384, \
            "Default model should have 384 dimensions"
        assert data["model"] == EmbeddingService.DEFAULT_MODEL

    def test_multiple_unsupported_models(self, client, auth_headers_user1):
        """
        Test multiple different unsupported models all return 404.

        Ensures consistent behavior across different invalid inputs.
        """
        unsupported_models = [
            "gpt-4",
            "bert-base-uncased",
            "random-model-name",
            "openai/text-davinci-003",
            ""  # Empty string
        ]

        for model in unsupported_models:
            response = client.post(
                "/v1/public/embeddings/generate",
                headers=auth_headers_user1,
                json={
                    "text": "Test text",
                    "model": model
                }
            )

            # Empty string might be treated differently (422 validation error)
            if model == "":
                # Either 404 or 422 is acceptable for empty string
                assert response.status_code in [404, 422], \
                    f"Empty model should return 404 or 422, got {response.status_code}"
            else:
                assert response.status_code == 404, \
                    f"Model '{model}' should return 404, got {response.status_code}"

                data = response.json()
                assert data["error_code"] == "MODEL_NOT_FOUND"

    def test_case_sensitive_model_names(self, client, auth_headers_user1):
        """
        Test that model names are case-sensitive.

        Ensures consistent behavior - model names must match exactly.
        """
        # Try uppercase version of default model
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text",
                "model": EmbeddingService.DEFAULT_MODEL.upper()
            }
        )

        # Should return 404 unless the service normalizes case (which it shouldn't)
        assert response.status_code == 404, \
            "Model names should be case-sensitive"

    def test_error_response_structure(self, client, auth_headers_user1):
        """
        Test that error response structure matches DX Contract.

        DX Contract §7: All errors return { detail, error_code }.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers_user1,
            json={
                "text": "Test text",
                "model": "invalid-model"
            }
        )

        assert response.status_code == 404
        data = response.json()

        # Must have exactly these fields (or at least these two)
        assert "detail" in data
        assert "error_code" in data

        # Verify types
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

        # Verify values
        assert data["error_code"] == "MODEL_NOT_FOUND"
        assert len(data["detail"]) > 0

    def test_get_model_info_unsupported(self, client, auth_headers_user1):
        """
        Test GET /embeddings/models/{model_name} with unsupported model.

        Should also return 404 with MODEL_NOT_FOUND for consistency.
        """
        response = client.get(
            "/v1/public/embeddings/models/unsupported-model",
            headers=auth_headers_user1
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "MODEL_NOT_FOUND"
        assert "detail" in data


class TestSupportedModels:
    """
    Test suite for supported models functionality.

    Ensures all documented models work correctly.
    """

    def test_all_supported_models_work(self, client, auth_headers_user1):
        """
        Test that all models listed in SUPPORTED_MODELS actually work.

        This ensures our documentation matches reality.
        """
        service = EmbeddingService()

        for model_name in service.SUPPORTED_MODELS.keys():
            response = client.post(
                "/v1/public/embeddings/generate",
                headers=auth_headers_user1,
                json={
                    "text": "Test text for embedding",
                    "model": model_name
                }
            )

            assert response.status_code == 200, \
                f"Supported model '{model_name}' should return 200, got {response.status_code}"

            data = response.json()
            assert data["model"] == model_name

            # Verify dimensions match spec
            expected_dims = service.SUPPORTED_MODELS[model_name]["dimensions"]
            assert data["dimensions"] == expected_dims, \
                f"Model {model_name} should have {expected_dims} dimensions, got {data['dimensions']}"

    def test_list_models_endpoint(self, client, auth_headers_user1):
        """
        Test GET /embeddings/models endpoint lists all supported models.

        Epic 3: Support multiple models with correct dimensions.
        """
        response = client.get(
            "/v1/public/embeddings/models",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert "models" in data
        assert "default_model" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

        # Verify all models have required fields
        for model in data["models"]:
            assert "name" in model
            assert "dimensions" in model
            assert "description" in model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
