"""
Integration tests for Vector DELETE endpoint.
Tests the new DELETE endpoint added to close frontend integration gaps.

Tests:
- DELETE /v1/public/{project_id}/database/vectors/{vector_id} - Delete vector
"""
import pytest
from fastapi import status


class TestDeleteVectorEndpoint:
    """Test suite for DELETE /v1/public/{project_id}/database/vectors/{vector_id} endpoint."""

    def test_delete_vector_success(self, client, auth_headers_user1):
        """Test successfully deleting a vector."""
        project_id = "proj_demo_u1_001"

        # Create a vector first
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Test document for deletion",
            "namespace": "test_delete",
            "metadata": {"test": "delete"}
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        assert create_response.status_code == status.HTTP_200_OK
        vector_id = create_response.json()["vector_id"]

        # Delete the vector
        delete_response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}?namespace=test_delete",
            headers=auth_headers_user1
        )

        assert delete_response.status_code == status.HTTP_200_OK

        data = delete_response.json()
        assert "message" in data
        assert data["vector_id"] == vector_id
        assert data["namespace"] == "test_delete"

    def test_delete_vector_default_namespace(self, client, auth_headers_user1):
        """Test deleting vector from default namespace."""
        project_id = "proj_demo_u1_001"

        # Create a vector in default namespace
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Test document default namespace"
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        vector_id = create_response.json()["vector_id"]

        # Delete without specifying namespace (should use default)
        delete_response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}",
            headers=auth_headers_user1
        )

        assert delete_response.status_code == status.HTTP_200_OK
        data = delete_response.json()
        assert data["namespace"] == "default"

    def test_delete_vector_not_found(self, client, auth_headers_user1):
        """Test deleting non-existent vector returns 404."""
        project_id = "proj_demo_u1_001"
        nonexistent_vector_id = "vec_nonexistent123"

        response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{nonexistent_vector_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert nonexistent_vector_id in data["detail"]

    def test_delete_vector_wrong_namespace(self, client, auth_headers_user1):
        """Test deleting vector from wrong namespace returns 404."""
        project_id = "proj_demo_u1_001"

        # Create vector in namespace1
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Test document",
            "namespace": "namespace1"
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        vector_id = create_response.json()["vector_id"]

        # Try to delete from namespace2
        response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}?namespace=namespace2",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_vector_missing_api_key(self, client):
        """Test missing X-API-Key header returns 401."""
        project_id = "proj_demo_u1_001"
        vector_id = "vec_123"

        response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_vector_namespace_isolation(self, client, auth_headers_user1):
        """Test that deleting from one namespace doesn't affect other namespaces."""
        project_id = "proj_demo_u1_001"

        # Create vector with same ID in two different namespaces
        vector_data1 = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Document in namespace1",
            "namespace": "namespace1",
            "vector_id": "shared_id_delete_test"
        }

        vector_data2 = {
            "vector_embedding": [0.2] * 384,
            "dimensions": 384,
            "document": "Document in namespace2",
            "namespace": "namespace2",
            "vector_id": "shared_id_delete_test"
        }

        # Create in both namespaces
        client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data1,
            headers=auth_headers_user1
        )
        client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data2,
            headers=auth_headers_user1
        )

        # Delete from namespace1
        delete_response = client.delete(
            f"/v1/public/{project_id}/database/vectors/shared_id_delete_test?namespace=namespace1",
            headers=auth_headers_user1
        )
        assert delete_response.status_code == status.HTTP_200_OK

        # Vector in namespace2 should still exist
        # (we can't directly verify this without a GET endpoint, but deleting it should succeed)
        delete_response2 = client.delete(
            f"/v1/public/{project_id}/database/vectors/shared_id_delete_test?namespace=namespace2",
            headers=auth_headers_user1
        )
        assert delete_response2.status_code == status.HTTP_200_OK

    def test_delete_vector_idempotency(self, client, auth_headers_user1):
        """Test that deleting the same vector twice returns 404 on second attempt."""
        project_id = "proj_demo_u1_001"

        # Create a vector
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Test idempotency"
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        vector_id = create_response.json()["vector_id"]

        # First delete should succeed
        delete_response1 = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}",
            headers=auth_headers_user1
        )
        assert delete_response1.status_code == status.HTTP_200_OK

        # Second delete should return 404
        delete_response2 = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}",
            headers=auth_headers_user1
        )
        assert delete_response2.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_vector_various_dimensions(self, client, auth_headers_user1):
        """Test deleting vectors of different dimensions."""
        project_id = "proj_demo_u1_001"

        dimensions_to_test = [384, 768, 1024, 1536]

        for dim in dimensions_to_test:
            # Create vector
            vector_data = {
                "vector_embedding": [0.1] * dim,
                "dimensions": dim,
                "document": f"Test document {dim}D",
                "namespace": f"test_dim_{dim}"
            }

            create_response = client.post(
                f"/v1/public/{project_id}/database/vectors/upsert",
                json=vector_data,
                headers=auth_headers_user1
            )
            vector_id = create_response.json()["vector_id"]

            # Delete vector
            delete_response = client.delete(
                f"/v1/public/{project_id}/database/vectors/{vector_id}?namespace=test_dim_{dim}",
                headers=auth_headers_user1
            )

            assert delete_response.status_code == status.HTTP_200_OK
            assert delete_response.json()["vector_id"] == vector_id

    def test_delete_vector_with_metadata(self, client, auth_headers_user1):
        """Test deleting vector that has metadata."""
        project_id = "proj_demo_u1_001"

        # Create vector with metadata
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Document with metadata",
            "namespace": "metadata_test",
            "metadata": {
                "agent_id": "test_agent",
                "task_type": "test",
                "importance": "high"
            }
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        vector_id = create_response.json()["vector_id"]

        # Delete vector
        delete_response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}?namespace=metadata_test",
            headers=auth_headers_user1
        )

        assert delete_response.status_code == status.HTTP_200_OK

    def test_delete_vector_response_format(self, client, auth_headers_user1):
        """Test that delete response has correct format."""
        project_id = "proj_demo_u1_001"

        # Create a vector
        vector_data = {
            "vector_embedding": [0.1] * 384,
            "dimensions": 384,
            "document": "Test response format"
        }

        create_response = client.post(
            f"/v1/public/{project_id}/database/vectors/upsert",
            json=vector_data,
            headers=auth_headers_user1
        )
        vector_id = create_response.json()["vector_id"]

        # Delete vector
        delete_response = client.delete(
            f"/v1/public/{project_id}/database/vectors/{vector_id}",
            headers=auth_headers_user1
        )

        assert delete_response.status_code == status.HTTP_200_OK

        data = delete_response.json()
        # Verify response structure
        assert isinstance(data, dict)
        assert "message" in data
        assert "vector_id" in data
        assert "namespace" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["vector_id"], str)
        assert isinstance(data["namespace"], str)
