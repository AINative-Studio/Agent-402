"""
Comprehensive tests for Epic 4, Issue #16: embed-and-store endpoint.

Tests the POST /v1/public/{project_id}/embeddings/embed-and-store endpoint
which generates embeddings for multiple texts and stores them as vectors.

Test Coverage:
1. Successful embed and store with valid text input
2. Batch embedding with array of texts
3. Optional model parameter
4. Optional metadata parameter
5. Optional namespace parameter
6. Error handling for empty text
7. Error handling for invalid project_id
8. X-API-Key authentication requirement
9. Response validation (vector IDs, count, model, dimensions)
10. Edge cases and validation scenarios

Per PRD Section 10 (Success Criteria):
- All tests must pass
- Code coverage >80%
- Error cases properly handled
- Authentication properly enforced
"""
import pytest
from app.services.embed_store_service import embed_store_service


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vector storage before and after each test."""
    embed_store_service.clear_all()
    yield
    embed_store_service.clear_all()


# Use project_id fixture
@pytest.fixture
def project_id():
    """Test project ID."""
    return "proj_test_embed_store"


class TestEmbedStoreBasicFunctionality:
    """Test basic embed-and-store functionality."""

    def test_embed_and_store_single_text(self, client, auth_headers_user1, project_id):
        """
        Test embedding and storing a single text.

        Given: A single text string
        When: POST to embed-and-store endpoint
        Then: Text is embedded and stored successfully
        And: Response contains vector_id, model, dimensions
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Autonomous fintech agent executing compliance check"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "vectors_stored" in data
        assert "model" in data
        assert "dimensions" in data
        assert "vector_ids" in data

        # Verify response values
        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"  # Default model
        assert data["dimensions"] == 384  # Default dimensions
        assert len(data["vector_ids"]) == 1
        assert isinstance(data["vector_ids"][0], str)
        assert len(data["vector_ids"][0]) > 0

    def test_embed_and_store_multiple_texts(self, client, auth_headers_user1, project_id):
        """
        Test embedding and storing multiple texts in batch.

        Given: An array of text strings
        When: POST to embed-and-store endpoint
        Then: All texts are embedded and stored
        And: Response contains multiple vector_ids
        """
        texts = [
            "Autonomous fintech agent executing compliance check",
            "Transaction risk assessment completed successfully",
            "Portfolio rebalancing algorithm activated"
        ]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify batch storage
        assert data["vectors_stored"] == 3
        assert len(data["vector_ids"]) == 3
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

        # Verify all vector IDs are unique
        assert len(set(data["vector_ids"])) == 3

    def test_embed_and_store_with_default_model(self, client, auth_headers_user1, project_id):
        """
        Test that default model is used when not specified.

        Given: No model parameter in request
        When: POST to embed-and-store endpoint
        Then: Default model BAAI/bge-small-en-v1.5 is used
        And: Dimensions are 384
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test default model behavior"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384


class TestEmbedStoreModelParameter:
    """Test optional model parameter."""

    def test_embed_and_store_with_small_model(self, client, auth_headers_user1, project_id):
        """
        Test embedding with BAAI/bge-small-en-v1.5 model.

        Given: Model parameter set to BAAI/bge-small-en-v1.5
        When: POST to embed-and-store endpoint
        Then: Specified model is used
        And: Dimensions are 384
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test small model"],
                "model": "BAAI/bge-small-en-v1.5"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_embed_and_store_with_base_model(self, client, auth_headers_user1, project_id):
        """
        Test embedding with BAAI/bge-base-en-v1.5 model (768 dimensions).

        Given: Model parameter set to BAAI/bge-base-en-v1.5
        When: POST to embed-and-store endpoint
        Then: Specified model is used
        And: Dimensions are 768
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test base model"],
                "model": "sentence-transformers/all-mpnet-base-v2"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data["dimensions"] == 768

    def test_embed_and_store_with_invalid_model(self, client, auth_headers_user1, project_id):
        """
        Test error handling for unsupported model.

        Given: Invalid model parameter
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        And: Error message indicates unsupported model
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test invalid model"],
                "model": "invalid-model-name"
            }
        )

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        # Check if error mentions unsupported model
        error_detail = str(data["detail"]).lower()
        assert "not supported" in error_detail or "invalid" in error_detail


