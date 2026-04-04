"""
Pydantic schemas for OpenConvAI HCS-10 protocol.

Issues #204, #205, #206, #207: OpenConvAI agent-to-agent messaging,
coordination, audit trail, and capability discovery.

Built by AINative Dev Team
Refs #204, #205, #206, #207
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# HCS-10 Core Message
# ---------------------------------------------------------------------------

class HCS10Message(BaseModel):
    """
    HCS-10 protocol message.

    Format: {protocol, version, sender_did, recipient_did, message_type,
             payload, conversation_id, timestamp}
    """

    protocol: str = Field(default="hcs-10", description="Protocol identifier")
    version: str = Field(default="1.0", description="Protocol version")
    sender_did: str = Field(..., description="DID of the sending agent")
    recipient_did: str = Field(..., description="DID of the recipient agent")
    message_type: str = Field(
        ...,
        description="Message type: text | task_request | task_result | coordination | discovery",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Message payload"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Conversation thread identifier"
    )
    timestamp: Optional[str] = Field(
        default=None, description="ISO 8601 timestamp"
    )


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class Conversation(BaseModel):
    """Represents an HCS-10 conversation thread between agents."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    initiator_did: str = Field(..., description="DID of the conversation initiator")
    participants: List[str] = Field(
        default_factory=list, description="All participant DIDs"
    )
    topic: str = Field(..., description="Conversation topic/subject")
    status: str = Field(default="active", description="Conversation status")
    created_at: Optional[str] = Field(
        default=None, description="ISO 8601 creation timestamp"
    )


# ---------------------------------------------------------------------------
# Workflow / Coordination
# ---------------------------------------------------------------------------

class StageDefinition(BaseModel):
    """Definition of a workflow stage."""

    name: str = Field(..., description="Stage name")
    agent_did: str = Field(..., description="DID of the agent responsible")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Stage input parameters"
    )


class StageResult(BaseModel):
    """Result submitted for a completed workflow stage."""

    workflow_id: str = Field(..., description="Parent workflow identifier")
    stage_name: str = Field(..., description="Name of the completed stage")
    agent_did: str = Field(..., description="DID of the agent that completed the stage")
    result: Dict[str, Any] = Field(
        default_factory=dict, description="Stage output"
    )
    status: str = Field(default="completed", description="Stage completion status")
    completed_at: Optional[str] = Field(
        default=None, description="ISO 8601 completion timestamp"
    )


class WorkflowStatus(BaseModel):
    """Overall status of a multi-agent workflow."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: str = Field(
        default="initiated",
        description="Workflow status: initiated | in_progress | completed | failed",
    )
    stages: Dict[str, Any] = Field(
        default_factory=dict,
        description="Stage name -> stage status/result mapping",
    )
    created_at: Optional[str] = Field(
        default=None, description="ISO 8601 creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, description="ISO 8601 last update timestamp"
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditEntry(BaseModel):
    """Single entry in the hcs10_audit_trail table."""

    audit_id: str = Field(..., description="Unique audit entry identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    sender_did: str = Field(..., description="Sender DID")
    recipient_did: str = Field(..., description="Recipient DID")
    message_type: str = Field(..., description="HCS-10 message type")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Message payload"
    )
    consensus_timestamp: str = Field(
        ..., description="Hedera consensus timestamp"
    )
    sequence_number: int = Field(..., description="HCS topic sequence number")
    logged_at: Optional[str] = Field(
        default=None, description="When this entry was logged"
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class DiscoveryMessage(BaseModel):
    """
    HCS-10 agent capability discovery broadcast.

    Format: {protocol, type, agent_did, capabilities, service_endpoint,
             heartbeat_timestamp}
    """

    protocol: str = Field(default="hcs-10", description="Protocol identifier")
    type: str = Field(default="discovery", description="Message type discriminator")
    agent_did: str = Field(..., description="DID of the advertising agent")
    capabilities: List[str] = Field(
        default_factory=list, description="List of capability identifiers"
    )
    service_endpoint: str = Field(
        ..., description="URL where the agent can be reached"
    )
    heartbeat_timestamp: Optional[str] = Field(
        default=None, description="ISO 8601 heartbeat timestamp"
    )


class AgentCapabilityRecord(BaseModel):
    """Record returned by the discovery service."""

    agent_did: str = Field(..., description="DID of the discovered agent")
    capabilities: List[str] = Field(
        default_factory=list, description="Agent capabilities"
    )
    service_endpoint: str = Field(..., description="Agent service endpoint URL")
    heartbeat_timestamp: Optional[str] = Field(
        default=None, description="Last seen heartbeat timestamp"
    )
    online: Optional[bool] = Field(
        default=None, description="Whether the agent is currently online"
    )


# ---------------------------------------------------------------------------
# API Request/Response schemas
# ---------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    """Request body for POST /hcs10/send."""

    sender_did: str
    recipient_did: str
    message_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Request body for POST /hcs10/workflow."""

    workflow_id: str
    stages: List[StageDefinition]


class DiscoverRequest(BaseModel):
    """Request body for POST /hcs10/discover."""

    capability: Optional[str] = None
    message_type: Optional[str] = None
