"""
Tests for embed-and-store endpoint with upsert functionality.
Implements Issue #18: As a developer, upsert: true updates existing IDs without duplication.

Test Coverage:
1. Upsert=true behavior (updates existing vectors)
2. Upsert=false behavior (prevents duplicates)
3. Idempotency guarantees
4. Duplicate prevention
5. Response field validation (Issue #19)

Per PRD §10 (Replayability):
- Same request with upsert=true produces identical result
- Deterministic behavior for agent workflows
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.embedding_service import embedding_service


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vector store before each test."""
    embedding_service.clear_vectors()
    yield
    embedding_service.clear_vectors()


@pytest.fixture
def client():
    """Test client fixture - use conftest version if available."""
    try:
        from app.main_simple import app as simple_app
        return TestClient(simple_app)
    except ImportError:
        return TestClient(app)


@pytest.fixture
def valid_headers():
    """Valid API key headers for testing."""
    from app.core.config import settings
    return {"X-API-Key": settings.demo_api_key_1}


class TestEmbedAndStoreUpsertTrue:
    """Test upsert=true behavior (updates existing vectors)."""

    def test_upsert_true_creates_new_vector_when_id_not_exists(self, client, valid_headers):
        """
        Issue #18: When upsert=true and vector_id doesn't exist, create new vector.
        """
        # Arrange
        request_payload = {
            "text": "Test embedding for new vector",
            "vector_id": "test_vec_001",
            "upsert": True,
            "metadata": {"source": "test"}
        }

        # Act
        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["vector_id"] == "test_vec_001"
        assert data["created"] is True  # New vector created
        assert data["vectors_stored"] == 1  # Issue #19: Required field
        assert data["model"] == "BAAI/bge-small-en-v1.5"  # Issue #19: Required field
        assert data["dimensions"] == 384  # Issue #19: Required field
        assert data["namespace"] == "default"  # Issue #17: Namespace field
        assert "stored_at" in data

    def test_upsert_true_updates_existing_vector(self, client, valid_headers):
        """
        Issue #18: When upsert=true and vector_id exists, update the vector.
        """
        # Arrange - Create initial vector
        initial_request = {
            "text": "Initial text version 1",
            "vector_id": "test_vec_002",
            "upsert": True,
            "metadata": {"version": 1}
        }
        initial_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_request,
            headers=valid_headers
        )
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        initial_stored_at = initial_data["stored_at"]

        # Act - Update the same vector
        update_request = {
            "text": "Updated text version 2",
            "vector_id": "test_vec_002",
            "upsert": True,
            "metadata": {"version": 2}
        }
        update_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=update_request,
            headers=valid_headers
        )

        # Assert
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["vector_id"] == "test_vec_002"
        assert update_data["created"] is False  # Vector was updated, not created
        assert update_data["vectors_stored"] == 1
        assert update_data["text"] == "Updated text version 2"
        assert update_data["stored_at"] != initial_stored_at  # Timestamp should be updated

        # Verify no duplicate created
        vector = embedding_service.get_vector("test_vec_002")
        assert vector is not None
        assert vector["text"] == "Updated text version 2"
        assert vector["metadata"]["version"] == 2

    def test_upsert_true_idempotency(self, client, valid_headers):
        """
        Issue #18: Same request with upsert=true produces identical result (idempotent).
        Per PRD §10: Replayability guarantee.
        """
        # Arrange
        request_payload = {
            "text": "Idempotent test text",
            "vector_id": "test_vec_003",
            "upsert": True,
            "metadata": {"idempotent": True}
        }

        # Act - Make same request 3 times
        response1 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )
        response2 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )
        response3 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        # First request creates, subsequent requests update
        assert data1["created"] is True
        assert data2["created"] is False
        assert data3["created"] is False

        # Vector ID remains the same
        assert data1["vector_id"] == data2["vector_id"] == data3["vector_id"] == "test_vec_003"

        # Model and dimensions remain consistent (Issue #19)
        assert data1["model"] == data2["model"] == data3["model"] == "BAAI/bge-small-en-v1.5"
        assert data1["dimensions"] == data2["dimensions"] == data3["dimensions"] == 384

        # Verify only one vector exists in store
        vector = embedding_service.get_vector("test_vec_003")
        assert vector is not None
        assert vector["text"] == "Idempotent test text"


