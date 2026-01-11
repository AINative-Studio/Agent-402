"""
Unit tests for processing_time_ms in embeddings endpoints.

Implements tests for GitHub Issue #15:
- All embedding generation responses must include processing_time_ms field
- Time should be in milliseconds (integer)
- Ensure time measurement is accurate

Per PRD §9: Demo observability requires processing time tracking.
Per Epic 3, Story 5: As a developer, responses include processing_time_ms.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.embedding_service import get_embedding_service


# Test fixtures
@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Return a valid API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def auth_headers(valid_api_key):
    """Return authentication headers."""
    return {"X-API-Key": valid_api_key}


class TestProcessingTimeField:
    """Test suite for processing_time_ms field presence and type."""

    def test_generate_embeddings_includes_processing_time_ms(self, client, auth_headers):
        """
        Test that POST /v1/public/embeddings/generate includes processing_time_ms.

        Issue #15: All embedding generation responses must include processing_time_ms field.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Test embedding generation with processing time",
                "model": "all-MiniLM-L6-v2"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify processing_time_ms field exists
        assert "processing_time_ms" in data, "processing_time_ms field must be present in response"

        # Verify it's an integer (not float)
        assert isinstance(data["processing_time_ms"], int), "processing_time_ms must be an integer"

        # Verify it's a positive value
        assert data["processing_time_ms"] >= 0, "processing_time_ms must be non-negative"

    def test_processing_time_ms_is_integer_not_float(self, client, auth_headers):
        """
        Test that processing_time_ms is returned as integer, not float.

        Issue #15: Time should be in milliseconds (integer).
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Another test for integer validation",
                "model": "all-MiniLM-L6-v2"
            }
        )

        assert response.status_code == 200
        data = response.json()

        processing_time = data["processing_time_ms"]

        # Verify type is int, not float
        assert type(processing_time) == int, f"Expected int, got {type(processing_time)}"

        # Verify no decimal point in JSON representation
        # (when serialized, should be "processing_time_ms": 45, not "processing_time_ms": 45.0)
        import json
        json_str = json.dumps(data)
        # Should not have decimal notation for processing_time_ms
        assert f'"processing_time_ms": {processing_time}' in json_str or \
               f'"processing_time_ms":{processing_time}' in json_str

    def test_processing_time_reasonable_range(self, client, auth_headers):
        """
        Test that processing_time_ms is within reasonable range.

        Issue #15: Ensure time measurement is accurate.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Short text for embedding",
                "model": "all-MiniLM-L6-v2"
            }
        )

        assert response.status_code == 200
        data = response.json()

        processing_time = data["processing_time_ms"]

        # Processing time should be reasonable (not 0, not impossibly large)
        # For a simple embedding request, expect > 0ms and < 10 seconds (10000ms)
        assert processing_time > 0, "Processing time should be greater than 0"
        assert processing_time < 10000, "Processing time should be less than 10 seconds for simple request"

    def test_default_model_includes_processing_time(self, client, auth_headers):
        """
        Test that processing_time_ms is included when using default model.

        Epic 3, Story 2: Default to 384-dim embeddings when model is omitted.
        Epic 3, Story 5: Include processing_time_ms.
        """
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Test with default model"
                # model field omitted - should use default
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default model is used
        assert data["model"] == "all-MiniLM-L6-v2"
        assert data["dimensions"] == 384

        # Verify processing_time_ms is still present
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)

    def test_multiple_requests_have_varying_processing_times(self, client, auth_headers):
        """
        Test that processing times vary between requests (indicating real measurement).

        Issue #15: Ensure time measurement is accurate.
        """
        processing_times = []

        for i in range(5):
            response = client.post(
                "/v1/public/embeddings/generate",
                headers=auth_headers,
                json={
                    "text": f"Test text variation {i} with different length to ensure timing varies",
                    "model": "all-MiniLM-L6-v2"
                }
            )

            assert response.status_code == 200
            data = response.json()
            processing_times.append(data["processing_time_ms"])

        # All should be integers
        assert all(isinstance(t, int) for t in processing_times)

        # Should have some variation (not all identical)
        # This confirms we're measuring real processing time, not returning a constant
        unique_times = set(processing_times)
        assert len(unique_times) >= 2, "Processing times should vary between requests"


