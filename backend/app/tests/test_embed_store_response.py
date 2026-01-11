"""
Tests for Embed-and-Store Response Structure (Epic 4, Issue 19).

Tests the response structure and metadata for POST /v1/public/{project_id}/embeddings/embed-and-store

Issue 19 Requirements (✓ ALL 28 TESTS PASSING):
1. ✓ Response includes vectors_stored count
2. ✓ Response includes model used for embedding
3. ✓ Response includes dimensions of the vectors
4. ✓ Response includes vector_ids array
5. ✓ vectors_stored matches number of texts provided
6. ✓ dimensions matches model's expected output (384, 768)
7. ✓ model field matches requested model (or default)
8. ✓ Response format follows DX Contract

Note: This test suite validates the embeddings_embed_store.py endpoint which uses:
- Request field: 'texts' (List[str])
- Response schema: EmbedStoreResponse with 4 fields (vectors_stored, model, dimensions, vector_ids)
- Metadata format: Dict (not List)

Test Coverage Summary (28 tests):
- Response structure validation: 4 tests
- Model field accuracy: 4 tests (default + BAAI/bge-small + sentence-transformers models)
- Dimensions field accuracy: 5 tests (384-dim and 768-dim models)
- Vector IDs field validation: 3 tests (uniqueness, format, type)
- Response consistency: 3 tests (namespace, metadata, multi-model)
- Field type validation: 3 tests (integers, strings, arrays)
- Edge cases: 4 tests (large batch, special chars, long text, minimal request)
- Authentication: 2 tests (missing key, invalid key)

Supported Models Tested:
- BAAI/bge-small-en-v1.5: 384 dimensions (default)
- sentence-transformers/all-MiniLM-L6-v2: 384 dimensions
- sentence-transformers/all-mpnet-base-v2: 768 dimensions

Per DX Contract Section 3 (Embeddings & Vectors):
- Default model: BAAI/bge-small-en-v1.5 → 384 dimensions
- Model must be specified consistently for store + search
- Response must include all required metadata fields

Per PRD Section 6 (Agent memory foundation):
- Vectors stored with complete metadata for auditability
- Namespace support for multi-agent isolation
- Deterministic behavior per PRD Section 10

Built by AINative Dev Team
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestEmbedStoreResponseStructure:
    """Tests for response structure validation."""

    def test_response_includes_all_required_fields(self, client, auth_headers_user1):
        """
        Test that response includes all required fields.
        Issue 19: Response includes vectors_stored, model, dimensions, vector_ids.
        """
        response = client.post(
            "/v1/public/proj_test_001/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [
                    "Autonomous agent executing compliance check",
                    "Transaction risk assessment completed"
                ]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields are present
        assert "vectors_stored" in data, "Response must include vectors_stored"
        assert "model" in data, "Response must include model"
        assert "dimensions" in data, "Response must include dimensions"
        assert "vector_ids" in data, "Response must include vector_ids"

    def test_vectors_stored_matches_text_count(self, client, auth_headers_user1):
        """
        Test that vectors_stored matches the number of texts provided.
        Issue 19: vectors_stored matches number of texts provided.
        """
        texts = [
            "First agent memory entry",
            "Second agent memory entry",
            "Third agent memory entry"
        ]

        response = client.post(
            "/v1/public/proj_test_002/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["vectors_stored"] == len(texts), \
            f"vectors_stored should be {len(texts)}, got {data['vectors_stored']}"

    def test_vector_ids_array_length_matches_text_count(self, client, auth_headers_user1):
        """
        Test that vector_ids array length matches text count.
        Issue 19: vector_ids array contains ID for each stored vector.
        """
        texts = [
            "Agent decision log entry 1",
            "Agent decision log entry 2",
            "Agent decision log entry 3",
            "Agent decision log entry 4"
        ]

        response = client.post(
            "/v1/public/proj_test_003/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["vector_ids"]) == len(texts), \
            f"vector_ids should contain {len(texts)} IDs, got {len(data['vector_ids'])}"

        # Verify each vector ID has the expected format
        for vector_id in data["vector_ids"]:
            assert vector_id.startswith("vec_"), \
                f"Vector ID should start with 'vec_', got {vector_id}"

    def test_single_text_returns_single_vector(self, client, auth_headers_user1):
        """
        Test embedding a single text returns correct count.
        Edge case: Single text input.
        """
        response = client.post(
            "/v1/public/proj_test_004/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Single agent memory entry"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["vectors_stored"] == 1
        assert len(data["vector_ids"]) == 1
        assert data["vector_ids"][0].startswith("vec_")


class TestEmbedStoreModelField:
    """Tests for model field in response."""

    def test_default_model_when_not_specified(self, client, auth_headers_user1):
        """
        Test that default model is used when model is not specified.
        Issue 19: model field matches requested model (or default).
        DX Contract: Default model is BAAI/bge-small-en-v1.5.
        """
        response = client.post(
            "/v1/public/proj_test_005/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test text for default model"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5", \
            "Default model should be BAAI/bge-small-en-v1.5"

    def test_model_matches_requested_model_small(self, client, auth_headers_user1):
        """
        Test that model field matches explicitly requested model (small).
        Issue 19: model field matches requested model.
        """
        response = client.post(
            "/v1/public/proj_test_006/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test text for small model"],
                "model": "BAAI/bge-small-en-v1.5"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5"

    def test_model_matches_requested_model_mpnet(self, client, auth_headers_user1):
        """
        Test that model field matches explicitly requested model (mpnet - 768 dims).
        Issue 19: model field matches requested model.
        """
        response = client.post(
            "/v1/public/proj_test_007/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test text for mpnet model"],
                "model": "sentence-transformers/all-mpnet-base-v2"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"

    def test_model_matches_requested_model_minilm(self, client, auth_headers_user1):
        """
        Test that model field matches explicitly requested model (MiniLM - 384 dims).
        Issue 19: model field matches requested model.
        """
        response = client.post(
            "/v1/public/proj_test_008/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test text for MiniLM model"],
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["model"] == "sentence-transformers/all-MiniLM-L6-v2"


class TestEmbedStoreDimensionsField:
    """Tests for dimensions field in response."""

    def test_dimensions_match_default_model(self, client, auth_headers_user1):
        """
        Test that dimensions match default model (384).
        Issue 19: dimensions matches model's expected output.
        DX Contract: BAAI/bge-small-en-v1.5 → 384 dimensions.
        """
        response = client.post(
            "/v1/public/proj_test_009/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test for default dimensions"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["dimensions"] == 384, \
            "Default model (BAAI/bge-small-en-v1.5) should have 384 dimensions"

    def test_dimensions_match_small_model(self, client, auth_headers_user1):
        """
        Test that dimensions match small model (384).
        Issue 19: dimensions matches model's expected output.
        """
        response = client.post(
            "/v1/public/proj_test_010/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test for small model dimensions"],
                "model": "BAAI/bge-small-en-v1.5"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["dimensions"] == 384, \
            "BAAI/bge-small-en-v1.5 should have 384 dimensions"

    def test_dimensions_match_mpnet_model(self, client, auth_headers_user1):
        """
        Test that dimensions match mpnet model (768).
        Issue 19: dimensions matches model's expected output.
        """
        response = client.post(
            "/v1/public/proj_test_011/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test for mpnet model dimensions"],
                "model": "sentence-transformers/all-mpnet-base-v2"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["dimensions"] == 768, \
            "sentence-transformers/all-mpnet-base-v2 should have 768 dimensions"

    def test_dimensions_match_minilm_model(self, client, auth_headers_user1):
        """
        Test that dimensions match MiniLM model (384).
        Issue 19: dimensions matches model's expected output.
        """
        response = client.post(
            "/v1/public/proj_test_012/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test for MiniLM model dimensions"],
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["dimensions"] == 384, \
            "sentence-transformers/all-MiniLM-L6-v2 should have 384 dimensions"

    def test_dimensions_type_is_integer(self, client, auth_headers_user1):
        """
        Test that dimensions field is an integer.
        Issue 19: Verify response format follows DX Contract.
        """
        response = client.post(
            "/v1/public/proj_test_013/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test dimensions type"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["dimensions"], int), \
            "dimensions should be an integer"
        assert data["dimensions"] > 0, \
            "dimensions should be positive"


class TestEmbedStoreVectorIdsField:
    """Tests for vector_ids field in response."""

    def test_vector_ids_are_unique(self, client, auth_headers_user1):
        """
        Test that all vector IDs are unique.
        Issue 19: vector_ids array contains unique IDs.
        """
        response = client.post(
            "/v1/public/proj_test_014/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [
                    "First unique vector",
                    "Second unique vector",
                    "Third unique vector",
                    "Fourth unique vector",
                    "Fifth unique vector"
                ]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        vector_ids = data["vector_ids"]
        unique_ids = set(vector_ids)

        assert len(vector_ids) == len(unique_ids), \
            "All vector IDs should be unique"

    def test_vector_ids_format(self, client, auth_headers_user1):
        """
        Test that vector IDs follow expected format.
        Issue 19: vector_ids follow vec_ prefix convention.
        """
        response = client.post(
            "/v1/public/proj_test_015/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test vector ID format"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for vector_id in data["vector_ids"]:
            assert isinstance(vector_id, str), \
                "Vector ID should be a string"
            assert vector_id.startswith("vec_"), \
                f"Vector ID should start with 'vec_', got {vector_id}"
            assert len(vector_id) > 4, \
                "Vector ID should have content after 'vec_' prefix"

    def test_vector_ids_is_array(self, client, auth_headers_user1):
        """
        Test that vector_ids is an array.
        Issue 19: Verify response format follows DX Contract.
        """
        response = client.post(
            "/v1/public/proj_test_016/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test vector_ids is array"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["vector_ids"], list), \
            "vector_ids should be an array"


class TestEmbedStoreResponseConsistency:
    """Tests for response consistency and metadata accuracy."""

    def test_response_with_namespace(self, client, auth_headers_user1):
        """
        Test response when custom namespace is provided.
        Issue 19: Response includes namespace used (not in schema, but should be consistent).
        """
        response = client.post(
            "/v1/public/proj_test_017/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test with custom namespace"],
                "namespace": "agent_memory_team"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Response structure should be consistent regardless of namespace
        assert "vectors_stored" in data
        assert "model" in data
        assert "dimensions" in data
        assert "vector_ids" in data

    def test_response_with_metadata(self, client, auth_headers_user1):
        """
        Test response when metadata is provided.
        Issue 19: Response structure consistent with metadata.
        """
        response = client.post(
            "/v1/public/proj_test_018/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test with metadata"],
                "metadata": {
                    "agent_id": "compliance_agent",
                    "task_type": "risk_assessment",
                    "source": "agent_memory"
                }
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Response structure should be consistent regardless of metadata
        assert data["vectors_stored"] == 1
        assert "model" in data
        assert "dimensions" in data
        assert len(data["vector_ids"]) == 1

    def test_multiple_texts_different_models(self, client, auth_headers_user1):
        """
        Test consistency when storing multiple texts with different models.
        Issue 19: Model and dimensions consistency across all vectors.
        """
        # Test with small model (384 dims)
        response_small = client.post(
            "/v1/public/proj_test_019/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Text 1", "Text 2", "Text 3"],
                "model": "BAAI/bge-small-en-v1.5"
            }
        )

        assert response_small.status_code == status.HTTP_200_OK
        data_small = response_small.json()

        assert data_small["model"] == "BAAI/bge-small-en-v1.5"
        assert data_small["dimensions"] == 384
        assert data_small["vectors_stored"] == 3

        # Test with mpnet model (768 dims)
        response_mpnet = client.post(
            "/v1/public/proj_test_020/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Text 1", "Text 2", "Text 3"],
                "model": "sentence-transformers/all-mpnet-base-v2"
            }
        )

        assert response_mpnet.status_code == status.HTTP_200_OK
        data_mpnet = response_mpnet.json()

        assert data_mpnet["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data_mpnet["dimensions"] == 768
        assert data_mpnet["vectors_stored"] == 3


class TestEmbedStoreResponseFieldTypes:
    """Tests for response field types and validation."""

    def test_vectors_stored_is_integer(self, client, auth_headers_user1):
        """
        Test that vectors_stored is an integer.
        Issue 19: Verify response format follows DX Contract.
        """
        response = client.post(
            "/v1/public/proj_test_021/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test vectors_stored type"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["vectors_stored"], int), \
            "vectors_stored should be an integer"
        assert data["vectors_stored"] >= 0, \
            "vectors_stored should be non-negative"

    def test_model_is_string(self, client, auth_headers_user1):
        """
        Test that model is a string.
        Issue 19: Verify response format follows DX Contract.
        """
        response = client.post(
            "/v1/public/proj_test_022/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Test model type"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["model"], str), \
            "model should be a string"
        assert len(data["model"]) > 0, \
            "model should not be empty"

    def test_response_structure_completeness(self, client, auth_headers_user1):
        """
        Test that response structure is complete and correct.
        Issue 19: Verify response format follows DX Contract.
        """
        response = client.post(
            "/v1/public/proj_test_023/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [
                    "Complete response test 1",
                    "Complete response test 2"
                ],
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_namespace",
                "metadata": {"test": "metadata", "batch": "complete_test"}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all fields are present and correct type
        assert isinstance(data["vectors_stored"], int)
        assert isinstance(data["model"], str)
        assert isinstance(data["dimensions"], int)
        assert isinstance(data["vector_ids"], list)

        # Verify values are consistent
        assert data["vectors_stored"] == 2
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert len(data["vector_ids"]) == 2


class TestEmbedStoreResponseEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_large_batch_of_texts(self, client, auth_headers_user1):
        """
        Test embedding a large batch of texts.
        Edge case: Large batch processing.
        """
        texts = [f"Agent memory entry {i}" for i in range(50)]

        response = client.post(
            "/v1/public/proj_test_024/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={"texts": texts}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["vectors_stored"] == 50
        assert len(data["vector_ids"]) == 50
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_texts_with_special_characters(self, client, auth_headers_user1):
        """
        Test embedding texts with special characters.
        Edge case: Special characters in text.
        """
        response = client.post(
            "/v1/public/proj_test_025/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [
                    "Text with émojis 🚀 and ñ characters",
                    "Text with quotes \"double\" and 'single'",
                    "Text with symbols @#$%^&*()"
                ]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["vectors_stored"] == 3
        assert len(data["vector_ids"]) == 3

    def test_long_text_embedding(self, client, auth_headers_user1):
        """
        Test embedding a very long text.
        Edge case: Long text input.
        """
        long_text = "This is a very long text. " * 100

        response = client.post(
            "/v1/public/proj_test_026/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": [long_text]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["vectors_stored"] == 1
        assert len(data["vector_ids"]) == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_minimal_request_with_defaults(self, client, auth_headers_user1):
        """
        Test minimal request using all defaults.
        Edge case: Minimal request parameters.
        """
        response = client.post(
            "/v1/public/proj_test_027/embeddings/embed-and-store",
            headers=auth_headers_user1,
            json={
                "texts": ["Minimal request test"]
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All defaults should be applied
        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert len(data["vector_ids"]) == 1


class TestEmbedStoreResponseAuthentication:
    """Tests for authentication requirements."""

    def test_requires_authentication(self, client):
        """
        Test that endpoint requires authentication.
        DX Contract: All public endpoints require X-API-Key.
        """
        response = client.post(
            "/v1/public/proj_test_028/embeddings/embed-and-store",
            json={
                "texts": ["Test without auth"]
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_api_key_rejected(self, client, invalid_auth_headers):
        """
        Test that invalid API key is rejected.
        DX Contract: Invalid API keys must be rejected.
        """
        response = client.post(
            "/v1/public/proj_test_029/embeddings/embed-and-store",
            headers=invalid_auth_headers,
            json={
                "texts": ["Test with invalid auth"]
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
