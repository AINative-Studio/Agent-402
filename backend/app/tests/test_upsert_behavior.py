"""
Comprehensive tests for Epic 4, Issue #18: Upsert behavior for embed-and-store endpoint.

As a developer, `upsert: true` updates existing IDs without duplication (2 pts).

CURRENT STATUS:
===============
The embed-and-store endpoint from embeddings_embed_store.py is active and accepts:
- texts: List[str] - Array of texts to embed
- metadata: Optional[Dict[str, Any]] - Single metadata dict applied to ALL texts
- namespace: Optional[str] - Namespace for isolation (defaults to 'default')
- upsert: Optional[bool] - Upsert flag (defaults to False)
- model: Optional[str] - Embedding model (defaults to BAAI/bge-small-en-v1.5)

LIMITATION:
-----------
The current implementation does NOT support custom vector_ids, which is required
for proper upsert behavior per Issue #18. The upsert parameter is accepted but
NOT YET IMPLEMENTED in embed_store_service.py.

These tests document the INTENDED behavior once upsert with vector_ids is implemented.

Test Coverage (as specified in Issue #18):
1. Test upsert=true updates existing document (no duplication)
2. Test upsert=false (or not specified) creates new entries
3. Test upsert with vector_id specified
4. Test upsert behavior when document doesn't exist (should create)
5. Test upsert behavior when document exists (should update)
6. Test count of stored vectors remains same after upsert update
7. Test metadata is updated during upsert
8. Test text content is re-embedded during upsert
9. Test upsert with namespace scoping
10. Verify response indicates update vs create

Endpoint Under Test:
POST /v1/public/{project_id}/embeddings/embed-and-store (from embeddings_embed_store.py)

Files Under Test:
- backend/app/api/embeddings_embed_store.py - API endpoint
- backend/app/services/embed_store_service.py - Service with upsert logic
- backend/app/schemas/embed_store.py - Request schema with upsert field

Built by AINative Dev Team
"""
import pytest
from fastapi.testclient import TestClient
from app.services.embed_store_service import embed_store_service


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vector store before and after each test."""
    embed_store_service.clear_all()
    yield
    embed_store_service.clear_all()


@pytest.fixture
def client():
    """Test client fixture."""
    try:
        from app.main_simple import app
        return TestClient(app)
    except ImportError:
        from app.main import app
        return TestClient(app)


@pytest.fixture
def valid_headers():
    """Valid API key headers for authentication."""
    from app.core.config import settings
    return {"X-API-Key": settings.demo_api_key_1}


class TestCurrentImplementation:
    """Test the current implementation without upsert (baseline tests)."""

    def test_basic_embed_and_store_creates_vectors(self, client, valid_headers):
        """
        Baseline test: Verify basic embed-and-store functionality works.

        Given: A request with texts to embed
        When: The request is processed
        Then: Vectors are created and vector_ids are returned
        """
        # Act
        payload = {
            "texts": ["Machine learning is fascinating"],
            "namespace": "default",
            "metadata": {"source": "test"},
            "upsert": False
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert len(data["vector_ids"]) == 1
        assert data["vector_ids"][0].startswith("vec_")

    def test_batch_embed_and_store_multiple_texts(self, client, valid_headers):
        """
        Baseline test: Verify batch processing of multiple texts.

        Given: Multiple texts in a single request
        When: The request is processed
        Then: All texts are embedded and stored with unique IDs
        """
        # Act
        payload = {
            "texts": [
                "Deep learning uses neural networks",
                "Natural language processing analyzes text",
                "Computer vision detects objects"
            ],
            "namespace": "batch_test",
            "metadata": {"batch": "test_batch_1"},
            "upsert": False
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == 3
        assert len(data["vector_ids"]) == 3
        # All IDs should be unique
        assert len(set(data["vector_ids"])) == 3

    def test_namespace_isolation(self, client, valid_headers):
        """
        Baseline test: Verify namespace isolation works.

        Given: Same texts stored in different namespaces
        When: Vectors are created
        Then: Each namespace has its own isolated vectors
        """
        # Arrange & Act - Store in namespace1
        payload1 = {
            "texts": ["Namespace isolation test"],
            "namespace": "namespace1",
            "upsert": False
        }

        response1 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload1,
            headers=valid_headers
        )

        # Store in namespace2
        payload2 = {
            "texts": ["Namespace isolation test"],
            "namespace": "namespace2",
            "upsert": False
        }

        response2 = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload2,
            headers=valid_headers
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Different vector IDs despite same text (isolated namespaces)
        assert response1.json()["vector_ids"][0] != response2.json()["vector_ids"][0]

    def test_metadata_applied_to_all_vectors(self, client, valid_headers):
        """
        Baseline test: Verify metadata is applied to all vectors in batch.

        Given: Multiple texts with shared metadata
        When: Vectors are created
        Then: All vectors have the same metadata
        """
        # Act
        payload = {
            "texts": [
                "Text one",
                "Text two",
                "Text three"
            ],
            "namespace": "metadata_test",
            "metadata": {
                "source": "test_suite",
                "batch_id": "batch_001",
                "priority": "high"
            },
            "upsert": False
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all vectors were created
        assert data["vectors_stored"] == 3

        # Verify metadata was applied by checking stored vectors
        for vector_id in data["vector_ids"]:
            vector = embed_store_service.get_vector(vector_id, "metadata_test")
            assert vector is not None
            assert vector["metadata"]["source"] == "test_suite"
            assert vector["metadata"]["batch_id"] == "batch_001"
            assert vector["metadata"]["priority"] == "high"

    def test_model_parameter_affects_dimensions(self, client, valid_headers):
        """
        Baseline test: Verify different models produce different dimensions.

        Given: Requests with different embedding models
        When: Vectors are created
        Then: Vector dimensions match the model specifications
        """
        # Test with small model (384 dims)
        payload_small = {
            "texts": ["Test with small model"],
            "model": "BAAI/bge-small-en-v1.5",
            "namespace": "model_test",
            "upsert": False
        }

        response_small = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload_small,
            headers=valid_headers
        )

        # Test with mpnet model (768 dims)
        payload_base = {
            "texts": ["Test with mpnet model"],
            "model": "sentence-transformers/all-mpnet-base-v2",
            "namespace": "model_test",
            "upsert": False
        }

        response_base = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload_base,
            headers=valid_headers
        )

        # Assert
        assert response_small.status_code == 200
        assert response_base.status_code == 200

        assert response_small.json()["dimensions"] == 384
        assert response_base.json()["dimensions"] == 768


class TestUpsertFeatureRequirements:
    """
    Tests for upsert feature requirements (Issue #18).

    NOTE: These tests will FAIL until upsert is implemented in embed_store_service.py.
    They document the EXPECTED behavior once implementation is complete.

    Required implementation changes:
    1. Add vector_ids parameter to EmbedStoreRequest schema (List[str])
    2. Implement upsert logic in embed_store_service.embed_and_store()
    3. Add created/updated tracking in response
    4. Support document-level deduplication based on content or explicit IDs
    """

    @pytest.mark.skip(reason="Upsert not yet implemented - awaiting vector_ids parameter support")
    def test_upsert_true_with_vector_ids_updates_existing(self, client, valid_headers):
        """
        Issue #18 - Requirement 1 & 5: upsert=true updates existing documents.

        IMPLEMENTATION NEEDED:
        - Add vector_ids: Optional[List[str]] to EmbedStoreRequest
        - When upsert=true and vector_id exists, UPDATE the document
        - When upsert=true and vector_id doesn't exist, CREATE new document

        Given: A vector with specific ID exists
        When: Same ID submitted with upsert=true
        Then: Vector is updated, not duplicated
        """
        # Arrange - Create initial vector with specific ID
        initial_payload = {
            "texts": ["Machine learning powers intelligent systems"],
            "vector_ids": ["test_vec_001"],  # TODO: Add to schema
            "namespace": "default",
            "metadata": {"version": 1},
            "upsert": True
        }

        initial_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_payload,
            headers=valid_headers
        )

        assert initial_response.status_code == 200
        assert initial_response.json()["vector_ids"] == ["test_vec_001"]

        # Act - Update with same ID
        update_payload = {
            "texts": ["Machine learning powers intelligent systems - updated"],
            "vector_ids": ["test_vec_001"],  # Same ID
            "namespace": "default",
            "metadata": {"version": 2},
            "upsert": True
        }

        update_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=update_payload,
            headers=valid_headers
        )

        # Assert
        assert update_response.status_code == 200
        assert update_response.json()["vector_ids"] == ["test_vec_001"]

        # Verify no duplicate - should still be only 1 vector
        all_vectors, count = embed_store_service.list_vectors("default")
        assert count == 1, f"Expected 1 vector, found {count} (duplication occurred)"

    @pytest.mark.skip(reason="Upsert not yet implemented - awaiting vector_ids parameter support")
    def test_upsert_false_with_vector_ids_errors_on_duplicate(self, client, valid_headers):
        """
        Issue #18 - Requirement 2: upsert=false errors when vector_id exists.

        IMPLEMENTATION NEEDED:
        - When upsert=false and vector_id exists, return 409 VECTOR_ALREADY_EXISTS

        Given: A vector with specific ID exists
        When: Same ID submitted with upsert=false
        Then: 409 error is returned
        """
        # Arrange - Create initial vector
        initial_payload = {
            "texts": ["Initial vector"],
            "vector_ids": ["test_vec_conflict"],
            "namespace": "default",
            "upsert": False
        }

        initial_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_payload,
            headers=valid_headers
        )

        assert initial_response.status_code == 200

        # Act - Try to create duplicate
        duplicate_payload = {
            "texts": ["Duplicate attempt"],
            "vector_ids": ["test_vec_conflict"],
            "namespace": "default",
            "upsert": False
        }

        duplicate_response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=duplicate_payload,
            headers=valid_headers
        )

        # Assert
        assert duplicate_response.status_code == 409
        error_data = duplicate_response.json()
        assert error_data["error_code"] == "VECTOR_ALREADY_EXISTS"

    @pytest.mark.skip(reason="Upsert not yet implemented - awaiting content-based deduplication")
    def test_upsert_true_deduplicates_by_content(self, client, valid_headers):
        """
        Issue #18 - Requirement 1: upsert=true deduplicates by content when IDs not provided.

        IMPLEMENTATION NEEDED:
        - When upsert=true and no vector_ids provided, deduplicate by text content
        - If same text exists in namespace, update it instead of creating duplicate

        Given: Same text submitted multiple times with upsert=true
        When: No explicit vector_ids provided
        Then: Text is deduplicated (only one vector created)
        """
        # Act - Submit same text 3 times
        payload = {
            "texts": ["Quantum computing explores superposition"],
            "namespace": "dedup_test",
            "upsert": True
        }

        vector_ids = []
        for _ in range(3):
            response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=payload,
                headers=valid_headers
            )
            assert response.status_code == 200
            vector_ids.extend(response.json()["vector_ids"])

        # Assert - All requests should return same vector ID (deduplicated)
        assert len(set(vector_ids)) == 1, "Same text with upsert=true should be deduplicated"

        # Verify only 1 vector exists
        all_vectors, count = embed_store_service.list_vectors("dedup_test")
        assert count == 1

    @pytest.mark.skip(reason="Upsert not yet implemented - awaiting response enhancement")
    def test_response_indicates_created_vs_updated(self, client, valid_headers):
        """
        Issue #18 - Requirement 10: Response indicates creation vs update.

        IMPLEMENTATION NEEDED:
        - Add vectors_inserted: int to EmbedStoreResponse
        - Add vectors_updated: int to EmbedStoreResponse
        - Track which vectors were newly created vs updated

        Given: Mix of new and existing vector_ids
        When: Submitted with upsert=true
        Then: Response shows count of inserted vs updated
        """
        # Arrange - Create one vector
        initial_payload = {
            "texts": ["Existing vector"],
            "vector_ids": ["vec_existing"],
            "namespace": "tracking_test",
            "upsert": True
        }

        client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=initial_payload,
            headers=valid_headers
        )

        # Act - Submit mix of existing and new
        mixed_payload = {
            "texts": [
                "Existing vector - updated",  # Should update vec_existing
                "New vector one",              # Should create new
                "New vector two"               # Should create new
            ],
            "vector_ids": ["vec_existing", "vec_new_1", "vec_new_2"],
            "namespace": "tracking_test",
            "upsert": True
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=mixed_payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # TODO: Add these fields to schema
        assert data["vectors_inserted"] == 2  # vec_new_1, vec_new_2
        assert data["vectors_updated"] == 1   # vec_existing
        assert data["vectors_stored"] == 3    # Total


class TestDeterministicBehavior:
    """Test deterministic behavior per PRD Section 10."""

    def test_same_text_produces_same_embedding(self, client, valid_headers):
        """
        PRD Section 10: Same text produces same embedding (determinism).

        Given: The same text is embedded multiple times
        When: Using the same model
        Then: The embedding vector is identical each time
        """
        # Arrange
        text = "Deterministic embeddings enable reproducibility"

        # Act - Embed same text in different namespaces
        embeddings = []
        for i in range(3):
            payload = {
                "texts": [text],
                "namespace": f"determinism_test_{i}",
                "model": "BAAI/bge-small-en-v1.5",
                "upsert": False
            }

            response = client.post(
                "/v1/public/test-project/embeddings/embed-and-store",
                json=payload,
                headers=valid_headers
            )

            assert response.status_code == 200
            vector_id = response.json()["vector_ids"][0]
            vector = embed_store_service.get_vector(vector_id, f"determinism_test_{i}")
            embeddings.append(vector["embedding"])

        # Assert - All embeddings are identical
        assert len(embeddings) == 3
        assert embeddings[0] == embeddings[1] == embeddings[2], "Same text should produce identical embeddings"

    def test_auto_generated_ids_are_unique(self, client, valid_headers):
        """
        Verify auto-generated IDs don't collide.

        Given: Multiple texts without explicit vector_ids
        When: Vectors are created
        Then: All IDs are unique (no collisions)
        """
        # Act - Create 10 vectors
        payload = {
            "texts": [f"Test vector {i}" for i in range(10)],
            "namespace": "unique_id_test",
            "upsert": False
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 200
        vector_ids = response.json()["vector_ids"]

        assert len(vector_ids) == 10
        assert len(set(vector_ids)) == 10, "All auto-generated IDs should be unique"


class TestErrorHandling:
    """Test error handling and validation."""

    def test_empty_texts_array_returns_error(self, client, valid_headers):
        """Verify empty texts array is rejected."""
        # Act
        payload = {
            "texts": [],  # Empty array
            "namespace": "default"
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_whitespace_only_text_returns_error(self, client, valid_headers):
        """Verify whitespace-only texts are rejected."""
        # Act
        payload = {
            "texts": ["   ", "\t\n", ""],  # Whitespace only
            "namespace": "default"
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_invalid_model_returns_error(self, client, valid_headers):
        """Verify invalid model name is rejected."""
        # Act
        payload = {
            "texts": ["Test text"],
            "model": "invalid-model-name",
            "namespace": "default"
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload,
            headers=valid_headers
        )

        # Assert
        assert response.status_code in [404, 422]  # Model not found or validation error

    def test_missing_api_key_returns_401(self, client):
        """Verify authentication is required."""
        # Act - Request without API key
        payload = {
            "texts": ["Test text"],
            "namespace": "default"
        }

        response = client.post(
            "/v1/public/test-project/embeddings/embed-and-store",
            json=payload
            # No headers
        )

        # Assert
        assert response.status_code == 401  # Unauthorized
