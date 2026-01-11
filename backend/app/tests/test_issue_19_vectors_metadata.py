"""
Tests for Issue #19: Embed-and-store responses include vectors_stored, model, dimensions.

Epic 4 Story 4 (2 points):
- As a developer, responses include vectors stored, model, and dimensions

Requirements:
- Embed-and-store responses MUST include: vectors_stored (count), model (used), dimensions (vector size)
- Add response schema with these required fields
- Calculate and return accurate counts and metadata
- Include processing_time_ms if available
- Ensure response format is consistent and documented

Per PRD §9: Demo proof requires observable metadata.
Per DX Contract: Response shapes must be deterministic and documented.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.embedding_service import embedding_service


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
    return "proj_test_abc123"


@pytest.fixture(autouse=True)
def clear_vector_store():
    """Clear vector store before each test."""
    embedding_service.clear_vectors()
    yield
    embedding_service.clear_vectors()


class TestIssue19VectorsStoredField:
    """Tests for vectors_stored field in embed-and-store response."""

    def test_response_includes_vectors_stored_field(self, client, auth_headers, test_project_id):
        """
        Test that embed-and-store response includes vectors_stored field.

        Issue #19 Requirement:
        - Response MUST include vectors_stored count
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test autonomous agent workflow"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #19: vectors_stored MUST be in response
        assert "vectors_stored" in data, "Response missing required field 'vectors_stored'"

    def test_vectors_stored_is_integer(self, client, auth_headers, test_project_id):
        """
        Test that vectors_stored is an integer value.

        Issue #19 Requirement:
        - vectors_stored must be a valid integer count
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test data"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["vectors_stored"], int), "vectors_stored must be an integer"
        assert data["vectors_stored"] >= 0, "vectors_stored must be non-negative"

    def test_vectors_stored_equals_one_for_single_text(self, client, auth_headers, test_project_id):
        """
        Test that vectors_stored equals 1 for single text input.

        Issue #19 Requirement:
        - For single text input, vectors_stored should be exactly 1
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Single document to store"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["vectors_stored"] == 1, "vectors_stored should be 1 for single text input"

    def test_vectors_stored_accurate_on_upsert(self, client, auth_headers, test_project_id):
        """
        Test that vectors_stored is accurate when upserting.

        Issue #19 Requirement:
        - vectors_stored count must be accurate even for upsert operations
        """
        vector_id = "vec_test_upsert"

        # First insert
        response1 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Initial text",
                "vector_id": vector_id,
                "upsert": True
            },
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response1.json()["vectors_stored"] == 1

        # Update via upsert
        response2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Updated text",
                "vector_id": vector_id,
                "upsert": True
            },
            headers=auth_headers
        )

        assert response2.status_code == 200
        # Still 1 vector stored (updated, not duplicated)
        assert response2.json()["vectors_stored"] == 1


