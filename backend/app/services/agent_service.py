"""
Agent service layer.
Implements business logic for agent operations.
Epic 12, Issue 1: CrewAI agent profiles management.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.models.agent import Agent, AgentScope
from app.services.agent_store import agent_store
from app.core.errors import (
    ProjectNotFoundError,
    UnauthorizedError,
    AgentNotFoundError,
    DuplicateAgentDIDError
)


class AgentService:
    """
    Agent service for business logic.
    Separates business logic from HTTP layer.
    """

    def __init__(self):
        self.store = agent_store

    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID."""
        return f"agent_{uuid.uuid4().hex[:12]}"

    def list_project_agents(self, project_id: str) -> List[Agent]:
        """
        List all agents for a project.
        Returns empty list if no agents exist.

        Args:
            project_id: Project identifier

        Returns:
            List of agents in the project (empty list if none)
        """
        return self.store.get_by_project_id(project_id)

    def get_agent(self, agent_id: str, project_id: str) -> Agent:
        """
        Get a single agent by ID.
        Validates that agent belongs to the project.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier

        Returns:
            Agent if found and belongs to project

        Raises:
            AgentNotFoundError: If agent doesn't exist or doesn't belong to project
        """
        agent = self.store.get_by_id(agent_id)

        if not agent:
            raise AgentNotFoundError(agent_id)

        if agent.project_id != project_id:
            raise AgentNotFoundError(agent_id)

        return agent

    def create_agent(
        self,
        project_id: str,
        did: str,
        role: str,
        name: str,
        description: Optional[str] = None,
        scope: AgentScope = AgentScope.PROJECT
    ) -> Agent:
        """
        Create a new agent in a project.

        Args:
            project_id: Project identifier
            did: Decentralized Identifier for the agent
            role: Agent role
            name: Human-readable agent name
            description: Optional agent description
            scope: Operational scope of the agent

        Returns:
            Created agent

        Raises:
            DuplicateAgentDIDError: If DID already exists in the project
        """
        # Check for duplicate DID in project
        if self.store.exists_did_in_project(did, project_id):
            raise DuplicateAgentDIDError(did, project_id)

        now = datetime.now(timezone.utc)
        agent = Agent(
            id=self._generate_agent_id(),
            did=did,
            role=role,
            name=name,
            description=description,
            scope=scope,
            project_id=project_id,
            created_at=now,
            updated_at=now
        )

        return self.store.create(agent)

    def count_project_agents(self, project_id: str) -> int:
        """Count total agents for a project."""
        return self.store.count_by_project_id(project_id)

    def delete_agent(self, agent_id: str, project_id: str) -> bool:
        """
        Delete an agent from a project.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier

        Returns:
            True if deleted, False otherwise

        Raises:
            AgentNotFoundError: If agent doesn't exist or doesn't belong to project
        """
        # First verify the agent exists and belongs to the project
        agent = self.get_agent(agent_id, project_id)
        return self.store.delete(agent.id)


# Global service instance
agent_service = AgentService()
