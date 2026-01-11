"""
Comprehensive tests for Events API.

Tests event creation, validation, and error handling.
Per PRD §6 (ZeroDB Integration - Audit Trail) and §10 (Success Criteria - Replayability).
"""
import json
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestEventCreation:
    """Test event creation with various scenarios."""

    def test_create_event_with_all_fields(self):
        """Test creating an event with all fields specified."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "analyst-001",
                    "decision": "approve_transaction",
                    "confidence": 0.95,
                    "reasoning": "All compliance checks passed"
                },
                "timestamp": "2025-01-11T22:00:00Z"
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "event_type" in data
        assert "data" in data
        assert "timestamp" in data
        assert "created_at" in data

        # Verify UUID format
        assert UUID(data["id"])

        # Verify field values
        assert data["event_type"] == "agent_decision"
        assert data["data"]["agent_id"] == "analyst-001"
        assert data["data"]["decision"] == "approve_transaction"
        assert data["data"]["confidence"] == 0.95
        assert data["timestamp"] == "2025-01-11T22:00:00Z"

        # Verify created_at is a valid ISO8601 timestamp
        assert datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))

    def test_create_event_without_timestamp(self):
        """Test creating an event without timestamp (should default to current time)."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "agent_tool_call",
                "data": {
                    "agent_id": "transaction-agent",
                    "tool_name": "x402.request",
                    "result": "success"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify timestamp was auto-generated
        assert "timestamp" in data
        assert data["timestamp"] is not None

        # Verify timestamp is valid ISO8601
        assert datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

    def test_create_compliance_check_event(self):
        """Test creating a compliance check event."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "compliance_check",
                "data": {
                    "subject": "user-12345",
                    "check_type": "kyc",
                    "status": "passed",
                    "risk_score": 0.15
                },
                "timestamp": "2025-01-11T15:30:00Z"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["event_type"] == "compliance_check"
        assert data["data"]["subject"] == "user-12345"
        assert data["data"]["check_type"] == "kyc"
        assert data["data"]["status"] == "passed"
        assert data["data"]["risk_score"] == 0.15

    def test_create_x402_request_event(self):
        """Test creating an X402 request tracking event."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "x402_request",
                "data": {
                    "did": "did:example:123",
                    "signature": "0x1234abcd",
                    "payload": {"action": "transfer", "amount": 1000},
                    "verified": True
                },
                "timestamp": "2025-01-11T16:00:00Z"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["event_type"] == "x402_request"
        assert data["data"]["did"] == "did:example:123"
        assert data["data"]["verified"] is True

    def test_create_custom_event_type(self):
        """Test creating a custom event type."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "portfolio_rebalance",
                "data": {
                    "portfolio_id": "port-456",
                    "old_allocation": {"btc": 0.5, "eth": 0.3, "usdc": 0.2},
                    "new_allocation": {"btc": 0.4, "eth": 0.4, "usdc": 0.2},
                    "reason": "market_conditions"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["event_type"] == "portfolio_rebalance"
        assert data["data"]["portfolio_id"] == "port-456"

    def test_create_event_with_nested_data(self):
        """Test creating an event with deeply nested data structures."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "analyst-002",
                    "decision": {
                        "action": "approve",
                        "conditions": ["kyc_passed", "amount_within_limits"],
                        "metadata": {
                            "confidence": 0.92,
                            "model_version": "v2.3.1",
                            "features_used": ["transaction_history", "risk_profile"]
                        }
                    }
                }
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["data"]["decision"]["action"] == "approve"
        assert len(data["data"]["decision"]["conditions"]) == 2
        assert data["data"]["decision"]["metadata"]["confidence"] == 0.92


class TestEventValidation:
    """Test event validation and error handling."""

    def test_missing_event_type(self):
        """Test that missing event_type returns validation error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_missing_data_field(self):
        """Test that missing data field returns validation error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event"
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_empty_event_type(self):
        """Test that empty event_type returns validation error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "",
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 422

    def test_event_type_too_long(self):
        """Test that event_type exceeding max length returns validation error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "a" * 256,  # Exceeds max length of 255
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 422


class TestTimestampValidation:
    """Test timestamp validation and error handling."""

    def test_valid_iso8601_with_z(self):
        """Test that valid ISO8601 timestamp with Z suffix is accepted."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-01-11T22:00:00Z"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["timestamp"] == "2025-01-11T22:00:00Z"

    def test_valid_iso8601_with_timezone(self):
        """Test that valid ISO8601 timestamp with timezone offset is accepted."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-01-11T22:00:00+00:00"
            }
        )

        assert response.status_code == 201

    def test_valid_iso8601_without_timezone(self):
        """Test that valid ISO8601 timestamp without timezone is accepted."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-01-11T22:00:00"
            }
        )

        assert response.status_code == 201

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format returns clear error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-01-11 22:00:00"  # Missing T separator
            }
        )

        assert response.status_code == 422
        data = response.json()

        # Verify error structure per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_TIMESTAMP"

        # Verify error message is helpful
        assert "Invalid timestamp" in data["detail"]
        assert "ISO8601" in data["detail"]

    def test_invalid_month_in_timestamp(self):
        """Test that invalid month returns clear error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-13-01T22:00:00Z"  # Month 13 is invalid
            }
        )

        assert response.status_code == 422
        data = response.json()

        assert data["error_code"] == "INVALID_TIMESTAMP"
        assert "Invalid timestamp" in data["detail"]

    def test_invalid_day_in_timestamp(self):
        """Test that invalid day returns clear error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "2025-01-32T22:00:00Z"  # Day 32 is invalid
            }
        )

        assert response.status_code == 422
        data = response.json()

        assert data["error_code"] == "INVALID_TIMESTAMP"

    def test_completely_invalid_timestamp(self):
        """Test that completely invalid timestamp returns clear error."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"},
                "timestamp": "not-a-timestamp"
            }
        )

        assert response.status_code == 422
        data = response.json()

        assert data["error_code"] == "INVALID_TIMESTAMP"
        assert "Invalid timestamp" in data["detail"]


