"""
Agent Memory API schemas for request/response validation.
Implements Epic 12 Issue 2: Agent memory persistence.

Per PRD Section 6 (ZeroDB Integration):
- Agent memory storage for decisions and context
- Namespace scoping for multi-agent isolation
- Support for various memory types (decisions, context, state)

Memory Schema Fields:
- agent_id: Unique identifier for the agent
- run_id: Identifier for the agent's execution run
- memory_type: Type of memory (decision, context, state, etc.)
- content: The actual memory content (text or structured data)
- metadata: Optional additional metadata for classification
- timestamp: When the memory was created
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class MemoryType(str, Enum):
    """
    Supported memory types for agent memory storage.

    Per PRD Section 6: Agent memory supports multiple types
    for different agent decision contexts.
    """
    DECISION = "decision"
    CONTEXT = "context"
    STATE = "state"
    OBSERVATION = "observation"
    GOAL = "goal"
    PLAN = "plan"
    RESULT = "result"
    ERROR = "error"


class AgentMemoryCreateRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/agent-memory.

    Epic 12 Issue 2: Agent memory persistence.

    Required Fields:
    - agent_id: Unique identifier for the agent
    - run_id: Identifier for the agent's execution run
    - memory_type: Type of memory being stored
    - content: The memory content (required, non-empty)

    Optional Fields:
    - metadata: Additional classification metadata
    - namespace: For multi-agent isolation (defaults to 'default')
    """
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the agent (required)"
    )
    run_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Identifier for the agent's execution run (required)"
    )
    memory_type: MemoryType = Field(
        ...,
        description="Type of memory being stored (decision, context, state, etc.)"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="The memory content (required, non-empty)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for memory classification and filtering"
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Namespace for multi-agent isolation. Defaults to 'default'"
    )

    @field_validator('agent_id', 'run_id')
    @classmethod
    def validate_identifier(cls, v):
        """Validate identifier format."""
        if not v or not v.strip():
            raise ValueError("Identifier cannot be empty or whitespace")
        return v.strip()

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Ensure content is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v.strip()

    @field_validator('namespace')
    @classmethod
    def validate_namespace(cls, v):
        """Validate namespace format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 255:
                raise ValueError("Namespace cannot exceed 255 characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "compliance_agent_001",
                "run_id": "run_20260110_123456",
                "memory_type": "decision",
                "content": "Decided to approve transaction TX-12345 based on compliance rules",
                "metadata": {
                    "transaction_id": "TX-12345",
                    "decision_type": "approval",
                    "confidence": 0.95
                },
                "namespace": "compliance_team"
            }
        }


class AgentMemoryResponse(BaseModel):
    """
    Response schema for agent memory entries.

    Returns the stored memory with generated ID and timestamp.
    """
    memory_id: str = Field(
        ...,
        description="Unique identifier for this memory entry"
    )
    agent_id: str = Field(
        ...,
        description="Agent identifier"
    )
    run_id: str = Field(
        ...,
        description="Execution run identifier"
    )
    memory_type: MemoryType = Field(
        ...,
        description="Type of memory"
    )
    content: str = Field(
        ...,
        description="Memory content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Memory metadata"
    )
    namespace: str = Field(
        ...,
        description="Namespace for isolation"
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp when memory was created"
    )
    project_id: str = Field(
        ...,
        description="Project identifier"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_abc123def456",
                "agent_id": "compliance_agent_001",
                "run_id": "run_20260110_123456",
                "memory_type": "decision",
                "content": "Decided to approve transaction TX-12345 based on compliance rules",
                "metadata": {
                    "transaction_id": "TX-12345",
                    "decision_type": "approval",
                    "confidence": 0.95
                },
                "namespace": "compliance_team",
                "timestamp": "2026-01-10T12:34:56.789Z",
                "project_id": "proj_xyz789"
            }
        }


class AgentMemoryCreateResponse(BaseModel):
    """
    Response schema for POST /v1/public/{project_id}/agent-memory.

    Confirms memory storage with ID and timestamp.
    """
    memory_id: str = Field(
        ...,
        description="Unique identifier for the created memory entry"
    )
    agent_id: str = Field(
        ...,
        description="Agent identifier"
    )
    run_id: str = Field(
        ...,
        description="Execution run identifier"
    )
    memory_type: MemoryType = Field(
        ...,
        description="Type of memory stored"
    )
    namespace: str = Field(
        ...,
        description="Namespace where memory was stored"
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp when memory was created"
    )
    created: bool = Field(
        default=True,
        description="Always true for new memory entries"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_abc123def456",
                "agent_id": "compliance_agent_001",
                "run_id": "run_20260110_123456",
                "memory_type": "decision",
                "namespace": "compliance_team",
                "timestamp": "2026-01-10T12:34:56.789Z",
                "created": True
            }
        }


class AgentMemoryListResponse(BaseModel):
    """
    Response schema for GET /v1/public/{project_id}/agent-memory.

    Returns paginated list of agent memories with filtering support.
    """
    memories: List[AgentMemoryResponse] = Field(
        default_factory=list,
        description="List of agent memory entries"
    )
    total: int = Field(
        ...,
        description="Total number of memories matching filters"
    )
    limit: int = Field(
        ...,
        description="Maximum number of results returned"
    )
    offset: int = Field(
        ...,
        description="Offset for pagination"
    )
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied to the query"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "memories": [
                    {
                        "memory_id": "mem_abc123def456",
                        "agent_id": "compliance_agent_001",
                        "run_id": "run_20260110_123456",
                        "memory_type": "decision",
                        "content": "Decided to approve transaction TX-12345",
                        "metadata": {"transaction_id": "TX-12345"},
                        "namespace": "compliance_team",
                        "timestamp": "2026-01-10T12:34:56.789Z",
                        "project_id": "proj_xyz789"
                    }
                ],
                "total": 1,
                "limit": 100,
                "offset": 0,
                "filters_applied": {
                    "agent_id": "compliance_agent_001"
                }
            }
        }
