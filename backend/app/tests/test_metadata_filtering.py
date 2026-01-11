"""
Tests for metadata filtering functionality (Issue #24).

Implements comprehensive test coverage for:
- Common filter operations (equals, contains, in list)
- Advanced filter operations (gt, gte, lt, lte, exists, not_equals)
- Filter validation
- No-match cases
- Edge cases
- Integration with similarity search

Per PRD §6 (Compliance & audit):
- Ensures precise filtering for compliance queries
- Tests audit trail filtering capabilities
- Verifies deterministic filtering behavior
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.vector_store_service import vector_store_service
from app.services.metadata_filter import MetadataFilter, MetadataFilterOperator


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vectors before and after each test."""
    vector_store_service.clear_all_vectors()
    yield
    vector_store_service.clear_all_vectors()


@pytest.fixture
def valid_api_key():
    """Get a valid API key from settings."""
    from app.core.config import settings
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
    return "proj_test_metadata_filter"


@pytest.fixture
def setup_test_vectors(client, auth_headers, test_project_id):
    """
    Setup test vectors with various metadata for filtering tests.

    Creates vectors with different metadata patterns:
    - Agent IDs (agent_1, agent_2, agent_3)
    - Sources (memory, decision, compliance)
    - Scores (0.5, 0.7, 0.9)
    - Tags (lists)
    - Status (active, pending, completed)
    """
    test_vectors = [
        {
            "text": "Agent 1 memory about fintech compliance",
            "metadata": {
                "agent_id": "agent_1",
                "source": "memory",
                "score": 0.9,
                "tags": ["fintech", "compliance"],
                "status": "active"
            }
        },
        {
            "text": "Agent 1 decision on transaction",
            "metadata": {
                "agent_id": "agent_1",
                "source": "decision",
                "score": 0.7,
                "tags": ["fintech", "transaction"],
                "status": "completed"
            }
        },
        {
            "text": "Agent 2 compliance check result",
            "metadata": {
                "agent_id": "agent_2",
                "source": "compliance",
                "score": 0.8,
                "tags": ["compliance", "audit"],
                "status": "active"
            }
        },
        {
            "text": "Agent 2 memory about risk assessment",
            "metadata": {
                "agent_id": "agent_2",
                "source": "memory",
                "score": 0.5,
                "tags": ["risk", "assessment"],
                "status": "pending"
            }
        },
        {
            "text": "Agent 3 fintech analysis",
            "metadata": {
                "agent_id": "agent_3",
                "source": "decision",
                "score": 0.95,
                "tags": ["fintech", "analysis"],
                "status": "completed"
            }
        }
    ]

    for vec_data in test_vectors:
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json=vec_data,
            headers=auth_headers
        )
        assert response.status_code == 200

    return test_vectors


class TestMetadataFilterValidation:
    """Tests for metadata filter validation (Issue #24)."""

    def test_validate_empty_filter(self):
        """Test validation of empty filter (should be valid - no filtering)."""
        MetadataFilter.validate_filter({})  # Should not raise

    def test_validate_none_filter(self):
        """Test validation of None filter (should be valid - no filtering)."""
        MetadataFilter.validate_filter(None)  # Should not raise

    def test_validate_simple_filter(self):
        """Test validation of simple equality filter."""
        MetadataFilter.validate_filter({"agent_id": "agent_1"})  # Should not raise

    def test_validate_operator_filter(self):
        """Test validation of operator-based filter."""
        MetadataFilter.validate_filter({"score": {"$gte": 0.8}})  # Should not raise

    def test_validate_invalid_filter_type(self):
        """Test validation fails for non-dict filter."""
        with pytest.raises(ValueError, match="metadata_filter must be a dictionary"):
            MetadataFilter.validate_filter("invalid")

    def test_validate_invalid_operator(self):
        """Test validation fails for unsupported operator."""
        with pytest.raises(ValueError, match="Unsupported operator"):
            MetadataFilter.validate_filter({"field": {"$invalid": "value"}})

    def test_validate_operator_without_dollar_sign(self):
        """Test validation fails for operator without $ prefix."""
        with pytest.raises(ValueError, match="Operator must start with '\\$'"):
            MetadataFilter.validate_filter({"field": {"eq": "value"}})

    def test_validate_in_operator_requires_list(self):
        """Test $in operator validation requires list value."""
        with pytest.raises(ValueError, match="requires a list value"):
            MetadataFilter.validate_filter({"tags": {"$in": "not_a_list"}})

    def test_validate_numeric_operator_requires_number(self):
        """Test numeric operators require numeric values."""
        with pytest.raises(ValueError, match="requires a numeric value"):
            MetadataFilter.validate_filter({"score": {"$gte": "not_a_number"}})

    def test_validate_exists_operator_requires_boolean(self):
        """Test $exists operator requires boolean value."""
        with pytest.raises(ValueError, match="requires a boolean value"):
            MetadataFilter.validate_filter({"field": {"$exists": "not_boolean"}})

    def test_validate_contains_operator_requires_string(self):
        """Test $contains operator requires string value."""
        with pytest.raises(ValueError, match="requires a string value"):
            MetadataFilter.validate_filter({"text": {"$contains": 123}})


