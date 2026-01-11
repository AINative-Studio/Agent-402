"""
Unit tests for ImmutableMiddleware (Append-Only Records Enforcement).

Tests Epic 12, Issue 6 requirements:
- Protected tables: agents, agent_memory, compliance_events, x402_requests
- GET requests are allowed on all protected endpoints
- POST requests are allowed on all protected endpoints
- PUT requests return 403 IMMUTABLE_RECORD on protected endpoints
- PATCH requests return 403 IMMUTABLE_RECORD on protected endpoints
- DELETE requests return 403 IMMUTABLE_RECORD on protected endpoints
- Error response includes { detail, error_code: "IMMUTABLE_RECORD" }
- Non-protected endpoints are unaffected by middleware

Per PRD Section 10 (Non-repudiation):
- All agent-related records are append-only
- UPDATE and DELETE operations are forbidden
- Returns HTTP 403 Forbidden with IMMUTABLE_RECORD error code
"""
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from app.middleware.immutable import ImmutableMiddleware


@pytest.fixture
def test_app():
    """
    Create a minimal FastAPI app with ImmutableMiddleware for testing.

    This app includes mock routes for all protected endpoints to test
    that the middleware correctly blocks mutations.
    """
    app = FastAPI()

    # Add ImmutableMiddleware
    app.add_middleware(ImmutableMiddleware)

    # Create mock routes for protected endpoints
    # These routes would normally be defined in the API routers

    # Agents endpoints
    @app.get("/v1/public/{project_id}/agents")
    async def list_agents(project_id: str):
        return {"agents": []}

    @app.get("/v1/public/{project_id}/agents/{agent_id}")
    async def get_agent(project_id: str, agent_id: str):
        return {"agent_id": agent_id}

    @app.post("/v1/public/{project_id}/agents")
    async def create_agent(project_id: str):
        return {"agent_id": "new-agent"}

    @app.put("/v1/public/{project_id}/agents/{agent_id}")
    async def update_agent(project_id: str, agent_id: str):
        return {"agent_id": agent_id, "updated": True}

    @app.patch("/v1/public/{project_id}/agents/{agent_id}")
    async def patch_agent(project_id: str, agent_id: str):
        return {"agent_id": agent_id, "patched": True}

    @app.delete("/v1/public/{project_id}/agents/{agent_id}")
    async def delete_agent(project_id: str, agent_id: str):
        return {"agent_id": agent_id, "deleted": True}

    # Agent memory endpoints
    @app.get("/v1/public/{project_id}/agent_memory")
    async def list_agent_memory(project_id: str):
        return {"memories": []}

    @app.post("/v1/public/{project_id}/agent_memory")
    async def create_agent_memory(project_id: str):
        return {"memory_id": "new-memory"}

    @app.put("/v1/public/{project_id}/agent_memory/{memory_id}")
    async def update_agent_memory(project_id: str, memory_id: str):
        return {"memory_id": memory_id, "updated": True}

    @app.patch("/v1/public/{project_id}/agent_memory/{memory_id}")
    async def patch_agent_memory(project_id: str, memory_id: str):
        return {"memory_id": memory_id, "patched": True}

    @app.delete("/v1/public/{project_id}/agent_memory/{memory_id}")
    async def delete_agent_memory(project_id: str, memory_id: str):
        return {"memory_id": memory_id, "deleted": True}

    # Hyphenated agent-memory endpoints
    @app.get("/v1/public/{project_id}/agent-memory")
    async def list_agent_memory_hyphen(project_id: str):
        return {"memories": []}

    @app.put("/v1/public/{project_id}/agent-memory/{memory_id}")
    async def update_agent_memory_hyphen(project_id: str, memory_id: str):
        return {"memory_id": memory_id, "updated": True}

    @app.delete("/v1/public/{project_id}/agent-memory/{memory_id}")
    async def delete_agent_memory_hyphen(project_id: str, memory_id: str):
        return {"memory_id": memory_id, "deleted": True}

    # Compliance events endpoints
    @app.get("/v1/public/{project_id}/compliance_events")
    async def list_compliance_events(project_id: str):
        return {"events": []}

    @app.post("/v1/public/{project_id}/compliance_events")
    async def create_compliance_event(project_id: str):
        return {"event_id": "new-event"}

    @app.put("/v1/public/{project_id}/compliance_events/{event_id}")
    async def update_compliance_event(project_id: str, event_id: str):
        return {"event_id": event_id, "updated": True}

    @app.patch("/v1/public/{project_id}/compliance_events/{event_id}")
    async def patch_compliance_event(project_id: str, event_id: str):
        return {"event_id": event_id, "patched": True}

    @app.delete("/v1/public/{project_id}/compliance_events/{event_id}")
    async def delete_compliance_event(project_id: str, event_id: str):
        return {"event_id": event_id, "deleted": True}

    # Hyphenated compliance-events endpoints
    @app.delete("/v1/public/{project_id}/compliance-events/{event_id}")
    async def delete_compliance_event_hyphen(project_id: str, event_id: str):
        return {"event_id": event_id, "deleted": True}

    # X402 requests endpoints
    @app.get("/v1/public/{project_id}/x402_requests")
    async def list_x402_requests(project_id: str):
        return {"requests": []}

    @app.post("/v1/public/{project_id}/x402_requests")
    async def create_x402_request(project_id: str):
        return {"request_id": "new-request"}

    @app.put("/v1/public/{project_id}/x402_requests/{request_id}")
    async def update_x402_request(project_id: str, request_id: str):
        return {"request_id": request_id, "updated": True}

    @app.patch("/v1/public/{project_id}/x402_requests/{request_id}")
    async def patch_x402_request(project_id: str, request_id: str):
        return {"request_id": request_id, "patched": True}

    @app.delete("/v1/public/{project_id}/x402_requests/{request_id}")
    async def delete_x402_request(project_id: str, request_id: str):
        return {"request_id": request_id, "deleted": True}

    # Non-protected endpoint (projects)
    @app.put("/v1/public/{project_id}")
    async def update_project(project_id: str):
        return {"project_id": project_id, "updated": True}

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # Root
    @app.get("/")
    async def root():
        return {"name": "Test API"}

    # Nested resource path for agents
    @app.delete("/v1/public/{project_id}/agents/{agent_id}/subresource/{sub_id}")
    async def delete_agent_subresource(project_id: str, agent_id: str, sub_id: str):
        return {"deleted": True}

    return app


