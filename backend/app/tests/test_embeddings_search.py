"""
Tests for POST /embeddings/search endpoint.

Implements testing for Epic 5 Story 1 (Issue #21): Search via /embeddings/search.

Test Coverage (Issue #21 Requirements):
1. Test POST /v1/public/{project_id}/embeddings/search endpoint
2. Test successful search returns results with: id, score, document, metadata
3. Test search with different models
4. Test empty results when no matches found
5. Test error handling for missing query
6. Test X-API-Key authentication requirement
7. Verify response includes: model, namespace, processing_time_ms

Additional Coverage:
- Namespace scoping (Issue #17)
- top_k limiting (Issue #22)
- Similarity threshold filtering
- Metadata filtering (Issue #24)
- Conditional field inclusion (Issue #26)
- Results ordered by similarity (highest first)

Per PRD §6 (Agent recall): Enables agent memory retrieval.
Per Epic 5 Story 1 (2 points): Developer can search via /embeddings/search.
Per DX Contract: All behaviors must be deterministic and documented.
"""
import pytest
from fastapi.testclient import TestClient


class TestEmbeddingSearch:
    """Tests for POST /v1/public/{project_id}/embeddings/search endpoint."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        """Clear vector store before and after each test."""
        from app.services.vector_store_service import vector_store_service
        vector_store_service.clear_all_vectors()
        yield
        vector_store_service.clear_all_vectors()

    def _embed_and_store(self, client, auth_headers, project_id, texts, namespace=None, metadata=None):
        """
        Helper to embed and store vectors using the NEW texts (array) format.

        IMPORTANT: The embed-and-store endpoint uses `texts` field (array), NOT `text` field.
        """
        request_data = {
            "texts": texts if isinstance(texts, list) else [texts],
            "namespace": namespace,
            "metadata": metadata or {}
        }
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to store vectors: {response.json()}"
        return response.json()

    # ========== Issue #21 Core Tests ==========

    def test_search_basic_success(self, client, auth_headers_user1):
        """
        Test basic search functionality with query text.

        Issue #21 Requirement 2: Test successful search returns results with id, score, document, metadata.
        Issue #21 Requirement 7: Verify response includes model, namespace, processing_time_ms.

        Epic 5 Story 1: Developer can search via /embeddings/search.
        Requirements:
        - Accept query text
        - Generate embedding for search
        - Return matching documents
        """
        project_id = "proj_test_search_001"

        # Store some vectors using NEW texts array format
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Autonomous fintech agent executing compliance check"]
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Payment processing completed successfully"]
        )

        # Search for similar vectors
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "compliance check agent"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #21 Requirement 7: Verify response structure
        assert "results" in data
        assert "namespace" in data
        assert "model" in data
        assert "processing_time_ms" in data

        # Verify results structure (Issue #21 Requirement 2)
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        assert data["namespace"] == "default"  # Default namespace
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["processing_time_ms"] >= 0

        # Issue #21 Requirement 2: Verify each result has id, score, document, metadata
        result = data["results"][0]
        assert "id" in result
        assert "score" in result
        assert "document" in result
        assert "metadata" in result

    def test_search_result_fields(self, client, auth_headers_user1):
        """
        Test that search results contain all required fields per Issue #21.

        Issue #21 Requirement 2: Results must have id, score, document, metadata.
        """
        project_id = "proj_test_search_002"

        # Store a vector with metadata
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Test content for structure validation"],
            metadata={"key": "value", "agent_id": "test_agent"}
        )

        # Search
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test content"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify each result has required fields per Issue #21
        assert len(data["results"]) > 0
        result = data["results"][0]

        # Issue #21: Required fields in SearchResult
        assert "id" in result, "Result must have 'id' field"
        assert "score" in result, "Result must have 'score' field"
        assert "document" in result, "Result must have 'document' field"
        assert "metadata" in result, "Result must have 'metadata' field"

        # Verify field types
        assert isinstance(result["id"], str)
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["document"], str)
        assert result["document"] == "Test content for structure validation"
        assert isinstance(result["metadata"], dict)
        assert result["metadata"]["key"] == "value"

    def test_search_with_different_models(self, client, auth_headers_user1):
        """
        Test search with different embedding models.

        Issue #21 Requirement 3: Test search with different models.
        """
        project_id = "proj_test_search_003"

        # Store with default model (384 dims)
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Default model content"],
            namespace="default_model"
        )

        # Search with default model
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "default model",
                "namespace": "default_model"
            },
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert len(data["results"]) > 0

        # Store with 768-dim model (use sentence-transformers/all-mpnet-base-v2 which is supported)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Large model content"],
                "model": "sentence-transformers/all-mpnet-base-v2",
                "namespace": "large_model"
            },
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with 768-dim model
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "large model",
                "model": "sentence-transformers/all-mpnet-base-v2",
                "namespace": "large_model"
            },
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"

    def test_search_empty_results(self, client, auth_headers_user1):
        """
        Test search with no matching vectors.

        Issue #21 Requirement 4: Test empty results when no matches found.
        """
        project_id = "proj_test_search_004"

        # Don't store any vectors

        # Search should return empty results (not an error)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "no matching vectors"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #21 Requirement 4: Empty results should be valid response
        assert data["results"] == []
        assert data["namespace"] == "default"
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["processing_time_ms"] >= 0

    def test_search_missing_query(self, client, auth_headers_user1):
        """
        Test error handling when query is missing.

        Issue #21 Requirement 5: Test error handling for missing query.
        """
        project_id = "proj_test_search_005"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={},  # No query provided
            headers=auth_headers_user1
        )

        # Issue #21 Requirement 5: Should return validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_search_empty_query(self, client, auth_headers_user1):
        """
        Test error handling for empty query string.

        Issue #21 Requirement 5: Test error handling for missing/invalid query.
        """
        project_id = "proj_test_search_006"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": ""},  # Empty query
            headers=auth_headers_user1
        )

        assert response.status_code == 422

    def test_search_whitespace_query(self, client, auth_headers_user1):
        """
        Test error handling for whitespace-only query.

        Issue #21 Requirement 5: Test error handling for invalid query.
        """
        project_id = "proj_test_search_007"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "   "},  # Whitespace-only
            headers=auth_headers_user1
        )

        assert response.status_code == 422

    def test_search_no_authentication(self, client):
        """
        Test that search requires authentication.

        Issue #21 Requirement 6: Test X-API-Key authentication requirement.
        """
        project_id = "proj_test_search_008"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test"}
            # No auth headers
        )

        # Issue #21 Requirement 6: Must return 401 Unauthorized
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_search_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test search with invalid API key.

        Issue #21 Requirement 6: Test X-API-Key authentication requirement.
        """
        project_id = "proj_test_search_009"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test"},
            headers=invalid_auth_headers
        )

        # Issue #21 Requirement 6: Must return 401 Unauthorized
        assert response.status_code == 401

    def test_search_response_processing_time(self, client, auth_headers_user1):
        """
        Test that processing_time_ms is included in response.

        Issue #21 Requirement 7: Verify response includes processing_time_ms.
        """
        project_id = "proj_test_search_010"

        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Performance test content"]
        )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "performance"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #21 Requirement 7: processing_time_ms is required
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)
        assert data["processing_time_ms"] >= 0

    # ========== Results Ordering Tests ==========

    def test_search_results_ordered_by_similarity(self, client, auth_headers_user1):
        """
        Test that search results are ordered by similarity (highest first).

        Epic 5 Story 1: Results in order of similarity (highest first).
        """
        project_id = "proj_test_search_011"

        # Store vectors with varying similarity to query
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent compliance check"]  # Very similar to query
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Payment processing system"]  # Less similar
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Compliance verification agent"]  # Similar to query
        )

        # Search
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent compliance check", "top_k": 10},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify results are ordered by score descending
        results = data["results"]
        assert len(results) >= 2

        for i in range(len(results) - 1):
            assert results[i]["score"] >= results[i + 1]["score"], \
                "Results must be ordered by score (highest first)"

        # Verify all results have score in valid range
        for result in results:
            assert "score" in result
            assert 0.0 <= result["score"] <= 1.0

    # ========== Namespace Scoping Tests (Issue #17) ==========

    def test_search_with_namespace_scoping(self, client, auth_headers_user1):
        """
        Test namespace scoping for search.

        Issue #17 (Epic 5 Story 3): Scope search by namespace.
        Requirements:
        - Only search vectors in specified namespace
        - Vectors from other namespaces are never returned
        """
        project_id = "proj_test_search_012"

        # Store vectors in different namespaces
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent memory in namespace 1"],
            namespace="agent_1"
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent memory in namespace 2"],
            namespace="agent_2"
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Default namespace memory"],
            namespace=None  # Default namespace
        )

        # Search in agent_1 namespace only
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent memory", "namespace": "agent_1"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify only agent_1 namespace results returned
        assert data["namespace"] == "agent_1"
        assert len(data["results"]) == 1
        assert "namespace 1" in data["results"][0]["document"]

        # Search in agent_2 namespace only
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent memory", "namespace": "agent_2"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert data["namespace"] == "agent_2"
        assert len(data["results"]) == 1
        assert "namespace 2" in data["results"][0]["document"]

        # Search in default namespace
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "memory"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert data["namespace"] == "default"
        assert len(data["results"]) == 1

    def test_search_empty_namespace_returns_empty(self, client, auth_headers_user1):
        """Test search in namespace with no vectors returns empty results (not error)."""
        project_id = "proj_test_search_013"

        # Store vector in default namespace
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Default namespace content"]
        )

        # Search in different namespace (should return empty, not error)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "content", "namespace": "empty_namespace"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert data["results"] == []
        assert data["namespace"] == "empty_namespace"

    # ========== top_k Limiting Tests (Issue #22) ==========

    def test_search_with_top_k_limit(self, client, auth_headers_user1):
        """
        Test top_k parameter to limit number of results.

        Issue #22: Limit results with top_k parameter.
        """
        project_id = "proj_test_search_014"

        # Store multiple vectors
        texts = [f"Agent workflow step {i}" for i in range(10)]
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            texts
        )

        # Search with top_k=3
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent workflow", "top_k": 3},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify only 3 results returned
        assert len(data["results"]) == 3

        # Search with top_k=5
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent workflow", "top_k": 5},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 5

    def test_search_top_k_default(self, client, auth_headers_user1):
        """Test that top_k defaults to 10."""
        project_id = "proj_test_search_015"

        # Store 15 vectors
        texts = [f"Content {i}" for i in range(15)]
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            texts
        )

        # Search without top_k (should default to 10)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "content"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Default top_k is 10
        assert len(data["results"]) == 10

    def test_search_invalid_top_k(self, client, auth_headers_user1):
        """Test validation of top_k parameter."""
        project_id = "proj_test_search_016"

        # top_k too low (< 1)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 0},
            headers=auth_headers_user1
        )
        assert response.status_code == 422

        # top_k too high (> 100)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 101},
            headers=auth_headers_user1
        )
        assert response.status_code == 422

    # ========== Similarity Threshold Tests ==========

    def test_search_with_similarity_threshold(self, client, auth_headers_user1):
        """
        Test similarity_threshold parameter to filter low-quality matches.

        Epic 5 Story 5: Use similarity_threshold to filter matches.
        """
        project_id = "proj_test_search_017"

        # Store vectors
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent compliance workflow"]
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Completely unrelated content xyz"]
        )

        # Search with high threshold (only high-quality matches)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "agent compliance",
                "similarity_threshold": 0.8,
                "top_k": 10
            },
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # All results should have score >= 0.8
        for result in data["results"]:
            assert result["score"] >= 0.8

    def test_search_invalid_similarity_threshold(self, client, auth_headers_user1):
        """Test validation of similarity_threshold parameter."""
        project_id = "proj_test_search_018"

        # Threshold too low (< 0.0)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "similarity_threshold": -0.1},
            headers=auth_headers_user1
        )
        assert response.status_code == 422

        # Threshold too high (> 1.0)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "similarity_threshold": 1.1},
            headers=auth_headers_user1
        )
        assert response.status_code == 422

    # ========== Metadata Filtering Tests (Issue #24) ==========

    def test_search_with_metadata_filter(self, client, auth_headers_user1):
        """
        Test metadata_filter parameter to filter by metadata.

        Issue #24: Filter results by metadata fields.
        """
        project_id = "proj_test_search_019"

        # Store vectors with different metadata
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent action A"],
            metadata={"agent_id": "agent_001", "task": "compliance"}
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent action B"],
            metadata={"agent_id": "agent_002", "task": "payment"}
        )
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent action C"],
            metadata={"agent_id": "agent_001", "task": "payment"}
        )

        # Search with agent_id filter
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "agent action",
                "metadata_filter": {"agent_id": "agent_001"}
            },
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return agent_001 results
        assert len(data["results"]) == 2
        for result in data["results"]:
            assert result["metadata"]["agent_id"] == "agent_001"

    # ========== Conditional Field Inclusion Tests (Issue #26) ==========

    def test_search_include_metadata_default(self, client, auth_headers_user1):
        """Test that metadata is included by default (include_metadata defaults to true)."""
        project_id = "proj_test_search_020"

        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Test metadata inclusion"],
            metadata={"key": "value"}
        )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test metadata"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        assert "metadata" in data["results"][0]
        assert data["results"][0]["metadata"] == {"key": "value"}

    def test_search_exclude_metadata(self, client, auth_headers_user1):
        """Test include_metadata=false excludes metadata from results."""
        project_id = "proj_test_search_021"

        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Test metadata exclusion"],
            metadata={"key": "value"}
        )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test metadata", "include_metadata": False},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        # When include_metadata=false, metadata should be None or omitted
        assert data["results"][0].get("metadata") is None

    def test_search_include_embeddings_false_default(self, client, auth_headers_user1):
        """Test that embeddings are NOT included by default (include_embeddings defaults to false)."""
        project_id = "proj_test_search_022"

        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Test embedding exclusion"]
        )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test embedding"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        # Default: embeddings should be None or omitted
        assert data["results"][0].get("embedding") is None

    def test_search_include_embeddings_true(self, client, auth_headers_user1):
        """Test include_embeddings=true includes embeddings in results."""
        project_id = "proj_test_search_023"

        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Test embedding inclusion"]
        )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test embedding", "include_embeddings": True},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        assert "embedding" in data["results"][0]
        assert isinstance(data["results"][0]["embedding"], list)
        assert len(data["results"][0]["embedding"]) == 384

    # ========== Determinism Tests ==========

    def test_search_deterministic(self, client, auth_headers_user1):
        """
        Test that same search query produces same results (determinism).

        Per PRD §10: Deterministic defaults for demo reproducibility.
        """
        project_id = "proj_test_search_024"

        # Store vectors
        self._embed_and_store(
            client, auth_headers_user1, project_id,
            ["Agent decision making process"]
        )

        # Search twice with same query
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent decision"},
            headers=auth_headers_user1
        )
        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent decision"},
            headers=auth_headers_user1
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical
        assert len(data1["results"]) == len(data2["results"])

        # Compare each result
        for r1, r2 in zip(data1["results"], data2["results"]):
            assert r1["id"] == r2["id"]
            assert r1["score"] == r2["score"]
            assert r1["document"] == r2["document"]


