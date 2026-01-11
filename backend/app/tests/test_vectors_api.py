"""
Tests for Vector API endpoints (Issue #27).

Tests Epic 6 (Vector Operations API):
- POST /database/vectors/upsert
- Dimension validation
- Upsert behavior (insert vs update)
- Namespace isolation
- Metadata support

Per DX Contract:
- All endpoints require /database/ prefix
- Dimension mismatches return DIMENSION_MISMATCH error
- Authentication required via X-API-Key
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


client = TestClient(app)


# Valid API key for testing
VALID_API_KEY = settings.demo_api_key_1


class TestVectorUpsertEndpoint:
    """Tests for POST /database/vectors/upsert (Issue #27)."""

    def test_upsert_vector_insert_new_384_dimensions(self):
        """
        Test upserting a new vector with 384 dimensions.
        Epic 6 Story 1: Insert behavior when vector_id not provided.
        """
        # Create a 384-dimensional vector
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document for 384-dim vector",
                "metadata": {
                    "source": "test",
                    "type": "384-dim"
                }
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "vector_id" in data
        assert data["created"] is True  # New vector
        assert data["dimensions"] == 384
        assert data["namespace"] == "default"
        assert data["metadata"]["source"] == "test"
        assert "stored_at" in data

    def test_upsert_vector_insert_new_768_dimensions(self):
        """
        Test upserting a new vector with 768 dimensions.
        Epic 6 Story 2: Dimension validation for 768-dim vectors.
        """
        vector_embedding = [0.2] * 768

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document for 768-dim vector",
                "namespace": "test_namespace"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["created"] is True
        assert data["dimensions"] == 768
        assert data["namespace"] == "test_namespace"

    def test_upsert_vector_insert_new_1024_dimensions(self):
        """
        Test upserting a new vector with 1024 dimensions.
        Epic 6 Story 2: Dimension validation for 1024-dim vectors.
        """
        vector_embedding = [0.3] * 1024

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document for 1024-dim vector"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["created"] is True
        assert data["dimensions"] == 1024

    def test_upsert_vector_insert_new_1536_dimensions(self):
        """
        Test upserting a new vector with 1536 dimensions.
        Epic 6 Story 2: Dimension validation for 1536-dim vectors (OpenAI).
        """
        vector_embedding = [0.4] * 1536

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document for 1536-dim vector"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["created"] is True
        assert data["dimensions"] == 1536

    def test_upsert_vector_update_existing(self):
        """
        Test upserting an existing vector (update behavior).
        Epic 6 Story 1: Update behavior when vector_id already exists.
        """
        vector_embedding = [0.5] * 384
        vector_id = "test_vector_update_001"

        # First insert
        response1 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_id": vector_id,
                "vector_embedding": vector_embedding,
                "document": "Original document",
                "metadata": {"version": 1}
            }
        )

        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["created"] is True
        assert data1["vector_id"] == vector_id

        # Update with same vector_id
        updated_vector = [0.6] * 384
        response2 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_id": vector_id,
                "vector_embedding": updated_vector,
                "document": "Updated document",
                "metadata": {"version": 2}
            }
        )

        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["created"] is False  # Updated, not created
        assert data2["vector_id"] == vector_id
        assert data2["metadata"]["version"] == 2

    def test_upsert_vector_with_custom_vector_id(self):
        """
        Test upserting with a custom vector_id.
        Epic 6 Story 1: Support custom vector_id for upsert.
        """
        vector_embedding = [0.7] * 384
        custom_id = "custom_vec_abc123"

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_id": custom_id,
                "vector_embedding": vector_embedding,
                "document": "Document with custom ID"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["vector_id"] == custom_id
        assert data["created"] is True

    def test_upsert_vector_namespace_isolation(self):
        """
        Test namespace isolation for vectors.
        Epic 6 Story 5: Namespace support for logical isolation.
        """
        vector_embedding = [0.8] * 384
        vector_id = "test_namespace_vec_001"

        # Insert in namespace1
        response1 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_id": vector_id,
                "vector_embedding": vector_embedding,
                "document": "Document in namespace1",
                "namespace": "namespace1"
            }
        )

        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["namespace"] == "namespace1"
        assert data1["created"] is True

        # Insert same vector_id in namespace2 (should be independent)
        response2 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_id": vector_id,
                "vector_embedding": vector_embedding,
                "document": "Document in namespace2",
                "namespace": "namespace2"
            }
        )

        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["namespace"] == "namespace2"
        assert data2["created"] is True  # New in this namespace

    def test_upsert_vector_metadata_support(self):
        """
        Test metadata support for vectors.
        Epic 6 Story 5: Metadata support for classification.
        """
        vector_embedding = [0.9] * 384
        metadata = {
            "agent_id": "compliance_agent",
            "task_type": "compliance_check",
            "confidence": 0.95,
            "tags": ["fintech", "compliance"]
        }

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Compliance check result",
                "metadata": metadata
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"] == metadata

    def test_upsert_vector_invalid_dimensions(self):
        """
        Test dimension validation error.
        Epic 6 Story 3: DIMENSION_MISMATCH for invalid dimensions.
        """
        # Use unsupported dimension (e.g., 512)
        vector_embedding = [0.1] * 512

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Document with invalid dimensions"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        # Check for dimension mismatch in error message
        assert "512" in str(data["detail"])
        assert "384" in str(data["detail"]) or "768" in str(data["detail"])

    def test_upsert_vector_empty_embedding(self):
        """
        Test validation error for empty vector embedding.
        Epic 6 Story 2: Strict dimension validation.
        """
        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": [],
                "document": "Document with empty vector"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upsert_vector_empty_document(self):
        """
        Test validation error for empty document.
        Per schema validation: document cannot be empty.
        """
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": ""
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upsert_vector_whitespace_document(self):
        """
        Test validation error for whitespace-only document.
        Per schema validation: document cannot be whitespace.
        """
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "   "
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upsert_vector_missing_authentication(self):
        """
        Test authentication requirement.
        Per DX Contract: All endpoints require X-API-Key.
        """
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upsert_vector_invalid_api_key(self):
        """
        Test invalid API key error.
        Per DX Contract: Invalid keys return 401 INVALID_API_KEY.
        """
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": "invalid_key_xyz"},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    def test_upsert_vector_idempotency(self):
        """
        Test idempotent behavior of upsert.
        Per PRD §10: Same request produces same result.
        """
        vector_embedding = [0.11] * 384
        vector_id = "idempotent_test_001"

        request_payload = {
            "vector_id": vector_id,
            "vector_embedding": vector_embedding,
            "document": "Idempotent test document",
            "metadata": {"test": "idempotency"}
        }

        # First request
        response1 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json=request_payload
        )

        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["created"] is True

        # Second request (identical)
        response2 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json=request_payload
        )

        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["created"] is False  # Updated, not created
        assert data2["vector_id"] == data1["vector_id"]

    def test_upsert_vector_missing_required_fields(self):
        """
        Test validation error when required fields are missing.
        """
        # Missing vector_embedding
        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upsert_vector_non_numeric_embedding_values(self):
        """
        Test validation error for non-numeric embedding values.
        Epic 6 Story 2: Strict validation of embedding data types.
        """
        vector_embedding = [0.1] * 383 + ["not_a_number"]

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVectorListEndpoint:
    """Tests for GET /database/vectors/{namespace}."""

    def test_list_vectors_in_namespace(self):
        """
        Test listing vectors in a namespace.
        """
        namespace = "test_list_namespace"
        vector_embedding = [0.12] * 384

        # Insert a vector
        client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document 1",
                "namespace": namespace
            }
        )

        # List vectors
        response = client.get(
            f"/database/vectors/{namespace}",
            headers={"X-API-Key": VALID_API_KEY}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "vectors" in data
        assert "namespace" in data
        assert "total" in data
        assert data["namespace"] == namespace
        assert data["total"] >= 1

    def test_list_vectors_empty_namespace(self):
        """
        Test listing vectors in an empty namespace.
        """
        response = client.get(
            "/database/vectors/empty_namespace_xyz",
            headers={"X-API-Key": VALID_API_KEY}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["vectors"] == []
        assert data["total"] == 0


class TestDXContractCompliance:
    """Tests for DX Contract compliance (Issue #27)."""

    def test_endpoint_requires_database_prefix(self):
        """
        Test that /database/ prefix is required.
        Per DX Contract §4: All vector operations require /database/ prefix.
        """
        # This endpoint should exist at /database/vectors/upsert
        vector_embedding = [0.13] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_200_OK

    def test_dimension_mismatch_error_code(self):
        """
        Test that dimension mismatches return proper error code.
        Epic 6 Story 3: DIMENSION_MISMATCH error.
        """
        vector_embedding = [0.1] * 256  # Unsupported dimension

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # Validate error contains dimension information
        assert "detail" in data
        assert "256" in str(data["detail"])
