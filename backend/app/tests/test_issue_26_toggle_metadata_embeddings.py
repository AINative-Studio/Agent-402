"""
Tests for Issue #26: Toggle metadata and embeddings in search results.

Requirements:
- Add include_metadata parameter (boolean, default true)
- Add include_embeddings parameter (boolean, default false)
- When include_metadata=false, exclude metadata from results (reduce response size)
- When include_embeddings=true, include full embedding vectors in results
- Default behavior should optimize for common use case (metadata yes, embeddings no)
- Test all combinations: both true, both false, mixed

Reference:
- PRD §9 (Demo visibility)
- Epic 5, Story 6 (1 point)
- DX-Contract.md for response format standards
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


client = TestClient(app)

# Valid API key for testing
VALID_API_KEY = settings.demo_api_key_1

# Project ID for testing
PROJECT_ID = "test_project_001"


@pytest.fixture(autouse=True)
def clear_vector_store():
    """Clear vector store before and after each test."""
    from app.services.vector_store_service import vector_store_service
    vector_store_service.clear_all_vectors()
    yield
    vector_store_service.clear_all_vectors()


async def store_vector_directly(project_id, text, model="BAAI/bge-small-en-v1.5", namespace="default", metadata=None):
    """
    Helper function to store a vector directly in vector_store_service.

    This bypasses the embed-and-store API endpoint and stores directly,
    ensuring vectors are available for search tests.
    """
    import asyncio
    from app.services.embedding_service import embedding_service

    # Generate embedding (async)
    embedding, model_used, dimensions, _ = await embedding_service.generate_embedding(
        text=text,
        model=model
    )

    # Store directly in vector_store_service (async)
    result = await embedding_service.embed_and_store(
        text=text,
        model=model,
        namespace=namespace,
        metadata=metadata,
        project_id=project_id,
        user_id="test_user"
    )

    return result


class TestIncludeMetadataParameter:
    """Tests for include_metadata parameter (Issue #26)."""

    async def test_search_with_metadata_included_by_default(self):
        """
        Test that metadata is included by default (include_metadata defaults to true).

        Epic 5 Story 6: Default behavior should include metadata.
        """
        # First, store a vector with metadata
        vector_text = "Test document for metadata inclusion test"
        metadata = {
            "agent_id": "test_agent",
            "task": "test_task",
            "priority": "high"
        }

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_metadata_default",
            metadata=metadata
        )

        # Search without specifying include_metadata (should default to true)
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_metadata_default",
                "top_k": 5
                # include_metadata not specified - should default to true
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify metadata is included
        assert len(data["results"]) > 0
        result = data["results"][0]
        assert "metadata" in result
        assert result["metadata"] is not None
        assert result["metadata"]["agent_id"] == "test_agent"
        assert result["metadata"]["task"] == "test_task"
        assert result["metadata"]["priority"] == "high"

    async def test_search_with_metadata_explicitly_true(self):
        """
        Test that metadata is included when include_metadata=true.

        Epic 5 Story 6: Explicit true value should include metadata.
        """
        # Store a vector with metadata
        vector_text = "Test document for explicit metadata inclusion"
        metadata = {
            "source": "test",
            "category": "example"
        }

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_metadata_true",
            metadata=metadata
        )



        # Search with include_metadata=true
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_metadata_true",
                "top_k": 5,
                "include_metadata": True
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify metadata is included
        assert len(data["results"]) > 0
        result = data["results"][0]
        assert "metadata" in result
        assert result["metadata"] is not None
        assert result["metadata"]["source"] == "test"
        assert result["metadata"]["category"] == "example"

    async def test_search_with_metadata_false_excludes_metadata(self):
        """
        Test that metadata is excluded when include_metadata=false.

        Epic 5 Story 6: include_metadata=false should exclude metadata to reduce response size.
        """
        # Store a vector with metadata
        vector_text = "Test document for metadata exclusion"
        metadata = {
            "large_field": "x" * 1000,  # Large metadata to test size reduction
            "another_field": "value"
        }

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_metadata_false",
            metadata=metadata
        )



        # Search with include_metadata=false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_metadata_false",
                "top_k": 5,
                "include_metadata": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify metadata is excluded (None or not present)
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Metadata should be None when excluded
        assert result.get("metadata") is None


