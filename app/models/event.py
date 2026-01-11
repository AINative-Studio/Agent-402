"""
Event data models for ZeroDB Public API.

Defines request/response schemas for event operations.
Supports audit trail and system tracking per PRD §6.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventCreate(BaseModel):
    """Request schema for creating a new event."""

    event_type: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Event type/category (e.g., 'agent_decision', 'agent_tool_call', 'compliance_check')"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event payload data as JSON object"
    )
    timestamp: Optional[str] = Field(
        None,
        description="ISO8601 timestamp (optional, defaults to current time)"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate timestamp is a valid ISO8601 format."""
        if v is None:
            return None

        # Validate ISO8601 format - must contain 'T' separator for strict ISO8601
        if 'T' not in v:
            from app.core.exceptions import InvalidTimestampException
            raise InvalidTimestampException(
                timestamp=v,
                reason="Missing 'T' separator between date and time"
            )

        # Validate ISO8601 format
        try:
            # Try parsing as ISO8601
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            from app.core.exceptions import InvalidTimestampException
            raise InvalidTimestampException(timestamp=v, reason=str(e))

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "agent_decision",
                    "data": {
                        "agent_id": "analyst-001",
                        "decision": "approve_transaction",
                        "confidence": 0.95,
                        "reasoning": "All compliance checks passed"
                    },
                    "timestamp": "2025-01-11T22:00:00Z"
                },
                {
                    "event_type": "agent_tool_call",
                    "data": {
                        "agent_id": "transaction-agent",
                        "tool_name": "x402.request",
                        "parameters": {"action": "submit_transaction"},
                        "result": "success"
                    }
                },
                {
                    "event_type": "compliance_check",
                    "data": {
                        "subject": "user-12345",
                        "check_type": "kyc",
                        "status": "passed",
                        "risk_score": 0.15
                    }
                }
            ]
        }
    }


class EventResponse(BaseModel):
    """Response schema for event operations."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique event identifier"
    )
    event_type: str = Field(
        ...,
        description="Event type/category"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event payload data"
    )
    timestamp: str = Field(
        ...,
        description="Event timestamp (ISO8601)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "event_type": "agent_decision",
                    "data": {
                        "agent_id": "analyst-001",
                        "decision": "approve_transaction",
                        "confidence": 0.95
                    },
                    "timestamp": "2025-01-11T22:00:00Z",
                    "created_at": "2025-01-11T22:00:01Z"
                }
            ]
        }
    }