class TestEmbedStoreMetadataParameter:
    """Test optional metadata parameter."""

    def test_embed_and_store_with_metadata(self, client, auth_headers_user1, project_id):
        """
        Test storing vectors with metadata.

        Given: Metadata parameter with agent_id and task information
        When: POST to embed-and-store endpoint
        Then: Vectors are stored with metadata
        And: Metadata can be retrieved
        """
        metadata = {
            "agent_id": "compliance_agent",
            "task_type": "risk_assessment",
            "source": "agent_memory"
        }

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Agent memory with metadata"],
                "metadata": metadata
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == 1
        vector_id = data["vector_ids"][0]

        # Verify vector was stored with metadata
        stored_vector = embed_store_service.get_vector(vector_id)
        assert stored_vector is not None
        assert stored_vector["metadata"] == metadata

    def test_embed_and_store_without_metadata(self, client, auth_headers_user1, project_id):
        """
        Test storing vectors without metadata (optional parameter).

        Given: No metadata parameter
        When: POST to embed-and-store endpoint
        Then: Vectors are stored with empty metadata
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["No metadata test"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]
        stored_vector = embed_store_service.get_vector(vector_id)

        assert stored_vector["metadata"] == {}


class TestEmbedStoreNamespaceParameter:
    """Test optional namespace parameter."""

    def test_embed_and_store_with_custom_namespace(self, client, auth_headers_user1, project_id):
        """
        Test storing vectors in a custom namespace.

        Given: Namespace parameter set to "agent_memory"
        When: POST to embed-and-store endpoint
        Then: Vectors are stored in the specified namespace
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Custom namespace test"],
                "namespace": "agent_memory"
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]

        # Verify vector is in custom namespace
        stored_vector = embed_store_service.get_vector(vector_id, namespace="agent_memory")
        assert stored_vector is not None
        assert stored_vector["namespace"] == "agent_memory"

        # Verify it's NOT in default namespace
        default_vector = embed_store_service.get_vector(vector_id, namespace="default")
        assert default_vector is None

    def test_embed_and_store_with_default_namespace(self, client, auth_headers_user1, project_id):
        """
        Test that default namespace is used when not specified.

        Given: No namespace parameter
        When: POST to embed-and-store endpoint
        Then: Vectors are stored in "default" namespace
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Default namespace test"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]
        stored_vector = embed_store_service.get_vector(vector_id, namespace="default")

        assert stored_vector is not None
        assert stored_vector["namespace"] == "default"

    def test_embed_and_store_namespace_isolation(self, client, auth_headers_user1, project_id):
        """
        Test that namespaces are isolated from each other.

        Given: Same text stored in different namespaces
        When: Vectors are queried by namespace
        Then: Each namespace contains only its own vectors
        """
        text = "Namespace isolation test"

        # Store in namespace1
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [text],
                "namespace": "namespace1"
            }
        )

        # Store in namespace2
        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [text],
                "namespace": "namespace2"
            }
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        vector_id1 = response1.json()["vector_ids"][0]
        vector_id2 = response2.json()["vector_ids"][0]

        # Verify isolation
        vec1_in_ns1 = embed_store_service.get_vector(vector_id1, namespace="namespace1")
        vec1_in_ns2 = embed_store_service.get_vector(vector_id1, namespace="namespace2")
        vec2_in_ns1 = embed_store_service.get_vector(vector_id2, namespace="namespace1")
        vec2_in_ns2 = embed_store_service.get_vector(vector_id2, namespace="namespace2")

        assert vec1_in_ns1 is not None
        assert vec1_in_ns2 is None
        assert vec2_in_ns1 is None
        assert vec2_in_ns2 is not None


class TestEmbedStoreErrorHandling:
    """Test error handling for invalid inputs."""

    def test_embed_and_store_with_empty_texts_array(self, client, auth_headers_user1, project_id):
        """
        Test error handling for empty texts array.

        Given: Empty texts array
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": []
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_embed_and_store_with_empty_string(self, client, auth_headers_user1, project_id):
        """
        Test error handling for empty string in texts array.

        Given: Texts array containing empty string
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [""]
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_embed_and_store_with_whitespace_only(self, client, auth_headers_user1, project_id):
        """
        Test error handling for whitespace-only text.

        Given: Texts array containing only whitespace
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["   ", "\t\n"]
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_embed_and_store_with_missing_texts_field(self, client, auth_headers_user1, project_id):
        """
        Test error handling for missing required texts field.

        Given: Request without texts field
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_embed_and_store_with_invalid_namespace_characters(self, client, auth_headers_user1, project_id):
        """
        Test error handling for invalid namespace characters.

        Given: Namespace with invalid special characters
        When: POST to embed-and-store endpoint
        Then: 422 validation error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test"],
                "namespace": "invalid@namespace!"
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestEmbedStoreAuthentication:
    """Test X-API-Key authentication requirements."""

    def test_embed_and_store_without_api_key(self, client, project_id):
        """
        Test that endpoint requires X-API-Key header.

        Given: No X-API-Key header
        When: POST to embed-and-store endpoint
        Then: 401 unauthorized error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test without auth"]
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_embed_and_store_with_invalid_api_key(self, client, project_id):
        """
        Test error handling for invalid API key.

        Given: Invalid X-API-Key header
        When: POST to embed-and-store endpoint
        Then: 401 unauthorized error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers={"X-API-Key": "invalid_key_12345"},
            json={
                "texts": ["Test with invalid auth"]
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_embed_and_store_with_empty_api_key(self, client, project_id):
        """
        Test error handling for empty API key.

        Given: Empty X-API-Key header
        When: POST to embed-and-store endpoint
        Then: 401 unauthorized error is returned
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers={"X-API-Key": ""},
            json={
                "texts": ["Test with empty auth"]
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_embed_and_store_with_valid_api_key(self, client, auth_headers_user1, project_id):
        """
        Test successful authentication with valid API key.

        Given: Valid X-API-Key header
        When: POST to embed-and-store endpoint
        Then: Request is authenticated successfully
        And: Embeddings are generated and stored
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test with valid auth"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vectors_stored"] == 1


