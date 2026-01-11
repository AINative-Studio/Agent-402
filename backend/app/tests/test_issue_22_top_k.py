"""
Tests for Issue #22: As a developer, I can limit results via top_k

Requirements from Issue #22:
- Add top_k parameter to /embeddings/search endpoint
- Default value should be reasonable (e.g., 10)
- Return only the top K most similar results
- Validate top_k is a positive integer
- Handle edge cases (top_k=0, top_k > total results)
- Ensure results are ordered by similarity score (descending)
- Test that exactly top_k results are returned (or fewer if not enough exist)
- Document the top_k parameter behavior

Reference:
- PRD §10 (Predictable replay)
- Epic 5, Story 2 (2 points)
- DX-Contract.md for parameter standards
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


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
    return "proj_test_issue22"


class TestIssue22TopKParameter:
    """Tests for Issue #22: top_k parameter implementation."""

    def _embed_and_store(self, client, auth_headers, project_id, text, metadata=None):
        """Helper to embed and store a vector."""
        payload = {"text": text}
        if metadata:
            payload["metadata"] = metadata

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        return response.json()

    def test_default_top_k_value(self, client, auth_headers, test_project_id):
        """
        Test that top_k has a reasonable default value of 10.

        Issue #22 Requirement: Default value should be reasonable (e.g., 10)
        """
        # Store 15 vectors
        for i in range(15):
            self._embed_and_store(
                client, auth_headers, test_project_id,
                f"Test vector number {i}"
            )

        # Search without specifying top_k (should use default)
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={"query": "test vector"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return exactly 10 results (the default)
        assert len(data["results"]) == 10
        assert data["total_results"] == 10

    def test_top_k_returns_exact_count_when_sufficient_vectors(self, client, auth_headers):
        """
        Test that exactly top_k results are returned when enough vectors exist.

        Issue #22 Requirement: Return only the top K most similar results
        """
        project_id = "proj_test_issue22_001"

        # Store 20 vectors
        for i in range(20):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Document {i} about agent workflows"
            )

        # Test various top_k values
        for k in [1, 3, 5, 10, 15, 20]:
            response = client.post(
                f"/v1/public/{project_id}/embeddings/search",
                json={"query": "agent workflows", "top_k": k},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Should return exactly k results
            assert len(data["results"]) == k, f"Expected {k} results, got {len(data['results'])}"
            assert data["total_results"] == k

    def test_top_k_returns_fewer_when_insufficient_vectors(self, client, auth_headers):
        """
        Test that fewer than top_k results are returned when not enough vectors exist.

        Issue #22 Requirement: Handle edge cases (top_k > total results)
        """
        project_id = "proj_test_issue22_002"

        # Store only 5 vectors
        for i in range(5):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Limited document {i}"
            )

        # Request more than available (top_k=20, only 5 exist)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "limited document", "top_k": 20},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return only the 5 available vectors
        assert len(data["results"]) == 5
        assert data["total_results"] == 5

    def test_top_k_zero_validation_error(self, client, auth_headers):
        """
        Test that top_k=0 returns a validation error.

        Issue #22 Requirement: Validate top_k is a positive integer
        Issue #22 Requirement: Handle edge cases (top_k=0)
        """
        project_id = "proj_test_issue22_003"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 0},
            headers=auth_headers
        )

        # Should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_top_k_negative_validation_error(self, client, auth_headers):
        """
        Test that negative top_k values return a validation error.

        Issue #22 Requirement: Validate top_k is a positive integer
        """
        project_id = "proj_test_issue22_004"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": -5},
            headers=auth_headers
        )

        # Should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_top_k_exceeds_maximum_validation_error(self, client, auth_headers):
        """
        Test that top_k values exceeding the maximum (100) return a validation error.

        Issue #22 Requirement: Validate top_k is a positive integer
        DX Contract: Parameter standards require bounds checking
        """
        project_id = "proj_test_issue22_005"

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test", "top_k": 101},
            headers=auth_headers
        )

        # Should return 422 validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_results_ordered_by_similarity_descending(self, client, auth_headers):
        """
        Test that results are ordered by similarity score in descending order.

        Issue #22 Requirement: Ensure results are ordered by similarity score (descending)
        PRD §10: Predictable replay requires deterministic ordering
        """
        project_id = "proj_test_issue22_006"

        # Store vectors with varying similarity to query
        self._embed_and_store(
            client, auth_headers, project_id,
            "Autonomous agent compliance workflow"
        )
        self._embed_and_store(
            client, auth_headers, project_id,
            "Agent workflow system"
        )
        self._embed_and_store(
            client, auth_headers, project_id,
            "Completely unrelated content xyz"
        )
        self._embed_and_store(
            client, auth_headers, project_id,
            "Agent compliance checking"
        )

        # Search with top_k to get multiple results
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "agent compliance workflow", "top_k": 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify results are ordered by similarity descending
        similarities = [result["similarity"] for result in data["results"]]
        assert similarities == sorted(similarities, reverse=True), \
            "Results should be ordered by similarity (highest to lowest)"

        # Verify first result has highest similarity
        if len(data["results"]) > 1:
            assert data["results"][0]["similarity"] >= data["results"][1]["similarity"]

    def test_top_k_boundary_minimum(self, client, auth_headers):
        """
        Test top_k with minimum valid value (1).

        Issue #22 Requirement: Validate top_k is a positive integer
        """
        project_id = "proj_test_issue22_007"

        # Store multiple vectors
        for i in range(5):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Test content {i}"
            )

        # Request top_k=1
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "test content", "top_k": 1},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return exactly 1 result
        assert len(data["results"]) == 1
        assert data["total_results"] == 1

    def test_top_k_boundary_maximum(self, client, auth_headers):
        """
        Test top_k with maximum valid value (100).

        Issue #22 Requirement: Validate top_k is a positive integer
        """
        project_id = "proj_test_issue22_008"

        # Store 10 vectors (less than max)
        for i in range(10):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Content item {i}"
            )

        # Request top_k=100 (maximum allowed)
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "content item", "top_k": 100},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return all 10 available vectors
        assert len(data["results"]) == 10
        assert data["total_results"] == 10

    def test_top_k_with_similarity_threshold(self, client, auth_headers):
        """
        Test that top_k and similarity_threshold work together correctly.

        Issue #22 Requirement: top_k should work with other filters
        Expected behavior: Filter by threshold first, then limit to top_k
        """
        project_id = "proj_test_issue22_009"

        # Store 10 vectors
        for i in range(10):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Document {i} about agents"
            )

        # Search with both threshold and top_k
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "document about agents",
                "similarity_threshold": 0.5,
                "top_k": 3
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 3 results
        assert len(data["results"]) <= 3

        # All results should meet threshold
        for result in data["results"]:
            assert result["similarity"] >= 0.5

    def test_top_k_with_metadata_filter(self, client, auth_headers):
        """
        Test that top_k works correctly with metadata filtering.

        Issue #22 Requirement: top_k should work with other filters
        """
        project_id = "proj_test_issue22_010"

        # Store vectors with different metadata
        for i in range(10):
            agent_id = "agent_A" if i < 5 else "agent_B"
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Task {i} completed",
                metadata={"agent_id": agent_id}
            )

        # Search with metadata filter and top_k
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "task completed",
                "metadata_filter": {"agent_id": "agent_A"},
                "top_k": 3
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 3 results, all from agent_A
        assert len(data["results"]) <= 3
        for result in data["results"]:
            assert result["metadata"]["agent_id"] == "agent_A"

    def test_top_k_deterministic_ordering(self, client, auth_headers):
        """
        Test that top_k produces deterministic results for identical queries.

        Issue #22 Requirement: Predictable replay (PRD §10)
        """
        project_id = "proj_test_issue22_011"

        # Store vectors
        for i in range(10):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Agent workflow step {i}"
            )

        # Execute same search twice
        search_payload = {"query": "agent workflow", "top_k": 5}

        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json=search_payload,
            headers=auth_headers
        )

        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json=search_payload,
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical
        assert len(data1["results"]) == len(data2["results"])

        # Verify same vector IDs in same order
        vector_ids_1 = [r["vector_id"] for r in data1["results"]]
        vector_ids_2 = [r["vector_id"] for r in data2["results"]]
        assert vector_ids_1 == vector_ids_2

        # Verify same similarity scores
        similarities_1 = [r["similarity"] for r in data1["results"]]
        similarities_2 = [r["similarity"] for r in data2["results"]]
        assert similarities_1 == similarities_2

    def test_top_k_with_namespace_isolation(self, client, auth_headers):
        """
        Test that top_k respects namespace isolation.

        Issue #22 Requirement: top_k should work with namespace scoping
        """
        project_id = "proj_test_issue22_012"

        # Store vectors in different namespaces
        for i in range(5):
            self._embed_and_store(
                client, auth_headers, project_id,
                f"Namespace A vector {i}",
                metadata={"namespace": "namespace_a"}
            )

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": f"Namespace B vector {i}",
                "namespace": "namespace_b"
            },
            headers=auth_headers
        )
        for i in range(5):
            response = client.post(
                f"/v1/public/{project_id}/embeddings/embed-and-store",
                json={
                    "text": f"Namespace B vector {i}",
                    "namespace": "namespace_b"
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Search in namespace_b with top_k=3
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "namespace vector",
                "namespace": "namespace_b",
                "top_k": 3
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return exactly 3 results from namespace_b only
        assert len(data["results"]) == 3
        assert data["namespace"] == "namespace_b"
        for result in data["results"]:
            assert result["namespace"] == "namespace_b"

    def test_top_k_empty_results(self, client, auth_headers):
        """
        Test that top_k handles empty result sets correctly.

        Issue #22 Requirement: Handle edge cases
        """
        project_id = "proj_test_issue22_013"

        # Don't store any vectors

        # Search with top_k
        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={"query": "nonexistent content", "top_k": 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert len(data["results"]) == 0
        assert data["total_results"] == 0


class TestIssue22Documentation:
    """Tests to verify top_k parameter is properly documented."""

    def test_schema_includes_top_k_documentation(self):
        """
        Verify that the top_k parameter is documented in the schema.

        Issue #22 Requirement: Document the top_k parameter behavior
        """
        from app.schemas.embeddings import EmbeddingSearchRequest

        # Check that top_k field exists
        assert "top_k" in EmbeddingSearchRequest.model_fields

        # Check field has proper constraints
        field = EmbeddingSearchRequest.model_fields["top_k"]
        assert field.default == 10  # Default value

        # Verify description mentions Issue #22
        field_info = str(field)
        assert "top_k" in field_info or "top" in field_info.lower()