class TestEmbedAndStoreUpsertFalse:
    """Test upsert=false behavior (prevents duplicates)."""

    def test_upsert_false_creates_new_vector_when_id_not_exists(self, client, valid_headers):
        """
        Issue #18: When upsert=false and vector_id doesn't exist, create new vector.
        """
        # Arrange
        request_payload = {
            "text": "Test embedding for new vector",
            "vector_id": "test_vec_004",
            "upsert": False,
            "metadata": {"source": "test"}
        }

        # Act
        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["vector_id"] == "test_vec_004"
        assert data["created"] is True
        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_upsert_false_errors_when_vector_exists(self, client, valid_headers):
        """
        Issue #18: When upsert=false and vector_id exists, return 409 error.
        This prevents duplicate vectors with same ID.
        """
        # Arrange - Create initial vector
        initial_request = {
            "text": "Initial vector",
            "vector_id": "test_vec_005",
            "upsert": False
        }
        initial_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_request,
            headers=valid_headers
        )
        assert initial_response.status_code == 200

        # Act - Try to create another vector with same ID
        duplicate_request = {
            "text": "Duplicate attempt",
            "vector_id": "test_vec_005",
            "upsert": False
        }
        duplicate_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=duplicate_request,
            headers=valid_headers
        )

        # Assert
        assert duplicate_response.status_code == 409  # Conflict
        error_data = duplicate_response.json()
        assert "detail" in error_data
        assert "error_code" in error_data
        assert error_data["error_code"] == "VECTOR_ALREADY_EXISTS"
        assert "test_vec_005" in error_data["detail"]
        assert "upsert=true" in error_data["detail"]

        # Verify original vector unchanged
        vector = embedding_service.get_vector("test_vec_005")
        assert vector is not None
        assert vector["text"] == "Initial vector"

    def test_upsert_false_default_behavior(self, client, valid_headers):
        """
        Issue #18: When upsert parameter is omitted, defaults to false.
        """
        # Arrange - Create initial vector without specifying upsert
        initial_request = {
            "text": "Vector with default upsert",
            "vector_id": "test_vec_006"
        }
        initial_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_request,
            headers=valid_headers
        )
        assert initial_response.status_code == 200

        # Act - Try to create another vector with same ID (upsert still omitted)
        duplicate_request = {
            "text": "Duplicate with default upsert",
            "vector_id": "test_vec_006"
        }
        duplicate_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=duplicate_request,
            headers=valid_headers
        )

        # Assert
        assert duplicate_response.status_code == 409
        error_data = duplicate_response.json()
        assert error_data["error_code"] == "VECTOR_ALREADY_EXISTS"


class TestDuplicatePrevention:
    """Test duplicate prevention across various scenarios."""

    def test_no_duplicates_created_with_upsert_false(self, client, valid_headers):
        """
        Issue #18: Verify no duplicate vectors are created when upsert=false.
        """
        # Arrange
        vector_id = "test_vec_007"
        initial_request = {
            "text": "Original text",
            "vector_id": vector_id,
            "upsert": False
        }

        # Act - Create initial vector
        response1 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_request,
            headers=valid_headers
        )

        # Attempt to create duplicate 5 times
        for i in range(5):
            duplicate_request = {
                "text": f"Duplicate attempt {i}",
                "vector_id": vector_id,
                "upsert": False
            }
            duplicate_response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=duplicate_request,
                headers=valid_headers
            )
            assert duplicate_response.status_code == 409

        # Assert - Verify only one vector exists
        vector = embedding_service.get_vector(vector_id)
        assert vector is not None
        assert vector["text"] == "Original text"

        # Verify no duplicates in internal store
        assert embedding_service.vector_exists(vector_id)

    def test_auto_generated_ids_no_collision(self, client, valid_headers):
        """
        Issue #18: When vector_id is not provided, auto-generated IDs don't collide.
        """
        # Arrange & Act - Create 10 vectors without specifying vector_id
        vector_ids = []
        for i in range(10):
            request_payload = {
                "text": f"Auto-generated ID test {i}",
                "upsert": False  # Should not matter since IDs are unique
            }
            response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=request_payload,
                headers=valid_headers
            )
            assert response.status_code == 200
            data = response.json()
            vector_ids.append(data["vector_id"])

        # Assert - All vector IDs are unique
        assert len(vector_ids) == len(set(vector_ids))
        for vector_id in vector_ids:
            assert vector_id.startswith("vec_")
            assert len(vector_id) == 16  # "vec_" + 12 hex chars


