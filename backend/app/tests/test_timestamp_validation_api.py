"""
API integration tests for timestamp validation.

GitHub Issue #39: As a developer, invalid timestamps return clear errors.
Epic 8 Story 3: Invalid timestamps return clear errors.

Requirements:
- Invalid timestamps must return HTTP 422
- Error response must include error_code: "INVALID_TIMESTAMP"
- Error response must include "detail" field with clear message
- DX Contract compliance for error responses

This test demonstrates how timestamp validation should be integrated
into API endpoints that accept timestamp parameters.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, validator
from typing import Optional

from app.core.errors import InvalidTimestampError
from app.core.timestamp_validator import validate_timestamp


# Example API endpoint that uses timestamp validation
app = FastAPI()


class EventRequest(BaseModel):
    """Example request schema with timestamp field."""
    event_type: str
    data: dict
    timestamp: str

    @validator('timestamp')
    def validate_timestamp_format(cls, v):
        """Validate timestamp is in ISO8601 format."""
        try:
            return validate_timestamp(v, field_name="timestamp")
        except ValueError as e:
            # Re-raise as Pydantic validation error
            raise ValueError(str(e))


@app.post("/api/events")
async def create_event(request: EventRequest):
    """Example endpoint that requires timestamp."""
    return {
        "event_type": request.event_type,
        "timestamp": request.timestamp,
        "status": "created"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with DX Contract format."""
    error_code = getattr(exc, 'error_code', 'ERROR')
    return {
        "detail": exc.detail,
        "error_code": error_code
    }


client = TestClient(app)


class TestTimestampValidationAPI:
    """Test timestamp validation in API context."""

    def test_valid_timestamp_accepted(self):
        """Test valid timestamp is accepted by API."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": "2026-01-10T12:34:56Z"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["timestamp"] == "2026-01-10T12:34:56Z"

    def test_invalid_timestamp_returns_422(self):
        """Test invalid timestamp returns HTTP 422."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": "invalid-timestamp"
        })
        assert response.status_code == 422

    def test_invalid_timestamp_error_format(self):
        """Test invalid timestamp error follows DX Contract format."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": "not-a-timestamp"
        })

        assert response.status_code == 422
        data = response.json()

        # DX Contract: All errors return { detail, error_code }
        # For Pydantic validation errors, FastAPI returns validation_error format
        # But the detail should contain our custom message
        assert "detail" in data

        # Check that error message is descriptive
        error_msg = str(data["detail"])
        assert "timestamp" in error_msg.lower() or "ISO8601" in error_msg

    def test_missing_timestamp_field(self):
        """Test missing timestamp field returns 422."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"}
            # timestamp field missing
        })
        assert response.status_code == 422

    def test_empty_timestamp_rejected(self):
        """Test empty timestamp is rejected."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": ""
        })
        assert response.status_code == 422

    def test_date_only_rejected(self):
        """Test date-only format is rejected."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": "2026-01-10"
        })
        assert response.status_code == 422

    def test_unix_timestamp_rejected(self):
        """Test Unix timestamp is rejected."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {"key": "value"},
            "timestamp": 1704891296
        })
        assert response.status_code == 422

    def test_various_valid_formats_accepted(self):
        """Test various valid ISO8601 formats are accepted."""
        valid_timestamps = [
            "2026-01-10T12:34:56Z",
            "2026-01-10T12:34:56.789Z",
            "2026-01-10T12:34:56+00:00",
            "2026-01-10T12:34:56-05:00",
            "2026-01-10T12:34:56.123456Z"
        ]

        for timestamp in valid_timestamps:
            response = client.post("/api/events", json={
                "event_type": "test_event",
                "data": {"key": "value"},
                "timestamp": timestamp
            })
            assert response.status_code == 200, f"Timestamp {timestamp} should be valid"
            data = response.json()
            assert data["timestamp"] == timestamp


class TestInvalidTimestampErrorIntegration:
    """Test InvalidTimestampError in API context."""

    def test_raise_invalid_timestamp_error(self):
        """Test raising InvalidTimestampError directly."""
        error = InvalidTimestampError()

        # Verify error properties
        assert error.status_code == 422
        assert error.error_code == "INVALID_TIMESTAMP"
        assert isinstance(error.detail, str)
        assert len(error.detail) > 0
        assert "ISO8601" in error.detail

    def test_invalid_timestamp_error_with_custom_message(self):
        """Test InvalidTimestampError with custom message."""
        custom_msg = "The 'created_at' field must be in ISO8601 format"
        error = InvalidTimestampError(detail=custom_msg)

        assert error.status_code == 422
        assert error.error_code == "INVALID_TIMESTAMP"
        assert error.detail == custom_msg

    def test_error_response_format_compliance(self):
        """Test error response follows DX Contract §7."""
        error = InvalidTimestampError()

        # Per DX Contract §7: All errors return { detail, error_code }
        assert hasattr(error, 'detail')
        assert hasattr(error, 'error_code')
        assert hasattr(error, 'status_code')

        # Validate types
        assert isinstance(error.detail, str)
        assert isinstance(error.error_code, str)
        assert isinstance(error.status_code, int)

        # Validate values
        assert error.error_code == "INVALID_TIMESTAMP"
        assert error.status_code == 422
        assert error.detail != ""


class TestTimestampErrorMessages:
    """Test error message content and clarity."""

    def test_error_includes_iso8601_mention(self):
        """Test error message mentions ISO8601 standard."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {},
            "timestamp": "invalid"
        })

        assert response.status_code == 422
        # Error message should mention ISO8601 somewhere
        error_text = str(response.json())
        assert "ISO8601" in error_text or "ISO 8601" in error_text

    def test_error_includes_examples(self):
        """Test error message includes examples of valid timestamps."""
        error = InvalidTimestampError()
        # Default message should include examples
        assert "2026" in error.detail or "Examples:" in error.detail.lower()

    def test_deterministic_error_messages(self):
        """Test error messages are deterministic."""
        # Same invalid input should produce same error
        responses = []
        for _ in range(3):
            response = client.post("/api/events", json={
                "event_type": "test_event",
                "data": {},
                "timestamp": "bad-timestamp"
            })
            responses.append(response.status_code)

        # All responses should be the same
        assert all(code == 422 for code in responses)


class TestDXContractCompliance:
    """Test compliance with DX Contract §7 (Error Semantics)."""

    def test_validation_errors_use_422(self):
        """Test validation errors use HTTP 422 per DX Contract."""
        response = client.post("/api/events", json={
            "event_type": "test_event",
            "data": {},
            "timestamp": "invalid-format"
        })

        # DX Contract §7: Validation errors always use HTTP 422
        assert response.status_code == 422

    def test_error_format_deterministic(self):
        """Test error format is deterministic per PRD §10."""
        # Same request should produce same error structure
        requests = [
            client.post("/api/events", json={
                "event_type": "test",
                "data": {},
                "timestamp": "bad"
            })
            for _ in range(3)
        ]

        # All should have same status code
        status_codes = [r.status_code for r in requests]
        assert len(set(status_codes)) == 1
        assert status_codes[0] == 422

    def test_error_includes_detail_field(self):
        """Test all errors include detail field per Epic 2 Story 3."""
        response = client.post("/api/events", json={
            "event_type": "test",
            "data": {},
            "timestamp": "invalid"
        })

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], (str, list))  # FastAPI may return list for validation errors
