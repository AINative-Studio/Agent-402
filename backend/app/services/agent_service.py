"""
Agent service layer.
Implements business logic for agent operations.
Epic 12, Issue 1: CrewAI agent profiles management.

Updated to use ZeroDB for persistence instead of in-memory storage.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.models.agent import Agent, AgentScope
from app.services.zerodb_client import get_zerodb_client
from app.core.errors import (
    ProjectNotFoundError,
    UnauthorizedError,
    AgentNotFoundError,
    DuplicateAgentDIDError
)

logger = logging.getLogger(__name__)

# ZeroDB table name for agents
AGENTS_TABLE = "agents"


def _row_to_agent(row_data: dict) -> Agent:
    """
    Convert a ZeroDB row to an Agent model.

    Args:
        row_data: Row data from ZeroDB (may include row_id wrapper or direct data)

    Returns:
        Agent model instance
    """
    # Handle both direct row_data and wrapped response formats
    data = row_data.get("row_data", row_data)

    # Parse timestamps
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")

    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    elif created_at is None:
        created_at = datetime.now(timezone.utc)

    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    elif updated_at is None:
        updated_at = datetime.now(timezone.utc)

    # Parse scope enum
    scope_value = data.get("scope", "PROJECT")
    try:
        scope = AgentScope(scope_value)
    except ValueError:
        scope = AgentScope.PROJECT

    return Agent(
        id=data.get("agent_id", data.get("id", "")),
        did=data.get("did", ""),
        role=data.get("role", ""),
        name=data.get("name", ""),
        description=data.get("description"),
        scope=scope,
        project_id=data.get("project_id", ""),
        created_at=created_at,
        updated_at=updated_at
    )


def _agent_to_row(agent: Agent) -> dict:
    """
    Convert an Agent model to ZeroDB row data.

    Args:
        agent: Agent model instance

    Returns:
        Dictionary suitable for ZeroDB insert/update
    """
    return {
        "agent_id": agent.id,
        "project_id": agent.project_id,
        "name": agent.name,
        "role": agent.role,
        "did": agent.did,
        "status": "active",
        "config": {
            "description": agent.description,
            "scope": agent.scope.value
        },
        "created_at": agent.created_at.isoformat() if agent.created_at else datetime.now(timezone.utc).isoformat(),
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else datetime.now(timezone.utc).isoformat()
    }


class AgentService:
    """
    Agent service for business logic.
    Separates business logic from HTTP layer.
    Uses ZeroDB for persistent storage.
    """

    def __init__(self, client=None):
        """
        Initialize the agent service.

        Args:
            client: Optional ZeroDB client instance (for testing)
        """
        self._client = client

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID."""
        return f"agent_{uuid.uuid4().hex[:12]}"

    async def list_project_agents(self, project_id: str) -> List[Agent]:
        """
        List all agents for a project.
        Returns empty list if no agents exist.

        Args:
            project_id: Project identifier

        Returns:
            List of agents in the project (empty list if none)
        """
        try:
            result = await self.client.query_rows(
                table_name=AGENTS_TABLE,
                filter={"project_id": project_id},
                limit=1000
            )

            rows = result.get("rows", [])
            agents = [_row_to_agent(row) for row in rows]

            logger.debug(f"Listed {len(agents)} agents for project {project_id}")
            return agents

        except Exception as e:
            logger.error(f"Error listing agents for project {project_id}: {e}")
            # Return empty list on error to maintain graceful degradation
            return []

    async def get_agent(self, agent_id: str, project_id: str) -> Agent:
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
        try:
            result = await self.client.query_rows(
                table_name=AGENTS_TABLE,
                filter={"agent_id": agent_id},
                limit=1
            )

            rows = result.get("rows", [])

            if not rows:
                raise AgentNotFoundError(agent_id)

            agent = _row_to_agent(rows[0])

            if agent.project_id != project_id:
                raise AgentNotFoundError(agent_id)

            return agent

        except AgentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            raise AgentNotFoundError(agent_id)

    async def create_agent(
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
        if await self._exists_did_in_project(did, project_id):
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

        try:
            row_data = _agent_to_row(agent)
            result = await self.client.insert_row(AGENTS_TABLE, row_data)

            logger.info(f"Created agent {agent.id} in project {project_id}")
            return agent

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise

    async def count_project_agents(self, project_id: str) -> int:
        """Count total agents for a project."""
        try:
            agents = await self.list_project_agents(project_id)
            return len(agents)
        except Exception as e:
            logger.error(f"Error counting agents for project {project_id}: {e}")
            return 0

    async def delete_agent(self, agent_id: str, project_id: str) -> bool:
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
        agent = await self.get_agent(agent_id, project_id)

        try:
            # Query to find the row_id for this agent
            result = await self.client.query_rows(
                table_name=AGENTS_TABLE,
                filter={"agent_id": agent_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                return False

            # Get the row_id from the result
            row_id = rows[0].get("row_id", rows[0].get("id"))

            if row_id:
                await self.client.delete_row(AGENTS_TABLE, str(row_id))
                logger.info(f"Deleted agent {agent_id} from project {project_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            return False

    async def _exists_did_in_project(self, did: str, project_id: str) -> bool:
        """
        Check if a DID already exists in a project.

        Args:
            did: Decentralized Identifier to check
            project_id: Project identifier

        Returns:
            True if DID exists in project, False otherwise
        """
        try:
            result = await self.client.query_rows(
                table_name=AGENTS_TABLE,
                filter={"did": did, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            return len(rows) > 0

        except Exception as e:
            logger.error(f"Error checking DID existence: {e}")
            return False

    async def update_agent(
        self,
        agent_id: str,
        project_id: str,
        name: Optional[str] = None,
        role: Optional[str] = None,
        description: Optional[str] = None,
        scope: Optional[AgentScope] = None
    ) -> Agent:
        """
        Update an existing agent.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier
            name: New name (optional)
            role: New role (optional)
            description: New description (optional)
            scope: New scope (optional)

        Returns:
            Updated agent

        Raises:
            AgentNotFoundError: If agent doesn't exist or doesn't belong to project
        """
        # First get the existing agent
        agent = await self.get_agent(agent_id, project_id)

        # Apply updates
        if name is not None:
            agent.name = name
        if role is not None:
            agent.role = role
        if description is not None:
            agent.description = description
        if scope is not None:
            agent.scope = scope

        agent.updated_at = datetime.now(timezone.utc)

        try:
            # Query to find the row_id for this agent
            result = await self.client.query_rows(
                table_name=AGENTS_TABLE,
                filter={"agent_id": agent_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise AgentNotFoundError(agent_id)

            row_id = rows[0].get("row_id", rows[0].get("id"))

            if row_id:
                row_data = _agent_to_row(agent)
                await self.client.update_row(AGENTS_TABLE, str(row_id), row_data)
                logger.info(f"Updated agent {agent_id}")

            return agent

        except AgentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            raise


# Global service instance
agent_service = AgentService()
