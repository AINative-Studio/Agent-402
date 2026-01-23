"""
Agent Interaction Schemas for Agent Hire/Task APIs.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 5 (Agent Personas):
- Agents can be hired for tasks
- Tasks are submitted and tracked
- Results are returned upon completion

Per PRD Section 8 (X402 Protocol):
- All agent interactions require X402 payment header
- Payments tracked and linked to tasks
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class AgentInteractionStatus(str, Enum):
    """
    Status enumeration for agent hire/task interactions.
    """
    AVAILABLE = "available"       # Agent is available for hire
    HIRED = "hired"               # Agent is hired for a task
    WORKING = "working"           # Agent is working on a task
    COMPLETED = "completed"       # Task completed successfully
    FAILED = "failed"             # Task failed
    CANCELLED = "cancelled"       # Task was cancelled


class TaskStatus(str, Enum):
    """
    Task execution status.
    """
    PENDING = "pending"           # Task submitted, awaiting execution
    IN_PROGRESS = "in_progress"   # Task is being executed
    COMPLETED = "completed"       # Task completed successfully
    FAILED = "failed"             # Task failed
    CANCELLED = "cancelled"       # Task was cancelled


class HireAgentRequest(BaseModel):
    """
    Request schema for hiring an agent.

    POST /agents/hire
    Requires X402 payment header.
    """
    agent_id: str = Field(
        ...,
        description="ID of the agent to hire"
    )
    task_description: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Description of the task to perform"
    )
    payment_amount_usdc: str = Field(
        ...,
        description="Payment amount in USDC (6 decimals)"
    )
    max_duration_seconds: Optional[int] = Field(
        3600,
        description="Maximum task duration in seconds (default: 1 hour)"
    )
    priority: Optional[str] = Field(
        "normal",
        description="Task priority: low, normal, high"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional task metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_analyst_001",
                "task_description": "Analyze financial data for Q4 2025",
                "payment_amount_usdc": "10.000000",
                "max_duration_seconds": 7200,
                "priority": "high",
                "metadata": {"report_format": "pdf"}
            }
        }


class HireAgentResponse(BaseModel):
    """
    Response schema for agent hire request.
    """
    hire_id: str = Field(
        ...,
        description="Unique hire transaction ID"
    )
    agent_id: str = Field(
        ...,
        description="ID of the hired agent"
    )
    task_id: str = Field(
        ...,
        description="ID of the created task"
    )
    status: AgentInteractionStatus = Field(
        ...,
        description="Current hire status"
    )
    payment_receipt_id: str = Field(
        ...,
        description="Payment receipt ID for the hire transaction"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when hire was created"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hire_id": "hire_abc123def456",
                "agent_id": "agent_analyst_001",
                "task_id": "task_xyz789",
                "status": "hired",
                "payment_receipt_id": "pay_rcpt_a1b2c3d4",
                "estimated_completion": "2026-01-23T14:00:00Z",
                "created_at": "2026-01-23T12:00:00Z"
            }
        }


class TaskSubmitRequest(BaseModel):
    """
    Request schema for submitting a task to a hired agent.

    POST /agents/tasks
    Requires existing hire transaction.
    """
    hire_id: str = Field(
        ...,
        description="Hire transaction ID from /agents/hire"
    )
    input_data: Dict[str, Any] = Field(
        ...,
        description="Task input data"
    )
    callback_url: Optional[str] = Field(
        None,
        description="Optional webhook URL for task completion notification"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hire_id": "hire_abc123def456",
                "input_data": {
                    "data_source": "financial_db",
                    "date_range": {"start": "2025-10-01", "end": "2025-12-31"},
                    "metrics": ["revenue", "profit_margin", "growth_rate"]
                },
                "callback_url": "https://api.example.com/webhooks/task-complete"
            }
        }


class TaskSubmitResponse(BaseModel):
    """
    Response schema for task submission.
    """
    task_id: str = Field(
        ...,
        description="Unique task ID"
    )
    hire_id: str = Field(
        ...,
        description="Associated hire transaction ID"
    )
    status: TaskStatus = Field(
        ...,
        description="Current task status"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when task was submitted"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_xyz789",
                "hire_id": "hire_abc123def456",
                "status": "pending",
                "estimated_completion": "2026-01-23T14:00:00Z",
                "created_at": "2026-01-23T12:00:00Z"
            }
        }


class AgentStatusResponse(BaseModel):
    """
    Response schema for agent status query.

    GET /agents/{agent_id}/status
    """
    agent_id: str = Field(
        ...,
        description="Agent identifier"
    )
    status: AgentInteractionStatus = Field(
        ...,
        description="Current agent status"
    )
    current_task_id: Optional[str] = Field(
        None,
        description="ID of current task (if working)"
    )
    current_hire_id: Optional[str] = Field(
        None,
        description="ID of current hire (if hired)"
    )
    reputation_score: Optional[int] = Field(
        None,
        description="Agent's reputation score from Arc blockchain"
    )
    trust_tier: Optional[int] = Field(
        None,
        description="Agent's trust tier (0-4)"
    )
    total_tasks_completed: int = Field(
        0,
        description="Total number of tasks completed"
    )
    availability: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent availability information"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_analyst_001",
                "status": "available",
                "current_task_id": None,
                "current_hire_id": None,
                "reputation_score": 85,
                "trust_tier": 3,
                "total_tasks_completed": 142,
                "availability": {
                    "is_available": True,
                    "next_available": None
                }
            }
        }


class TaskResult(BaseModel):
    """
    Response schema for task result.

    GET /tasks/{task_id}/result
    """
    task_id: str = Field(
        ...,
        description="Task identifier"
    )
    hire_id: str = Field(
        ...,
        description="Associated hire transaction ID"
    )
    agent_id: str = Field(
        ...,
        description="Agent that executed the task"
    )
    status: TaskStatus = Field(
        ...,
        description="Final task status"
    )
    output_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Task output data"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if task failed"
    )
    execution_time_seconds: Optional[float] = Field(
        None,
        description="Task execution time in seconds"
    )
    payment_receipt_id: str = Field(
        ...,
        description="Payment receipt ID"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="Timestamp when task started"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when task completed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional result metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_xyz789",
                "hire_id": "hire_abc123def456",
                "agent_id": "agent_analyst_001",
                "status": "completed",
                "output_data": {
                    "report_url": "https://storage.example.com/reports/q4-2025.pdf",
                    "summary": "Q4 2025 shows 15% YoY revenue growth",
                    "metrics": {
                        "revenue": 1250000,
                        "profit_margin": 0.23,
                        "growth_rate": 0.15
                    }
                },
                "error_message": None,
                "execution_time_seconds": 45.7,
                "payment_receipt_id": "pay_rcpt_a1b2c3d4",
                "started_at": "2026-01-23T12:00:05Z",
                "completed_at": "2026-01-23T12:00:51Z",
                "metadata": {"report_format": "pdf"}
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response for agent interaction endpoints.
    """
    detail: str = Field(
        ...,
        description="Human-readable error message"
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Agent not available for hire",
                "error_code": "AGENT_NOT_AVAILABLE"
            }
        }
