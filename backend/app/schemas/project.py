"""
Project API schemas for request/response validation.
These schemas define the contract with API consumers per DX Contract.

Issue #123: Enhanced Projects API for agent task management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.project import ProjectStatus, ProjectTier


class ProjectWorkflowStatus(str, Enum):
    """
    Extended project status for workflow management.
    Issue #123: Status workflow (draft -> active -> completed -> archived).
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class AgentRole(str, Enum):
    """
    Agent role within a project.
    Issue #123: Role-based agent associations.
    """
    EXECUTOR = "executor"
    OBSERVER = "observer"
    ADMIN = "admin"
    MEMBER = "member"


class TaskStatus(str, Enum):
    """
    Task status for project task tracking.
    Issue #123: Task tracking per project.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectResponse(BaseModel):
    """
    Project response schema for GET /v1/public/projects.
    Per Epic 1 Story 2: id, name, status, tier.
    """
    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(..., description="Project status (ACTIVE, INACTIVE, SUSPENDED)")
    tier: ProjectTier = Field(..., description="Project tier (FREE, STARTER, PRO, ENTERPRISE)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "proj_abc123",
                "name": "My Agent Project",
                "status": "ACTIVE",
                "tier": "FREE"
            }
        }


class ProjectListResponse(BaseModel):
    """
    Response schema for listing projects.
    Returns array of projects for authenticated user.
    """
    projects: List[ProjectResponse] = Field(
        default_factory=list,
        description="List of projects owned by the authenticated user"
    )
    total: int = Field(..., description="Total number of projects")

    class Config:
        json_schema_extra = {
            "example": {
                "projects": [
                    {
                        "id": "proj_abc123",
                        "name": "My Agent Project",
                        "status": "ACTIVE",
                        "tier": "FREE"
                    },
                    {
                        "id": "proj_xyz789",
                        "name": "Production Project",
                        "status": "ACTIVE",
                        "tier": "PRO"
                    }
                ],
                "total": 2
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
                "detail": "Invalid or missing API key",
                "error_code": "INVALID_API_KEY"
            }
        }


# Issue #123: New schemas for enhanced Projects API


class ProjectAgentAssociationRequest(BaseModel):
    """
    Request schema for associating an agent with a project.
    POST /v1/public/projects/{id}/agents
    """
    agent_did: str = Field(..., description="Agent DID (Decentralized Identifier)")
    role: AgentRole = Field(
        default=AgentRole.MEMBER,
        description="Agent role within the project"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_did": "did:example:agent123",
                "role": "executor"
            }
        }


class ProjectAgentAssociationResponse(BaseModel):
    """
    Response schema for agent association.
    """
    project_id: str = Field(..., description="Project identifier")
    agent_did: str = Field(..., description="Agent DID")
    role: str = Field(..., description="Agent role")
    associated_at: datetime = Field(..., description="Association timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "agent_did": "did:example:agent123",
                "role": "executor",
                "associated_at": "2025-01-15T10:30:00Z"
            }
        }


class ProjectAgentListResponse(BaseModel):
    """
    Response schema for listing agents associated with a project.
    GET /v1/public/projects/{id}/agents
    """
    agents: List[ProjectAgentAssociationResponse] = Field(
        default_factory=list,
        description="List of associated agents"
    )
    total: int = Field(..., description="Total number of associated agents")

    class Config:
        json_schema_extra = {
            "example": {
                "agents": [
                    {
                        "project_id": "proj_abc123",
                        "agent_did": "did:example:agent123",
                        "role": "executor",
                        "associated_at": "2025-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class ProjectTaskTrackRequest(BaseModel):
    """
    Request schema for tracking a task under a project.
    POST /v1/public/projects/{id}/tasks
    """
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Task status"
    )
    agent_did: Optional[str] = Field(
        None, description="Agent DID that executed the task"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Task result data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "completed",
                "agent_did": "did:example:agent123",
                "result": {"output": "success"}
            }
        }


class ProjectTaskResponse(BaseModel):
    """
    Response schema for a tracked task.
    """
    project_id: str = Field(..., description="Project identifier")
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    agent_did: Optional[str] = Field(None, description="Agent DID")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    tracked_at: datetime = Field(..., description="Tracking timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "task_id": "task_abc123",
                "status": "completed",
                "agent_did": "did:example:agent123",
                "result": {"output": "success"},
                "tracked_at": "2025-01-15T10:30:00Z"
            }
        }


class ProjectTaskListResponse(BaseModel):
    """
    Response schema for listing tasks tracked under a project.
    GET /v1/public/projects/{id}/tasks
    """
    tasks: List[ProjectTaskResponse] = Field(
        default_factory=list,
        description="List of tracked tasks"
    )
    total: int = Field(..., description="Total number of tracked tasks")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "project_id": "proj_abc123",
                        "task_id": "task_abc123",
                        "status": "completed",
                        "tracked_at": "2025-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class ProjectPaymentLinkRequest(BaseModel):
    """
    Request schema for linking a payment to a project.
    POST /v1/public/projects/{id}/payments
    """
    payment_receipt_id: str = Field(
        ..., description="X402 payment receipt ID"
    )
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")

    class Config:
        json_schema_extra = {
            "example": {
                "payment_receipt_id": "x402_req_abc123",
                "amount": 100.50,
                "currency": "USD"
            }
        }


class ProjectPaymentResponse(BaseModel):
    """
    Response schema for a linked payment.
    """
    project_id: str = Field(..., description="Project identifier")
    payment_receipt_id: str = Field(..., description="Payment receipt ID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    linked_at: datetime = Field(..., description="Link timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "payment_receipt_id": "x402_req_abc123",
                "amount": 100.50,
                "currency": "USD",
                "linked_at": "2025-01-15T10:30:00Z"
            }
        }


class ProjectPaymentSummaryResponse(BaseModel):
    """
    Response schema for project payment summary.
    GET /v1/public/projects/{id}/payments
    """
    total_spent: float = Field(..., description="Total amount spent")
    payment_count: int = Field(..., description="Number of payments")
    payments: List[ProjectPaymentResponse] = Field(
        default_factory=list,
        description="List of payments"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_spent": 225.25,
                "payment_count": 3,
                "payments": [
                    {
                        "project_id": "proj_abc123",
                        "payment_receipt_id": "x402_req_abc123",
                        "amount": 100.50,
                        "currency": "USD",
                        "linked_at": "2025-01-15T10:30:00Z"
                    }
                ]
            }
        }


class ProjectStatusUpdateRequest(BaseModel):
    """
    Request schema for updating project status.
    PATCH /v1/public/projects/{id}/status
    """
    status: ProjectWorkflowStatus = Field(
        ..., description="New project status"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "active"
            }
        }
