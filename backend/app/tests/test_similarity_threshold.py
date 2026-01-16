"""
Tests for similarity_threshold parameter in embeddings search.

Implements Issue #25: As a developer, I can enforce similarity_threshold

Test Coverage:
- Threshold parameter validation (0.0-1.0 range)
- Threshold filtering behavior (only results >= threshold)
- Integration with top_k parameter (threshold first, then top_k)
- No-match cases when threshold is too high
- Various threshold values (0.0, 0.5, 0.7, 0.9, 1.0)
- Edge cases and validation errors

Per Epic 5 Story 5 (Issue #25):
- Similarity threshold filters low-quality matches
- Threshold is applied before top_k limiting
- Results are sorted by similarity (descending)
- Empty results when no vectors meet threshold

Per PRD §10 (Explainability):
- Deterministic threshold behavior
- Clear documentation of filtering logic
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.vector_store_service import vector_store_service


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
    return "proj_threshold_test_123"


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vector store before each test."""
    vector_store_service.clear_all_vectors()
    yield
    vector_store_service.clear_all_vectors()


@pytest.fixture
def setup_test_vectors(client, auth_headers, test_project_id):
    """
    Set up test vectors with known similarity scores.

    Creates 5 vectors with different texts that will produce
    predictable similarity scores when queried.
    """
    # Store multiple vectors with different content
    # Using the batch embed-and-store endpoint with documents array (Issue #16)
    test_documents = [
        "autonomous agent workflow",
        "agent system design",
        "workflow automation",
        "completely unrelated content xyz",
        "random text about nothing",
    ]

    # Use the documents (array) field per the updated endpoint
    response = client.post(
        f"/v1/public/{test_project_id}/embeddings/embed-and-store",
        json={
            "documents": test_documents,
            "namespace": "threshold_test"
        },
        headers=auth_headers
    )
    assert response.status_code == 200, f"Failed to store vectors: {response.json()}"

    return response.json()


