"""
Run API schemas for request/response validation.
Implements Epic 12, Issue 5: Agent run replay from ZeroDB records.

Per PRD Section 10 (Success Criteria):
- Enable deterministic replay of agent runs
- Complete audit trail and replayability

Per PRD Section 11 (Deterministic Replay):
- Aggregate all records for a run_id
- Order chronologically by timestamp
- Validate all linked records exist
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Run status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentProfileRecord(BaseModel):
    """
    Agent profile record schema.
    Per PRD Section 6: Agent profile stores agent configuration and identity.
    """
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: Optional[str] = Field(None, description="Human-readable agent name")
    agent_type: Optional[str] = Field(None, description="Type/category of agent")
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent configuration parameters"
    )
    created_at: str = Field(..., description="ISO timestamp when agent was created")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_compliance_001",
                "agent_name": "Compliance Checker",
                "agent_type": "compliance",
                "configuration": {
                    "model": "gpt-4",
                    "temperature": 0.0,
                    "max_tokens": 1000
                },
                "created_at": "2026-01-10T10:00:00.000Z"
            }
        }


class AgentMemoryRecord(BaseModel):
    """
    Agent memory record schema.
    Per PRD Section 6: Agent memory stores input/output summaries per task.
    """
    memory_id: str = Field(..., description="Unique memory record identifier")
    agent_id: str = Field(..., description="Agent that created this memory")
    run_id: str = Field(..., description="Run this memory belongs to")
    task_id: Optional[str] = Field(None, description="Task associated with this memory")
    input_summary: str = Field(..., description="Summary of input processed")
    output_summary: str = Field(..., description="Summary of output produced")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this memory"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: str = Field(..., description="ISO timestamp when memory was created")

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_001",
                "agent_id": "agent_compliance_001",
                "run_id": "run_abc123",
                "task_id": "task_001",
                "input_summary": "Analyze transaction TXN-001 for compliance",
                "output_summary": "Transaction compliant with AML regulations",
                "confidence": 0.95,
                "metadata": {"source": "transaction_queue"},
                "timestamp": "2026-01-10T10:05:00.000Z"
            }
        }


class ComplianceEventRecord(BaseModel):
    """
    Compliance event record schema.
    Per PRD Section 6: Compliance events track all regulatory actions.
    """
    event_id: str = Field(..., description="Unique event identifier")
    run_id: str = Field(..., description="Run this event belongs to")
    agent_id: str = Field(..., description="Agent that triggered this event")
    event_type: str = Field(
        ...,
        description="Type of compliance event (e.g., CHECK, VIOLATION, APPROVAL)"
    )
    event_category: Optional[str] = Field(
        None,
        description="Category of compliance (e.g., AML, KYC, SANCTIONS)"
    )
    description: str = Field(..., description="Human-readable event description")
    severity: Optional[str] = Field(
        None,
        description="Severity level (INFO, WARNING, ERROR, CRITICAL)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    timestamp: str = Field(..., description="ISO timestamp when event occurred")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_001",
                "run_id": "run_abc123",
                "agent_id": "agent_compliance_001",
                "event_type": "CHECK",
                "event_category": "AML",
                "description": "AML compliance check completed for transaction TXN-001",
                "severity": "INFO",
                "metadata": {"transaction_id": "TXN-001", "check_passed": True},
                "timestamp": "2026-01-10T10:05:30.000Z"
            }
        }


class X402RequestRecord(BaseModel):
    """
    X402 payment request record schema.
    Per PRD Section 6: X402 requests track all payment operations.
    """
    request_id: str = Field(..., description="Unique request identifier")
    run_id: str = Field(..., description="Run this request belongs to")
    agent_id: str = Field(..., description="Agent that initiated this request")
    request_type: str = Field(
        ...,
        description="Type of X402 request (e.g., PAYMENT, VERIFICATION, SETTLEMENT)"
    )
    amount: Optional[float] = Field(None, description="Payment amount if applicable")
    currency: Optional[str] = Field(None, description="Currency code (e.g., USD)")
    status: str = Field(..., description="Request status (PENDING, COMPLETED, FAILED)")
    request_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original request payload"
    )
    response_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response payload received"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request metadata"
    )
    timestamp: str = Field(..., description="ISO timestamp when request was made")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "x402_001",
                "run_id": "run_abc123",
                "agent_id": "agent_payment_001",
                "request_type": "PAYMENT",
                "amount": 100.50,
                "currency": "USD",
                "status": "COMPLETED",
                "request_payload": {"recipient": "ACC-789", "memo": "Invoice #123"},
                "response_payload": {"confirmation_id": "CONF-456"},
                "metadata": {"retry_count": 0},
                "timestamp": "2026-01-10T10:06:00.000Z"
            }
        }


class RunSummary(BaseModel):
    """
    Run summary for listing runs.
    Provides overview without full replay data.
    """
    run_id: str = Field(..., description="Unique run identifier")
    project_id: str = Field(..., description="Project this run belongs to")
    agent_id: str = Field(..., description="Primary agent for this run")
    status: RunStatus = Field(..., description="Current run status")
    started_at: str = Field(..., description="ISO timestamp when run started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when run completed")
    memory_count: int = Field(
        default=0,
        ge=0,
        description="Number of memory records in this run"
    )
    event_count: int = Field(
        default=0,
        ge=0,
        description="Number of compliance events in this run"
    )
    request_count: int = Field(
        default=0,
        ge=0,
        description="Number of X402 requests in this run"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional run metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_abc123",
                "project_id": "proj_001",
                "agent_id": "agent_compliance_001",
                "status": "COMPLETED",
                "started_at": "2026-01-10T10:00:00.000Z",
                "completed_at": "2026-01-10T10:10:00.000Z",
                "memory_count": 5,
                "event_count": 3,
                "request_count": 2,
                "metadata": {"trigger": "scheduled"}
            }
        }


class RunDetail(BaseModel):
    """
    Detailed run information.
    Includes summary plus agent profile.
    """
    run_id: str = Field(..., description="Unique run identifier")
    project_id: str = Field(..., description="Project this run belongs to")
    status: RunStatus = Field(..., description="Current run status")
    agent_profile: AgentProfileRecord = Field(
        ...,
        description="Agent profile for this run"
    )
    started_at: str = Field(..., description="ISO timestamp when run started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when run completed")
    duration_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Run duration in milliseconds"
    )
    memory_count: int = Field(
        default=0,
        ge=0,
        description="Number of memory records"
    )
    event_count: int = Field(
        default=0,
        ge=0,
        description="Number of compliance events"
    )
    request_count: int = Field(
        default=0,
        ge=0,
        description="Number of X402 requests"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional run metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_abc123",
                "project_id": "proj_001",
                "status": "COMPLETED",
                "agent_profile": {
                    "agent_id": "agent_compliance_001",
                    "agent_name": "Compliance Checker",
                    "agent_type": "compliance",
                    "configuration": {},
                    "created_at": "2026-01-10T10:00:00.000Z"
                },
                "started_at": "2026-01-10T10:00:00.000Z",
                "completed_at": "2026-01-10T10:10:00.000Z",
                "duration_ms": 600000,
                "memory_count": 5,
                "event_count": 3,
                "request_count": 2,
                "metadata": {}
            }
        }


class RunReplayData(BaseModel):
    """
    Complete replay data for a run.
    Aggregates all records needed for deterministic replay.

    Per PRD Section 11 (Deterministic Replay):
    - Agent profile configuration
    - All agent_memory entries in chronological order
    - All compliance_events in chronological order
    - All x402_requests in chronological order
    - Validation that all linked records exist
    """
    run_id: str = Field(..., description="Unique run identifier")
    project_id: str = Field(..., description="Project this run belongs to")
    status: RunStatus = Field(..., description="Run status")
    agent_profile: AgentProfileRecord = Field(
        ...,
        description="Agent profile for deterministic configuration"
    )
    agent_memory: List[AgentMemoryRecord] = Field(
        default_factory=list,
        description="All memory records in chronological order"
    )
    compliance_events: List[ComplianceEventRecord] = Field(
        default_factory=list,
        description="All compliance events in chronological order"
    )
    x402_requests: List[X402RequestRecord] = Field(
        default_factory=list,
        description="All X402 requests in chronological order"
    )
    started_at: str = Field(..., description="ISO timestamp when run started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when run completed")
    replay_generated_at: str = Field(
        ...,
        description="ISO timestamp when this replay data was generated"
    )
    validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation results for linked records"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_abc123",
                "project_id": "proj_001",
                "status": "COMPLETED",
                "agent_profile": {
                    "agent_id": "agent_compliance_001",
                    "agent_name": "Compliance Checker",
                    "agent_type": "compliance",
                    "configuration": {},
                    "created_at": "2026-01-10T10:00:00.000Z"
                },
                "agent_memory": [],
                "compliance_events": [],
                "x402_requests": [],
                "started_at": "2026-01-10T10:00:00.000Z",
                "completed_at": "2026-01-10T10:10:00.000Z",
                "replay_generated_at": "2026-01-10T12:00:00.000Z",
                "validation": {
                    "all_records_present": True,
                    "chronological_order_verified": True
                }
            }
        }


class RunListResponse(BaseModel):
    """
    Response schema for GET /v1/public/{project_id}/runs.
    Returns list of run summaries with pagination info.
    """
    runs: List[RunSummary] = Field(
        default_factory=list,
        description="List of run summaries"
    )
    total: int = Field(..., description="Total number of runs")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "runs": [
                    {
                        "run_id": "run_abc123",
                        "project_id": "proj_001",
                        "agent_id": "agent_001",
                        "status": "COMPLETED",
                        "started_at": "2026-01-10T10:00:00.000Z",
                        "completed_at": "2026-01-10T10:10:00.000Z",
                        "memory_count": 5,
                        "event_count": 3,
                        "request_count": 2,
                        "metadata": {}
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20
            }
        }


class LatestRunInfo(BaseModel):
    """
    Minimal info about the latest run for stats display.
    """
    run_id: str = Field(..., description="Run identifier")
    status: str = Field(..., description="Run status")
    started_at: str = Field(..., description="When the run started")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_demo_001",
                "status": "COMPLETED",
                "started_at": "2026-01-10T10:00:00.000Z"
            }
        }


class ProjectStatsResponse(BaseModel):
    """
    Response schema for GET /v1/public/{project_id}/stats.
    Returns aggregate statistics for the Overview page.
    Per PRD Section 5.1: KPI strip with latest run status, ledger entries, memory items.
    """
    total_runs: int = Field(default=0, ge=0, description="Total number of runs")
    latest_run: Optional[LatestRunInfo] = Field(None, description="Info about the most recent run")
    total_x402_requests: int = Field(default=0, ge=0, description="Total X402 requests across all runs")
    total_memory_entries: int = Field(default=0, ge=0, description="Total memory entries across all runs")
    total_compliance_events: int = Field(default=0, ge=0, description="Total compliance events across all runs")

    class Config:
        json_schema_extra = {
            "example": {
                "total_runs": 5,
                "latest_run": {
                    "run_id": "run_demo_001",
                    "status": "COMPLETED",
                    "started_at": "2026-01-10T10:00:00.000Z"
                },
                "total_x402_requests": 12,
                "total_memory_entries": 25,
                "total_compliance_events": 18
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
                "detail": "Run not found: run_abc123",
                "error_code": "RUN_NOT_FOUND"
            }
        }
