"""
Agent and Task operations for ainative-agent SDK.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

from .client import AsyncHTTPClient
from .types import Agent, Task, TaskConfig


class AgentOperations:
    """
    CRUD operations for agent resources.

    All methods are async and return strongly-typed models.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client

    async def create(self, config: dict[str, Any]) -> Agent:
        """
        Create a new agent.

        Args:
            config: Agent configuration dict (name, role, description, scope, …)

        Returns:
            The created Agent.
        """
        data = await self._client.post("/agents", json=config)
        return Agent.model_validate(data)

    async def get(self, agent_id: str) -> Agent:
        """
        Retrieve a single agent by ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            The Agent.

        Raises:
            NotFoundError: When the agent does not exist.
        """
        data = await self._client.get(f"/agents/{agent_id}")
        return Agent.model_validate(data)

    async def list(self, **params: Any) -> list[Agent]:
        """
        List agents, optionally filtered by query params.

        Returns:
            List of Agents.
        """
        data = await self._client.get("/agents", params=params or None)
        if isinstance(data, list):
            return [Agent.model_validate(item) for item in data]
        # Some APIs wrap lists in a key
        items = data.get("agents", data.get("items", data.get("data", [])))
        return [Agent.model_validate(item) for item in items]

    async def update(self, agent_id: str, config: dict[str, Any]) -> Agent:
        """
        Update an existing agent.

        Args:
            agent_id: The agent's unique identifier.
            config: Fields to update.

        Returns:
            The updated Agent.
        """
        data = await self._client.patch(f"/agents/{agent_id}", json=config)
        return Agent.model_validate(data)

    async def delete(self, agent_id: str) -> None:
        """
        Delete an agent by ID.

        Args:
            agent_id: The agent's unique identifier.
        """
        await self._client.delete(f"/agents/{agent_id}")


class TaskOperations:
    """
    Operations for task resources.

    All methods are async.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client

    async def create(
        self,
        description: str,
        agent_types: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            description: Human-readable task description.
            agent_types: List of agent role types to assign.
            config: Optional runtime configuration.

        Returns:
            The created Task.
        """
        payload: dict[str, Any] = {
            "description": description,
            "agent_types": agent_types or [],
            "config": config or {},
        }
        data = await self._client.post("/tasks", json=payload)
        return Task.model_validate(data)

    async def get(self, task_id: str) -> Task:
        """
        Retrieve a single task by ID.

        Args:
            task_id: The task's unique identifier.

        Returns:
            The Task.

        Raises:
            NotFoundError: When the task does not exist.
        """
        data = await self._client.get(f"/tasks/{task_id}")
        return Task.model_validate(data)

    async def list(self, status: str | None = None, **params: Any) -> list[Task]:
        """
        List tasks, optionally filtered by status.

        Args:
            status: Filter by task status (pending, running, completed, failed).
            **params: Additional query parameters.

        Returns:
            List of Tasks.
        """
        query: dict[str, Any] = {**params}
        if status is not None:
            query["status"] = status
        data = await self._client.get("/tasks", params=query or None)
        if isinstance(data, list):
            return [Task.model_validate(item) for item in data]
        items = data.get("tasks", data.get("items", data.get("data", [])))
        return [Task.model_validate(item) for item in items]
