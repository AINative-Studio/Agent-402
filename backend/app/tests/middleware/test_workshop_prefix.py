"""
Unit tests for WorkshopPrefixMiddleware.

Refs #300, #285.

The middleware rewrites `/api/v1/<path>` to the underlying router prefix when
`WORKSHOP_MODE=true`. When disabled, `/api/v1/*` must 404.

Behavior:
- Default convention: `/api/v1/<domain>/...`
    -> `/v1/public/<default_project_id>/<domain>/...`
- Override registry lets B2/B3 map non-conventional paths (e.g. `/hcs10/*`,
  `/marketplace/*`) without editing the middleware file.
- HTTP method, body, headers, and query string are preserved.
- Path parameters carry through because only the prefix is rewritten.
- Legacy `/v1/public/{project_id}/...` paths are untouched in both modes.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def echo_app():
    """Build a minimal FastAPI app that echoes path + method + query back."""
    app = FastAPI()

    @app.get("/v1/public/{project_id}/agents")
    async def list_agents(project_id: str, limit: int = 10):
        return {"project_id": project_id, "limit": limit, "route": "agents"}

    @app.get("/v1/public/{project_id}/agent-memory/{memory_id}")
    async def get_memory(project_id: str, memory_id: str):
        return {"project_id": project_id, "memory_id": memory_id, "route": "memory"}

    @app.post("/v1/public/{project_id}/agent-memory")
    async def create_memory(project_id: str, body: dict):
        return {"project_id": project_id, "body": body, "route": "create_memory"}

    @app.get("/marketplace/listings")
    async def list_marketplace():
        return {"route": "marketplace"}

    @app.post("/hcs10/send")
    async def hcs10_send(body: dict):
        return {"body": body, "route": "hcs10_send"}

    return app


class DescribeWorkshopPrefixMiddlewareDisabled:
    """When WORKSHOP_MODE is off, /api/v1/* must not resolve."""

    def it_returns_404_for_api_v1_path(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=False,
            default_project_id="proj_test",
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/agents")

        assert response.status_code == 404

    def it_leaves_legacy_routes_working(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=False,
            default_project_id="proj_test",
        )
        client = TestClient(echo_app)

        response = client.get("/v1/public/proj_xyz/agents")

        assert response.status_code == 200
        assert response.json()["project_id"] == "proj_xyz"


class DescribeWorkshopPrefixMiddlewareEnabled:
    """When WORKSHOP_MODE is on, /api/v1/* is rewritten."""

    def it_rewrites_api_v1_to_default_project(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == "proj_workshop"
        assert body["route"] == "agents"

    def it_preserves_query_string(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/agents?limit=42")

        assert response.status_code == 200
        assert response.json()["limit"] == 42

    def it_preserves_path_parameters(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/agent-memory/mem_abc123")

        assert response.status_code == 200
        body = response.json()
        assert body["memory_id"] == "mem_abc123"
        assert body["project_id"] == "proj_workshop"

    def it_preserves_method_and_body_on_post(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        payload = {"content": "hello", "type": "semantic"}
        response = client.post("/api/v1/agent-memory", json=payload)

        assert response.status_code == 200
        assert response.json()["body"] == payload

    def it_leaves_legacy_routes_untouched_when_enabled(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/v1/public/proj_other/agents")

        assert response.status_code == 200
        assert response.json()["project_id"] == "proj_other"

    def it_leaves_non_api_v1_paths_untouched(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/marketplace/listings")

        assert response.status_code == 200


class DescribeWorkshopPrefixOverrides:
    """Overrides route non-conventional /api/v1/* prefixes to the right target."""

    def it_uses_override_for_marketplace(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
            overrides={"marketplace/": "/marketplace/"},
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/marketplace/listings")

        assert response.status_code == 200
        assert response.json()["route"] == "marketplace"

    def it_uses_override_for_hcs10(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
            overrides={"hcs10/": "/hcs10/"},
        )
        client = TestClient(echo_app)

        response = client.post("/api/v1/hcs10/send", json={"msg": "hi"})

        assert response.status_code == 200
        assert response.json()["body"] == {"msg": "hi"}

    def it_prefers_override_over_default_convention(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
            overrides={"marketplace/": "/marketplace/"},
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/marketplace/listings")

        assert response.status_code == 200
        assert response.json()["route"] == "marketplace"


class DescribeWorkshopPrefixEdgeCases:
    """Defensive behavior on odd inputs."""

    def it_handles_exact_prefix_with_no_suffix(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        echo_app.add_middleware(
            WorkshopPrefixMiddleware,
            enabled=True,
            default_project_id="proj_workshop",
        )
        client = TestClient(echo_app)

        response = client.get("/api/v1/")

        assert response.status_code in (404, 405)

    def it_bypasses_websocket_scope(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="proj_workshop",
        )

        assert mw._should_rewrite({"type": "lifespan", "path": "/api/v1/agents"}) is False
        assert mw._should_rewrite({"type": "websocket", "path": "/api/v1/agents"}) is False
        assert mw._should_rewrite({"type": "http", "path": "/api/v1/agents"}) is True

    def it_rewrite_returns_unchanged_for_non_api_v1(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="proj_workshop",
        )

        assert mw._rewrite_path("/health") == "/health"
        assert mw._rewrite_path("/v1/public/p/x") == "/v1/public/p/x"

    def it_rewrite_applies_default_convention(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="proj_ws",
        )

        assert mw._rewrite_path("/api/v1/agents") == "/v1/public/proj_ws/agents"
        assert (
            mw._rewrite_path("/api/v1/agent-memory/mem_1")
            == "/v1/public/proj_ws/agent-memory/mem_1"
        )

    def it_rewrite_applies_overrides_first(self, echo_app):
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="proj_ws",
            overrides={"anchor/": "/anchor/", "hcs10/": "/hcs10/"},
        )

        assert mw._rewrite_path("/api/v1/anchor/memory") == "/anchor/memory"
        assert mw._rewrite_path("/api/v1/hcs10/send") == "/hcs10/send"
        # Non-override path still uses convention
        assert mw._rewrite_path("/api/v1/agents") == "/v1/public/proj_ws/agents"

    def it_appends_trailing_slash_to_override_target(self, echo_app):
        """Override targets missing a trailing slash are normalized."""
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="proj_ws",
            overrides={"marketplace/": "/marketplace"},  # no trailing slash
        )

        assert mw._rewrite_path("/api/v1/marketplace/listings") == "/marketplace/listings"

    def it_leaves_path_unchanged_when_no_default_project_and_no_override(self, echo_app):
        """Safety: empty default_project_id + no matching override => unchanged."""
        from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

        mw = WorkshopPrefixMiddleware(
            app=echo_app,
            enabled=True,
            default_project_id="",
        )

        assert mw._rewrite_path("/api/v1/agents") == "/api/v1/agents"
