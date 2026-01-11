"""
Integration tests for Events API endpoints.

Tests GitHub Issue #38: Event creation API with validation.
Per Epic 8 (Events API) and PRD §10 (Replayability).

Coverage:
- POST /v1/public/database/events
- GET /v1/public/database/events
- Authentication requirements
- Error handling
- Response format stability
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

    def test_create_event_without_timestamp(self):
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
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "event_id" in data
        assert "timestamp" in data
        assert data["timestamp"] is not None
        # Verify timestamp is in ISO8601 format
        assert "T" in data["timestamp"]
        assert data["timestamp"].endswith("Z")

    def test_create_event_with_nested_data(self):
        """Create event with nested data object."""
        payload = {
            "event_type": "transaction_executed",
            "data": {
                "transaction_id": "txn_123",
                "amount": 1000.00,
                "metadata": {
                    "compliance": {
                        "kyc_passed": True,
                        "aml_check": "cleared"
                    }
                }
            }
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        assert response.json()["event_type"] == "transaction_executed"

    def test_create_event_missing_event_type(self):
        """Reject request missing event_type."""
        payload = {
            "data": {"test": "value"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_missing_data(self):
        """Reject request missing data field."""
        payload = {
            "event_type": "test_event"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_empty_event_type(self):
        """Reject empty event_type."""
        payload = {
            "event_type": "",
            "data": {"test": "value"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_event_type_too_long(self):
        """Reject event_type exceeding 100 characters."""
        payload = {
            "event_type": "a" * 101,
            "data": {"test": "value"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_event_invalid_timestamp_format(self):
        """Reject invalid timestamp format."""
        invalid_timestamps = [
            "2026-01-10",  # Date only
            "18:30:00",  # Time only
            "01/10/2026 18:30:00",  # US format
            "not a timestamp",
        ]

        for invalid_ts in invalid_timestamps:
            payload = {
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": invalid_ts
            }

            response = client.post(
                "/v1/public/database/events",
                json=payload,
                headers={"X-API-Key": "test_api_key"}
            )

            assert response.status_code == 422
            data = response.json()
            assert "detail" in data
            assert "ISO8601" in str(data)

    def test_create_event_data_not_object(self):
        """Reject data that is not a JSON object."""
        # Test with array
        payload = {
            "event_type": "test_event",
            "data": ["not", "an", "object"]
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422

        # Test with string
        payload = {
            "event_type": "test_event",
            "data": "not an object"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 422

    def test_create_event_no_api_key(self):
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

    def test_create_event_response_format_stable(self):
        """Verify response format is stable per Epic 8 Story 4."""
        payload = {
            "event_type": "agent_decision",
            "data": {"agent_id": "agent_001"}
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify all required fields are present
        required_fields = ["event_id", "event_type", "timestamp", "status"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify status is always "created"
        assert data["status"] == "created"

    def test_create_event_with_various_iso8601_formats(self):
        """Accept various valid ISO8601 timestamp formats."""
        valid_timestamps = [
            "2026-01-10T18:30:00Z",
            "2026-01-10T18:30:00.123Z",
            "2026-01-10T18:30:00+00:00",
            "2026-01-10T18:30:00-05:00",
        ]

        for timestamp in valid_timestamps:
            payload = {
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": timestamp
            }

            response = client.post(
                "/v1/public/database/events",
                json=payload,
                headers={"X-API-Key": "test_api_key"}
            )

            assert response.status_code == 201
            assert response.json()["timestamp"] == timestamp


class TestListEventsEndpoint:
    """Test GET /v1/public/database/events endpoint."""

    def test_list_events_success(self):
        """Successfully list events."""
        response = client.get(
            "/v1/public/database/events",
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["total"], int)

    def test_list_events_with_filters(self):
        """List events with query parameters."""
        response = client.get(
            "/v1/public/database/events?event_type=agent_decision&limit=10&offset=0",
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_list_events_no_api_key(self):
        """Reject list request without API key."""
        response = client.get("/v1/public/database/events")
        assert response.status_code == 401


class TestAgentLifecycleEvents:
    """Test agent lifecycle event creation."""

    def test_create_agent_decision_event(self):
        """Create agent_decision event."""
        payload = {
            "event_type": "agent_decision",
            "data": {
                "agent_id": "agent_analyst_001",
                "decision": "approve_transaction",
                "amount": 1000.00,
                "confidence": 0.95
            }
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "agent_decision"

    def test_create_agent_tool_call_event(self):
        """Create agent_tool_call event."""
        payload = {
            "event_type": "agent_tool_call",
            "data": {
                "agent_id": "agent_transaction_001",
                "tool_name": "x402.request",
                "tool_args": {
                    "did": "did:example:123",
                    "payload": {"amount": 500}
                },
                "result": "success"
            }
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "agent_tool_call"


class TestReplayabilityScenario:
    """Test event creation supports workflow replay per PRD §10."""

    def test_events_with_explicit_timestamps_preserve_order(self):
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
                headers={"X-API-Key": "test_api_key"}
            )
            assert response.status_code == 201
            created_events.append(response.json())

        # Verify timestamps are preserved
        for i, created in enumerate(created_events):
            assert created["timestamp"] == events[i]["timestamp"]

    def test_compliance_event_with_full_metadata(self):
        """Create compliance event with complete audit trail."""
        payload = {
            "event_type": "compliance_check",
            "data": {
                "subject": "user_12345",
                "agent_id": "agent_compliance_001",
                "checks": {
                    "kyc": {"status": "passed", "provider": "jumio"},
                    "aml": {"status": "passed", "risk_score": 0.05},
                    "sanctions": {"status": "clear", "lists_checked": 5}
                },
                "overall_result": "approved",
                "reviewer": "system",
                "metadata": {
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0"
                }
            },
            "timestamp": "2026-01-10T18:30:00Z"
        }

        response = client.post(
            "/v1/public/database/events",
            json=payload,
            headers={"X-API-Key": "test_api_key"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "compliance_check"
        assert "event_id" in data
