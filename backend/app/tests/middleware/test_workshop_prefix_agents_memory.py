"""
Integration tests for the workshop /api/v1/ prefix applied to the agents
and agent-memory routers.

Refs #301, #285.

These routers follow the default convention
    `/v1/public/{project_id}/{domain}`
so the middleware's default convention mapping is sufficient — no router
code changes required. The tests below prove that:

- `GET /api/v1/agents` resolves through the middleware to the underlying
  `/v1/public/{workshop_default_project_id}/agents` handler.
- `POST /api/v1/agent-memory` resolves through the middleware.
- `GET /api/v1/agent-memory/{memory_id}` resolves, preserving the path param.
- Legacy `/v1/public/{project_id}/agents` and `/agent-memory` still work.

A fresh minimal FastAPI app is built for each test so `workshop_mode=True`
can be exercised deterministically without mutating the app-level settings.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agent_memory import router as agent_memory_router
from app.api.agents import router as agents_router
from app.core.auth import get_current_user
from app.middleware.workshop_prefix import WorkshopPrefixMiddleware


def _build_app(*, workshop_mode: bool, project_id: str = "proj_test_b1") -> FastAPI:
    """Build a minimal FastAPI app with the two routers and workshop middleware."""
    app = FastAPI()
    app.include_router(agents_router)
    app.include_router(agent_memory_router)
    app.add_middleware(
        WorkshopPrefixMiddleware,
        enabled=workshop_mode,
        default_project_id=project_id,
    )
    # Override auth so tests don't need API keys — the middleware under test
    # is about routing, not authentication.
    app.dependency_overrides[get_current_user] = lambda: "test_user"
    return app


@pytest.fixture
def canned_agent() -> SimpleNamespace:
    """Attribute-accessor object matching what `agent_service.list_project_agents` returns."""
    return SimpleNamespace(
        id="agent_abc123",
        agent_id="agent_abc123",
        project_id="proj_test_b1",
        name="Compliance Agent",
        role="compliance",
        did="did:hedera:testnet:0.0.1",
        description="compliance agent",
        scope="PROJECT",
        created_at="2026-04-17T00:00:00Z",
        updated_at="2026-04-17T00:00:00Z",
    )


@pytest.fixture
def canned_memory() -> Dict[str, Any]:
    return {
        "memory_id": "mem_abc123",
        "agent_id": "agent_abc123",
        "run_id": "run_1",
        "memory_type": "decision",
        "content": "approve TX-12345",
        "metadata": {},
        "namespace": "default",
        "timestamp": "2026-04-17T00:00:00Z",
        "project_id": "proj_test_b1",
        "embedding_id": None,
    }


class DescribeAgentsRouterWorkshopAlias:
    """The /api/v1/agents alias must resolve to the agents router."""

    def it_routes_get_api_v1_agents_via_convention(self, canned_agent):
        app = _build_app(workshop_mode=True)
        with patch(
            "app.api.agents.project_service.get_project",
            return_value={"project_id": "proj_test_b1"},
        ), patch(
            "app.api.agents.agent_service.list_project_agents",
            new=AsyncMock(return_value=[canned_agent]),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/agents")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["agents"][0]["id"] == "agent_abc123"

    def it_still_routes_legacy_path_when_workshop_mode_enabled(self, canned_agent):
        app = _build_app(workshop_mode=True)
        with patch(
            "app.api.agents.project_service.get_project",
            return_value={"project_id": "proj_other"},
        ), patch(
            "app.api.agents.agent_service.list_project_agents",
            new=AsyncMock(return_value=[canned_agent]),
        ):
            client = TestClient(app)
            response = client.get("/v1/public/proj_other/agents")

        assert response.status_code == 200
        assert response.json()["agents"][0]["id"] == "agent_abc123"

    def it_404s_api_v1_agents_when_workshop_mode_disabled(self, canned_agent):
        app = _build_app(workshop_mode=False)
        client = TestClient(app)

        response = client.get("/api/v1/agents")

        assert response.status_code == 404


class DescribeAgentMemoryRouterWorkshopAlias:
    """`/api/v1/agent-memory` must resolve to the agent_memory router."""

    def it_routes_post_api_v1_agent_memory(self, canned_memory):
        app = _build_app(workshop_mode=True)
        payload = {
            "agent_id": "agent_abc123",
            "run_id": "run_1",
            "memory_type": "decision",
            "content": "approve TX-12345",
        }
        with patch(
            "app.api.agent_memory.agent_memory_service.store_memory",
            new=AsyncMock(return_value=canned_memory),
        ):
            client = TestClient(app)
            response = client.post("/api/v1/agent-memory", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["memory_id"] == "mem_abc123"
        assert body["agent_id"] == "agent_abc123"

    def it_routes_get_api_v1_agent_memory_with_path_param(self, canned_memory):
        app = _build_app(workshop_mode=True)
        with patch(
            "app.api.agent_memory.agent_memory_service.get_memory",
            new=AsyncMock(return_value=canned_memory),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/agent-memory/mem_abc123")

        assert response.status_code == 200
        assert response.json()["memory_id"] == "mem_abc123"

    def it_still_routes_legacy_memory_path(self, canned_memory):
        app = _build_app(workshop_mode=True)
        payload = {
            "agent_id": "agent_abc123",
            "run_id": "run_1",
            "memory_type": "decision",
            "content": "approve TX-12345",
        }
        with patch(
            "app.api.agent_memory.agent_memory_service.store_memory",
            new=AsyncMock(return_value=canned_memory),
        ):
            client = TestClient(app)
            response = client.post(
                "/v1/public/proj_other/agent-memory", json=payload
            )

        assert response.status_code == 201
        assert response.json()["memory_id"] == "mem_abc123"

    def it_404s_api_v1_agent_memory_when_workshop_mode_disabled(self):
        app = _build_app(workshop_mode=False)
        client = TestClient(app)

        response = client.get("/api/v1/agent-memory/mem_abc123")

        assert response.status_code == 404


class DescribeAgentMemoryRouterWorkshopListFilters:
    """Query parameters (filters, pagination) must survive the rewrite."""

    def it_preserves_list_filter_query_params(self):
        app = _build_app(workshop_mode=True)

        async def _list_memories(
            project_id: str,
            agent_id: str = None,
            run_id: str = None,
            memory_type: str = None,
            namespace: str = None,
            limit: int = 100,
            offset: int = 0,
        ):
            # Echo back what the handler received after rewrite
            return (
                [
                    {
                        "memory_id": "mem_x",
                        "agent_id": agent_id or "none",
                        "run_id": run_id or "none",
                        "memory_type": memory_type or "none",
                        "content": "x",
                        "metadata": {},
                        "namespace": namespace or "default",
                        "timestamp": "2026-04-17T00:00:00Z",
                        "project_id": project_id,
                        "embedding_id": None,
                    }
                ],
                1,
                {},
            )

        with patch(
            "app.api.agent_memory.agent_memory_service.list_memories",
            new=_list_memories,
        ):
            client = TestClient(app)
            response = client.get(
                "/api/v1/agent-memory?agent_id=a1&run_id=r1&memory_type=decision&limit=5"
            )

        assert response.status_code == 200
        body = response.json()
        assert body["memories"][0]["agent_id"] == "a1"
        assert body["memories"][0]["run_id"] == "r1"
        assert body["memories"][0]["memory_type"] == "decision"
        assert body["memories"][0]["project_id"] == "proj_test_b1"
