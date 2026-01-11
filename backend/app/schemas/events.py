"""
Event API schemas for request/response validation.
Implements agent lifecycle event support per Epic 8 Story 5 (Issue #41).

PRD Alignment:
- §5: Agent personas with lifecycle tracking
- §6: Audit trail and compliance events
- §10: Replayability and explainability
"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# Agent lifecycle event types
AgentEventType = Literal[
    "agent_decision",
    "agent_tool_call",
    "agent_error",
    "agent_start",
    "agent_complete"
]


class AgentDecisionData(BaseModel):
    """Data schema for agent_decision events."""
    agent_id: str = Field(..., description="Agent identifier (DID or agent ID)")
    decision: str = Field(..., description="Decision made by the agent")
    reasoning: str = Field(..., description="Reasoning behind the decision")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the decision"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "did:ethr:0xabc123",
                "decision": "approve_transaction",
                "reasoning": "Risk score below threshold and KYC passed",
                "context": {
                    "risk_score": 0.23,
                    "kyc_status": "verified",
                    "transaction_amount": 1000.00
                }
            }
        }


class AgentToolCallData(BaseModel):
    """Data schema for agent_tool_call events."""
    agent_id: str = Field(..., description="Agent identifier (DID or agent ID)")
    tool_name: str = Field(..., description="Name of the tool called")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the tool"
    )
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Result returned by the tool (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "compliance_agent",
                "tool_name": "x402.request",
                "parameters": {
                    "endpoint": "/compliance/kyc",
                    "subject": "user_12345"
                },
                "result": {
                    "status": "approved",
                    "risk_score": 0.15
                }
            }
        }


class AgentErrorData(BaseModel):
    """Data schema for agent_error events."""
    agent_id: str = Field(..., description="Agent identifier (DID or agent ID)")
    error_type: str = Field(..., description="Type/category of error")
    error_message: str = Field(..., description="Error message")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "transaction_agent",
                "error_type": "SIGNATURE_VERIFICATION_FAILED",
                "error_message": "Invalid DID signature for X402 request",
                "context": {
                    "did": "did:ethr:0xabc123",
                    "endpoint": "/x402",
                    "timestamp": "2026-01-11T10:30:00Z"
                }
            }
        }


class AgentStartData(BaseModel):
    """Data schema for agent_start events."""
    agent_id: str = Field(..., description="Agent identifier (DID or agent ID)")
    task: str = Field(..., description="Task being started")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent configuration for this task"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "analyst_agent",
                "task": "market_analysis",
                "config": {
                    "symbols": ["BTC-USD", "ETH-USD"],
                    "timeframe": "1h",
                    "analysis_type": "technical"
                }
            }
        }


class AgentCompleteData(BaseModel):
    """Data schema for agent_complete events."""
    agent_id: str = Field(..., description="Agent identifier (DID or agent ID)")
    result: Dict[str, Any] = Field(
        ...,
        description="Result of the completed task"
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Task duration in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "compliance_agent",
                "result": {
                    "status": "completed",
                    "checks_performed": 5,
                    "passed": 5,
                    "failed": 0
                },
                "duration_ms": 2340
            }
        }


class CreateEventRequest(BaseModel):
    """
    Request schema for creating events.
    Supports generic events and agent lifecycle events.
    """
    event_type: str = Field(
        ...,
        description="Event type (e.g., 'agent_decision', 'agent_tool_call', 'compliance_check')"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event payload data (structure depends on event_type)"
    )
    timestamp: Optional[str] = Field(
        None,
        description="Event timestamp in ISO 8601 format (auto-generated if not provided)"
    )
    source: Optional[str] = Field(
        None,
        description="Event source identifier (e.g., 'crewai', 'agent_system')"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracking related events"
    )

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO 8601 timestamp format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid ISO 8601 timestamp format: {v}") from e
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "event_type": "agent_decision",
                    "data": {
                        "agent_id": "compliance_agent",
                        "decision": "approve_transaction",
                        "reasoning": "All compliance checks passed",
                        "context": {"risk_score": 0.15}
                    },
                    "timestamp": "2026-01-11T10:30:00Z",
                    "source": "crewai",
                    "correlation_id": "task_abc123"
                },
                {
                    "event_type": "agent_tool_call",
                    "data": {
                        "agent_id": "transaction_agent",
                        "tool_name": "x402.request",
                        "parameters": {"endpoint": "/x402"},
                        "result": {"status": "success"}
                    }
                },
                {
                    "event_type": "compliance_check",
                    "data": {
                        "subject": "user_12345",
                        "check_type": "kyc",
                        "result": "passed"
                    }
                }
            ]
        }


class CreateEventResponse(BaseModel):
    """
    Stable response schema for event creation.

    Per GitHub Issue #40 (Stable Response Format):
    - All successful event writes return this exact format
    - HTTP 201 (Created) status for successful writes
    - Fields always in same order: id, event_type, data, timestamp, created_at
    - Response format guaranteed stable per DX Contract

    Per PRD §9 (Demo Clarity):
    - Clear, predictable response structure
    - All fields always present (no optional fields)

    Per PRD §10 (Determinism):
    - id: UUID string (auto-generated, unique)
    - event_type: echoed from request
    - data: echoed from request
    - timestamp: normalized ISO8601 timestamp
    - created_at: server-side creation timestamp for audit trail
    """
    id: str = Field(
        ...,
        description="Unique event identifier (UUID)",
        examples=["evt_1234567890abcdef"]
    )
    event_type: str = Field(
        ...,
        description="Event type (echoed from request)"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Event payload data (echoed from request)"
    )
    timestamp: str = Field(
        ...,
        description="Normalized ISO8601 timestamp of the event"
    )
    created_at: str = Field(
        ...,
        description="Server-side creation timestamp in ISO8601 format"
    )

    class Config:
        # Fields are serialized in the order they are defined
        # This ensures stable response format per Issue #40
        json_schema_extra = {
            "example": {
                "id": "evt_1234567890abcdef",
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "compliance_agent",
                    "decision": "approve_transaction",
                    "reasoning": "All compliance checks passed",
                    "context": {"risk_score": 0.15}
                },
                "timestamp": "2026-01-11T10:30:00.000Z",
                "created_at": "2026-01-11T10:30:01.234Z"
            }
        }


class EventResponse(BaseModel):
    """Response schema for event retrieval."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: str = Field(..., description="Event timestamp in ISO 8601 format")
    source: Optional[str] = Field(None, description="Event source identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123xyz456",
                "event_type": "agent_decision",
                "data": {
                    "agent_id": "compliance_agent",
                    "decision": "approve_transaction",
                    "reasoning": "All compliance checks passed",
                    "context": {"risk_score": 0.15}
                },
                "timestamp": "2026-01-11T10:30:00Z",
                "source": "crewai",
                "correlation_id": "task_abc123",
                "created_at": "2026-01-11T10:30:01Z"
            }
        }


class EventListResponse(BaseModel):
    """Response schema for listing events."""
    events: list[EventResponse] = Field(..., description="List of events")
    total: int = Field(..., ge=0, description="Total number of events")
    limit: int = Field(..., ge=1, description="Maximum events returned")
    offset: int = Field(..., ge=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_id": "evt_abc123",
                        "event_type": "agent_decision",
                        "data": {"agent_id": "compliance_agent", "decision": "approve"},
                        "timestamp": "2026-01-11T10:30:00Z",
                        "source": "crewai",
                        "correlation_id": "task_abc",
                        "created_at": "2026-01-11T10:30:01Z"
                    }
                ],
                "total": 1,
                "limit": 10,
                "offset": 0
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response per DX Contract.
    All errors return { detail, error_code }.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid timestamp format. Must be ISO 8601.",
                "error_code": "INVALID_TIMESTAMP"
            }
        }
