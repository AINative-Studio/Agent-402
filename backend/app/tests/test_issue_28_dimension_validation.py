"""
Tests for Issue #28: Strict dimension length enforcement.

GitHub Issue #28 Requirements:
- Validate vector_embedding array length matches expected dimensions
- Enforce strict validation before storage
- Only allow supported dimensions: 384, 768, 1024, 1536
- Return clear error if length mismatch
- Support project-level dimension configuration
- Follow PRD §10 for determinism

Test Coverage:
1. Test all supported dimensions (384, 768, 1024, 1536)
2. Test dimension mismatch errors
3. Test unsupported dimensions
4. Test empty vectors
5. Test validation error messages
6. Test deterministic behavior
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


client = TestClient(app)


# Valid API key for testing
VALID_API_KEY = settings.demo_api_key_1


class TestDimensionValidation:
    """Tests for strict dimension validation per Issue #28."""

    def test_valid_384_dimensions(self):
        """
        Test vector with exactly 384 dimensions is accepted.
        Issue #28: Supported dimension - 384.
        """
        vector_embedding = [0.1] * 384

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with 384 dimensions"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 384
        assert data["created"] is True

    def test_valid_768_dimensions(self):
        """
        Test vector with exactly 768 dimensions is accepted.
        Issue #28: Supported dimension - 768.
        """
        vector_embedding = [0.2] * 768

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with 768 dimensions"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 768
        assert data["created"] is True

    def test_valid_1024_dimensions(self):
        """
        Test vector with exactly 1024 dimensions is accepted.
        Issue #28: Supported dimension - 1024.
        """
        vector_embedding = [0.3] * 1024

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with 1024 dimensions"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 1024
        assert data["created"] is True

    def test_valid_1536_dimensions(self):
        """
        Test vector with exactly 1536 dimensions is accepted.
        Issue #28: Supported dimension - 1536.
        """
        vector_embedding = [0.4] * 1536

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with 1536 dimensions"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 1536
        assert data["created"] is True

    def test_unsupported_dimension_512(self):
        """
        Test vector with 512 dimensions is rejected.
        Issue #28: Only allow supported dimensions.
        """
        vector_embedding = [0.5] * 512

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with unsupported 512 dimensions"
            }
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Check error message mentions supported dimensions
        error_detail = str(data["detail"])
        assert "512" in error_detail or "not supported" in error_detail.lower()
        assert "384" in error_detail
        assert "768" in error_detail
        assert "1024" in error_detail
        assert "1536" in error_detail

    def test_unsupported_dimension_256(self):
        """
        Test vector with 256 dimensions is rejected.
        Issue #28: Clear error for unsupported dimensions.
        """
        vector_embedding = [0.1] * 256

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with unsupported 256 dimensions"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_detail = str(data["detail"])

        # Verify error message is clear
        assert "256" in error_detail or "not supported" in error_detail.lower()
        assert "384" in error_detail  # Lists supported dimensions

    def test_unsupported_dimension_2048(self):
        """
        Test vector with 2048 dimensions is rejected.
        Issue #28: Reject dimensions larger than max supported.
        """
        vector_embedding = [0.1] * 2048

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test document with unsupported 2048 dimensions"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_detail = str(data["detail"])
        assert "2048" in error_detail or "not supported" in error_detail.lower()

    def test_empty_vector_rejected(self):
        """
        Test empty vector is rejected.
        Issue #28: Enforce strict validation before storage.
        """
        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": [],
                "document": "Test document with empty vector"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_detail = str(data["detail"]).lower()
        assert "empty" in error_detail or "cannot" in error_detail

    def test_single_element_vector_rejected(self):
        """
        Test single-element vector is rejected.
        Issue #28: Dimension must match supported sizes.
        """
        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": [0.5],
                "document": "Test document with single element"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_dimension_mismatch_error_message_quality(self):
        """
        Test that dimension mismatch errors include helpful information.
        Issue #28: Return clear error if length mismatch.
        """
        # Try an unsupported dimension
        vector_embedding = [0.1] * 600

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Test dimension mismatch error"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        error_detail = str(data["detail"])

        # Error should mention:
        # 1. The attempted dimension
        assert "600" in error_detail

        # 2. List of supported dimensions
        assert "384" in error_detail
        assert "768" in error_detail
        assert "1024" in error_detail
        assert "1536" in error_detail

        # 3. Clear indication of the problem
        assert any(keyword in error_detail.lower() for keyword in [
            "not supported",
            "mismatch",
            "invalid"
        ])

    def test_deterministic_validation(self):
        """
        Test that dimension validation is deterministic.
        Issue #28: Follow PRD §10 for determinism.

        Same input should always produce same result.
        """
        vector_embedding = [0.1] * 384

        # Make same request twice
        response1 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Determinism test document",
                "vector_id": "determinism_test_1"
            }
        )

        response2 = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Determinism test document",
                "vector_id": "determinism_test_1"
            }
        )

        # Both should succeed with same status
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Dimensions should be consistently reported
        assert response1.json()["dimensions"] == 384
        assert response2.json()["dimensions"] == 384

    def test_all_supported_dimensions_in_sequence(self):
        """
        Test all supported dimensions work correctly in sequence.
        Issue #28: Comprehensive test of all supported dimensions.
        """
        test_cases = [
            (384, "BAAI/bge-small-en-v1.5 compatible"),
            (768, "BAAI/bge-base-en-v1.5 compatible"),
            (1024, "BAAI/bge-large-en-v1.5 compatible"),
            (1536, "OpenAI ada-002 compatible")
        ]

        for dims, description in test_cases:
            vector_embedding = [0.1] * dims

            response = client.post(
                "/database/vectors/upsert",
                headers={"X-API-Key": VALID_API_KEY},
                json={
                    "vector_embedding": vector_embedding,
                    "document": f"Test {description}",
                    "metadata": {
                        "dimensions": dims,
                        "description": description
                    }
                }
            )

            assert response.status_code == status.HTTP_200_OK, \
                f"Failed for {dims} dimensions: {response.json()}"

            data = response.json()
            assert data["dimensions"] == dims, \
                f"Expected {dims} dimensions, got {data['dimensions']}"
            assert data["created"] is True

    def test_namespace_with_dimension_validation(self):
        """
        Test dimension validation works with namespace parameter.
        Issue #28: Support project-level dimension configuration.
        """
        vector_embedding = [0.5] * 768

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Namespace dimension test",
                "namespace": "test_namespace_dims"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 768
        assert data["namespace"] == "test_namespace_dims"

    def test_metadata_with_dimension_validation(self):
        """
        Test dimension validation works with metadata.
        Issue #28: Ensure validation doesn't break other features.
        """
        vector_embedding = [0.3] * 1024

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "Metadata dimension test",
                "metadata": {
                    "model": "BAAI/bge-large-en-v1.5",
                    "test": "dimension_validation"
                }
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dimensions"] == 1024
        assert data["metadata"]["model"] == "BAAI/bge-large-en-v1.5"