class TestIssue19ModelField:
    """Tests for model field in embed-and-store response."""

    def test_response_includes_model_field(self, client, auth_headers, test_project_id):
        """
        Test that embed-and-store response includes model field.

        Issue #19 Requirement:
        - Response MUST include model used
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test text"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #19: model MUST be in response
        assert "model" in data, "Response missing required field 'model'"

    def test_model_shows_default_when_omitted(self, client, auth_headers, test_project_id):
        """
        Test that model field shows default model when not specified.

        Issue #19 Requirement:
        - Response must indicate which model was actually used
        - Default model is BAAI/bge-small-en-v1.5
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test with default model"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == "BAAI/bge-small-en-v1.5", "Should return default model name"

    def test_model_shows_specified_model(self, client, auth_headers, test_project_id):
        """
        Test that model field shows the specified model.

        Issue #19 Requirement:
        - Response must accurately reflect which model was used
        """
        specified_model = "sentence-transformers/all-mpnet-base-v2"

        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test with specific model",
                "model": specified_model
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["model"] == specified_model, "Should return specified model name"

    def test_model_is_string(self, client, auth_headers, test_project_id):
        """
        Test that model field is a string value.

        Issue #19 Requirement:
        - model must be a valid string
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["model"], str), "model must be a string"
        assert len(data["model"]) > 0, "model must not be empty"


class TestIssue19DimensionsField:
    """Tests for dimensions field in embed-and-store response."""

    def test_response_includes_dimensions_field(self, client, auth_headers, test_project_id):
        """
        Test that embed-and-store response includes dimensions field.

        Issue #19 Requirement:
        - Response MUST include dimensions (vector size)
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test text"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Issue #19: dimensions MUST be in response
        assert "dimensions" in data, "Response missing required field 'dimensions'"

    def test_dimensions_is_integer(self, client, auth_headers, test_project_id):
        """
        Test that dimensions is an integer value.

        Issue #19 Requirement:
        - dimensions must be a valid integer
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["dimensions"], int), "dimensions must be an integer"
        assert data["dimensions"] > 0, "dimensions must be positive"

    def test_dimensions_matches_default_model(self, client, auth_headers, test_project_id):
        """
        Test that dimensions matches default model (384).

        Issue #19 Requirement:
        - dimensions must accurately reflect the vector size
        - Default model produces 384 dimensions
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test with default model"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dimensions"] == 384, "Default model should produce 384 dimensions"

    def test_dimensions_matches_specified_model(self, client, auth_headers, test_project_id):
        """
        Test that dimensions matches specified model.

        Issue #19 Requirement:
        - dimensions must accurately match the model's output size
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test",
                "model": "sentence-transformers/all-mpnet-base-v2"  # 768 dimensions
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dimensions"] == 768, "all-mpnet-base-v2 should produce 768 dimensions"

    def test_dimensions_consistent_across_requests(self, client, auth_headers, test_project_id):
        """
        Test that dimensions are consistent across multiple requests.

        Issue #19 Requirement:
        - Behavior must be deterministic (same model = same dimensions)
        """
        response1 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "First request"
            },
            headers=auth_headers
        )

        response2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Second request"
            },
            headers=auth_headers
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["dimensions"] == data2["dimensions"], "Dimensions should be consistent"


class TestIssue19ProcessingTimeField:
    """Tests for processing_time_ms field (Issue #19 - included when available)."""

    def test_response_includes_processing_time(self, client, auth_headers, test_project_id):
        """
        Test that processing_time_ms is included in response.

        Issue #19 Requirement:
        - Include processing_time_ms when available
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "processing_time_ms" in data, "Response should include processing_time_ms"

    def test_processing_time_is_integer(self, client, auth_headers, test_project_id):
        """Test that processing_time_ms is an integer."""
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["processing_time_ms"], int), "processing_time_ms must be integer"
        assert data["processing_time_ms"] >= 0, "processing_time_ms must be non-negative"


class TestIssue19AllFieldsTogether:
    """Tests verifying all Issue #19 fields are present together."""

    def test_all_required_fields_present(self, client, auth_headers, test_project_id):
        """
        Test that all required Issue #19 fields are present in response.

        Issue #19 Requirement:
        - Response MUST include: vectors_stored, model, dimensions
        - SHOULD include: processing_time_ms
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Complete metadata test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # All required fields per Issue #19
        required_fields = ["vectors_stored", "model", "dimensions"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Recommended field
        assert "processing_time_ms" in data, "Should include processing_time_ms"

    def test_field_values_are_accurate(self, client, auth_headers, test_project_id):
        """
        Test that all field values are accurate and consistent.

        Issue #19 Requirement:
        - Calculate and return accurate counts and metadata
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Accuracy test",
                "model": "BAAI/bge-small-en-v1.5"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify accuracy
        assert data["vectors_stored"] == 1
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384
        assert data["processing_time_ms"] >= 0

    def test_field_types_are_correct(self, client, auth_headers, test_project_id):
        """
        Test that all fields have correct types.

        Issue #19 Requirement:
        - Ensure response format is consistent and documented
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Type validation test"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify types
        assert isinstance(data["vectors_stored"], int), "vectors_stored must be int"
        assert isinstance(data["model"], str), "model must be string"
        assert isinstance(data["dimensions"], int), "dimensions must be int"
        assert isinstance(data["processing_time_ms"], int), "processing_time_ms must be int"

    def test_response_format_is_deterministic(self, client, auth_headers, test_project_id):
        """
        Test that response format is deterministic across requests.

        Issue #19 Requirement:
        - Ensure response format is consistent (per DX Contract)
        """
        # Make multiple requests
        responses = []
        for i in range(3):
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "text": f"Request {i}"
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should have same field set
        field_sets = [set(r.keys()) for r in responses]
        assert all(fs == field_sets[0] for fs in field_sets), "Response format should be consistent"


class TestIssue19Documentation:
    """Tests for Issue #19 documentation requirements."""

    def test_response_schema_is_documented(self, client):
        """
        Test that response schema is properly documented in OpenAPI spec.

        Issue #19 Requirement:
        - Ensure response format is consistent and documented
        """
        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()

        # Find embed-and-store endpoint
        embed_store_path = None
        for path_key in openapi_spec.get("paths", {}).keys():
            if "embed-and-store" in path_key:
                embed_store_path = path_key
                break

        assert embed_store_path is not None, "embed-and-store endpoint should be in OpenAPI spec"

        # Check response schema
        endpoint = openapi_spec["paths"][embed_store_path]["post"]
        response_schema = endpoint.get("responses", {}).get("200", {})

        assert response_schema, "200 response should be documented"

    def test_example_response_includes_all_fields(self, client):
        """
        Test that example response includes all required fields.

        Issue #19 Requirement:
        - API documentation with response examples
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()

        # Get EmbedAndStoreResponse schema
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        embed_store_response = schemas.get("EmbedAndStoreResponse", {})

        if embed_store_response:
            example = embed_store_response.get("example", {})
            if example:
                # Check example has required fields
                assert "vectors_stored" in example, "Example should include vectors_stored"
                assert "model" in example, "Example should include model"
                assert "dimensions" in example, "Example should include dimensions"


class TestIssue19ErrorCases:
    """Tests for error handling with Issue #19 fields."""

    def test_invalid_model_still_returns_error_with_detail(self, client, auth_headers, test_project_id):
        """
        Test that invalid model returns proper error (doesn't break Issue #19 implementation).

        Issue #19 Requirement:
        - Error handling should not interfere with metadata fields
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "text": "Test",
                "model": "invalid-model"
            },
            headers=auth_headers
        )

        # Should get error, not success with metadata
        assert response.status_code == 404
        data = response.json()

        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"