class TestIncludeEmbeddingsParameter:
    """Tests for include_embeddings parameter (Issue #26)."""

    async def test_search_excludes_embeddings_by_default(self):
        """
        Test that embeddings are excluded by default (include_embeddings defaults to false).

        Epic 5 Story 6: Default behavior should exclude embeddings to optimize response size.
        """
        # Store a vector
        vector_text = "Test document for embedding exclusion default"

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_embedding_default"
        )



        # Search without specifying include_embeddings (should default to false)
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_embedding_default",
                "top_k": 5
                # include_embeddings not specified - should default to false
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify embeddings are excluded
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Embedding should be None when excluded
        assert result.get("embedding") is None

    async def test_search_with_embeddings_explicitly_false(self):
        """
        Test that embeddings are excluded when include_embeddings=false.

        Epic 5 Story 6: Explicit false value should exclude embeddings.
        """
        # Store a vector
        vector_text = "Test document for explicit embedding exclusion"

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_embedding_false"
        )



        # Search with include_embeddings=false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_embedding_false",
                "top_k": 5,
                "include_embeddings": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify embeddings are excluded
        assert len(data["results"]) > 0
        result = data["results"][0]
        assert result.get("embedding") is None

    async def test_search_with_embeddings_true_includes_embeddings(self):
        """
        Test that embeddings are included when include_embeddings=true.

        Epic 5 Story 6: include_embeddings=true should include full embedding vectors.
        PRD §9: Support including embeddings for debugging/advanced use cases.
        """
        # Store a vector
        vector_text = "Test document for embedding inclusion"

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_embedding_true"
        )



        # Search with include_embeddings=true
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_embedding_true",
                "top_k": 5,
                "include_embeddings": True
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify embeddings are included
        assert len(data["results"]) > 0
        result = data["results"][0]
        assert "embedding" in result
        assert result["embedding"] is not None
        assert isinstance(result["embedding"], list)

        # Verify embedding has correct dimensions (384 for bge-small)
        assert len(result["embedding"]) == 384

        # Verify embedding contains float values
        assert all(isinstance(x, (int, float)) for x in result["embedding"])


class TestParameterCombinations:
    """Tests for all combinations of include_metadata and include_embeddings (Issue #26)."""

    async def test_both_parameters_true(self):
        """
        Test include_metadata=true and include_embeddings=true.

        Both metadata and embeddings should be included.
        WARNING: This produces the largest response size.
        """
        # Store a vector with metadata
        vector_text = "Test document for both parameters true"
        metadata = {"test": "data"}

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_both_true",
            metadata=metadata
        )



        # Search with both parameters true
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_both_true",
                "top_k": 5,
                "include_metadata": True,
                "include_embeddings": True
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify both metadata and embeddings are included
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Metadata should be present
        assert result.get("metadata") is not None
        assert result["metadata"]["test"] == "data"

        # Embedding should be present
        assert result.get("embedding") is not None
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) == 384

    async def test_both_parameters_false(self):
        """
        Test include_metadata=false and include_embeddings=false.

        Neither metadata nor embeddings should be included.
        This produces the smallest response size.
        """
        # Store a vector with metadata
        vector_text = "Test document for both parameters false"
        metadata = {"test": "data"}

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_both_false",
            metadata=metadata
        )



        # Search with both parameters false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_both_false",
                "top_k": 5,
                "include_metadata": False,
                "include_embeddings": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify neither metadata nor embeddings are included
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Metadata should be None
        assert result.get("metadata") is None

        # Embedding should be None
        assert result.get("embedding") is None

        # Core fields should still be present
        assert "id" in result
        assert "document" in result
        assert "score" in result

    async def test_metadata_true_embeddings_false(self):
        """
        Test include_metadata=true and include_embeddings=false.

        This is the default behavior - optimal for most use cases.
        Includes metadata for filtering/context, excludes large embeddings.
        """
        # Store a vector with metadata
        vector_text = "Test document for metadata true embeddings false"
        metadata = {"agent": "test"}

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_meta_true_embed_false",
            metadata=metadata
        )



        # Search with metadata=true, embeddings=false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_meta_true_embed_false",
                "top_k": 5,
                "include_metadata": True,
                "include_embeddings": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify metadata is included, embeddings are excluded
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Metadata should be present
        assert result.get("metadata") is not None
        assert result["metadata"]["agent"] == "test"

        # Embedding should be None
        assert result.get("embedding") is None

    async def test_metadata_false_embeddings_true(self):
        """
        Test include_metadata=false and include_embeddings=true.

        Includes embeddings for advanced processing, excludes metadata.
        Useful for cases where embeddings are needed but metadata is not.
        """
        # Store a vector with metadata
        vector_text = "Test document for metadata false embeddings true"
        metadata = {"agent": "test"}

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_meta_false_embed_true",
            metadata=metadata
        )



        # Search with metadata=false, embeddings=true
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_meta_false_embed_true",
                "top_k": 5,
                "include_metadata": False,
                "include_embeddings": True
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Verify embeddings are included, metadata is excluded
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Metadata should be None
        assert result.get("metadata") is None

        # Embedding should be present
        assert result.get("embedding") is not None
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) == 384