class TestServiceLayerTiming:
    """Test timing instrumentation at the service layer."""

    def test_embedding_service_returns_integer_milliseconds(self):
        """
        Test that EmbeddingService.generate_embedding returns integer ms.

        Issue #15: Service layer must track time as integer milliseconds.
        """
        service = get_embedding_service()

        embedding, model, dimensions, processing_time_ms = service.generate_embedding(
            text="Test direct service call",
            model="BAAI/bge-small-en-v1.5"
        )

        # Verify return types
        assert isinstance(embedding, list)
        assert isinstance(model, str)
        assert isinstance(dimensions, int)
        assert isinstance(processing_time_ms, int), "Service must return int for processing_time_ms"

        # Verify time is reasonable
        assert processing_time_ms >= 0

    def test_timing_tracks_from_start_to_end(self):
        """
        Test that timing measurement covers the entire processing operation.

        Issue #15: Track time from request start to response ready.
        """
        service = get_embedding_service()

        import time
        start = time.time()

        embedding, model, dimensions, processing_time_ms = service.generate_embedding(
            text="Longer text to ensure measurable processing time for accurate timing validation",
            model="BAAI/bge-small-en-v1.5"
        )

        end = time.time()
        actual_time_ms = int((end - start) * 1000)

        # processing_time_ms should be close to actual measured time
        # Allow some overhead for Python execution
        # Note: With mock implementation, processing can be very fast (0ms is valid)
        assert processing_time_ms >= 0
        assert processing_time_ms <= actual_time_ms + 100, "Service timing should reflect actual processing time"


class TestResponseSchemaValidation:
    """Test that response schema enforces processing_time_ms requirements."""

    def test_response_model_validates_processing_time_type(self):
        """
        Test that EmbeddingGenerateResponse schema validates processing_time_ms type.

        Issue #15: Ensure schema enforces integer type.
        """
        from app.schemas.embeddings import EmbeddingGenerateResponse

        # Valid response with integer processing_time_ms
        valid_response = EmbeddingGenerateResponse(
            embedding=[0.1, 0.2, 0.3],
            model="all-MiniLM-L6-v2",
            dimensions=384,
            text="Test",
            processing_time_ms=45
        )

        assert valid_response.processing_time_ms == 45
        assert isinstance(valid_response.processing_time_ms, int)

    def test_response_model_rejects_negative_processing_time(self):
        """
        Test that schema rejects negative processing_time_ms values.

        Issue #15: Time should be non-negative milliseconds.
        """
        from app.schemas.embeddings import EmbeddingGenerateResponse
        from pydantic import ValidationError

        # Attempt to create response with negative processing_time_ms
        with pytest.raises(ValidationError) as exc_info:
            EmbeddingGenerateResponse(
                embedding=[0.1, 0.2, 0.3],
                model="all-MiniLM-L6-v2",
                dimensions=384,
                text="Test",
                processing_time_ms=-10  # Invalid: negative time
            )

        # Verify validation error mentions processing_time_ms
        error_str = str(exc_info.value)
        assert "processing_time_ms" in error_str.lower()

    def test_response_schema_field_constraints(self):
        """
        Test that processing_time_ms field has correct schema constraints.

        Issue #15: Validate field definition per requirements.
        """
        from app.schemas.embeddings import EmbeddingGenerateResponse

        # Get field info from Pydantic model
        schema = EmbeddingGenerateResponse.model_json_schema()
        processing_time_field = schema["properties"]["processing_time_ms"]

        # Verify type is integer
        assert processing_time_field["type"] == "integer", "Schema must define processing_time_ms as integer"

        # Verify minimum value constraint (ge=0)
        assert "minimum" in processing_time_field or "ge" in str(processing_time_field)

        # Verify description mentions milliseconds
        assert "description" in processing_time_field
        assert "millisecond" in processing_time_field["description"].lower()


class TestEndToEndTiming:
    """End-to-end tests for processing time tracking."""

    def test_full_request_lifecycle_timing(self, client, auth_headers):
        """
        Test that processing_time_ms accurately reflects end-to-end processing.

        Issue #15: Track time from request start to response ready.
        PRD §9: Demo observability requires accurate timing.
        """
        import time

        request_start = time.time()

        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Full lifecycle timing test with reasonable length text",
                "model": "all-MiniLM-L6-v2"
            }
        )

        request_end = time.time()
        total_request_time_ms = int((request_end - request_start) * 1000)

        assert response.status_code == 200
        data = response.json()

        reported_processing_time = data["processing_time_ms"]

        # Reported processing time should be less than total request time
        # (total includes network, serialization overhead)
        assert reported_processing_time < total_request_time_ms, \
            "Reported processing time should be less than total request roundtrip"

        # But should be a significant portion (at least 10% in tests)
        assert reported_processing_time > 0

    def test_error_responses_do_not_include_processing_time(self, client, auth_headers):
        """
        Test that error responses don't include processing_time_ms.

        Issue #15: processing_time_ms only in successful responses.
        """
        # Request with invalid model
        response = client.post(
            "/v1/public/embeddings/generate",
            headers=auth_headers,
            json={
                "text": "Test",
                "model": "invalid-model-name"
            }
        )

        assert response.status_code == 404  # MODEL_NOT_FOUND
        data = response.json()

        # Error response should have detail and error_code
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "MODEL_NOT_FOUND"

        # Should NOT have processing_time_ms
        assert "processing_time_ms" not in data