class TestDimensionBoundaries:
    """Test edge cases around dimension boundaries."""

    def test_383_dimensions_rejected(self):
        """Test 383 dimensions (one less than 384) is rejected."""
        vector_embedding = [0.1] * 383

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "383 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_385_dimensions_rejected(self):
        """Test 385 dimensions (one more than 384) is rejected."""
        vector_embedding = [0.1] * 385

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "385 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_767_dimensions_rejected(self):
        """Test 767 dimensions (one less than 768) is rejected."""
        vector_embedding = [0.1] * 767

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "767 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_769_dimensions_rejected(self):
        """Test 769 dimensions (one more than 768) is rejected."""
        vector_embedding = [0.1] * 769

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "769 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_1023_dimensions_rejected(self):
        """Test 1023 dimensions (one less than 1024) is rejected."""
        vector_embedding = [0.1] * 1023

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "1023 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_1025_dimensions_rejected(self):
        """Test 1025 dimensions (one more than 1024) is rejected."""
        vector_embedding = [0.1] * 1025

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "1025 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_1535_dimensions_rejected(self):
        """Test 1535 dimensions (one less than 1536) is rejected."""
        vector_embedding = [0.1] * 1535

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "1535 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_1537_dimensions_rejected(self):
        """Test 1537 dimensions (one more than 1536) is rejected."""
        vector_embedding = [0.1] * 1537

        response = client.post(
            "/database/vectors/upsert",
            headers={"X-API-Key": VALID_API_KEY},
            json={
                "vector_embedding": vector_embedding,
                "document": "1537 dimension test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