class TestResponseSizeOptimization:
    """Tests to verify response size optimization (Issue #26)."""

    async def test_response_size_comparison(self):
        """
        Test that excluding embeddings significantly reduces response size.

        Epic 5 Story 6: Document performance/size tradeoff.
        Embeddings are large (384+ floats), so excluding them should greatly reduce size.
        """
        # Store a vector
        vector_text = "Test document for response size comparison"

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_response_size"
        )



        # Search without embeddings
        response_without = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_response_size",
                "top_k": 5,
                "include_embeddings": False
            }
        )

        # Search with embeddings
        response_with = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_response_size",
                "top_k": 5,
                "include_embeddings": True
            }
        )

        assert response_without.status_code == status.HTTP_200_OK
        assert response_with.status_code == status.HTTP_200_OK

        # Compare response sizes
        size_without = len(response_without.content)
        size_with = len(response_with.content)

        # Response with embeddings should be significantly larger
        # For 384-dim vector, embeddings add ~3KB per result (384 floats * ~8 bytes)
        assert size_with > size_without

        # Verify at least 50% size increase when including embeddings
        # (conservative estimate, actual increase is usually much higher)
        assert size_with >= size_without * 1.5


class TestOtherFunctionalityNotBroken:
    """Tests to ensure toggling doesn't break other functionality (Issue #26)."""

    async def test_metadata_filtering_still_works(self):
        """
        Ensure metadata_filter parameter still works with include_metadata toggle.

        Even when include_metadata=false, metadata_filter should still work
        (filtering happens server-side, inclusion happens in response).
        """
        # Store multiple vectors with different metadata
        vectors = [
            {"text": "Vector 1", "metadata": {"type": "A", "priority": 1}},
            {"text": "Vector 2", "metadata": {"type": "B", "priority": 2}},
            {"text": "Vector 3", "metadata": {"type": "A", "priority": 3}}
        ]

        for vec in vectors:
            await store_vector_directly(
                PROJECT_ID,
                vec["text"],
                namespace="test_metadata_filter",
                metadata=vec["metadata"]
            )

        # Search with metadata_filter and include_metadata=false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": "Vector",
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_metadata_filter",
                "top_k": 10,
                "metadata_filter": {"type": "A"},
                "include_metadata": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Should only get vectors with type=A (filtering still works)
        # Even though metadata is not included in response
        assert len(data["results"]) == 2

    async def test_similarity_threshold_still_works(self):
        """
        Ensure similarity_threshold parameter still works with toggles.
        """
        # Store a vector
        vector_text = "Specific test document for similarity"

        await store_vector_directly(
            PROJECT_ID,
            vector_text,
            namespace="test_similarity_threshold"
        )

        # Search with high similarity threshold and both toggles false
        search_response = client.post(
            f"/v1/public/{PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "query": vector_text,
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": "test_similarity_threshold",
                "top_k": 10,
                "similarity_threshold": 0.9,
                "include_metadata": False,
                "include_embeddings": False
            }
        )

        assert search_response.status_code == status.HTTP_200_OK
        data = search_response.json()

        # Should get results (exact match has high similarity)
        assert len(data["results"]) > 0

        # All results should have high similarity
        for result in data["results"]:
            assert result["score"] >= 0.9