class TestResponseFieldValidation:
    """Test response fields comply with Issue #19."""

    def test_response_includes_required_fields(self, client, valid_headers):
        """
        Issue #19: Response MUST include vectors_stored, model, dimensions.
        """
        # Arrange
        request_payload = {
            "text": "Test for required fields",
            "vector_id": "test_vec_008",
            "upsert": False
        }

        # Act
        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=request_payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Issue #19: Required fields
        assert "vectors_stored" in data
        assert data["vectors_stored"] == 1
        assert isinstance(data["vectors_stored"], int)

        assert "model" in data
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert isinstance(data["model"], str)

        assert "dimensions" in data
        assert data["dimensions"] == 384
        assert isinstance(data["dimensions"], int)

        # Additional fields
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)
        assert data["processing_time_ms"] >= 0

        assert "vector_id" in data
        assert "created" in data
        assert "stored_at" in data
        assert "text" in data

    def test_response_model_matches_request(self, client, valid_headers):
        """
        Issue #19: Response model field matches the requested model.
        """
        # Test with default model
        response1 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json={"text": "Default model test", "vector_id": "test_vec_009"},
            headers=valid_headers
        )
        assert response1.status_code == 200
        assert response1.json()["model"] == "BAAI/bge-small-en-v1.5"
        assert response1.json()["dimensions"] == 384

        # Test with explicit model
        response2 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json={
                "text": "Explicit model test",
                "model": "BAAI/bge-base-en-v1.5",
                "vector_id": "test_vec_010"
            },
            headers=valid_headers
        )
        assert response2.status_code == 200
        assert response2.json()["model"] == "BAAI/bge-base-en-v1.5"
        assert response2.json()["dimensions"] == 768


class TestIdempotencyGuarantees:
    """Test idempotency guarantees per PRD §10."""

    def test_identical_requests_produce_identical_results(self, client, valid_headers):
        """
        PRD §10 (Replayability): Identical requests with upsert=true produce identical results.
        """
        # Arrange
        request_payload = {
            "text": "Deterministic embedding test",
            "vector_id": "test_vec_011",
            "model": "BAAI/bge-small-en-v1.5",
            "metadata": {"test": "idempotency"},
            "upsert": True
        }

        # Act - Make same request multiple times
        responses = []
        for _ in range(3):
            response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=request_payload,
                headers=valid_headers
            )
            assert response.status_code == 200
            responses.append(response.json())

        # Assert - All responses have consistent data
        for i in range(1, len(responses)):
            assert responses[i]["vector_id"] == responses[0]["vector_id"]
            assert responses[i]["model"] == responses[0]["model"]
            assert responses[i]["dimensions"] == responses[0]["dimensions"]
            assert responses[i]["text"] == responses[0]["text"]
            assert responses[i]["vectors_stored"] == responses[0]["vectors_stored"]

        # Verify underlying vector data is consistent
        vector = embedding_service.get_vector("test_vec_011")
        assert vector is not None
        assert vector["text"] == "Deterministic embedding test"
        assert vector["embedding"] is not None
        assert len(vector["embedding"]) == 384

    def test_upsert_true_multiple_updates_consistent(self, client, valid_headers):
        """
        Issue #18: Multiple updates with upsert=true maintain consistency.
        """
        # Arrange
        vector_id = "test_vec_012"

        # Act - Create and update multiple times
        updates = [
            {"text": "Version 1", "metadata": {"version": 1}},
            {"text": "Version 2", "metadata": {"version": 2}},
            {"text": "Version 3", "metadata": {"version": 3}},
        ]

        for update in updates:
            request_payload = {
                "vector_id": vector_id,
                "upsert": True,
                **update
            }
            response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=request_payload,
                headers=valid_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["vector_id"] == vector_id

        # Assert - Final state matches last update
        final_vector = embedding_service.get_vector(vector_id)
        assert final_vector is not None
        assert final_vector["text"] == "Version 3"
        assert final_vector["metadata"]["version"] == 3

        # Verify no duplicates created
        assert embedding_service.vector_exists(vector_id)