class TestSimilarityThresholdValidation:
    """Tests for similarity_threshold parameter validation."""

    def test_threshold_default_value(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test default threshold value is 0.0 (return all results).

        Issue #25 Requirement: Default behavior when threshold not specified.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # With default threshold (0.0), all vectors should be returned
        assert len(data["results"]) > 0

    def test_threshold_valid_range(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that valid threshold values (0.0-1.0) are accepted.

        Issue #25 Requirement: Threshold should be a float between 0.0 and 1.0.
        """
        valid_thresholds = [0.0, 0.1, 0.5, 0.7, 0.9, 1.0]

        for threshold in valid_thresholds:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/search",
                json={
                    "query": "agent workflow",
                    "namespace": "threshold_test",
                    "similarity_threshold": threshold,
                    "top_k": 5
                },
                headers=auth_headers
            )

            assert response.status_code == 200, f"Failed for threshold {threshold}"

    def test_threshold_negative_value(self, client, auth_headers, test_project_id):
        """
        Test that negative threshold values are rejected.

        Issue #25 Requirement: Validate threshold is in valid range.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": -0.1,
                "top_k": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_threshold_above_one(self, client, auth_headers, test_project_id):
        """
        Test that threshold values > 1.0 are rejected.

        Issue #25 Requirement: Validate threshold is in valid range.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 1.5,
                "top_k": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_threshold_invalid_type(self, client, auth_headers, test_project_id):
        """
        Test that non-numeric threshold values are rejected.

        Issue #25 Requirement: Validate threshold is in valid range.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": "invalid",
                "top_k": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 422


class TestThresholdFiltering:
    """Tests for threshold filtering behavior."""

    def test_threshold_filters_results(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that threshold filters out low-similarity results.

        Issue #25 Requirement: Only return results with similarity score >= threshold.
        """
        # First, get all results with threshold 0.0
        response_low = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.0,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response_low.status_code == 200
        data_low = response_low.json()
        results_low = data_low["results"]
        total_low = len(results_low)

        # Then, get results with higher threshold
        response_high = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.7,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response_high.status_code == 200
        data_high = response_high.json()
        results_high = data_high["results"]
        total_high = len(results_high)

        # Higher threshold should return fewer or equal results
        assert total_high <= total_low

        # All high-threshold results should have similarity >= 0.7
        for result in results_high:
            assert result["score"] >= 0.7

    def test_threshold_zero_returns_all(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that threshold 0.0 returns all results.

        Issue #25 Requirement: Default behavior returns all results.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.0,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return all 5 stored vectors
        assert len(data["results"]) == 5

    def test_threshold_one_strict_matching(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that threshold 1.0 requires perfect matches.

        Issue #25 Requirement: Handle cases where no results meet threshold.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "completely different query text",
                "namespace": "threshold_test",
                "similarity_threshold": 1.0,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # With threshold 1.0, unlikely to have perfect matches
        # Results should be empty or very few
        assert len(data["results"]) >= 0

        # Any results that do exist must have similarity >= 1.0 (essentially 1.0)
        for result in data["results"]:
            assert result["score"] >= 0.99  # Allow for floating point precision

    def test_threshold_ensures_minimum_quality(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that all returned results meet the threshold requirement.

        Issue #25 Requirement: Only return results with similarity score >= threshold.
        """
        thresholds = [0.3, 0.5, 0.7, 0.9]

        for threshold in thresholds:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/search",
                json={
                    "query": "agent workflow",
                    "namespace": "threshold_test",
                    "similarity_threshold": threshold,
                    "top_k": 10
                },
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Verify all results meet the threshold
            for result in data["results"]:
                assert result["score"] >= threshold, \
                    f"Result score {result['score']} below threshold {threshold}"


class TestThresholdWithTopK:
    """Tests for interaction between threshold and top_k parameters."""

    def test_threshold_applied_before_top_k(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that threshold is applied before top_k limiting.

        Issue #25 Requirement: Combine with top_k parameter (apply threshold first, then top_k).
        """
        # Get results with threshold and generous top_k
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.6,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # All results should pass threshold
        for result in data["results"]:
            assert result["score"] >= 0.6

        # Results should be sorted by similarity descending
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limits_threshold_results(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that top_k limits results after threshold filtering.

        Issue #25 Requirement: Apply threshold first, then top_k.
        """
        # First, get all results passing threshold
        response_all = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent",
                "namespace": "threshold_test",
                "similarity_threshold": 0.5,
                "top_k": 100
            },
            headers=auth_headers
        )

        assert response_all.status_code == 200
        data_all = response_all.json()
        total_all = len(data_all["results"])

        # Then, limit with top_k
        response_limited = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent",
                "namespace": "threshold_test",
                "similarity_threshold": 0.5,
                "top_k": 2
            },
            headers=auth_headers
        )

        assert response_limited.status_code == 200
        data_limited = response_limited.json()

        # Should return at most top_k results
        assert len(data_limited["results"]) <= 2

        # If there were more than 2 results passing threshold,
        # we should get exactly 2 (the top 2)
        if total_all > 2:
            assert len(data_limited["results"]) == 2

            # Verify we got the top 2 by score
            limited_scores = [r["score"] for r in data_limited["results"]]
            all_scores = [r["score"] for r in data_all["results"]]
            assert limited_scores == all_scores[:2]

    def test_threshold_and_top_k_both_zero(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test behavior when threshold is 0.0 and top_k is set.

        Issue #25 Requirement: Proper interaction between parameters.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.0,
                "top_k": 3
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 3 results (limited by top_k)
        assert len(data["results"]) <= 3

        # Results should be sorted by score
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)