@pytest.fixture
def client(test_app):
    """Test client for the app with ImmutableMiddleware."""
    return TestClient(test_app)


class TestImmutableMiddleware:
    """Test suite for ImmutableMiddleware append-only enforcement."""

    # =========================================================================
    # Test GET requests are allowed on all protected endpoints
    # =========================================================================

    def test_get_agents_allowed(self, client):
        """
        Test that GET requests are allowed on /agents endpoint.
        Epic 12 Issue 6: Read operations are allowed on immutable tables.
        """
        response = client.get("/v1/public/project-1/agents")

        # GET should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_get_agent_memory_allowed(self, client):
        """
        Test that GET requests are allowed on /agent_memory endpoint.
        Epic 12 Issue 6: Read operations are allowed on immutable tables.
        """
        response = client.get("/v1/public/project-1/agent_memory")

        # GET should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_get_compliance_events_allowed(self, client):
        """
        Test that GET requests are allowed on /compliance_events endpoint.
        Epic 12 Issue 6: Read operations are allowed on immutable tables.
        """
        response = client.get("/v1/public/project-1/compliance_events")

        # GET should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_get_x402_requests_allowed(self, client):
        """
        Test that GET requests are allowed on /x402_requests endpoint.
        Epic 12 Issue 6: Read operations are allowed on immutable tables.
        """
        response = client.get("/v1/public/project-1/x402_requests")

        # GET should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_get_agents_with_hyphen_notation(self, client):
        """
        Test that GET requests work with hyphenated endpoint names.
        Epic 12 Issue 6: Support both underscore and hyphen notation.
        """
        response = client.get("/v1/public/project-1/agent-memory")

        # GET should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    # =========================================================================
    # Test POST requests are allowed on all protected endpoints
    # =========================================================================

    def test_post_agents_allowed(self, client):
        """
        Test that POST requests are allowed on /agents endpoint.
        Epic 12 Issue 6: Create/append operations are allowed on immutable tables.
        """
        response = client.post("/v1/public/project-1/agents", json={})

        # POST should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_post_agent_memory_allowed(self, client):
        """
        Test that POST requests are allowed on /agent_memory endpoint.
        Epic 12 Issue 6: Create/append operations are allowed on immutable tables.
        """
        response = client.post("/v1/public/project-1/agent_memory", json={})

        # POST should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_post_compliance_events_allowed(self, client):
        """
        Test that POST requests are allowed on /compliance_events endpoint.
        Epic 12 Issue 6: Create/append operations are allowed on immutable tables.
        """
        response = client.post("/v1/public/project-1/compliance_events", json={})

        # POST should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    def test_post_x402_requests_allowed(self, client):
        """
        Test that POST requests are allowed on /x402_requests endpoint.
        Epic 12 Issue 6: Create/append operations are allowed on immutable tables.
        """
        response = client.post("/v1/public/project-1/x402_requests", json={})

        # POST should be allowed (not blocked by middleware)
        assert response.status_code == status.HTTP_200_OK

    # =========================================================================
    # Test PUT requests return 403 IMMUTABLE_RECORD on protected endpoints
    # =========================================================================

    def test_put_agents_blocked(self, client):
        """
        Test that PUT requests are blocked on /agents endpoint.
        Epic 12 Issue 6: Update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.put("/v1/public/project-1/agents/agent-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agents" in data["detail"]
        assert "append-only" in data["detail"]

    def test_put_agent_memory_blocked(self, client):
        """
        Test that PUT requests are blocked on /agent_memory endpoint.
        Epic 12 Issue 6: Update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.put("/v1/public/project-1/agent_memory/memory-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agent_memory" in data["detail"]
        assert "append-only" in data["detail"]

    def test_put_compliance_events_blocked(self, client):
        """
        Test that PUT requests are blocked on /compliance_events endpoint.
        Epic 12 Issue 6: Update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.put("/v1/public/project-1/compliance_events/event-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "compliance_events" in data["detail"]
        assert "append-only" in data["detail"]

    def test_put_x402_requests_blocked(self, client):
        """
        Test that PUT requests are blocked on /x402_requests endpoint.
        Epic 12 Issue 6: Update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.put("/v1/public/project-1/x402_requests/request-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "x402_requests" in data["detail"]
        assert "append-only" in data["detail"]

    def test_put_hyphenated_endpoint_blocked(self, client):
        """
        Test that PUT requests are blocked on hyphenated endpoint names.
        Epic 12 Issue 6: Support both underscore and hyphen notation.
        """
        response = client.put("/v1/public/project-1/agent-memory/memory-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    # =========================================================================
    # Test PATCH requests return 403 IMMUTABLE_RECORD on protected endpoints
    # =========================================================================

    def test_patch_agents_blocked(self, client):
        """
        Test that PATCH requests are blocked on /agents endpoint.
        Epic 12 Issue 6: Partial update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.patch("/v1/public/project-1/agents/agent-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agents" in data["detail"]
        assert "append-only" in data["detail"]

    def test_patch_agent_memory_blocked(self, client):
        """
        Test that PATCH requests are blocked on /agent_memory endpoint.
        Epic 12 Issue 6: Partial update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.patch("/v1/public/project-1/agent_memory/memory-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agent_memory" in data["detail"]
        assert "append-only" in data["detail"]

    def test_patch_compliance_events_blocked(self, client):
        """
        Test that PATCH requests are blocked on /compliance_events endpoint.
        Epic 12 Issue 6: Partial update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.patch("/v1/public/project-1/compliance_events/event-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "compliance_events" in data["detail"]
        assert "append-only" in data["detail"]

    def test_patch_x402_requests_blocked(self, client):
        """
        Test that PATCH requests are blocked on /x402_requests endpoint.
        Epic 12 Issue 6: Partial update operations return 403 IMMUTABLE_RECORD.
        """
        response = client.patch("/v1/public/project-1/x402_requests/request-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "x402_requests" in data["detail"]
        assert "append-only" in data["detail"]

    # =========================================================================
    # Test DELETE requests return 403 IMMUTABLE_RECORD on protected endpoints
    # =========================================================================

    def test_delete_agents_blocked(self, client):
        """
        Test that DELETE requests are blocked on /agents endpoint.
        Epic 12 Issue 6: Delete operations return 403 IMMUTABLE_RECORD.
        """
        response = client.delete("/v1/public/project-1/agents/agent-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agents" in data["detail"]
        assert "append-only" in data["detail"]

    def test_delete_agent_memory_blocked(self, client):
        """
        Test that DELETE requests are blocked on /agent_memory endpoint.
        Epic 12 Issue 6: Delete operations return 403 IMMUTABLE_RECORD.
        """
        response = client.delete("/v1/public/project-1/agent_memory/memory-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "agent_memory" in data["detail"]
        assert "append-only" in data["detail"]

    def test_delete_compliance_events_blocked(self, client):
        """
        Test that DELETE requests are blocked on /compliance_events endpoint.
        Epic 12 Issue 6: Delete operations return 403 IMMUTABLE_RECORD.
        """
        response = client.delete("/v1/public/project-1/compliance_events/event-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "compliance_events" in data["detail"]
        assert "append-only" in data["detail"]

    def test_delete_x402_requests_blocked(self, client):
        """
        Test that DELETE requests are blocked on /x402_requests endpoint.
        Epic 12 Issue 6: Delete operations return 403 IMMUTABLE_RECORD.
        """
        response = client.delete("/v1/public/project-1/x402_requests/request-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "IMMUTABLE_RECORD"
        assert "x402_requests" in data["detail"]
        assert "append-only" in data["detail"]

    def test_delete_hyphenated_endpoint_blocked(self, client):
        """
        Test that DELETE requests are blocked on hyphenated endpoint names.
        Epic 12 Issue 6: Support both underscore and hyphen notation.
        """
        response = client.delete("/v1/public/project-1/compliance-events/event-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    # =========================================================================
    # Test error response format
    # =========================================================================

    def test_error_response_format(self, client):
        """
        Test that immutability errors follow DX Contract format.
        Per DX Contract Section 7: All errors return { detail, error_code }.
        """
        response = client.put("/v1/public/project-1/agents/agent-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()

        # Must have exactly these fields per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0
        assert len(data["error_code"]) > 0

    def test_error_detail_contains_table_name(self, client):
        """
        Test that error detail contains the table name.
        Epic 12 Issue 6: Error messages should be informative.
        """
        response = client.delete("/v1/public/project-1/agents/agent-123")

        data = response.json()
        assert "agents" in data["detail"].lower()

    def test_error_detail_mentions_append_only(self, client):
        """
        Test that error detail mentions append-only semantics.
        Epic 12 Issue 6: Error messages explain the constraint.
        """
        response = client.patch("/v1/public/project-1/agent_memory/memory-123", json={})

        data = response.json()
        assert "append-only" in data["detail"].lower()

    def test_error_detail_references_prd(self, client):
        """
        Test that error detail references PRD Section 10.
        Epic 12 Issue 6: Error messages reference PRD requirements.
        """
        response = client.put("/v1/public/project-1/compliance_events/event-123", json={})

        data = response.json()
        assert "PRD Section 10" in data["detail"] or "non-repudiation" in data["detail"].lower()

    # =========================================================================
    # Test non-protected endpoints are unaffected
    # =========================================================================

    def test_non_protected_endpoints_unaffected_by_middleware(self, client):
        """
        Test that non-protected endpoints allow all HTTP methods.
        Epic 12 Issue 6: Middleware only affects protected tables.
        """
        # Test that /projects endpoint (not protected) allows PUT
        response = client.put("/v1/public/project-1", json={})

        # Should not be blocked by ImmutableMiddleware
        assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_unaffected(self, client):
        """
        Test that health check endpoint is not affected by middleware.
        Health checks should not be subject to immutability constraints.
        """
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK

    def test_root_endpoint_unaffected(self, client):
        """
        Test that root endpoint is not affected by middleware.
        API information should not be subject to immutability constraints.
        """
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK

    # =========================================================================
    # Test case sensitivity and path variations
    # =========================================================================

    def test_path_matching_case_insensitive(self, client):
        """
        Test that path matching is case-insensitive.
        Epic 12 Issue 6: Robust path detection.
        """
        response = client.delete("/v1/public/project-1/AGENTS/agent-123")

        # Should still be blocked (case-insensitive matching)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    def test_path_with_trailing_slash(self, client):
        """
        Test that paths with trailing slashes are handled correctly.
        Epic 12 Issue 6: Robust path detection.
        """
        response = client.delete("/v1/public/project-1/agents/agent-123/")

        # Should still be blocked
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    # =========================================================================
    # Test all protected tables
    # =========================================================================

    def test_all_four_protected_tables_blocked_for_put(self, client):
        """
        Test that all four protected tables block PUT requests.
        Epic 12 Issue 6: agents, agent_memory, compliance_events, x402_requests.
        """
        protected_endpoints = [
            "/v1/public/project-1/agents/agent-123",
            "/v1/public/project-1/agent_memory/memory-123",
            "/v1/public/project-1/compliance_events/event-123",
            "/v1/public/project-1/x402_requests/request-123"
        ]

        for endpoint in protected_endpoints:
            response = client.put(endpoint, json={})

            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"PUT to {endpoint} should be blocked"

            data = response.json()
            assert data["error_code"] == "IMMUTABLE_RECORD", \
                f"PUT to {endpoint} should return IMMUTABLE_RECORD"

    def test_all_four_protected_tables_blocked_for_patch(self, client):
        """
        Test that all four protected tables block PATCH requests.
        Epic 12 Issue 6: agents, agent_memory, compliance_events, x402_requests.
        """
        protected_endpoints = [
            "/v1/public/project-1/agents/agent-123",
            "/v1/public/project-1/agent_memory/memory-123",
            "/v1/public/project-1/compliance_events/event-123",
            "/v1/public/project-1/x402_requests/request-123"
        ]

        for endpoint in protected_endpoints:
            response = client.patch(endpoint, json={})

            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"PATCH to {endpoint} should be blocked"

            data = response.json()
            assert data["error_code"] == "IMMUTABLE_RECORD", \
                f"PATCH to {endpoint} should return IMMUTABLE_RECORD"

    def test_all_four_protected_tables_blocked_for_delete(self, client):
        """
        Test that all four protected tables block DELETE requests.
        Epic 12 Issue 6: agents, agent_memory, compliance_events, x402_requests.
        """
        protected_endpoints = [
            "/v1/public/project-1/agents/agent-123",
            "/v1/public/project-1/agent_memory/memory-123",
            "/v1/public/project-1/compliance_events/event-123",
            "/v1/public/project-1/x402_requests/request-123"
        ]

        for endpoint in protected_endpoints:
            response = client.delete(endpoint)

            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"DELETE to {endpoint} should be blocked"

            data = response.json()
            assert data["error_code"] == "IMMUTABLE_RECORD", \
                f"DELETE to {endpoint} should return IMMUTABLE_RECORD"

    # =========================================================================
    # Test middleware order and integration
    # =========================================================================

    def test_middleware_blocks_mutations_early(self, client):
        """
        Test that middleware blocks mutations early in request pipeline.
        Epic 12 Issue 6: Immutable enforcement happens before route processing.
        """
        response = client.delete("/v1/public/project-1/agents/agent-123")

        # Should be blocked by ImmutableMiddleware (403)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    def test_multiple_mutations_all_blocked(self, client):
        """
        Test that multiple mutation attempts are all blocked.
        Epic 12 Issue 6: Consistent enforcement across requests.
        """
        endpoints_and_methods = [
            ("PUT", "/v1/public/project-1/agents/agent-1"),
            ("PATCH", "/v1/public/project-1/agent_memory/mem-1"),
            ("DELETE", "/v1/public/project-1/compliance_events/event-1"),
            ("PUT", "/v1/public/project-1/x402_requests/req-1"),
        ]

        for method, endpoint in endpoints_and_methods:
            if method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "PATCH":
                response = client.patch(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["error_code"] == "IMMUTABLE_RECORD"

    # =========================================================================
    # Edge cases and boundary conditions
    # =========================================================================

    def test_empty_payload_still_blocked(self, client):
        """
        Test that mutations with empty payload are still blocked.
        Epic 12 Issue 6: Block all mutations regardless of payload.
        """
        response = client.put("/v1/public/project-1/agents/agent-123", json={})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    def test_nested_resource_path_blocked(self, client):
        """
        Test that nested resource paths are blocked.
        Epic 12 Issue 6: Block all paths containing protected table names.
        """
        response = client.delete(
            "/v1/public/project-1/agents/agent-123/subresource/123"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    def test_query_parameters_do_not_affect_blocking(self, client):
        """
        Test that query parameters do not affect mutation blocking.
        Epic 12 Issue 6: Block based on path and method, not query params.
        """
        response = client.delete("/v1/public/project-1/agents/agent-123?force=true")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "IMMUTABLE_RECORD"

    def test_different_project_ids_all_blocked(self, client):
        """
        Test that middleware blocks mutations across all project IDs.
        Epic 12 Issue 6: Enforce immutability globally, not per-project.
        """
        project_ids = ["project-1", "project-2", "test-project", "prod-123"]

        for project_id in project_ids:
            response = client.delete(f"/v1/public/{project_id}/agents/agent-123")

            # All should be blocked
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["error_code"] == "IMMUTABLE_RECORD"