class TestAuthentication:
    """Test API key authentication for events endpoint."""

    def test_missing_api_key(self):
        """Test that missing API key returns 401."""
        response = client.post(
            "/v1/public/database/events",
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 401
        data = response.json()

        # Verify error structure per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_empty_api_key(self):
        """Test that empty API key returns 401."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": ""},
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 401
        data = response.json()

        assert data["error_code"] == "INVALID_API_KEY"

    def test_whitespace_api_key(self):
        """Test that whitespace-only API key returns 401."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "   "},
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 401
        data = response.json()

        assert data["error_code"] == "INVALID_API_KEY"


class TestEndpointPrefix:
    """Test that endpoint requires /database/ prefix per DX Contract."""

    def test_correct_prefix_works(self):
        """Test that /database/events works correctly."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
        )

        assert response.status_code == 201

    def test_missing_database_prefix_returns_404(self):
        """Test that /events without /database/ prefix returns 404."""
        response = client.post(
            "/v1/public/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": {"test": "value"}
            }
        )

        # Per DX Contract: Missing /database/ prefix returns 404
        assert response.status_code == 404


class TestAuditTrailUseCases:
    """Test real-world audit trail and replayability scenarios."""

    def test_agent_workflow_sequence(self):
        """Test recording a sequence of agent events for workflow replay."""
        # Event 1: Agent decision
        response1 = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "workflow-test-key"},
            json={
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "analyst-001",
                    "run_id": "run-12345",
                    "decision": "initiate_compliance_check",
                    "timestamp": "2025-01-11T10:00:00Z"
                }
            }
        )
        assert response1.status_code == 201
        event1 = response1.json()

        # Event 2: Compliance check
        response2 = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "workflow-test-key"},
            json={
                "event_type": "compliance_check",
                "data": {
                    "agent_id": "compliance-agent",
                    "run_id": "run-12345",
                    "check_type": "kyc",
                    "status": "passed",
                    "timestamp": "2025-01-11T10:01:00Z"
                }
            }
        )
        assert response2.status_code == 201
        event2 = response2.json()

        # Event 3: Transaction execution
        response3 = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "workflow-test-key"},
            json={
                "event_type": "agent_tool_call",
                "data": {
                    "agent_id": "transaction-agent",
                    "run_id": "run-12345",
                    "tool_name": "x402.request",
                    "result": "success",
                    "timestamp": "2025-01-11T10:02:00Z"
                }
            }
        )
        assert response3.status_code == 201
        event3 = response3.json()

        # Verify all events were created with unique IDs
        assert event1["id"] != event2["id"] != event3["id"]

        # Verify all events have the same run_id for replay
        assert event1["data"]["run_id"] == "run-12345"
        assert event2["data"]["run_id"] == "run-12345"
        assert event3["data"]["run_id"] == "run-12345"

    def test_compliance_audit_scenario(self):
        """Test recording events for compliance audit requirements."""
        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "compliance-test-key"},
            json={
                "event_type": "compliance_check",
                "data": {
                    "subject": "transaction-tx-999",
                    "check_type": "kyt",
                    "status": "flagged",
                    "risk_score": 0.85,
                    "reason": "high_value_transaction",
                    "reviewer": "compliance-agent-002",
                    "timestamp": "2025-01-11T14:30:00Z"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify audit trail contains all necessary information
        assert data["event_type"] == "compliance_check"
        assert data["data"]["status"] == "flagged"
        assert data["data"]["risk_score"] == 0.85
        assert data["data"]["reviewer"] == "compliance-agent-002"

        # Verify timestamps for audit trail
        assert "timestamp" in data
        assert "created_at" in data


class TestDataIntegrity:
    """Test data integrity and immutability of events."""

    def test_event_id_is_unique(self):
        """Test that each event gets a unique ID."""
        events = []

        for i in range(5):
            response = client.post(
                "/v1/public/database/events",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "event_type": "test_event",
                    "data": {"iteration": i}
                }
            )
            assert response.status_code == 201
            events.append(response.json())

        # Verify all IDs are unique
        ids = [event["id"] for event in events]
        assert len(ids) == len(set(ids))

    def test_event_preserves_data_structure(self):
        """Test that complex data structures are preserved exactly."""
        original_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null_value": None,
            "array": [1, 2, 3],
            "nested_object": {
                "key1": "value1",
                "key2": {
                    "deep_key": "deep_value"
                }
            }
        }

        response = client.post(
            "/v1/public/database/events",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event_type": "test_event",
                "data": original_data
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Verify data structure is preserved exactly
        assert data["data"] == original_data