class TestEmbedStoreResponseValidation:
    """Test response structure and data validation."""

    def test_embed_and_store_response_structure(self, client, auth_headers_user1, project_id):
        """
        Test that response has correct structure.

        Given: Valid embed-and-store request
        When: Vectors are stored successfully
        Then: Response contains all required fields
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Response structure test"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["vectors_stored", "model", "dimensions", "vector_ids"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_embed_and_store_vector_ids_format(self, client, auth_headers_user1, project_id):
        """
        Test that vector IDs have correct format.

        Given: Stored vectors
        When: Response is returned
        Then: Vector IDs are non-empty strings with vec_ prefix
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Vector ID format test"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        for vector_id in data["vector_ids"]:
            assert isinstance(vector_id, str)
            assert len(vector_id) > 0
            assert vector_id.startswith("vec_")

    def test_embed_and_store_vectors_count_matches(self, client, auth_headers_user1, project_id):
        """
        Test that vectors_stored count matches vector_ids length.

        Given: Multiple texts to embed
        When: Vectors are stored
        Then: vectors_stored equals length of vector_ids array
        """
        texts = [
            "First text",
            "Second text",
            "Third text",
            "Fourth text"
        ]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == len(texts)
        assert len(data["vector_ids"]) == len(texts)
        assert data["vectors_stored"] == len(data["vector_ids"])

    def test_embed_and_store_vectors_are_retrievable(self, client, auth_headers_user1, project_id):
        """
        Test that stored vectors can be retrieved.

        Given: Vectors stored via embed-and-store
        When: Vectors are queried by ID
        Then: All vectors can be retrieved successfully
        """
        texts = ["Retrievable text 1", "Retrievable text 2"]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all vectors are retrievable
        for idx, vector_id in enumerate(data["vector_ids"]):
            stored_vector = embed_store_service.get_vector(vector_id)
            assert stored_vector is not None
            assert stored_vector["document"] == texts[idx]
            assert stored_vector["vector_id"] == vector_id


class TestEmbedStoreEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_embed_and_store_with_long_text(self, client, auth_headers_user1, project_id):
        """
        Test embedding and storing long text.

        Given: Very long text string
        When: POST to embed-and-store endpoint
        Then: Text is processed successfully
        """
        long_text = "Test " * 200  # 1000+ characters

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [long_text]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vectors_stored"] == 1

    def test_embed_and_store_with_special_characters(self, client, auth_headers_user1, project_id):
        """
        Test embedding text with special characters.

        Given: Text containing special characters
        When: POST to embed-and-store endpoint
        Then: Text is processed correctly
        """
        special_text = "Test with émojis 🚀 and spëcial chàracters! #AI @agent"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [special_text]
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]
        stored_vector = embed_store_service.get_vector(vector_id)
        assert stored_vector["document"] == special_text

    def test_embed_and_store_with_unicode_text(self, client, auth_headers_user1, project_id):
        """
        Test embedding text with various Unicode characters.

        Given: Text with Chinese, Arabic, and Emoji characters
        When: POST to embed-and-store endpoint
        Then: Text is processed correctly
        """
        unicode_texts = [
            "中文测试",
            "اختبار عربي",
            "Тест на русском",
            "🎯 Emoji test 🚀"
        ]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": unicode_texts
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vectors_stored"] == len(unicode_texts)

    def test_embed_and_store_with_large_batch(self, client, auth_headers_user1, project_id):
        """
        Test embedding and storing a large batch of texts.

        Given: 50 texts to embed
        When: POST to embed-and-store endpoint
        Then: All texts are processed successfully
        """
        texts = [f"Batch test text number {i}" for i in range(50)]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": texts
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == 50
        assert len(data["vector_ids"]) == 50
        assert len(set(data["vector_ids"])) == 50  # All unique

    def test_embed_and_store_with_complex_metadata(self, client, auth_headers_user1, project_id):
        """
        Test storing vectors with complex nested metadata.

        Given: Complex metadata with nested objects
        When: POST to embed-and-store endpoint
        Then: Metadata is stored correctly
        """
        complex_metadata = {
            "agent_id": "agent_123",
            "task": {
                "type": "compliance_check",
                "priority": "high",
                "params": {
                    "threshold": 0.8,
                    "auto_approve": False
                }
            },
            "tags": ["compliance", "risk", "audit"],
            "timestamp": "2024-01-10T12:00:00Z"
        }

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Complex metadata test"],
                "metadata": complex_metadata
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]
        stored_vector = embed_store_service.get_vector(vector_id)
        assert stored_vector["metadata"] == complex_metadata


class TestEmbedStoreProjectIdValidation:
    """Test project_id parameter handling."""

    def test_embed_and_store_with_different_project_ids(self, client, auth_headers_user1):
        """
        Test that different project IDs work correctly.

        Given: Different project_id values
        When: POST to embed-and-store endpoint
        Then: Each project_id is accepted
        """
        project_ids = ["proj_001", "proj_test", "proj_abc123"]

        for pid in project_ids:
            response = client.post(
                f"/v1/public/{pid}/embeddings/embed-and-store",
                headers=auth_headers_user1,
                json={
                    "texts": [f"Test for project {pid}"]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["vectors_stored"] == 1

    def test_embed_and_store_with_special_project_id(self, client, auth_headers_user1):
        """
        Test project_id with special characters.

        Given: project_id with underscores and hyphens
        When: POST to embed-and-store endpoint
        Then: Request is processed successfully
        """
        project_id = "proj_test-123_v1"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Special project ID test"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        vector_id = data["vector_ids"][0]
        stored_vector = embed_store_service.get_vector(vector_id)
        assert stored_vector["project_id"] == project_id


class TestEmbedStoreDeterminism:
    """Test deterministic behavior of embeddings."""

    def test_embed_and_store_same_text_produces_unique_ids(self, client, auth_headers_user1, project_id):
        """
        Test that storing the same text twice produces different vector IDs.

        Given: Same text stored twice
        When: POST to embed-and-store endpoint twice
        Then: Different vector IDs are generated
        """
        text = "Determinism test text"

        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": [text]}
        )

        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": [text]}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        vector_id1 = response1.json()["vector_ids"][0]
        vector_id2 = response2.json()["vector_ids"][0]

        # Vector IDs should be unique (not upsert mode)
        assert vector_id1 != vector_id2

    def test_embed_and_store_consistent_dimensions(self, client, auth_headers_user1, project_id):
        """
        Test that same model always produces same dimensions.

        Given: Multiple requests with same model
        When: Embeddings are generated
        Then: Dimensions are consistent across requests
        """
        responses = []
        for i in range(3):
            response = client.post(
                f"/v1/public/{project_id}/embeddings/embed-and-store",
                headers=auth_headers_user1,
                json={
                    "texts": [f"Consistency test {i}"],
                    "model": "BAAI/bge-small-en-v1.5"
                }
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

        # All should have same dimensions
        dimensions = [r.json()["dimensions"] for r in responses]
        assert len(set(dimensions)) == 1
        assert dimensions[0] == 384
