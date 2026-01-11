"""
Agent data store.
For MVP demo (PRD Section 9), we use deterministic in-memory storage.
In production, this would connect to ZeroDB or a database.
Epic 12, Issue 1: Agent profiles storage.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.models.agent import Agent, AgentScope


class AgentStore:
    """
    In-memory agent store for deterministic demo.
    Per PRD Section 9: Demo setup must be deterministic.
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._initialize_demo_agents()

    def _initialize_demo_agents(self):
        """
        Initialize deterministic demo agents per PRD Section 9.
        Creates predefined agents for demo projects.
        """
        demo_agents = [
            # Agents for user_1 project 1
            Agent(
                id="agent_demo_001",
                did="did:web:ainative.dev:agents:researcher-alpha",
                role="researcher",
                name="Research Agent Alpha",
                description="Specialized agent for financial research and market data gathering",
                scope=AgentScope.PROJECT,
                project_id="proj_demo_u1_001",
                created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Agent(
                id="agent_demo_002",
                did="did:web:ainative.dev:agents:analyst-beta",
                role="analyst",
                name="Analysis Agent Beta",
                description="Data analysis and reporting agent for financial insights",
                scope=AgentScope.PROJECT,
                project_id="proj_demo_u1_001",
                created_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # Agents for user_1 project 2
            Agent(
                id="agent_demo_003",
                did="did:web:ainative.dev:agents:executor-gamma",
                role="executor",
                name="Executor Agent Gamma",
                description="Transaction execution and payment processing agent",
                scope=AgentScope.PROJECT,
                project_id="proj_demo_u1_002",
                created_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # Agents for user_2 project 1
            Agent(
                id="agent_demo_004",
                did="did:web:ainative.dev:agents:orchestrator-delta",
                role="orchestrator",
                name="Orchestrator Agent Delta",
                description="Multi-agent workflow orchestration for CrewAI",
                scope=AgentScope.GLOBAL,
                project_id="proj_demo_u2_001",
                created_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Agent(
                id="agent_demo_005",
                did="did:web:ainative.dev:agents:compliance-epsilon",
                role="compliance",
                name="Compliance Agent Epsilon",
                description="Regulatory compliance verification and KYC agent",
                scope=AgentScope.RESTRICTED,
                project_id="proj_demo_u2_002",
                created_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for agent in demo_agents:
            self._agents[agent.id] = agent

    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def get_by_project_id(self, project_id: str) -> List[Agent]:
        """
        Get all agents for a project.
        Returns empty list if no agents exist.
        """
        return [
            agent for agent in self._agents.values()
            if agent.project_id == project_id
        ]

    def get_by_did(self, did: str, project_id: str) -> Optional[Agent]:
        """
        Get agent by DID within a project.
        DIDs should be unique within a project.
        """
        for agent in self._agents.values():
            if agent.did == did and agent.project_id == project_id:
                return agent
        return None

    def create(self, agent: Agent) -> Agent:
        """
        Create a new agent.
        For production, this would insert into ZeroDB.
        """
        self._agents[agent.id] = agent
        return agent

    def update(self, agent: Agent) -> Agent:
        """Update an existing agent."""
        if agent.id not in self._agents:
            raise ValueError(f"Agent not found: {agent.id}")
        agent.updated_at = datetime.now(timezone.utc)
        self._agents[agent.id] = agent
        return agent

    def delete(self, agent_id: str) -> bool:
        """Delete an agent by ID."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def count_by_project_id(self, project_id: str) -> int:
        """Count agents in a project."""
        return len(self.get_by_project_id(project_id))

    def exists_did_in_project(self, did: str, project_id: str) -> bool:
        """Check if a DID already exists in a project."""
        return self.get_by_did(did, project_id) is not None


# Global singleton instance for demo
agent_store = AgentStore()