class TestSimpleEqualityFiltering:
    """Tests for simple equality filtering (Issue #24)."""

    def test_filter_by_agent_id(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering by agent_id using simple equality."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {"agent_id": "agent_1"}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

        # Should only return agent_1 vectors
        for result in data["results"]:
            assert result["metadata"]["agent_id"] == "agent_1"

        # Should have 2 agent_1 vectors
        assert len(data["results"]) <= 2

    def test_filter_by_source(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering by source field."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "memory",
                "top_k": 10,
                "metadata_filter": {"source": "memory"}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return memory source vectors
        for result in data["results"]:
            assert result["metadata"]["source"] == "memory"

    def test_filter_by_multiple_fields(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering by multiple fields (AND logic)."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {
                    "agent_id": "agent_1",
                    "source": "memory"
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return vectors matching BOTH conditions
        for result in data["results"]:
            assert result["metadata"]["agent_id"] == "agent_1"
            assert result["metadata"]["source"] == "memory"

        # Should have only 1 matching vector
        assert len(data["results"]) == 1


class TestInListFiltering:
    """Tests for $in operator filtering (Issue #24)."""

    def test_filter_agent_in_list(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $in operator for agent_id."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "fintech",
                "top_k": 10,
                "metadata_filter": {
                    "agent_id": {"$in": ["agent_1", "agent_3"]}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return agent_1 and agent_3 vectors
        for result in data["results"]:
            assert result["metadata"]["agent_id"] in ["agent_1", "agent_3"]

        # Should not contain agent_2
        agent_ids = [r["metadata"]["agent_id"] for r in data["results"]]
        assert "agent_2" not in agent_ids

    def test_filter_tags_in_list(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $in operator for array field tags."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "analysis",
                "top_k": 10,
                "metadata_filter": {
                    "tags": {"$in": ["fintech", "compliance"]}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Results should have tags that match the filter
        # Note: This tests if the tags field (which is a list) is IN the filter list
        for result in data["results"]:
            tags = result["metadata"]["tags"]
            assert tags in [["fintech", "compliance"], ["fintech", "transaction"], ["fintech", "analysis"]]


class TestContainsFiltering:
    """Tests for $contains operator filtering (Issue #24)."""

    def test_filter_status_contains(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $contains operator for partial string match."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {
                    "status": {"$contains": "act"}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return "active" status vectors (contains "act")
        for result in data["results"]:
            assert "act" in result["metadata"]["status"]


class TestNumericFiltering:
    """Tests for numeric comparison operators (Issue #24)."""

    def test_filter_score_gte(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $gte (greater than or equal) operator."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "analysis",
                "top_k": 10,
                "metadata_filter": {
                    "score": {"$gte": 0.8}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return vectors with score >= 0.8
        for result in data["results"]:
            assert result["metadata"]["score"] >= 0.8

    def test_filter_score_gt(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $gt (greater than) operator."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "analysis",
                "top_k": 10,
                "metadata_filter": {
                    "score": {"$gt": 0.8}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return vectors with score > 0.8
        for result in data["results"]:
            assert result["metadata"]["score"] > 0.8

    def test_filter_score_lte(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $lte (less than or equal) operator."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "memory",
                "top_k": 10,
                "metadata_filter": {
                    "score": {"$lte": 0.7}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return vectors with score <= 0.7
        for result in data["results"]:
            assert result["metadata"]["score"] <= 0.7

    def test_filter_score_lt(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with $lt (less than) operator."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "memory",
                "top_k": 10,
                "metadata_filter": {
                    "score": {"$lt": 0.6}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return vectors with score < 0.6
        for result in data["results"]:
            assert result["metadata"]["score"] < 0.6


class TestNoMatchCases:
    """Tests for cases where no results match metadata filters (Issue #24)."""

    def test_no_match_agent_id(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with agent_id that doesn't exist."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {"agent_id": "agent_nonexistent"}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert len(data["results"]) == 0
        assert data["total_results"] == 0

    def test_no_match_score_too_high(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with score threshold that no vectors meet."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {
                    "score": {"$gte": 1.5}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert len(data["results"]) == 0
        assert data["total_results"] == 0

    def test_no_match_multiple_contradicting_filters(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with contradicting conditions."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {
                    "agent_id": "agent_1",
                    "source": "compliance"  # agent_1 doesn't have compliance source
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert len(data["results"]) == 0


class TestCombinedFiltering:
    """Tests for complex combined filtering scenarios (Issue #24)."""

    def test_combined_equality_and_numeric(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test combining equality and numeric filters."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "fintech",
                "top_k": 10,
                "metadata_filter": {
                    "source": "memory",
                    "score": {"$gte": 0.8}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should match both conditions
        for result in data["results"]:
            assert result["metadata"]["source"] == "memory"
            assert result["metadata"]["score"] >= 0.8

    def test_combined_in_and_numeric(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test combining $in and numeric filters."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "analysis",
                "top_k": 10,
                "metadata_filter": {
                    "agent_id": {"$in": ["agent_1", "agent_2"]},
                    "score": {"$gte": 0.7}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should match both conditions
        for result in data["results"]:
            assert result["metadata"]["agent_id"] in ["agent_1", "agent_2"]
            assert result["metadata"]["score"] >= 0.7


class TestFilteringAfterSimilarity:
    """Tests that metadata filtering is applied AFTER similarity search (Issue #24)."""

    def test_filtering_refines_similarity_results(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test that metadata filter refines similarity search results."""
        # First search without filter
        response_no_filter = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response_no_filter.status_code == 200
        data_no_filter = response_no_filter.json()
        total_without_filter = len(data_no_filter["results"])

        # Then search with filter
        response_with_filter = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {"agent_id": "agent_1"}
            },
            headers=auth_headers
        )

        assert response_with_filter.status_code == 200
        data_with_filter = response_with_filter.json()
        total_with_filter = len(data_with_filter["results"])

        # Filter should reduce or keep same number of results
        assert total_with_filter <= total_without_filter

        # All filtered results should match the filter
        for result in data_with_filter["results"]:
            assert result["metadata"]["agent_id"] == "agent_1"


class TestEdgeCases:
    """Tests for edge cases in metadata filtering (Issue #24)."""

    def test_filter_with_missing_field(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering by field that doesn't exist in metadata."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {"nonexistent_field": "value"}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return no results since field doesn't exist
        assert len(data["results"]) == 0

    def test_filter_with_null_value(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with null value."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {"agent_id": None}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        # Should work but return no results (no vectors have null agent_id)

    def test_filter_empty_in_list(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test filtering with empty $in list."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "top_k": 10,
                "metadata_filter": {
                    "agent_id": {"$in": []}
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return no results (nothing can be in empty list)
        assert len(data["results"]) == 0


class TestFilterIntegrationWithSimilarityThreshold:
    """Tests integration of metadata filters with similarity threshold (Issue #24)."""

    def test_filter_and_similarity_threshold(self, client, auth_headers, test_project_id, setup_test_vectors):
        """Test that both similarity threshold and metadata filter are applied."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "fintech compliance check",
                "top_k": 10,
                "similarity_threshold": 0.5,
                "metadata_filter": {"source": "memory"}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Results should pass both similarity threshold AND metadata filter
        for result in data["results"]:
            assert result["similarity"] >= 0.5
            assert result["metadata"]["source"] == "memory"
