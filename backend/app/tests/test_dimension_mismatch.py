"""
Tests for dimension mismatch error handling (Issue #29).

Per GitHub Issue #29:
- Dimension mismatches must return HTTP 422
- Error response must include error_code: "DIMENSION_MISMATCH"
- Error response must include "detail" field with clear message
- Error message should specify expected vs actual dimensions
- Follow PRD §10 for clear failure modes

Test Coverage:
- Dimension validation in vector storage
- Error response format compliance
- Clear error messages with expected/actual dimensions
- Various mismatch scenarios
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.zerodb_vector_service import zerodb_vector_service
from app.core.errors import APIError


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Get a valid API key from settings."""
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


class TestDimensionMismatchErrorHandling:
    """Tests for dimension mismatch error handling per Issue #29."""

    def test_dimension_mismatch_returns_422(self):
        """
        Test that dimension mismatches return HTTP 422.

        Per Issue #29: Dimension mismatches must return HTTP 422.
        """
        # Test with 384-dim model but provide wrong dimensions
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 768,  # Wrong: 768 dims instead of 384
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        # Verify HTTP status code
        assert exc_info.value.status_code == 422

    def test_dimension_mismatch_error_code(self):
        """
        Test that dimension mismatches return error_code: "DIMENSION_MISMATCH".

        Per Issue #29: Error response must include error_code: "DIMENSION_MISMATCH".
        """
        # Test with dimension mismatch
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 1024,  # Wrong: 1024 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        # Verify error code
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"

    def test_dimension_mismatch_detail_field(self):
        """
        Test that dimension mismatches return "detail" field.

        Per Issue #29: Error response must include "detail" field with clear message.
        """
        # Test with dimension mismatch
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 100,  # Wrong: 100 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        # Verify detail field exists and is a string
        assert hasattr(exc_info.value, 'detail')
        assert isinstance(exc_info.value.detail, str)
        assert len(exc_info.value.detail) > 0

    def test_dimension_mismatch_message_includes_expected_actual(self):
        """
        Test that error message specifies expected vs actual dimensions.

        Per Issue #29: Error message should specify expected vs actual dimensions.
        """
        # Test with dimension mismatch
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 512,  # Actual: 512 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expected: 384 dims
                namespace="test"
            )

        error_message = exc_info.value.detail

        # Verify message includes both expected and actual dimensions
        assert "512" in error_message  # Actual dimension
        assert "384" in error_message  # Expected dimension
        assert "BAAI/bge-small-en-v1.5" in error_message  # Model name

    def test_dimension_mismatch_bge_base_768(self):
        """
        Test dimension mismatch for BGE-base model (768 dimensions).

        Per Issue #29: Various mismatch scenarios should be tested.
        """
        # Test with BGE-base expecting 768, but providing 384
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 384,  # Wrong: 384 dims
                document="Test document",
                model="sentence-transformers/all-mpnet-base-v2",  # Expects 768 dims
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"
        assert "384" in exc_info.value.detail
        assert "768" in exc_info.value.detail

    def test_dimension_mismatch_distilroberta_768(self):
        """
        Test dimension mismatch for distilroberta model (768 dimensions).

        Per Issue #29: Various mismatch scenarios should be tested.
        """
        # Test with distilroberta model expecting 768, but providing 384
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 384,  # Wrong: 384 dims
                document="Test document",
                model="sentence-transformers/all-distilroberta-v1",  # Expects 768 dims
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"
        assert "384" in exc_info.value.detail
        assert "768" in exc_info.value.detail

    def test_dimension_match_success_384(self):
        """
        Test successful storage when dimensions match (384).

        Per Issue #29: Verify that correct dimensions pass validation.
        """
        # Test with correct dimensions for BGE-small
        vector_id, created = zerodb_vector_service.store_vector(
            vector_embedding=[0.1] * 384,  # Correct: 384 dims
            document="Test document",
            model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
            namespace="test"
        )

        # Should succeed without raising exception
        assert vector_id is not None
        assert isinstance(created, bool)

    def test_dimension_match_success_768(self):
        """
        Test successful storage when dimensions match (768).

        Per Issue #29: Verify that correct dimensions pass validation.
        """
        # Test with correct dimensions for all-mpnet-base-v2
        vector_id, created = zerodb_vector_service.store_vector(
            vector_embedding=[0.1] * 768,  # Correct: 768 dims
            document="Test document",
            model="sentence-transformers/all-mpnet-base-v2",  # Expects 768 dims
            namespace="test"
        )

        # Should succeed without raising exception
        assert vector_id is not None
        assert isinstance(created, bool)

    def test_dimension_mismatch_zero_dimensions(self):
        """
        Test dimension mismatch with empty vector.

        Per Issue #29: Edge case - empty vector should fail validation.
        """
        # Test with empty vector
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[],  # Wrong: 0 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"
        assert "0" in exc_info.value.detail
        assert "384" in exc_info.value.detail

    def test_dimension_mismatch_too_many_dimensions(self):
        """
        Test dimension mismatch with too many dimensions.

        Per Issue #29: Test when actual > expected dimensions.
        """
        # Test with too many dimensions
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 2000,  # Wrong: 2000 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"
        assert "2000" in exc_info.value.detail
        assert "384" in exc_info.value.detail

    def test_dimension_mismatch_too_few_dimensions(self):
        """
        Test dimension mismatch with too few dimensions.

        Per Issue #29: Test when actual < expected dimensions.
        """
        # Test with too few dimensions
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 100,  # Wrong: 100 dims
                document="Test document",
                model="BAAI/bge-small-en-v1.5",  # Expects 384 dims
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"
        assert "100" in exc_info.value.detail
        assert "384" in exc_info.value.detail

    def test_dimension_mismatch_batch_storage(self):
        """
        Test dimension mismatch in batch storage operation.

        Per Issue #29: Ensure batch operations also validate dimensions.
        """
        # Test batch storage with one dimension mismatch
        vectors = [
            {
                "vector_embedding": [0.1] * 384,  # Correct
                "document": "Doc 1",
                "model": "BAAI/bge-small-en-v1.5"
            },
            {
                "vector_embedding": [0.1] * 768,  # Wrong: dimension mismatch
                "document": "Doc 2",
                "model": "BAAI/bge-small-en-v1.5"  # Expects 384
            }
        ]

        # Should fail on second vector
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.batch_store_vectors(
                vectors=vectors,
                namespace="test"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "DIMENSION_MISMATCH"


class TestDimensionMismatchEndToEnd:
    """End-to-end tests for dimension mismatch via API endpoints."""

    def test_embed_and_store_dimension_validation(self, client, auth_headers, test_project_id):
        """
        Test that embed-and-store validates dimensions correctly.

        Per Issue #29: Dimension validation should work through the API.

        Note: This test verifies that the embedding service generates
        vectors with correct dimensions matching the model specs.
        """
        # Generate embedding with one model (embed-and-store uses "documents" field)
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "documents": ["Test autonomous agent workflow"],
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_dim_validation"
            },
            headers=auth_headers
        )

        # Should succeed with correct dimensions
        assert response.status_code == 200
        data = response.json()
        assert data["dimensions"] == 384
        assert data["model"] == "BAAI/bge-small-en-v1.5"


