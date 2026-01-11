"""
X402 Request API schemas for request/response validation.
Implements Epic 12 Issue 4: X402 requests linked to agent + task.

Per PRD Section 6 (ZeroDB Integration):
- X402 signed requests are logged with agent and task linkage
- Supports linking to agent_memory and compliance_events records
- Enables audit trail for X402 protocol transactions

Per PRD Section 8 (X402 Protocol):
- X402 requests contain signed payment authorizations
- Requests must be traceable to originating agent and task
- Supports compliance and audit requirements
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class X402RequestStatus(str, Enum):
    """
    Status of an X402 request.

    Values:
    - PENDING: Request created but not yet processed
    - APPROVED: Request has been approved
    - REJECTED: Request has been rejected
    - EXPIRED: Request has expired without processing
    - COMPLETED: Request has been fully processed
    """
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


class X402RequestCreate(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/x402-requests.

    Creates a new X402 signed request record linked to agent and task.

    Epic 12 Issue 4 Requirements:
    - agent_id: DID or identifier of the agent creating the request
    - task_id: Identifier of the task that produced the request
    - run_id: Identifier of the agent run context
    - request_payload: The X402 protocol payload (payment authorization)
    - signature: Cryptographic signature of the request
    - linked_memory_ids: Optional links to agent_memory records
    - linked_compliance_ids: Optional links to compliance_events records
    """
    agent_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Agent identifier (DID or internal ID) that produced this request. "
            "Used for tracing X402 requests back to the originating agent."
        )
    )
    task_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Task identifier that produced this X402 request. "
            "Enables correlation between tasks and payment authorizations."
        )
    )
    run_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Run identifier for the agent execution context. "
            "Groups related X402 requests within a single agent run."
        )
    )
    request_payload: Dict[str, Any] = Field(
        ...,
        description=(
            "The X402 protocol request payload. Contains payment authorization details, "
            "amount, recipient, and other protocol-specific fields."
        )
    )
    signature: str = Field(
        ...,
        min_length=1,
        description=(
            "Cryptographic signature of the X402 request. "
            "Used to verify authenticity and integrity of the request."
        )
    )
    status: Optional[X402RequestStatus] = Field(
        default=X402RequestStatus.PENDING,
        description="Initial status of the request. Defaults to PENDING."
    )
    linked_memory_ids: Optional[List[str]] = Field(
        default_factory=list,
        description=(
            "List of agent_memory record IDs linked to this request. "
            "Enables tracing decision context for X402 authorizations."
        )
    )
    linked_compliance_ids: Optional[List[str]] = Field(
        default_factory=list,
        description=(
            "List of compliance_events record IDs linked to this request. "
            "Enables compliance audit trail for X402 transactions."
        )
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Additional metadata for the X402 request. "
            "Can include custom fields for agent-specific context."
        )
    )

    @validator('request_payload')
    def validate_payload_not_empty(cls, v):
        """Ensure request_payload is not empty."""
        if not v:
            raise ValueError("request_payload cannot be empty")
        return v

    @validator('signature')
    def validate_signature_not_whitespace(cls, v):
        """Ensure signature is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("signature cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "did:ethr:0xabc123def456",
                "task_id": "task_payment_001",
                "run_id": "run_2026_01_10_001",
                "request_payload": {
                    "type": "payment_authorization",
                    "amount": "100.00",
                    "currency": "USD",
                    "recipient": "did:ethr:0xdef789abc012",
                    "memo": "Service payment for task completion"
                },
                "signature": "0xsig123abc456def789...",
                "status": "PENDING",
                "linked_memory_ids": ["mem_abc123", "mem_def456"],
                "linked_compliance_ids": ["comp_evt_001"],
                "metadata": {
                    "priority": "high",
                    "source": "payment_agent"
                }
            }
        }


class X402RequestResponse(BaseModel):
    """
    Response schema for X402 request operations.

    Returns the created or retrieved X402 request with all linked records.
    """
    request_id: str = Field(
        ...,
        description="Unique identifier for the X402 request"
    )
    project_id: str = Field(
        ...,
        description="Project ID this request belongs to"
    )
    agent_id: str = Field(
        ...,
        description="Agent identifier that produced this request"
    )
    task_id: str = Field(
        ...,
        description="Task identifier that produced this request"
    )
    run_id: str = Field(
        ...,
        description="Run identifier for the agent execution context"
    )
    request_payload: Dict[str, Any] = Field(
        ...,
        description="The X402 protocol request payload"
    )
    signature: str = Field(
        ...,
        description="Cryptographic signature of the request"
    )
    status: X402RequestStatus = Field(
        ...,
        description="Current status of the X402 request"
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp when request was created"
    )
    linked_memory_ids: List[str] = Field(
        default_factory=list,
        description="List of linked agent_memory record IDs"
    )
    linked_compliance_ids: List[str] = Field(
        default_factory=list,
        description="List of linked compliance_events record IDs"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the request"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "request_id": "x402_req_abc123",
                "project_id": "proj_xyz789",
                "agent_id": "did:ethr:0xabc123def456",
                "task_id": "task_payment_001",
                "run_id": "run_2026_01_10_001",
                "request_payload": {
                    "type": "payment_authorization",
                    "amount": "100.00",
                    "currency": "USD",
                    "recipient": "did:ethr:0xdef789abc012"
                },
                "signature": "0xsig123abc456def789...",
                "status": "PENDING",
                "timestamp": "2026-01-10T12:34:56.789Z",
                "linked_memory_ids": ["mem_abc123", "mem_def456"],
                "linked_compliance_ids": ["comp_evt_001"],
                "metadata": {"priority": "high"}
            }
        }


class X402RequestWithLinks(X402RequestResponse):
    """
    Extended response schema that includes full linked records.

    Used for GET /v1/public/{project_id}/x402-requests/{request_id}
    when full linked record data is requested.
    """
    linked_memories: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description=(
            "Full agent_memory records linked to this request. "
            "Includes memory content and metadata for audit trail."
        )
    )
    linked_compliance_events: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description=(
            "Full compliance_events records linked to this request. "
            "Includes compliance check results and metadata."
        )
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "request_id": "x402_req_abc123",
                "project_id": "proj_xyz789",
                "agent_id": "did:ethr:0xabc123def456",
                "task_id": "task_payment_001",
                "run_id": "run_2026_01_10_001",
                "request_payload": {
                    "type": "payment_authorization",
                    "amount": "100.00",
                    "currency": "USD"
                },
                "signature": "0xsig123abc456def789...",
                "status": "COMPLETED",
                "timestamp": "2026-01-10T12:34:56.789Z",
                "linked_memory_ids": ["mem_abc123"],
                "linked_compliance_ids": ["comp_evt_001"],
                "metadata": {"priority": "high"},
                "linked_memories": [
                    {
                        "memory_id": "mem_abc123",
                        "content": "Payment decision rationale...",
                        "created_at": "2026-01-10T12:30:00Z"
                    }
                ],
                "linked_compliance_events": [
                    {
                        "event_id": "comp_evt_001",
                        "event_type": "PAYMENT_AUTHORIZATION",
                        "passed": True,
                        "created_at": "2026-01-10T12:32:00Z"
                    }
                ]
            }
        }


class X402RequestListResponse(BaseModel):
    """
    Response schema for listing X402 requests.

    Supports pagination and filtering by agent_id, task_id, run_id.
    """
    requests: List[X402RequestResponse] = Field(
        default_factory=list,
        description="List of X402 requests matching the query"
    )
    total: int = Field(
        ...,
        description="Total number of requests matching the query",
        ge=0
    )
    limit: int = Field(
        ...,
        description="Maximum number of requests returned",
        ge=1
    )
    offset: int = Field(
        ...,
        description="Offset for pagination",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "request_id": "x402_req_abc123",
                        "project_id": "proj_xyz789",
                        "agent_id": "did:ethr:0xabc123def456",
                        "task_id": "task_payment_001",
                        "run_id": "run_2026_01_10_001",
                        "request_payload": {"type": "payment_authorization"},
                        "signature": "0xsig123...",
                        "status": "COMPLETED",
                        "timestamp": "2026-01-10T12:34:56.789Z",
                        "linked_memory_ids": [],
                        "linked_compliance_ids": []
                    }
                ],
                "total": 1,
                "limit": 100,
                "offset": 0
            }
        }


class X402RequestFilter(BaseModel):
    """
    Filter parameters for listing X402 requests.

    All filters are optional and combined with AND logic.
    """
    agent_id: Optional[str] = Field(
        default=None,
        description="Filter by agent identifier"
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Filter by task identifier"
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Filter by run identifier"
    )
    status: Optional[X402RequestStatus] = Field(
        default=None,
        description="Filter by request status"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results (1-1000)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "did:ethr:0xabc123def456",
                "task_id": "task_payment_001",
                "status": "PENDING",
                "limit": 50,
                "offset": 0
            }
        }
