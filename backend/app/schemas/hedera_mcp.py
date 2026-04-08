"""
Pydantic schemas for Hedera MCP server API (Issue #268).

Provides request and response models for:
- AuditEvent: log entry for project HCS audit trail
- AuditSummary: event counts by type
- PaymentChannel: agent-to-agent micropayment channel
- Micropayment: individual payment record

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Audit schemas
# ---------------------------------------------------------------------------

class LogAuditEventRequest(BaseModel):
    """Request body for POST /hedera/audit/{project_id}/log."""

    topic_id: str = Field(
        ...,
        min_length=1,
        description="Hedera HCS topic ID for this project (e.g. 0.0.1234)",
    )
    event_type: str = Field(
        ...,
        min_length=1,
        description="Event type: payment, decision, handoff, memory_anchor, compliance",
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Arbitrary event data to log",
    )
    agent_id: str = Field(
        ...,
        min_length=1,
        description="ID of the agent that generated the event",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topic_id": "0.0.7777",
                "event_type": "payment",
                "payload": {"amount": 10.0, "currency": "HBAR", "recipient": "did:hedera:testnet:0.0.200"},
                "agent_id": "agent-finance-001",
            }
        }


class AuditEvent(BaseModel):
    """A single HCS audit event record."""

    sequence_number: int = Field(..., description="HCS sequence number")
    event_type: Optional[str] = Field(None, description="Type of audit event")
    consensus_timestamp: Optional[str] = Field(None, description="HCS consensus timestamp")
    raw_message: Optional[str] = Field(None, description="Base64-encoded raw HCS message")

    class Config:
        json_schema_extra = {
            "example": {
                "sequence_number": 42,
                "event_type": "payment",
                "consensus_timestamp": "2026-04-03T00:00:00.000Z",
            }
        }


class LogAuditEventResponse(BaseModel):
    """Response for POST /hedera/audit/{project_id}/log."""

    sequence_number: int = Field(..., description="HCS sequence number of the logged event")
    project_id: str = Field(..., description="Project ID")
    event_type: str = Field(..., description="Logged event type")


class AuditLogResponse(BaseModel):
    """Response for GET /hedera/audit/{project_id}."""

    project_id: str = Field(..., description="Project ID")
    topic_id: str = Field(..., description="HCS topic ID")
    events: List[AuditEvent] = Field(default_factory=list, description="List of audit events")
    count: int = Field(..., description="Number of events returned")


class AuditSummary(BaseModel):
    """Response for GET /hedera/audit/{project_id}/summary."""

    project_id: str = Field(..., description="Project ID")
    topic_id: str = Field(..., description="HCS topic ID")
    total: int = Field(..., description="Total number of events")
    by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Event count grouped by event_type",
    )


# ---------------------------------------------------------------------------
# Payment channel schemas
# ---------------------------------------------------------------------------

class PaymentChannel(BaseModel):
    """An agent-to-agent micropayment channel."""

    channel_id: str = Field(..., description="Unique channel identifier")
    sender_did: str = Field(..., description="DID of the sending agent")
    receiver_did: str = Field(..., description="DID of the receiving agent")
    max_amount: float = Field(..., description="Maximum HBAR in this channel")
    status: str = Field(default="open", description="Channel status: open or closed")
    remaining: float = Field(..., description="Remaining HBAR balance")
    spent: float = Field(default=0.0, description="Total HBAR spent so far")


class Micropayment(BaseModel):
    """A single micropayment within a channel."""

    payment_id: str = Field(..., description="Unique payment identifier")
    channel_id: str = Field(..., description="Channel this payment belongs to")
    amount: float = Field(..., description="Amount transferred in HBAR")
    memo: Optional[str] = Field(None, description="Payment memo")
    transaction_id: Optional[str] = Field(None, description="Hedera transaction ID")
    status: str = Field(..., description="Payment status: SUCCESS or FAILED")
