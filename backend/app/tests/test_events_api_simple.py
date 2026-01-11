"""
Simplified integration tests for Events API endpoints.

Tests GitHub Issue #38: Event creation API with validation.
Per Epic 8 (Events API) and PRD §10 (Replayability).
"""
import pytest


class TestCreateEventEndpoint:
    """Test POST /v1/public/database/events endpoint."""

    def test_create_event_success(self, client, auth_headers_user1):
        """Successfully create event with all fields."""
        payload = {
            "event_type": "agent_decision",
            "data": {
                "agent_id": "agent_001",
                "action": "approve",
                "confidence": 0.95
            },
            "timestamp": "2026-01-10T18:30:00Z"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        assert "event_id" in data
        assert data["event_type"] == "agent_decision"
        assert data["timestamp"] == "2026-01-10T18:30:00Z"
        assert data["status"] == "created"

    def test_create_event_without_timestamp(self, client, auth_headers_user1):
        """Create event without timestamp auto-generates it."""
        payload = {
            "event_type": "compliance_check",
            "data": {
                "subject": "user_123",
                "risk_score": 0.12
            }
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()
        assert "event_id" in data
        assert "timestamp" in data
        assert data["timestamp"] is not None
        # Verify timestamp is in ISO8601 format
        assert "T" in data["timestamp"]
        assert data["timestamp"].endswith("Z")

    def test_create_event_missing_event_type(self, client, auth_headers_user1):
        """Reject request missing event_type."""
        payload = {
            "data": {"test": "value"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_missing_data(self, client, auth_headers_user1):
        """Reject request missing data field."""
        payload = {
            "event_type": "test_event"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_invalid_timestamp(self, client, auth_headers_user1):
        """Reject invalid timestamp format."""
        payload = {
            "event_type": "test_event",
            "data": {"test": "value"},
            "timestamp": "invalid_timestamp"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "ISO8601" in str(data)

    def test_create_event_no_api_key(self, client):
        """Reject request without API key."""
        payload = {
            "event_type": "test_event",
            "data": {"test": "value"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload
        )

        assert response.status_code == 401

    def test_create_event_response_format_stable(self, client, auth_headers_user1):
        """Verify response format is stable per Epic 8 Story 4."""
        payload = {
            "event_type": "agent_decision",
            "data": {"agent_id": "agent_001"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == 201
        data = response.json()

        # Verify all required fields are present
        required_fields = ["event_id", "event_type", "timestamp", "status"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify status is always "created"
        assert data["status"] == "created"


class TestListEventsEndpoint:
    """Test GET /v1/public/database/events endpoint."""

    def test_list_events_success(self, client, auth_headers_user1):
        """Successfully list events."""
        response = client.get(
            "/v1/public/database/events",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["total"], int)

    def test_list_events_no_api_key(self, client):
        """Reject list request without API key."""
        response = client.get("/v1/public/database/events")
        assert response.status_code == 401


class TestReplayabilityScenario:
    """Test event creation supports workflow replay per PRD §10."""

    def test_events_with_explicit_timestamps_preserve_order(self, client, auth_headers_user1):
        """Events with explicit timestamps preserve chronological order."""
        # Create events in specific order
        events = [
            {
                "event_type": "agent_created",
                "data": {"agent_id": "agent_001", "role": "analyst"},
                "timestamp": "2026-01-10T18:00:00Z"
            },
            {
                "event_type": "agent_decision",
                "data": {"agent_id": "agent_001", "decision": "analyze"},
                "timestamp": "2026-01-10T18:01:00Z"
            },
            {
                "event_type": "agent_tool_call",
                "data": {"agent_id": "agent_001", "tool": "market_data"},
                "timestamp": "2026-01-10T18:02:00Z"
            }
        ]

        created_events = []
        for event in events:
            response = client.post(
                "/v1/public/database/events",
                json=event,
                headers=auth_headers_user1
            )
            assert response.status_code == 201
            created_events.append(response.json())

        # Verify timestamps are preserved
        for i, created in enumerate(created_events):
            assert created["timestamp"] == events[i]["timestamp"]
