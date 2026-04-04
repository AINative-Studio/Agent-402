"""
Tests for ainative_agent.agents — AgentOperations and TaskOperations.

Describes: agent CRUD, task lifecycle, and type coercion.

Built by AINative Dev Team.
"""
from __future__ import annotations

import pytest

from ainative_agent import AINativeSDK
from ainative_agent.errors import NotFoundError
from ainative_agent.types import Agent, Task
from tests.conftest import make_response

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

AGENT_PAYLOAD = {
    "id": "agent_abc123",
    "did": "did:key:z6Mk",
    "name": "test-agent",
    "role": "researcher",
    "description": "A test agent",
    "scope": "RUN",
    "project_id": "proj_xyz",
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}

TASK_PAYLOAD = {
    "id": "task_def456",
    "description": "Research AI trends",
    "agent_types": ["researcher"],
    "status": "pending",
    "config": {"max_steps": 10, "timeout_seconds": None, "metadata": {}},
    "result": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}


# ---------------------------------------------------------------------------
# describe: AgentOperations.create
# ---------------------------------------------------------------------------


class DescribeAgentCreate:
    async def it_returns_agent_model_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=AGENT_PAYLOAD)
        agent = await sdk.agents.create({"name": "test-agent", "role": "researcher"})
        assert isinstance(agent, Agent)
        assert agent.id == "agent_abc123"
        assert agent.name == "test-agent"

    async def it_posts_to_agents_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=AGENT_PAYLOAD)
        await sdk.agents.create({"name": "test-agent", "role": "researcher"})
        call = mock_httpx_client.request.call_args
        assert "/agents" in call.kwargs["url"]
        assert call.kwargs["method"] == "POST"

    async def it_sends_config_as_json_body(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=AGENT_PAYLOAD)
        config = {"name": "bot", "role": "assistant", "description": "helpful bot"}
        await sdk.agents.create(config)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"] == config

    async def it_raises_auth_error_on_401(self, sdk, mock_httpx_client):
        from ainative_agent.errors import AuthError
        mock_httpx_client.request.return_value = make_response(401, text_body="Unauthorized")
        with pytest.raises(AuthError):
            await sdk.agents.create({"name": "bot", "role": "assistant"})


# ---------------------------------------------------------------------------
# describe: AgentOperations.get
# ---------------------------------------------------------------------------


class DescribeAgentGet:
    async def it_returns_agent_model_by_id(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=AGENT_PAYLOAD)
        agent = await sdk.agents.get("agent_abc123")
        assert agent.id == "agent_abc123"
        assert agent.role == "researcher"

    async def it_requests_correct_url(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=AGENT_PAYLOAD)
        await sdk.agents.get("agent_abc123")
        call = mock_httpx_client.request.call_args
        assert "/agents/agent_abc123" in call.kwargs["url"]

    async def it_raises_not_found_for_unknown_id(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.agents.get("agent_missing")


# ---------------------------------------------------------------------------
# describe: AgentOperations.list
# ---------------------------------------------------------------------------


class DescribeAgentList:
    async def it_returns_list_of_agents_from_array_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[AGENT_PAYLOAD])
        agents = await sdk.agents.list()
        assert len(agents) == 1
        assert isinstance(agents[0], Agent)

    async def it_returns_list_of_agents_from_wrapped_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"agents": [AGENT_PAYLOAD, AGENT_PAYLOAD]}
        )
        agents = await sdk.agents.list()
        assert len(agents) == 2

    async def it_returns_empty_list_when_no_agents(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        agents = await sdk.agents.list()
        assert agents == []


# ---------------------------------------------------------------------------
# describe: AgentOperations.update
# ---------------------------------------------------------------------------


class DescribeAgentUpdate:
    async def it_returns_updated_agent(self, sdk, mock_httpx_client):
        updated = {**AGENT_PAYLOAD, "name": "renamed-agent"}
        mock_httpx_client.request.return_value = make_response(200, json_body=updated)
        agent = await sdk.agents.update("agent_abc123", {"name": "renamed-agent"})
        assert agent.name == "renamed-agent"

    async def it_sends_patch_to_agent_url(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=AGENT_PAYLOAD)
        await sdk.agents.update("agent_abc123", {"name": "new"})
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "PATCH"
        assert "/agents/agent_abc123" in call.kwargs["url"]


# ---------------------------------------------------------------------------
# describe: AgentOperations.delete
# ---------------------------------------------------------------------------


class DescribeAgentDelete:
    async def it_sends_delete_request(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        await sdk.agents.delete("agent_abc123")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "DELETE"
        assert "/agents/agent_abc123" in call.kwargs["url"]

    async def it_returns_none_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        result = await sdk.agents.delete("agent_abc123")
        assert result is None

    async def it_raises_not_found_when_agent_missing(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.agents.delete("agent_missing")


# ---------------------------------------------------------------------------
# describe: TaskOperations.create
# ---------------------------------------------------------------------------


class DescribeTaskCreate:
    async def it_returns_task_model_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=TASK_PAYLOAD)
        task = await sdk.tasks.create(
            description="Research AI trends",
            agent_types=["researcher"],
        )
        assert isinstance(task, Task)
        assert task.id == "task_def456"
        assert task.description == "Research AI trends"

    async def it_posts_to_tasks_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=TASK_PAYLOAD)
        await sdk.tasks.create(description="Do something")
        call = mock_httpx_client.request.call_args
        assert "/tasks" in call.kwargs["url"]
        assert call.kwargs["method"] == "POST"

    async def it_includes_agent_types_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=TASK_PAYLOAD)
        await sdk.tasks.create(description="task", agent_types=["researcher", "writer"])
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["agent_types"] == ["researcher", "writer"]

    async def it_defaults_agent_types_to_empty_list(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=TASK_PAYLOAD)
        await sdk.tasks.create(description="task")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["agent_types"] == []

    async def it_includes_config_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=TASK_PAYLOAD)
        await sdk.tasks.create(description="task", config={"max_steps": 5})
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["config"] == {"max_steps": 5}


# ---------------------------------------------------------------------------
# describe: TaskOperations.get
# ---------------------------------------------------------------------------


class DescribeTaskGet:
    async def it_returns_task_model_by_id(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=TASK_PAYLOAD)
        task = await sdk.tasks.get("task_def456")
        assert task.id == "task_def456"
        assert task.status == "pending"

    async def it_raises_not_found_for_unknown_task(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.tasks.get("task_missing")


# ---------------------------------------------------------------------------
# describe: TaskOperations.list
# ---------------------------------------------------------------------------


class DescribeTaskList:
    async def it_returns_list_of_tasks(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[TASK_PAYLOAD])
        tasks = await sdk.tasks.list()
        assert len(tasks) == 1
        assert isinstance(tasks[0], Task)

    async def it_filters_by_status_when_provided(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[TASK_PAYLOAD])
        await sdk.tasks.list(status="pending")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["params"]["status"] == "pending"

    async def it_does_not_send_params_when_no_filters(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.tasks.list()
        call = mock_httpx_client.request.call_args
        assert call.kwargs["params"] is None

    async def it_returns_tasks_from_wrapped_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"tasks": [TASK_PAYLOAD]}
        )
        tasks = await sdk.tasks.list()
        assert len(tasks) == 1
