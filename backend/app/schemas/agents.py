"""
Agent API schemas for request/response validation.
These schemas define the contract with API consumers per DX Contract.
Epic 12, Issue 1: Agent profiles with did, role, name, description, scope.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from app.models.agent import AgentScope


class AgentRole(str, Enum):
    """
    Agent role enumeration per Issue #61.
    Defines the role/function of a CrewAI agent.
    """
    ANALYST = "analyst"
    COMPLIANCE = "compliance"
    TRANSACTION = "transaction"
    ORCHESTRATOR = "orchestrator"


class AgentCreateRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/agents.
    Creates a new agent profile within a project.
    Per Issue #61: DID format validation and role enum validation.
    """
    did: str = Field(
        ...,
        description="Decentralized Identifier for the agent (must be did:key:z6Mk... format)",
        min_length=1,
        max_length=256,
        examples=["did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"]
    )
    role: AgentRole = Field(
        ...,
        description="Agent role (analyst, compliance, transaction, orchestrator)",
        examples=["analyst"]
    )
    name: str = Field(
        ...,
        description="Human-readable agent name",
        min_length=1,
        max_length=200,
        examples=["Research Agent Alpha"]
    )
    description: Optional[str] = Field(
        None,
        description="Agent description and purpose",
        max_length=1000,
        examples=["Specialized agent for financial research and data gathering"]
    )
    scope: AgentScope = Field(
        AgentScope.RUN,
        description="Operational scope of the agent (SYSTEM, PROJECT, RUN)"
    )

    @field_validator('did')
    @classmethod
    def validate_did_format(cls, v: str) -> str:
        """
        Validate DID format per Issue #61.
        Must be did:key:z6Mk... format.
        """
        if not v.startswith("did:key:"):
            raise ValueError("DID must start with 'did:key:' prefix")

        # Extract the identifier part after did:key:
        identifier = v[8:]  # Remove "did:key:" prefix

        if not identifier.startswith("z6Mk"):
            raise ValueError("DID key identifier must start with 'z6Mk'")

        if len(identifier) < 10:
            raise ValueError("DID key identifier is too short")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "role": "analyst",
                "name": "Research Agent Alpha",
                "description": "Specialized agent for financial research and data gathering",
                "scope": "RUN"
            }
        }


class UpdateAgentRequest(BaseModel):
    """
    Request schema for PATCH /v1/public/{project_id}/agents/{agent_id}.
    Updates an existing agent profile. All fields are optional.
    """
    role: Optional[AgentRole] = Field(
        None,
        description="Agent role (analyst, compliance, transaction, orchestrator)",
        examples=["analyst"]
    )
    name: Optional[str] = Field(
        None,
        description="Human-readable agent name",
        min_length=1,
        max_length=200,
        examples=["Updated Agent Name"]
    )
    description: Optional[str] = Field(
        None,
        description="Agent description and purpose",
        max_length=1000,
        examples=["Updated agent description"]
    )
    scope: Optional[AgentScope] = Field(
        None,
        description="Operational scope of the agent (SYSTEM, PROJECT, RUN)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "analyst",
                "name": "Updated Research Agent",
                "description": "Updated agent description",
                "scope": "PROJECT"
            }
        }


class AgentResponse(BaseModel):
    """
    Response schema for agent operations.
    Returns full agent profile with all fields.
    Note: agent_id is the primary field, id kept for backward compatibility.
    """
    id: str = Field(..., description="Unique agent identifier (deprecated, use agent_id)")
    agent_id: str = Field(..., description="Unique agent identifier (primary field)")
    did: str = Field(..., description="Decentralized Identifier for the agent")
    role: str = Field(..., description="Agent role")
    name: str = Field(..., description="Human-readable agent name")
    description: Optional[str] = Field(None, description="Agent description and purpose")
    scope: AgentScope = Field(..., description="Operational scope of the agent")
    project_id: str = Field(..., description="Project this agent belongs to")
    created_at: datetime = Field(..., description="Timestamp of agent creation")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last update")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "agent_abc123",
                "agent_id": "agent_abc123",
                "did": "did:web:agent.example.com:researcher-01",
                "role": "researcher",
                "name": "Research Agent Alpha",
                "description": "Specialized agent for financial research and data gathering",
                "scope": "PROJECT",
                "project_id": "proj_demo_u1_001",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }


class AgentListResponse(BaseModel):
    """
    Response schema for listing agents.
    Returns array of agents for a project.
    """
    agents: List[AgentResponse] = Field(
        default_factory=list,
        description="List of agents in the project"
    )
    total: int = Field(..., description="Total number of agents")

    class Config:
        json_schema_extra = {
            "example": {
                "agents": [
                    {
                        "id": "agent_abc123",
                        "did": "did:web:agent.example.com:researcher-01",
                        "role": "researcher",
                        "name": "Research Agent Alpha",
                        "description": "Specialized agent for financial research",
                        "scope": "PROJECT",
                        "project_id": "proj_demo_u1_001",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z"
                    },
                    {
                        "id": "agent_xyz789",
                        "did": "did:web:agent.example.com:analyst-02",
                        "role": "analyst",
                        "name": "Analysis Agent Beta",
                        "description": "Data analysis and reporting agent",
                        "scope": "PROJECT",
                        "project_id": "proj_demo_u1_001",
                        "created_at": "2025-01-02T00:00:00Z",
                        "updated_at": "2025-01-02T00:00:00Z"
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
                "detail": "Agent not found: agent_abc123",
                "error_code": "AGENT_NOT_FOUND"
            }
        }