class TestDimensionMismatchErrorFormat:
    """Test error response format compliance for dimension mismatches."""

    def test_error_format_has_detail_and_error_code(self):
        """
        Test error format includes both detail and error_code.

        Per DX Contract §7: All errors return { detail, error_code }.
        Per Issue #29: Dimension mismatches must follow this format.
        """
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 256,
                document="Test",
                model="BAAI/bge-small-en-v1.5",
                namespace="test"
            )

        error = exc_info.value

        # Verify error has required fields
        assert hasattr(error, 'detail')
        assert hasattr(error, 'error_code')
        assert hasattr(error, 'status_code')

        # Verify values are correct types
        assert isinstance(error.detail, str)
        assert isinstance(error.error_code, str)
        assert isinstance(error.status_code, int)

        # Verify specific values
        assert error.status_code == 422
        assert error.error_code == "DIMENSION_MISMATCH"
        assert len(error.detail) > 0

    def test_error_message_is_human_readable(self):
        """
        Test that error message is clear and human-readable.

        Per PRD §10: Clear failure modes for developer experience.
        Per Issue #29: Error message should specify expected vs actual dimensions.
        """
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 200,
                document="Test document",
                model="BAAI/bge-small-en-v1.5",
                namespace="test"
            )

        error_message = exc_info.value.detail

        # Verify message is human-readable and informative
        assert "dimension" in error_message.lower() or "dimensions" in error_message.lower()
        assert "200" in error_message  # Actual dimension
        assert "384" in error_message  # Expected dimension
        assert "BAAI/bge-small-en-v1.5" in error_message  # Model name

        # Verify message structure makes sense
        # Should indicate: actual dimensions, expected dimensions, model
        assert "do not match" in error_message.lower() or "mismatch" in error_message.lower()

    def test_different_models_different_error_messages(self):
        """
        Test that error messages correctly reflect different model expectations.

        Per Issue #29: Error message should specify the model and its expected dimensions.
        """
        # Test with BGE-small (384 dims)
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 100,
                document="Test",
                model="BAAI/bge-small-en-v1.5",
                namespace="test"
            )

        error1 = exc_info.value.detail
        assert "384" in error1
        assert "BAAI/bge-small-en-v1.5" in error1

        # Test with all-mpnet-base-v2 (768 dims)
        with pytest.raises(APIError) as exc_info:
            zerodb_vector_service.store_vector(
                vector_embedding=[0.1] * 100,
                document="Test",
                model="sentence-transformers/all-mpnet-base-v2",
                namespace="test"
            )

        error2 = exc_info.value.detail
        assert "768" in error2
        assert "all-mpnet-base-v2" in error2

        # Error messages should be different for different models
        assert error1 != error2
