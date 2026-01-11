"""
Event API schemas for request/response validation.
Implements GitHub Issue #38: Event schema validation with event_type, data, timestamp.

Per PRD §10 (Replayability) and Epic 8 (Events API).
"""
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class EventCreateRequest(BaseModel):
    """
    Event creation request schema for POST /v1/public/database/events.

    Per Epic 8 Story 2: events accept event_type, data, timestamp.
    Per PRD §10: Ensures replayability through timestamp handling.

    Fields:
    - event_type: string, required, non-empty, max 100 characters
    - data: JSON object, required, can be nested
    - timestamp: ISO8601 datetime string, optional (defaults to current time)
    """
    event_type: str = Field(
        ...,
        description="Event type identifier (e.g., 'agent_decision', 'compliance_check')",
        min_length=1,
        max_length=100,
        examples=["agent_decision", "compliance_check", "transaction_executed"]
    )

    data: Dict[str, Any] = Field(
        ...,
        description="Event payload data as JSON object, can be nested",
        examples=[{
            "agent_id": "agent_123",
            "action": "risk_assessment",
            "result": "approved",
            "confidence": 0.95
        }]
    )

    timestamp: Optional[str] = Field(
        default=None,
        description="ISO8601 timestamp (e.g., '2026-01-10T18:30:00Z'). Auto-generated if not provided.",
        examples=["2026-01-10T18:30:00Z", "2026-01-11T12:45:30.123Z"]
    )

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """
        Validate event_type is non-empty after stripping whitespace.
        Max length is enforced by Field constraint.
        """
        v = v.strip()
        if not v:
            raise ValueError("event_type cannot be empty or whitespace-only")
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate timestamp is in valid ISO8601 datetime format.
        Returns None if not provided (will be auto-generated).

        Requires full datetime format with time component, not just date.

        Raises:
            ValueError: If timestamp is provided but not valid ISO8601 datetime format
        """
        if v is None:
            return None

        # Strip whitespace
        v = v.strip()
        if not v:
            return None

        # Require 'T' separator for datetime (reject date-only formats)
        if 'T' not in v:
            raise ValueError(
                f"timestamp must be in ISO8601 datetime format with time component "
                f"(e.g., '2026-01-10T18:30:00Z'). Date-only format not accepted. "
                f"Received: '{v}'"
            )

        # Validate ISO8601 format by attempting to parse
        try:
            # Support various ISO8601 formats:
            # - 2026-01-10T18:30:00Z
            # - 2026-01-10T18:30:00.123Z
            # - 2026-01-10T18:30:00+00:00
            # - 2026-01-10T18:30:00-05:00
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError as e:
            raise ValueError(
                f"timestamp must be in ISO8601 format (e.g., '2026-01-10T18:30:00Z'). "
                f"Received: '{v}'. Error: {str(e)}"
            )

    @model_validator(mode='after')
    def ensure_data_is_dict(self) -> 'EventCreateRequest':
        """
        Ensure data field is a dictionary (JSON object).
        Pydantic typing handles this, but we add explicit validation for clarity.
        """
        if not isinstance(self.data, dict):
            raise ValueError("data must be a JSON object (dictionary)")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "agent_analyst_001",
                    "decision": "approve_transaction",
                    "amount": 1000.00,
                    "confidence": 0.95,
                    "metadata": {
                        "risk_score": 0.12,
                        "compliance_passed": True
                    }
                },
                "timestamp": "2026-01-10T18:30:00Z"
            }
        }


class EventResponse(BaseModel):
    """
    Event creation response schema.

    Per Epic 8 Story 4: event writes return stable success response.
    """
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type identifier")
    timestamp: str = Field(..., description="ISO8601 timestamp (auto-generated or provided)")
    status: str = Field(default="created", description="Event creation status")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123xyz",
                "event_type": "agent_decision",
                "timestamp": "2026-01-10T18:30:00Z",
                "status": "created"
            }
        }


class EventListResponse(BaseModel):
    """
    Response schema for listing events.
    Supports pagination and filtering by event_type.
    """
    events: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of events"
    )
    total: int = Field(..., description="Total number of events matching filter")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_id": "evt_abc123",
                        "event_type": "agent_decision",
                        "data": {
                            "agent_id": "agent_001",
                            "action": "approve"
                        },
                        "timestamp": "2026-01-10T18:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class AgentLifecycleEvent(BaseModel):
    """
    Specialized event schema for agent lifecycle events.

    Per Epic 8 Story 5: Agent system can emit agent lifecycle events.
    Common event types: agent_decision, agent_tool_call, agent_error.
    """
    event_type: str = Field(
        ...,
        description="Agent lifecycle event type",
        pattern="^agent_(decision|tool_call|error|created|terminated)$",
        examples=["agent_decision", "agent_tool_call", "agent_error"]
    )

    data: Dict[str, Any] = Field(
        ...,
        description="Agent event data including agent_id, action, and result"
    )

    timestamp: Optional[str] = Field(
        default=None,
        description="ISO8601 timestamp. Auto-generated if not provided."
    )

    @model_validator(mode='after')
    def validate_agent_data(self) -> 'AgentLifecycleEvent':
        """
        Validate agent lifecycle events contain required agent_id field.
        """
        if 'agent_id' not in self.data:
            raise ValueError("Agent lifecycle events must include 'agent_id' in data")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "agent_tool_call",
                "data": {
                    "agent_id": "agent_transaction_001",
                    "tool_name": "x402.request",
                    "tool_args": {
                        "did": "did:example:123",
                        "payload": {"amount": 500}
                    },
                    "result": "success"
                },
                "timestamp": "2026-01-10T18:35:00Z"
            }
        }
