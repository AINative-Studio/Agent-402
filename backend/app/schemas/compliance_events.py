"""
Compliance Events API schemas for request/response validation.
Implements Epic 12 Issue 3: Write outcomes to compliance_events.

Per PRD Section 6 (ZeroDB Integration):
- Compliance agents write outcomes to compliance_events table
- Events support auditability and compliance tracking
- Events include agent_id, event_type, outcome, risk_score, details

Event Types (per Issue 3 requirements):
- KYC_CHECK: Know Your Customer verification results
- KYT_CHECK: Know Your Transaction analysis results
- RISK_ASSESSMENT: Risk scoring and assessment outcomes
- COMPLIANCE_DECISION: Final compliance decisions
- AUDIT_LOG: Audit trail entries for compliance actions
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ComplianceEventType(str, Enum):
    """
    Supported compliance event types per Issue 3.

    These types cover the full compliance workflow:
    - KYC_CHECK: Identity verification
    - KYT_CHECK: Transaction monitoring
    - RISK_ASSESSMENT: Risk scoring
    - COMPLIANCE_DECISION: Final decisions
    - AUDIT_LOG: Audit trail
    """
    KYC_CHECK = "KYC_CHECK"
    KYT_CHECK = "KYT_CHECK"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    COMPLIANCE_DECISION = "COMPLIANCE_DECISION"
    AUDIT_LOG = "AUDIT_LOG"


class ComplianceOutcome(str, Enum):
    """
    Possible outcomes for compliance events.

    Outcomes indicate the result of a compliance check:
    - PASS: Compliance check passed
    - FAIL: Compliance check failed
    - PENDING: Awaiting further review
    - ESCALATED: Escalated for manual review
    - ERROR: Error during processing
    """
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    ESCALATED = "ESCALATED"
    ERROR = "ERROR"


class ComplianceEventCreate(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/compliance-events.

    Epic 12 Issue 3: Compliance agents write outcomes to compliance_events.

    All fields per Issue 3 requirements:
    - agent_id: Identifier of the compliance agent
    - event_type: Type of compliance event
    - outcome: Result of the compliance check
    - risk_score: Numerical risk assessment (0.0-1.0)
    - details: Additional context and data
    - run_id: Optional workflow run identifier
    """
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Identifier of the compliance agent that generated this event"
    )
    event_type: ComplianceEventType = Field(
        ...,
        description="Type of compliance event (KYC_CHECK, KYT_CHECK, RISK_ASSESSMENT, COMPLIANCE_DECISION, AUDIT_LOG)"
    )
    outcome: ComplianceOutcome = Field(
        ...,
        description="Outcome of the compliance check (PASS, FAIL, PENDING, ESCALATED, ERROR)"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk score from 0.0 (low risk) to 1.0 (high risk)"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details and context for the compliance event"
    )
    run_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional workflow run identifier for tracing related events"
    )

    @validator('agent_id')
    def validate_agent_id(cls, v):
        """Ensure agent_id is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("agent_id cannot be empty or whitespace")
        return v.strip()

    @validator('run_id')
    def validate_run_id(cls, v):
        """Ensure run_id is not empty or whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("run_id cannot be empty or whitespace if provided")
        return v.strip() if v else None

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "compliance_agent_001",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.15,
                "details": {
                    "customer_id": "cust_12345",
                    "verification_method": "document",
                    "documents_verified": ["passport", "utility_bill"],
                    "confidence_score": 0.95
                },
                "run_id": "run_abc123"
            }
        }


class ComplianceEventResponse(BaseModel):
    """
    Response schema for compliance event operations.

    Returns the full event data including system-generated fields:
    - event_id: Unique identifier (system-generated)
    - timestamp: Event creation timestamp (system-generated)
    - project_id: Project the event belongs to
    """
    event_id: str = Field(
        ...,
        description="Unique identifier for the compliance event"
    )
    project_id: str = Field(
        ...,
        description="Project ID the event belongs to"
    )
    agent_id: str = Field(
        ...,
        description="Identifier of the compliance agent"
    )
    event_type: ComplianceEventType = Field(
        ...,
        description="Type of compliance event"
    )
    outcome: ComplianceOutcome = Field(
        ...,
        description="Outcome of the compliance check"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk score (0.0-1.0)"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event details"
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Workflow run identifier"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when the event was created"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123def456",
                "project_id": "proj_xyz789",
                "agent_id": "compliance_agent_001",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.15,
                "details": {
                    "customer_id": "cust_12345",
                    "verification_method": "document"
                },
                "run_id": "run_abc123",
                "timestamp": "2026-01-10T12:34:56.789Z"
            }
        }


class ComplianceEventListResponse(BaseModel):
    """
    Response schema for listing compliance events.

    Supports pagination and filtering for compliance event queries.
    """
    events: List[ComplianceEventResponse] = Field(
        default_factory=list,
        description="List of compliance events"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of events matching the query"
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum number of events returned"
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Offset for pagination"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_id": "evt_abc123def456",
                        "project_id": "proj_xyz789",
                        "agent_id": "compliance_agent_001",
                        "event_type": "KYC_CHECK",
                        "outcome": "PASS",
                        "risk_score": 0.15,
                        "details": {},
                        "run_id": "run_abc123",
                        "timestamp": "2026-01-10T12:34:56.789Z"
                    }
                ],
                "total": 1,
                "limit": 100,
                "offset": 0
            }
        }


class ComplianceEventFilter(BaseModel):
    """
    Query parameters for filtering compliance events.

    Supports filtering by agent, event type, outcome, risk score range, and time range.
    """
    agent_id: Optional[str] = Field(
        default=None,
        description="Filter by agent ID"
    )
    event_type: Optional[ComplianceEventType] = Field(
        default=None,
        description="Filter by event type"
    )
    outcome: Optional[ComplianceOutcome] = Field(
        default=None,
        description="Filter by outcome"
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Filter by run ID"
    )
    min_risk_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum risk score filter"
    )
    max_risk_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum risk score filter"
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Start time filter (ISO 8601 format)"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="End time filter (ISO 8601 format)"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of events to return (1-1000)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination"
    )
