"""
Tests for GitHub Issue #40: Stable response format for event writes.

Requirements:
- All successful event writes return consistent response format
- Response must include: id, event_type, data, timestamp, created_at
- HTTP 201 (Created) status for successful writes
- Response format must be stable per DX Contract
- Follow PRD §9 for demo clarity

Test Coverage:
- Response format consistency
- Field presence validation
- Field order stability
- Timestamp normalization
- HTTP 201 status code
- Error handling
"""
import pytest
from datetime import datetime, timezone

# Test constants
PROJECT_ID = "test_project_123"
BASE_URL = f"/v1/public/{PROJECT_ID}/database/events"


class TestStableResponseFormat:
    """Test suite for Issue #40: Stable response format."""

    def test_successful_event_write_returns_http_201(self, client, auth_headers_user1):
        """Test that successful event writes return HTTP 201 (Created)."""
        response = client.post(
            BASE_URL,
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "agent_001",
                    "decision": "approve"
                }
            },
            headers=auth_headers_user1
        )

        assert response.status_code == 201, \
            f"Expected 201, got {response.status_code}: {response.text}"

    def test_response_contains_all_required_fields(self, client, auth_headers_user1):
        """Test that response contains all required fields."""
        response = client.post(
            BASE_URL,
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "agent_001",
                    "decision": "approve"
                }
            },
            headers=auth_headers_user1
        )

        data = response.json()

        # All required fields must be present
        required_fields = ["id", "event_type", "data", "timestamp", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_response_field_order_is_stable(self, client, auth_headers_user1):
        """Test that response fields are always in the same order."""
        response = client.post(
            BASE_URL,
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "agent_001",
                    "decision": "approve"
                }
            },
            headers=auth_headers_user1
        )

        data = response.json()
        field_names = list(data.keys())

        # Fields must be in this exact order per Issue #40
        expected_order = ["id", "event_type", "data", "timestamp", "created_at"]
        assert field_names == expected_order, \
            f"Field order mismatch. Expected {expected_order}, got {field_names}"

    def test_id_field_format(self, client, auth_headers_user1):
        """Test that id field is a UUID string with evt_ prefix."""
        response = client.post(
            BASE_URL,
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            },
            headers=auth_headers_user1
        )

        data = response.json()
        event_id = data["id"]

        # ID should start with evt_
        assert event_id.startswith("evt_"), \
            f"ID should start with 'evt_', got: {event_id}"

        # ID should be a reasonable length (evt_ + 16 hex chars)
        assert len(event_id) == 20, \
            f"ID should be 20 characters (evt_ + 16 hex), got {len(event_id)}"

    def test_event_type_echoed_from_request(self, client, auth_headers_user1):
        """Test that event_type is echoed from request."""
        event_type = "custom_event_type"

        response = client.post(
            BASE_URL,
            json={
                "event_type": event_type,
                "data": {"test": "value"}
            },
            headers=auth_headers_user1
        )

        data = response.json()
        assert data["event_type"] == event_type, \
            f"Expected event_type '{event_type}', got '{data['event_type']}'"

    def test_missing_api_key_returns_401(self, client):
        """Test that missing API key returns 401 unauthorized."""
        response = client.post(
            BASE_URL,
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
            # No X-API-Key header
        )

        assert response.status_code == 401, \
            f"Expected 401 for missing API key, got {response.status_code}"