class TestSearchEdgeCases:
    """Test edge cases and boundary conditions for search."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        """Clear vector store before and after each test."""
        from app.services.vector_store_service import vector_store_service
        vector_store_service.clear_all_vectors()
        yield
        vector_store_service.clear_all_vectors()

    def test_search_with_very_long_query(self, client, auth_headers_user1):
        """Test search with very long query text."""
        project_id = "proj_test_edge_001"

        # Store a vector
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"texts": ["Short content"]},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with long query
        long_query = " ".join(["agent workflow"] * 100)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": long_query},
            headers=auth_headers_user1
        )

        assert response.status_code == 200

    def test_search_with_special_characters(self, client, auth_headers_user1):
        """Test search with special characters in query."""
        project_id = "proj_test_edge_002"

        # Store vectors
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"texts": ["Transaction: $10,000 @agent #compliance"]},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with special characters
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "$10,000 transaction #compliance"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

    def test_search_with_unicode(self, client, auth_headers_user1):
        """Test search with Unicode characters."""
        project_id = "proj_test_edge_003"

        # Store vector with unicode
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"texts": ["Agent workflow with émojis"]},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with unicode
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "workflow émojis"},
            headers=auth_headers_user1
        )

        assert response.status_code == 200

    def test_search_top_k_boundary_values(self, client, auth_headers_user1):
        """Test top_k with boundary values."""
        project_id = "proj_test_edge_004"

        # Store vector
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"texts": ["Test content"]},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Test top_k = 1 (minimum valid)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 1},
            headers=auth_headers_user1
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) <= 1

        # Test top_k = 100 (maximum valid)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 100},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

    def test_search_similarity_threshold_boundary_values(self, client, auth_headers_user1):
        """Test similarity_threshold with boundary values."""
        project_id = "proj_test_edge_005"

        # Store vector
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"texts": ["Test content"]},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Test threshold = 0.0 (minimum valid)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "similarity_threshold": 0.0},
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Test threshold = 1.0 (maximum valid)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "similarity_threshold": 1.0},
            headers=auth_headers_user1
        )
        assert response.status_code == 200
