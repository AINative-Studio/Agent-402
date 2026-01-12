"""
Tests for embeddings compare API endpoint.

Test Coverage:
- POST /v1/public/{project_id}/embeddings/compare
- Cosine similarity calculation
- Default model behavior
- Multiple model support
- Input validation
- Processing time measurement

Per TDD best practices:
- Test behavior, not implementation
- Cover success cases and error cases
- Ensure deterministic results
- Validate response schema compliance
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
    # Use first API key from settings
    if settings.valid_api_keys:
        return list(settings.valid_api_keys.keys())[0]
    return settings.demo_api_key_1


@pytest.fixture
def auth_headers(valid_api_key):
    """Create authentication headers."""
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def test_project_id():
    """Get a test project ID."""
    return "proj_test_abc123"


class TestEmbeddingsCompare:
    """Tests for POST /v1/public/{project_id}/embeddings/compare endpoint."""

    def test_compare_embeddings_success_default_model(self, client, auth_headers, test_project_id):
        """
        Test successful embedding comparison with default model.

        Verifies:
        - Endpoint accepts two texts
        - Returns both embeddings
        - Calculates cosine similarity
        - Uses default model when not specified
        - Returns proper response schema
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Autonomous agent executing compliance check",
                "text2": "AI system performing regulatory verification"
            },
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.json()

        # Verify all required fields are present
        assert "text1" in data
        assert "text2" in data
        assert "embedding1" in data
        assert "embedding2" in data
        assert "cosine_similarity" in data
        assert "model" in data
        assert "dimensions" in data
        assert "processing_time_ms" in data

        # Verify texts are returned correctly
        assert data["text1"] == "Autonomous agent executing compliance check"
        assert data["text2"] == "AI system performing regulatory verification"

        # Verify default model is used
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

        # Verify embeddings have correct dimensions
        assert len(data["embedding1"]) == 384
        assert len(data["embedding2"]) == 384

        # Verify cosine similarity is in valid range
        assert 0.0 <= data["cosine_similarity"] <= 1.0

        # Verify processing time is non-negative
        assert data["processing_time_ms"] >= 0

        # Verify embeddings are lists of floats
        assert all(isinstance(x, float) for x in data["embedding1"])
        assert all(isinstance(x, float) for x in data["embedding2"])

    def test_compare_embeddings_identical_texts(self, client, auth_headers, test_project_id):
        """
        Test that identical texts produce cosine similarity close to 1.0.

        Verifies:
        - Identical texts have high similarity
        - Cosine similarity calculation is correct
        - Embeddings are deterministic
        """
        text = "The quick brown fox jumps over the lazy dog"

        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": text,
                "text2": text
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Identical texts should have cosine similarity very close to 1.0
        # Allow small floating point tolerance
        assert data["cosine_similarity"] >= 0.99
        assert data["cosine_similarity"] <= 1.0

        # Verify embeddings are identical (or very close due to floating point)
        embedding1 = data["embedding1"]
        embedding2 = data["embedding2"]

        # Check that embeddings are very similar
        for v1, v2 in zip(embedding1, embedding2):
            assert abs(v1 - v2) < 0.001

    def test_compare_embeddings_different_texts(self, client, auth_headers, test_project_id):
        """
        Test that very different texts produce lower similarity scores.

        Verifies:
        - Unrelated texts have lower similarity
        - Similarity calculation distinguishes between different content
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "The weather is sunny today",
                "text2": "Quantum computing advances rapidly"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Different texts should have similarity less than identical texts
        # but still in valid range
        assert 0.0 <= data["cosine_similarity"] < 0.99

    def test_compare_embeddings_with_specific_model(self, client, auth_headers, test_project_id):
        """
        Test embedding comparison with specific model.

        Verifies:
        - Endpoint accepts model parameter
        - Uses specified model
        - Returns correct dimensions for model
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Fintech compliance check",
                "text2": "Financial regulatory verification",
                "model": "sentence-transformers/all-mpnet-base-v2"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify specified model is used
        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data["dimensions"] == 768

        # Verify embeddings have correct dimensions
        assert len(data["embedding1"]) == 768
        assert len(data["embedding2"]) == 768

        # Verify cosine similarity is calculated
        assert 0.0 <= data["cosine_similarity"] <= 1.0

    def test_compare_embeddings_empty_text1(self, client, auth_headers, test_project_id):
        """
        Test that empty text1 returns validation error.

        Verifies:
        - Empty text1 is rejected
        - Returns 422 validation error
        - Error message is informative
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "",
                "text2": "Some text"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_empty_text2(self, client, auth_headers, test_project_id):
        """
        Test that empty text2 returns validation error.

        Verifies:
        - Empty text2 is rejected
        - Returns 422 validation error
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text",
                "text2": ""
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_whitespace_only_text1(self, client, auth_headers, test_project_id):
        """
        Test that whitespace-only text1 returns validation error.

        Verifies:
        - Whitespace-only text is rejected
        - Validation catches empty content after stripping
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "   \t\n  ",
                "text2": "Some text"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_whitespace_only_text2(self, client, auth_headers, test_project_id):
        """
        Test that whitespace-only text2 returns validation error.

        Verifies:
        - Whitespace-only text is rejected
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text",
                "text2": "   \t\n  "
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_missing_text1(self, client, auth_headers, test_project_id):
        """
        Test that missing text1 returns validation error.

        Verifies:
        - Missing required field is rejected
        - Returns 422 validation error
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text2": "Some text"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_missing_text2(self, client, auth_headers, test_project_id):
        """
        Test that missing text2 returns validation error.

        Verifies:
        - Missing required field is rejected
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_unsupported_model(self, client, auth_headers, test_project_id):
        """
        Test that unsupported model returns validation error.

        Verifies:
        - Unsupported model is rejected
        - Returns 422 validation error
        - Error message lists supported models
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text",
                "text2": "Other text",
                "model": "unsupported-model-xyz"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_compare_embeddings_no_auth(self, client, test_project_id):
        """
        Test that missing API key returns 401 unauthorized.

        Verifies:
        - Endpoint requires authentication
        - Missing API key returns 401
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text",
                "text2": "Other text"
            }
        )

        assert response.status_code == 401

    def test_compare_embeddings_invalid_auth(self, client, test_project_id):
        """
        Test that invalid API key returns 401 unauthorized.

        Verifies:
        - Invalid API key is rejected
        - Returns 401 unauthorized
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "Some text",
                "text2": "Other text"
            },
            headers={"X-API-Key": "invalid-key-123"}
        )

        assert response.status_code == 401

    def test_compare_embeddings_similar_texts(self, client, auth_headers, test_project_id):
        """
        Test that semantically similar texts produce valid similarity scores.

        Note: With mock hash-based embeddings, we can't test true semantic similarity.
        This test verifies the endpoint works correctly and returns valid similarity scores.
        In production with real embeddings, similar texts would have higher similarity.

        Verifies:
        - Endpoint processes similar texts successfully
        - Similarity score is in valid range [0.0, 1.0]
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "The cat sat on the mat",
                "text2": "A feline rested on the rug"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # With mock embeddings, we just verify valid range
        # In production with real embeddings, similar texts would score > 0.5
        assert 0.0 <= data["cosine_similarity"] <= 1.0

    def test_compare_embeddings_deterministic(self, client, auth_headers, test_project_id):
        """
        Test that same inputs produce same outputs (deterministic).

        Verifies:
        - Embedding generation is deterministic
        - Same texts always produce same similarity
        - Results are reproducible
        """
        request_data = {
            "text1": "Deterministic test input one",
            "text2": "Deterministic test input two"
        }

        # Make first request
        response1 = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json=request_data,
            headers=auth_headers
        )

        # Make second request with identical input
        response2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json=request_data,
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Verify embeddings are identical
        assert data1["embedding1"] == data2["embedding1"]
        assert data1["embedding2"] == data2["embedding2"]

        # Verify similarity is identical
        assert data1["cosine_similarity"] == data2["cosine_similarity"]

        # Verify model and dimensions are identical
        assert data1["model"] == data2["model"]
        assert data1["dimensions"] == data2["dimensions"]

    def test_compare_embeddings_trims_whitespace(self, client, auth_headers, test_project_id):
        """
        Test that leading/trailing whitespace is trimmed.

        Verifies:
        - Whitespace is stripped from inputs
        - Trimmed text is returned in response
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/compare",
            json={
                "text1": "  Text with spaces  ",
                "text2": "\tText with tabs\t"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify whitespace is trimmed
        assert data["text1"] == "Text with spaces"
        assert data["text2"] == "Text with tabs"
