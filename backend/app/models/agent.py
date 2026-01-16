"""
Agent domain model.
Represents CrewAI agent profiles per PRD Section 5 (Agent Personas).
Epic 12, Issue 1: Agent profiles with did, role, name, description, scope.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AgentScope(str, Enum):
    """
    Agent scope enumeration.
    Defines the operational scope of an agent.
    Per Issue #61: SYSTEM, PROJECT, RUN scopes.
    """
    SYSTEM = "SYSTEM"       # System-wide scope across all projects
    PROJECT = "PROJECT"     # Limited to a single project
    RUN = "RUN"            # Limited to a single run (default)


@dataclass
class Agent:
    """
    Internal agent model.
    Represents a CrewAI agent profile within a project.

    Attributes:
        id: Unique agent identifier (auto-generated)
        did: Decentralized Identifier for the agent
        role: Agent role (e.g., "researcher", "analyst", "executor")
        name: Human-readable agent name
        description: Agent description and purpose
        scope: Operational scope of the agent
        project_id: Project this agent belongs to
        created_at: Timestamp of agent creation
        updated_at: Timestamp of last update
    """
    id: str
    did: str
    role: str
    name: str
    project_id: str
    description: Optional[str] = None
    scope: AgentScope = AgentScope.RUN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "did": self.did,
            "role": self.role,
            "name": self.name,
            "description": self.description,
            "scope": self.scope.value,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