class TestNoMatchCases:
    """Tests for cases where no results meet the threshold."""

    def test_no_results_high_threshold(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that empty results are returned when threshold is too high.

        Issue #25 Requirement: Handle cases where no results meet threshold.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "completely unrelated query xyz abc",
                "namespace": "threshold_test",
                "similarity_threshold": 0.95,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return successfully with empty or very few results
        assert "results" in data
        assert len(data["results"]) >= 0

        # Any results that exist must meet threshold
        for result in data["results"]:
            assert result["score"] >= 0.95

    def test_empty_namespace_with_threshold(self, client, auth_headers, test_project_id):
        """
        Test search with threshold in empty namespace.

        Issue #25 Requirement: Handle cases where no results meet threshold.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "empty_namespace",
                "similarity_threshold": 0.7,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert len(data["results"]) == 0
        assert data["results"] == []

    def test_no_match_returns_proper_structure(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that no-match cases still return proper response structure.

        Issue #25 Requirement: Handle cases where no results meet threshold.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "unrelated content",
                "namespace": "threshold_test",
                "similarity_threshold": 0.99,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure is correct
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "model" in data
        assert "namespace" in data
        assert "processing_time_ms" in data


class TestThresholdEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_threshold_exactly_at_boundary(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test threshold behavior at exact similarity boundaries.

        Issue #25 Requirement: Only return results with similarity >= threshold.
        """
        # Get all results to find actual similarity scores
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.0,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["results"]) > 0:
            # Use the lowest score as threshold
            scores = [r["score"] for r in data["results"]]
            lowest_score = min(scores)

            # Test with threshold exactly at lowest score
            response_exact = client.post(
                f"/v1/public/{test_project_id}/embeddings/search",
                json={
                    "query": "agent workflow",
                    "namespace": "threshold_test",
                    "similarity_threshold": lowest_score,
                    "top_k": 10
                },
                headers=auth_headers
            )

            assert response_exact.status_code == 200
            data_exact = response_exact.json()

            # Should include the result with exact threshold match
            assert len(data_exact["results"]) > 0

            # All results should have score >= threshold
            for result in data_exact["results"]:
                assert result["score"] >= lowest_score

    def test_threshold_with_metadata_filter(self, client, auth_headers, test_project_id):
        """
        Test threshold works correctly with metadata filtering.

        Issue #25 Requirement: Threshold should work with other filters.
        """
        # Store vectors with metadata using the documents array field
        client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "documents": ["agent workflow alpha"],
                "namespace": "metadata_test",
                "metadata": [{"type": "workflow", "priority": "high"}]
            },
            headers=auth_headers
        )

        client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "documents": ["agent workflow beta"],
                "namespace": "metadata_test",
                "metadata": [{"type": "workflow", "priority": "low"}]
            },
            headers=auth_headers
        )

        # Search with both threshold and metadata filter
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "metadata_test",
                "similarity_threshold": 0.5,
                "metadata_filter": {"priority": "high"},
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return high priority results that meet threshold
        for result in data["results"]:
            assert result["metadata"]["priority"] == "high"
            assert result["score"] >= 0.5

    def test_results_sorted_by_similarity_with_threshold(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that results are always sorted by similarity descending.

        Issue #25 Requirement: Results should be sorted by similarity.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "agent workflow",
                "namespace": "threshold_test",
                "similarity_threshold": 0.4,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["results"]) > 1:
            # Extract scores
            scores = [r["score"] for r in data["results"]]

            # Verify sorted in descending order
            assert scores == sorted(scores, reverse=True)

            # Verify all meet threshold
            for score in scores:
                assert score >= 0.4


class TestThresholdDocumentation:
    """Tests to verify threshold behavior is properly documented."""

    def test_threshold_in_request_example(self, client, auth_headers, test_project_id):
        """
        Test that threshold parameter is correctly documented in examples.

        Issue #25 Requirement: Documentation with threshold examples.
        """
        # This test documents the expected request format
        example_request = {
            "query": "compliance check results",
            "model": "BAAI/bge-small-en-v1.5",
            "namespace": "agent_memory",
            "top_k": 5,
            "similarity_threshold": 0.7,  # Only return results with similarity >= 0.7
            "metadata_filter": {"agent_id": "compliance_agent"},
            "include_embeddings": False
        }

        # This should be a valid request
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json=example_request,
            headers=auth_headers
        )

        # Should accept the request (even if no results)
        assert response.status_code == 200

    def test_threshold_behavior_deterministic(self, client, auth_headers, test_project_id, setup_test_vectors):
        """
        Test that threshold behavior is deterministic.

        Issue #25 Requirement: Same threshold produces same results.
        Per PRD §10: Deterministic behavior for explainability.
        """
        search_request = {
            "query": "agent workflow",
            "namespace": "threshold_test",
            "similarity_threshold": 0.6,
            "top_k": 5
        }

        # Make the same request twice
        response1 = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json=search_request,
            headers=auth_headers
        )

        response2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json=search_request,
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Should return identical results
        assert len(data1["results"]) == len(data2["results"])

        # Verify same vector IDs in same order
        ids1 = [r["id"] for r in data1["results"]]
        ids2 = [r["id"] for r in data2["results"]]
        assert ids1 == ids2

        # Verify same scores
        scores1 = [r["score"] for r in data1["results"]]
        scores2 = [r["score"] for r in data2["results"]]
        assert scores1 == scores2
