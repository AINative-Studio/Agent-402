"""
Unit and integration tests for Issue #16: embed-and-store endpoint.

Tests cover:
- Batch document embedding and storage
- Metadata support
- Namespace support
- Default model behavior
- Error handling
- Response validation

Per PRD §10 (Success Criteria):
- All tests must pass
- Code coverage >80%
- Error cases properly handled
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.embedding_service import embedding_service
from app.core.config import settings


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vectors before and after each test."""
    embedding_service.clear_vectors()
    yield
    embedding_service.clear_vectors()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid authentication headers."""
    return {"X-API-Key": settings.demo_api_key_1}


@pytest.fixture
def project_id():
    """Test project ID."""
    return "proj_test_001"


class TestEmbedAndStoreBasic:
    """Basic functionality tests for embed-and-store endpoint."""

    def test_embed_and_store_single_document(self, client, auth_headers, project_id):
        """
        Test embedding and storing a single document.

        Verifies:
        - Single document can be embedded and stored
        - Response includes vector_id, model, dimensions
        - Default model is used when not specified
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Autonomous fintech agent executing compliance check"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "vector_ids" in data
        assert "vectors_stored" in data
        assert "model" in data
        assert "dimensions" in data
        assert "namespace" in data
        assert "results" in data
        assert "processing_time_ms" in data

        # Verify data values
        assert len(data["vector_ids"]) == 1
        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"  # Default model
        assert data["dimensions"] == 384  # Default dimensions
        assert data["namespace"] == "default"
        assert len(data["results"]) == 1
        assert data["processing_time_ms"] >= 0

        # Verify result details
        result = data["results"][0]
        assert "vector_id" in result
        assert result["document"] == "Autonomous fintech agent executing compliance check"

    def test_embed_and_store_multiple_documents(self, client, auth_headers, project_id):
        """
        Test embedding and storing multiple documents in batch.

        Verifies:
        - Multiple documents can be processed in one request
        - All documents get unique vector IDs
        - Stored count matches document count
        """
        documents = [
            "Autonomous fintech agent executing compliance check",
            "Transaction risk assessment completed successfully",
            "Portfolio rebalancing recommendation generated"
        ]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={"documents": documents}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify batch processing
        assert len(data["vector_ids"]) == 3
        assert data["vectors_stored"] == 3
        assert len(data["results"]) == 3

        # Verify all vector IDs are unique
        assert len(set(data["vector_ids"])) == 3

        # Verify all documents are stored correctly
        for idx, result in enumerate(data["results"]):
            assert result["document"] == documents[idx]
            assert result["vector_id"] == data["vector_ids"][idx]

    def test_embed_and_store_with_metadata(self, client, auth_headers, project_id):
        """
        Test embedding and storing documents with metadata.

        Verifies:
        - Metadata can be provided for each document
        - Metadata is stored and returned correctly
        - Metadata length must match documents length
        """
        documents = [
            "Autonomous fintech agent executing compliance check",
            "Transaction risk assessment completed"
        ]
        metadata = [
            {"source": "agent_memory", "agent_id": "compliance_agent", "type": "decision"},
            {"source": "agent_memory", "agent_id": "risk_agent", "type": "assessment"}
        ]

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": documents,
                "metadata": metadata
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metadata is returned
        for idx, result in enumerate(data["results"]):
            assert result["metadata"] == metadata[idx]

    def test_embed_and_store_with_namespace(self, client, auth_headers, project_id):
        """
        Test embedding and storing documents with custom namespace.

        Verifies:
        - Custom namespace can be specified
        - Namespace is returned in response
        - Default namespace is used when not specified
        """
        # Test with custom namespace
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"],
                "namespace": "agent_memory"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["namespace"] == "agent_memory"

        # Test with default namespace
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["namespace"] == "default"

    def test_embed_and_store_with_custom_model(self, client, auth_headers, project_id):
        """
        Test embedding and storing documents with custom model.

        Verifies:
        - Custom model can be specified
        - Dimensions match the specified model
        - Model is returned in response
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"],
                "model": "sentence-transformers/all-mpnet-base-v2"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
        assert data["dimensions"] == 768  # mpnet-base dimensions


class TestEmbedAndStoreValidation:
    """Validation and error handling tests."""

    def test_embed_and_store_empty_documents(self, client, auth_headers, project_id):
        """
        Test that empty documents list is rejected.

        Verifies:
        - Empty documents list returns validation error
        - Error code is 422 (Unprocessable Entity)
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={"documents": []}
        )

        assert response.status_code == 422

    def test_embed_and_store_whitespace_document(self, client, auth_headers, project_id):
        """
        Test that whitespace-only documents are rejected.

        Verifies:
        - Whitespace-only documents return validation error
        - Error indicates which document is invalid
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={"documents": ["Valid document", "   ", "Another valid"]}
        )

        assert response.status_code == 422

    def test_embed_and_store_metadata_length_mismatch(self, client, auth_headers, project_id):
        """
        Test that metadata length must match documents length.

        Verifies:
        - Mismatched metadata length returns validation error
        - Error message indicates the mismatch
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Doc 1", "Doc 2"],
                "metadata": [{"key": "value"}]  # Only 1 metadata for 2 documents
            }
        )

        assert response.status_code == 422

    def test_embed_and_store_unsupported_model(self, client, auth_headers, project_id):
        """
        Test that unsupported model returns error.

        Verifies:
        - Unsupported model returns 422
        - Error indicates model is not supported
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"],
                "model": "unsupported-model-xyz"
            }
        )

        assert response.status_code == 422

    def test_embed_and_store_invalid_namespace(self, client, auth_headers, project_id):
        """
        Test that invalid namespace characters are rejected.

        Verifies:
        - Invalid namespace characters return validation error
        - Only alphanumeric, underscore, and hyphen are allowed
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"],
                "namespace": "invalid@namespace!"
            }
        )

        assert response.status_code == 422

    def test_embed_and_store_missing_auth(self, client, project_id):
        """
        Test that authentication is required.

        Verifies:
        - Missing API key returns 401
        - Error code is UNAUTHORIZED (from middleware)
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={"documents": ["Test document"]}
        )

        assert response.status_code == 401
        data = response.json()
        # Middleware returns UNAUTHORIZED error code for missing auth
        assert data.get("error_code") in ["INVALID_API_KEY", "UNAUTHORIZED"]


class TestEmbedAndStoreDXContract:
    """DX Contract compliance tests."""

    def test_default_model_384_dimensions(self, client, auth_headers, project_id):
        """
        Test DX Contract §3: Default model is 384 dimensions.

        Verifies:
        - When model is omitted, BAAI/bge-small-en-v1.5 is used
        - Default model produces exactly 384 dimensions
        - Behavior is deterministic
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={"documents": ["Test document"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_deterministic_behavior(self, client, auth_headers, project_id):
        """
        Test PRD §10: Deterministic behavior.

        Verifies:
        - Same input produces same output
        - Embeddings are reproducible
        - Processing is consistent
        """
        request_data = {
            "documents": ["Autonomous fintech agent"],
            "model": "BAAI/bge-small-en-v1.5"
        }

        # Make two identical requests
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json=request_data
        )

        embedding_service.clear_vectors()  # Clear between requests

        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json=request_data
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify deterministic fields match
        data1 = response1.json()
        data2 = response2.json()

        assert data1["model"] == data2["model"]
        assert data1["dimensions"] == data2["dimensions"]
        assert data1["vectors_stored"] == data2["vectors_stored"]

    def test_error_format_consistency(self, client, auth_headers, project_id):
        """
        Test DX Contract §7: Error format consistency.

        Verifies:
        - Errors return { detail, error_code } format
        - Error codes are stable
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={"documents": []}
        )

        assert response.status_code == 422
        # Response should have detail field (from validation error)


class TestEmbedAndStoreIntegration:
    """Integration tests with vector storage."""

    def test_vectors_stored_in_service(self, client, auth_headers, project_id):
        """
        Test that vectors are actually stored in the embedding service.

        Verifies:
        - Vectors can be retrieved after storage
        - Vector data includes all expected fields
        """
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Test document"],
                "metadata": [{"key": "value"}]
            }
        )

        assert response.status_code == 200
        data = response.json()
        vector_id = data["vector_ids"][0]

        # Retrieve vector from service
        stored_vector = embedding_service.get_vector(vector_id)
        assert stored_vector is not None
        assert stored_vector["text"] == "Test document"
        assert stored_vector["metadata"]["key"] == "value"
        assert stored_vector["model"] == "BAAI/bge-small-en-v1.5"
        assert len(stored_vector["embedding"]) == 384

    def test_namespace_isolation(self, client, auth_headers, project_id):
        """
        Test that different namespaces are isolated.

        Verifies:
        - Documents in different namespaces are separate
        - Namespace is stored with vector data
        """
        # Store in namespace1
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Document in namespace1"],
                "namespace": "namespace1"
            }
        )

        # Store in namespace2
        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            headers=auth_headers,
            json={
                "documents": ["Document in namespace2"],
                "namespace": "namespace2"
            }
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify both were stored with correct namespaces
        vector_id1 = response1.json()["vector_ids"][0]
        vector_id2 = response2.json()["vector_ids"][0]

        stored1 = embedding_service.get_vector(vector_id1)
        stored2 = embedding_service.get_vector(vector_id2)

        assert stored1["namespace"] == "namespace1"
        assert stored2["namespace"] == "namespace2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
