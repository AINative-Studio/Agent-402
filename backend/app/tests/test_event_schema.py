"""
Comprehensive tests for Event Schema Validation.

Tests GitHub Issue #38: Event schema validation with event_type, data, timestamp.
Per PRD §10 (Replayability) and Epic 8 (Events API).

Coverage:
- event_type validation: required, non-empty, max length
- data validation: required, must be JSON object
- timestamp validation: optional, ISO8601 format, auto-generation
- Agent lifecycle events validation
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.schemas.event import (
    EventCreateRequest,
    EventResponse,
    AgentLifecycleEvent
)


class TestEventTypeValidation:
    """Test event_type field validation."""

    def test_event_type_required(self):
        """event_type is required field."""
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                data={"test": "value"}
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('event_type',)
        assert errors[0]['type'] == 'missing'

    def test_event_type_valid(self):
        """event_type accepts valid string."""
        event = EventCreateRequest(
            event_type="agent_decision",
            data={"agent_id": "agent_001"}
        )
        assert event.event_type == "agent_decision"

    def test_event_type_empty_string_fails(self):
        """event_type cannot be empty string."""
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type="",
                data={"test": "value"}
            )

        errors = exc_info.value.errors()
        assert any('at least 1 character' in str(e) for e in errors)

    def test_event_type_whitespace_only_fails(self):
        """event_type cannot be whitespace-only."""
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type="   ",
                data={"test": "value"}
            )

        errors = exc_info.value.errors()
        # After stripping, becomes empty which violates min_length or custom validation
        assert len(errors) > 0

    def test_event_type_max_length(self):
        """event_type enforces max length of 100 characters."""
        # Valid: exactly 100 characters
        valid_type = "a" * 100
        event = EventCreateRequest(
            event_type=valid_type,
            data={"test": "value"}
        )
        assert len(event.event_type) == 100

        # Invalid: 101 characters
        invalid_type = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type=invalid_type,
                data={"test": "value"}
            )

        errors = exc_info.value.errors()
        assert any('at most 100 characters' in str(e) for e in errors)

    def test_event_type_strips_whitespace(self):
        """event_type strips leading/trailing whitespace."""
        event = EventCreateRequest(
            event_type="  agent_decision  ",
            data={"test": "value"}
        )
        assert event.event_type == "agent_decision"

    def test_event_type_special_characters(self):
        """event_type accepts special characters like underscores."""
        event = EventCreateRequest(
            event_type="agent_tool_call",
            data={"test": "value"}
        )
        assert event.event_type == "agent_tool_call"


class TestDataValidation:
    """Test data field validation."""

    def test_data_required(self):
        """data is required field."""
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type="test_event"
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('data',)
        assert errors[0]['type'] == 'missing'

    def test_data_valid_object(self):
        """data accepts valid JSON object."""
        data = {
            "agent_id": "agent_001",
            "action": "approve",
            "confidence": 0.95
        }
        event = EventCreateRequest(
            event_type="test_event",
            data=data
        )
        assert event.data == data

    def test_data_nested_object(self):
        """data supports nested JSON objects."""
        data = {
            "agent_id": "agent_001",
            "metadata": {
                "risk_score": 0.12,
                "compliance": {
                    "kyc_passed": True,
                    "aml_check": "passed"
                }
            }
        }
        event = EventCreateRequest(
            event_type="test_event",
            data=data
        )
        assert event.data == data
        assert event.data["metadata"]["compliance"]["kyc_passed"] is True

    def test_data_empty_object(self):
        """data accepts empty object."""
        event = EventCreateRequest(
            event_type="test_event",
            data={}
        )
        assert event.data == {}

    def test_data_various_types(self):
        """data supports various JSON-compatible types."""
        data = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }
        event = EventCreateRequest(
            event_type="test_event",
            data=data
        )
        assert event.data == data

    def test_data_must_be_dict(self):
        """data must be a dictionary/object, not other types."""
        # Test with array
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type="test_event",
                data=["not", "an", "object"]  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any('dict' in str(e).lower() for e in errors)

        # Test with string
        with pytest.raises(ValidationError) as exc_info:
            EventCreateRequest(
                event_type="test_event",
                data="not an object"  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any('dict' in str(e).lower() for e in errors)


class TestTimestampValidation:
    """Test timestamp field validation."""

    def test_timestamp_optional(self):
        """timestamp is optional field."""
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"}
        )
        assert event.timestamp is None

    def test_timestamp_valid_iso8601_z(self):
        """timestamp accepts valid ISO8601 format with Z suffix."""
        timestamp = "2026-01-10T18:30:00Z"
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp

    def test_timestamp_valid_iso8601_milliseconds(self):
        """timestamp accepts ISO8601 with milliseconds."""
        timestamp = "2026-01-10T18:30:00.123Z"
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp

    def test_timestamp_valid_iso8601_timezone_offset(self):
        """timestamp accepts ISO8601 with timezone offset."""
        timestamp = "2026-01-10T18:30:00+00:00"
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp

    def test_timestamp_valid_iso8601_negative_offset(self):
        """timestamp accepts ISO8601 with negative timezone offset."""
        timestamp = "2026-01-10T18:30:00-05:00"
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp

    def test_timestamp_invalid_format_fails(self):
        """timestamp rejects invalid formats."""
        invalid_timestamps = [
            "2026-01-10",  # Date only
            "18:30:00",  # Time only
            "01/10/2026 18:30:00",  # US format
            "not a timestamp",  # Random string
            "2026-13-01T18:30:00Z",  # Invalid month
            "2026-01-32T18:30:00Z",  # Invalid day
        ]

        for invalid_ts in invalid_timestamps:
            with pytest.raises(ValidationError) as exc_info:
                EventCreateRequest(
                    event_type="test_event",
                    data={"test": "value"},
                    timestamp=invalid_ts
                )

            errors = exc_info.value.errors()
            assert len(errors) > 0
            assert any('ISO8601' in str(e) for e in errors)

    def test_timestamp_empty_string_treated_as_none(self):
        """timestamp empty string is treated as None."""
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=""
        )
        assert event.timestamp is None

    def test_timestamp_whitespace_treated_as_none(self):
        """timestamp whitespace-only string is treated as None."""
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp="   "
        )
        assert event.timestamp is None


class TestEventResponseSchema:
    """Test EventResponse schema."""

    def test_event_response_creation(self):
        """EventResponse creates successfully with required fields."""
        response = EventResponse(
            event_id="evt_abc123",
            event_type="agent_decision",
            timestamp="2026-01-10T18:30:00Z",
            status="created"
        )
        assert response.event_id == "evt_abc123"
        assert response.event_type == "agent_decision"
        assert response.timestamp == "2026-01-10T18:30:00Z"
        assert response.status == "created"

    def test_event_response_default_status(self):
        """EventResponse uses default status 'created'."""
        response = EventResponse(
            event_id="evt_abc123",
            event_type="agent_decision",
            timestamp="2026-01-10T18:30:00Z"
        )
        assert response.status == "created"


class TestAgentLifecycleEvents:
    """Test AgentLifecycleEvent schema validation."""

    def test_agent_lifecycle_valid_event_types(self):
        """AgentLifecycleEvent accepts valid agent event types."""
        valid_types = [
            "agent_decision",
            "agent_tool_call",
            "agent_error",
            "agent_created",
            "agent_terminated"
        ]

        for event_type in valid_types:
            event = AgentLifecycleEvent(
                event_type=event_type,
                data={"agent_id": "agent_001"}
            )
            assert event.event_type == event_type

    def test_agent_lifecycle_invalid_event_type(self):
        """AgentLifecycleEvent rejects non-agent event types."""
        invalid_types = [
            "compliance_check",  # Not an agent lifecycle event
            "user_login",
            "agent_unknown",  # Not in allowed list
        ]

        for event_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                AgentLifecycleEvent(
                    event_type=event_type,
                    data={"agent_id": "agent_001"}
                )

            errors = exc_info.value.errors()
            assert len(errors) > 0

    def test_agent_lifecycle_requires_agent_id(self):
        """AgentLifecycleEvent requires agent_id in data."""
        with pytest.raises(ValidationError) as exc_info:
            AgentLifecycleEvent(
                event_type="agent_decision",
                data={"action": "approve"}  # Missing agent_id
            )

        errors = exc_info.value.errors()
        assert any('agent_id' in str(e) for e in errors)

    def test_agent_lifecycle_with_complete_data(self):
        """AgentLifecycleEvent accepts complete agent event data."""
        event = AgentLifecycleEvent(
            event_type="agent_tool_call",
            data={
                "agent_id": "agent_transaction_001",
                "tool_name": "x402.request",
                "tool_args": {
                    "did": "did:example:123",
                    "payload": {"amount": 500}
                },
                "result": "success",
                "execution_time_ms": 245
            },
            timestamp="2026-01-10T18:35:00Z"
        )
        assert event.data["agent_id"] == "agent_transaction_001"
        assert event.data["tool_name"] == "x402.request"
        assert event.data["result"] == "success"


class TestCompleteEventExamples:
    """Test complete event examples from documentation."""

    def test_compliance_event_example(self):
        """Test compliance check event example."""
        event = EventCreateRequest(
            event_type="compliance_check",
            data={
                "subject": "user_12345",
                "risk_score": 0.12,
                "checks": {
                    "kyc": "passed",
                    "aml": "passed",
                    "sanctions": "clear"
                },
                "result": "approved"
            },
            timestamp="2026-01-10T18:30:00Z"
        )
        assert event.event_type == "compliance_check"
        assert event.data["risk_score"] == 0.12
        assert event.timestamp == "2026-01-10T18:30:00Z"

    def test_transaction_event_example(self):
        """Test transaction executed event example."""
        event = EventCreateRequest(
            event_type="transaction_executed",
            data={
                "transaction_id": "txn_abc123",
                "amount": 1000.00,
                "currency": "USD",
                "from_account": "acc_001",
                "to_account": "acc_002",
                "status": "completed"
            },
            timestamp="2026-01-10T18:35:00Z"
        )
        assert event.event_type == "transaction_executed"
        assert event.data["amount"] == 1000.00
        assert event.data["status"] == "completed"

    def test_agent_decision_event_example(self):
        """Test agent decision event example from documentation."""
        event = EventCreateRequest(
            event_type="agent_decision",
            data={
                "agent_id": "agent_analyst_001",
                "decision": "approve_transaction",
                "amount": 1000.00,
                "confidence": 0.95,
                "metadata": {
                    "risk_score": 0.12,
                    "compliance_passed": True
                }
            },
            timestamp="2026-01-10T18:30:00Z"
        )
        assert event.event_type == "agent_decision"
        assert event.data["confidence"] == 0.95
        assert event.data["metadata"]["compliance_passed"] is True


class TestAutoTimestampGeneration:
    """Test automatic timestamp generation behavior."""

    def test_timestamp_auto_generation_format(self):
        """Verify auto-generated timestamps are in correct ISO8601 format."""
        # This test validates the format that will be used by the API
        # When timestamp is None, API generates current UTC time
        now = datetime.now(timezone.utc)
        generated_timestamp = now.isoformat().replace('+00:00', 'Z')

        # Verify format matches ISO8601
        assert 'T' in generated_timestamp
        assert generated_timestamp.endswith('Z')

        # Verify it can be parsed back
        parsed = datetime.fromisoformat(generated_timestamp.replace('Z', '+00:00'))
        assert parsed.tzinfo is not None

    def test_event_without_timestamp_accepts_none(self):
        """Event without timestamp has None value, ready for auto-generation."""
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"}
        )
        # API endpoint will generate timestamp when event.timestamp is None
        assert event.timestamp is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_data_with_unicode_characters(self):
        """data supports Unicode characters."""
        event = EventCreateRequest(
            event_type="test_event",
            data={
                "message": "Hello 世界 🌍",
                "emoji": "✅",
                "special": "Café résumé"
            }
        )
        assert event.data["message"] == "Hello 世界 🌍"
        assert event.data["emoji"] == "✅"

    def test_data_with_large_nested_structure(self):
        """data supports deeply nested structures."""
        event = EventCreateRequest(
            event_type="test_event",
            data={
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "value": "deep"
                            }
                        }
                    }
                }
            }
        )
        assert event.data["level1"]["level2"]["level3"]["level4"]["value"] == "deep"

    def test_event_type_with_numbers(self):
        """event_type can contain numbers."""
        event = EventCreateRequest(
            event_type="agent_v2_decision",
            data={"test": "value"}
        )
        assert event.event_type == "agent_v2_decision"

    def test_timestamp_with_microseconds(self):
        """timestamp accepts microseconds precision."""
        timestamp = "2026-01-10T18:30:00.123456Z"
        event = EventCreateRequest(
            event_type="test_event",
            data={"test": "value"},
            timestamp=timestamp
        )
        assert event.timestamp == timestamp
