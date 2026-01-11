"""
Tests for Agent Memory Persistence API (Epic 12, Issue 2).

Tests all endpoints:
- POST /v1/public/{project_id}/agent-memory (Create memory entry)
- GET /v1/public/{project_id}/agent-memory (List memories with filters)
- GET /v1/public/{project_id}/agent-memory/{memory_id} (Get single memory)

Test Coverage:
- Memory creation with all memory types
- Filtering by agent_id, run_id, memory_type, namespace
- Namespace isolation (multi-agent isolation)
- Error cases: memory not found, invalid memory_type
- Pagination support
- Metadata handling
- Default namespace behavior
- Edge cases and validation

Per PRD Section 6 (ZeroDB Integration):
- Agent memory storage for decisions and context
- Namespace scoping for multi-agent isolation
- Support for various memory types

Per DX Contract Section 4 (Endpoint Prefixing):
- All public endpoints use /v1/public/ prefix
- Authentication required via X-API-Key
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestAgentMemoryCreate:
    """Tests for POST /v1/public/{project_id}/agent-memory."""

    def test_create_memory_decision_type(self, client, auth_headers_user1):
        """
        Test creating a memory with decision type.
        Epic 12 Issue 2: Basic memory creation.
        """
        response = client.post(
            "/v1/public/proj_test_001/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "compliance_agent_001",
                "run_id": "run_20260110_123456",
                "memory_type": "decision",
                "content": "Decided to approve transaction TX-12345 based on compliance rules",
                "metadata": {
                    "transaction_id": "TX-12345",
                    "decision_type": "approval",
                    "confidence": 0.95
                }
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert "memory_id" in data
        assert data["memory_id"].startswith("mem_")
        assert data["agent_id"] == "compliance_agent_001"
        assert data["run_id"] == "run_20260110_123456"
        assert data["memory_type"] == "decision"
        assert data["namespace"] == "default"  # Default namespace
        assert data["created"] is True
        assert "timestamp" in data

    def test_create_memory_with_custom_namespace(self, client, auth_headers_user1):
        """
        Test creating a memory with custom namespace.
        Epic 12 Issue 2: Namespace isolation support.
        """
        response = client.post(
            "/v1/public/proj_test_002/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "risk_agent_001",
                "run_id": "run_20260110_234567",
                "memory_type": "context",
                "content": "Market volatility increased by 15%",
                "namespace": "risk_assessment_team"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["namespace"] == "risk_assessment_team"
        assert data["memory_type"] == "context"

    def test_create_memory_all_types(self, client, auth_headers_user1):
        """
        Test creating memories with all supported memory types.
        Epic 12 Issue 2: Support for various memory types.
        """
        memory_types = [
            "decision", "context", "state", "observation",
            "goal", "plan", "result", "error"
        ]

        for mem_type in memory_types:
            response = client.post(
                "/v1/public/proj_test_003/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "multi_type_agent",
                    "run_id": f"run_{mem_type}",
                    "memory_type": mem_type,
                    "content": f"Test content for {mem_type} type"
                }
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["memory_type"] == mem_type

    def test_create_memory_with_metadata(self, client, auth_headers_user1):
        """
        Test creating a memory with complex metadata.
        Epic 12 Issue 2: Metadata support for classification.
        """
        response = client.post(
            "/v1/public/proj_test_004/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "analysis_agent_001",
                "run_id": "run_metadata_test",
                "memory_type": "result",
                "content": "Analysis completed successfully",
                "metadata": {
                    "metrics": {
                        "accuracy": 0.98,
                        "precision": 0.95,
                        "recall": 0.97
                    },
                    "tags": ["production", "high-priority"],
                    "duration_ms": 1234
                }
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Note: metadata is not returned in create response
        assert data["created"] is True

    def test_create_memory_without_metadata(self, client, auth_headers_user1):
        """
        Test creating a memory without metadata (optional field).
        Epic 12 Issue 2: Metadata is optional.
        """
        response = client.post(
            "/v1/public/proj_test_005/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "simple_agent",
                "run_id": "run_no_metadata",
                "memory_type": "observation",
                "content": "Observed temperature increase"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created"] is True

    def test_create_memory_missing_required_fields(self, client, auth_headers_user1):
        """
        Test creating a memory with missing required fields.
        Epic 12 Issue 2: Input validation.
        """
        # Missing agent_id
        response = client.post(
            "/v1/public/proj_test_006/agent-memory",
            headers=auth_headers_user1,
            json={
                "run_id": "run_missing_field",
                "memory_type": "decision",
                "content": "Test content"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_empty_content(self, client, auth_headers_user1):
        """
        Test creating a memory with empty content.
        Epic 12 Issue 2: Content validation.
        """
        response = client.post(
            "/v1/public/proj_test_007/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_empty_content",
                "memory_type": "decision",
                "content": ""
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_whitespace_content(self, client, auth_headers_user1):
        """
        Test creating a memory with whitespace-only content.
        Epic 12 Issue 2: Content validation.
        """
        response = client.post(
            "/v1/public/proj_test_008/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_whitespace",
                "memory_type": "decision",
                "content": "   "
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_invalid_memory_type(self, client, auth_headers_user1):
        """
        Test creating a memory with invalid memory type.
        Epic 12 Issue 2: Memory type validation.
        """
        response = client.post(
            "/v1/public/proj_test_009/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_invalid_type",
                "memory_type": "invalid_type",
                "content": "Test content"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_without_authentication(self, client):
        """
        Test creating a memory without authentication.
        DX Contract: X-API-Key required.
        """
        response = client.post(
            "/v1/public/proj_test_010/agent-memory",
            json={
                "agent_id": "test_agent",
                "run_id": "run_no_auth",
                "memory_type": "decision",
                "content": "Test content"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_memory_with_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test creating a memory with invalid API key.
        DX Contract: Valid X-API-Key required.
        """
        response = client.post(
            "/v1/public/proj_test_011/agent-memory",
            headers=invalid_auth_headers,
            json={
                "agent_id": "test_agent",
                "run_id": "run_invalid_key",
                "memory_type": "decision",
                "content": "Test content"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentMemoryList:
    """Tests for GET /v1/public/{project_id}/agent-memory."""

    def test_list_all_memories_empty(self, client, auth_headers_user1):
        """
        Test listing memories when none exist.
        Epic 12 Issue 2: List endpoint baseline.
        """
        response = client.get(
            "/v1/public/proj_empty_001/agent-memory",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["memories"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert data["filters_applied"] == {}

    def test_list_all_memories(self, client, auth_headers_user1):
        """
        Test listing all memories without filters.
        Epic 12 Issue 2: Basic list functionality.
        """
        project_id = "proj_list_001"

        # Create some test memories
        for i in range(3):
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": f"agent_{i}",
                    "run_id": f"run_{i}",
                    "memory_type": "decision",
                    "content": f"Decision {i}"
                }
            )

        # List all memories
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_list_memories_filter_by_agent_id(self, client, auth_headers_user1):
        """
        Test filtering memories by agent_id.
        Epic 12 Issue 2: Agent-specific memory retrieval.
        """
        project_id = "proj_filter_agent_001"

        # Create memories for different agents
        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_alpha",
                "run_id": "run_001",
                "memory_type": "decision",
                "content": "Alpha decision 1"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_alpha",
                "run_id": "run_002",
                "memory_type": "context",
                "content": "Alpha context 1"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_beta",
                "run_id": "run_003",
                "memory_type": "decision",
                "content": "Beta decision 1"
            }
        )

        # Filter by agent_alpha
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"agent_id": "agent_alpha"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 2
        assert data["total"] == 2
        assert data["filters_applied"]["agent_id"] == "agent_alpha"

        # Verify all returned memories are from agent_alpha
        for memory in data["memories"]:
            assert memory["agent_id"] == "agent_alpha"

    def test_list_memories_filter_by_run_id(self, client, auth_headers_user1):
        """
        Test filtering memories by run_id.
        Epic 12 Issue 2: Run-specific memory retrieval.
        """
        project_id = "proj_filter_run_001"

        # Create memories for different runs
        for i in range(3):
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "test_agent",
                    "run_id": "run_special",
                    "memory_type": "decision",
                    "content": f"Decision {i}"
                }
            )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_other",
                "memory_type": "decision",
                "content": "Other decision"
            }
        )

        # Filter by run_special
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"run_id": "run_special"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 3
        assert data["total"] == 3
        assert data["filters_applied"]["run_id"] == "run_special"

        for memory in data["memories"]:
            assert memory["run_id"] == "run_special"

    def test_list_memories_filter_by_memory_type(self, client, auth_headers_user1):
        """
        Test filtering memories by memory_type.
        Epic 12 Issue 2: Type-specific memory retrieval.
        """
        project_id = "proj_filter_type_001"

        # Create memories of different types
        memory_types = ["decision", "context", "state"]
        for mem_type in memory_types:
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "test_agent",
                    "run_id": "run_type_test",
                    "memory_type": mem_type,
                    "content": f"Content for {mem_type}"
                }
            )

        # Filter by decision type
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"memory_type": "decision"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 1
        assert data["total"] == 1
        assert data["filters_applied"]["memory_type"] == "decision"
        assert data["memories"][0]["memory_type"] == "decision"

    def test_list_memories_filter_by_namespace(self, client, auth_headers_user1):
        """
        Test filtering memories by namespace.
        Epic 12 Issue 2: Namespace-specific memory retrieval.
        """
        project_id = "proj_filter_namespace_001"

        # Create memories in different namespaces
        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_ns1",
                "run_id": "run_001",
                "memory_type": "decision",
                "content": "Namespace 1 decision",
                "namespace": "team_alpha"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_ns2",
                "run_id": "run_002",
                "memory_type": "decision",
                "content": "Namespace 2 decision",
                "namespace": "team_beta"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_default",
                "run_id": "run_003",
                "memory_type": "decision",
                "content": "Default namespace decision"
            }
        )

        # Filter by team_alpha namespace
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"namespace": "team_alpha"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 1
        assert data["total"] == 1
        assert data["filters_applied"]["namespace"] == "team_alpha"
        assert data["memories"][0]["namespace"] == "team_alpha"

    def test_list_memories_multiple_filters(self, client, auth_headers_user1):
        """
        Test combining multiple filters.
        Epic 12 Issue 2: Complex filtering support.
        """
        project_id = "proj_multi_filter_001"

        # Create diverse memories
        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_001",
                "run_id": "run_target",
                "memory_type": "decision",
                "content": "Target memory",
                "namespace": "team_alpha"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_001",
                "run_id": "run_other",
                "memory_type": "decision",
                "content": "Other run",
                "namespace": "team_alpha"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_002",
                "run_id": "run_target",
                "memory_type": "decision",
                "content": "Other agent",
                "namespace": "team_alpha"
            }
        )

        # Filter by agent_id + run_id + namespace
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": "agent_001",
                "run_id": "run_target",
                "namespace": "team_alpha"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 1
        assert data["total"] == 1
        assert data["filters_applied"]["agent_id"] == "agent_001"
        assert data["filters_applied"]["run_id"] == "run_target"
        assert data["filters_applied"]["namespace"] == "team_alpha"

    def test_list_memories_pagination(self, client, auth_headers_user1):
        """
        Test pagination support.
        Epic 12 Issue 2: Paginated memory retrieval.
        """
        project_id = "proj_pagination_001"

        # Create 10 memories
        for i in range(10):
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "test_agent",
                    "run_id": f"run_{i:03d}",
                    "memory_type": "decision",
                    "content": f"Decision {i}"
                }
            )

        # Get first page (limit 3)
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"limit": 3, "offset": 0}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 3
        assert data["total"] == 10
        assert data["limit"] == 3
        assert data["offset"] == 0

        # Get second page
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"limit": 3, "offset": 3}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 3
        assert data["total"] == 10
        assert data["offset"] == 3

    def test_list_memories_ordering(self, client, auth_headers_user1):
        """
        Test that memories are ordered by timestamp descending.
        Epic 12 Issue 2: Most recent first ordering.
        """
        project_id = "proj_ordering_001"

        # Create memories sequentially
        memory_ids = []
        for i in range(3):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "test_agent",
                    "run_id": f"run_{i}",
                    "memory_type": "decision",
                    "content": f"Decision {i}"
                }
            )
            memory_ids.append(response.json()["memory_id"])

        # List memories
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Most recent should be first (reverse order)
        timestamps = [m["timestamp"] for m in data["memories"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_memories_without_authentication(self, client):
        """
        Test listing memories without authentication.
        DX Contract: X-API-Key required.
        """
        response = client.get("/v1/public/proj_test_001/agent-memory")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_memories_with_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test listing memories with invalid API key.
        DX Contract: Valid X-API-Key required.
        """
        response = client.get(
            "/v1/public/proj_test_001/agent-memory",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentMemoryGet:
    """Tests for GET /v1/public/{project_id}/agent-memory/{memory_id}."""

    def test_get_memory_by_id(self, client, auth_headers_user1):
        """
        Test retrieving a single memory by ID.
        Epic 12 Issue 2: Single memory retrieval.
        """
        project_id = "proj_get_001"

        # Create a memory
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_get_test",
                "memory_type": "decision",
                "content": "Important decision",
                "metadata": {"priority": "high"}
            }
        )

        memory_id = create_response.json()["memory_id"]

        # Get the memory
        response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["memory_id"] == memory_id
        assert data["agent_id"] == "test_agent"
        assert data["run_id"] == "run_get_test"
        assert data["memory_type"] == "decision"
        assert data["content"] == "Important decision"
        assert data["metadata"]["priority"] == "high"
        assert data["namespace"] == "default"
        assert "timestamp" in data
        assert data["project_id"] == project_id

    def test_get_memory_with_namespace_hint(self, client, auth_headers_user1):
        """
        Test retrieving a memory with namespace hint for faster lookup.
        Epic 12 Issue 2: Optimized namespace lookups.
        """
        project_id = "proj_get_namespace_001"

        # Create memory with custom namespace
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_namespace",
                "memory_type": "context",
                "content": "Namespace-specific context",
                "namespace": "team_gamma"
            }
        )

        memory_id = create_response.json()["memory_id"]

        # Get with namespace hint
        response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1,
            params={"namespace": "team_gamma"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["memory_id"] == memory_id
        assert data["namespace"] == "team_gamma"

    def test_get_memory_not_found(self, client, auth_headers_user1):
        """
        Test retrieving a non-existent memory.
        Epic 12 Issue 2: 404 error handling.
        """
        response = client.get(
            "/v1/public/proj_get_002/agent-memory/mem_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert data["error_code"] == "MEMORY_NOT_FOUND"
        assert "mem_nonexistent" in data["detail"]

    def test_get_memory_wrong_namespace(self, client, auth_headers_user1):
        """
        Test retrieving a memory with wrong namespace hint.
        Epic 12 Issue 2: Namespace isolation verification.
        """
        project_id = "proj_get_wrong_ns_001"

        # Create memory in namespace A
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_ns_test",
                "memory_type": "decision",
                "content": "Namespace A decision",
                "namespace": "namespace_a"
            }
        )

        memory_id = create_response.json()["memory_id"]

        # Try to get with wrong namespace hint (should still work, searches all)
        response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1,
            params={"namespace": "namespace_b"}
        )

        # Should return 404 when namespace hint is wrong
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_memory_without_authentication(self, client):
        """
        Test retrieving a memory without authentication.
        DX Contract: X-API-Key required.
        """
        response = client.get(
            "/v1/public/proj_test_001/agent-memory/mem_test"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_memory_with_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test retrieving a memory with invalid API key.
        DX Contract: Valid X-API-Key required.
        """
        response = client.get(
            "/v1/public/proj_test_001/agent-memory/mem_test",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentMemoryNamespaceIsolation:
    """Tests for namespace isolation (multi-agent isolation)."""

    def test_namespace_isolation_list(self, client, auth_headers_user1):
        """
        Test that namespaces properly isolate agent memories.
        Epic 12 Issue 2: Multi-agent isolation via namespaces.
        """
        project_id = "proj_isolation_001"

        # Create memories in different namespaces
        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_team_a",
                "run_id": "run_001",
                "memory_type": "decision",
                "content": "Team A decision",
                "namespace": "team_a"
            }
        )

        client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_team_b",
                "run_id": "run_002",
                "memory_type": "decision",
                "content": "Team B decision",
                "namespace": "team_b"
            }
        )

        # List memories in team_a namespace
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"namespace": "team_a"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["memories"]) == 1
        assert data["memories"][0]["namespace"] == "team_a"
        assert data["memories"][0]["agent_id"] == "agent_team_a"

    def test_default_namespace_behavior(self, client, auth_headers_user1):
        """
        Test default namespace when not specified.
        Epic 12 Issue 2: Default namespace is 'default'.
        """
        project_id = "proj_default_ns_001"

        # Create memory without specifying namespace
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_default",
                "memory_type": "decision",
                "content": "Default namespace decision"
            }
        )

        assert create_response.json()["namespace"] == "default"

        # List memories (should be in default namespace)
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1
        )

        assert len(list_response.json()["memories"]) == 1
        assert list_response.json()["memories"][0]["namespace"] == "default"

    def test_cross_namespace_search(self, client, auth_headers_user1):
        """
        Test searching across all namespaces when no filter specified.
        Epic 12 Issue 2: Global search without namespace filter.
        """
        project_id = "proj_cross_ns_001"

        # Create memories in multiple namespaces
        namespaces = ["ns1", "ns2", "ns3"]
        for ns in namespaces:
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": f"agent_{ns}",
                    "run_id": f"run_{ns}",
                    "memory_type": "decision",
                    "content": f"{ns} decision",
                    "namespace": ns
                }
            )

        # List all memories without namespace filter
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should get all memories from all namespaces
        assert len(data["memories"]) == 3
        retrieved_namespaces = {m["namespace"] for m in data["memories"]}
        assert retrieved_namespaces == {"ns1", "ns2", "ns3"}


class TestAgentMemoryEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_content(self, client, auth_headers_user1):
        """
        Test storing very long content.
        Epic 12 Issue 2: Large content handling.
        """
        project_id = "proj_long_content_001"

        # Create content that's very long
        long_content = "x" * 10000

        response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_long",
                "memory_type": "context",
                "content": long_content
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify retrieval
        memory_id = response.json()["memory_id"]
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        assert get_response.status_code == status.HTTP_200_OK
        assert len(get_response.json()["content"]) == 10000

    def test_special_characters_in_content(self, client, auth_headers_user1):
        """
        Test storing content with special characters.
        Epic 12 Issue 2: Unicode and special character support.
        """
        project_id = "proj_special_chars_001"

        special_content = "Test with émojis 🚀 and spécial chärs: \n\t\"quotes\""

        response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_special",
                "memory_type": "decision",
                "content": special_content
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify content preserved
        memory_id = response.json()["memory_id"]
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        assert get_response.json()["content"] == special_content

    def test_pagination_boundary_conditions(self, client, auth_headers_user1):
        """
        Test pagination at boundaries.
        Epic 12 Issue 2: Pagination edge cases.
        """
        project_id = "proj_pagination_boundary_001"

        # Create exactly 5 memories
        for i in range(5):
            client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": "test_agent",
                    "run_id": f"run_{i}",
                    "memory_type": "decision",
                    "content": f"Decision {i}"
                }
            )

        # Test offset beyond total
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"offset": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["memories"]) == 0
        assert data["total"] == 5

        # Test limit larger than total
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"limit": 100}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["memories"]) == 5
        assert data["total"] == 5

    def test_complex_nested_metadata(self, client, auth_headers_user1):
        """
        Test storing complex nested metadata structures.
        Epic 12 Issue 2: Complex metadata support.
        """
        project_id = "proj_complex_metadata_001"

        complex_metadata = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep_nested"
                    },
                    "array": [1, 2, 3]
                },
                "boolean": True,
                "number": 42.5
            },
            "tags": ["tag1", "tag2", "tag3"]
        }

        response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "test_agent",
                "run_id": "run_metadata",
                "memory_type": "result",
                "content": "Complex metadata test",
                "metadata": complex_metadata
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify metadata preserved
        memory_id = response.json()["memory_id"]
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        retrieved_metadata = get_response.json()["metadata"]
        assert retrieved_metadata["level1"]["level2"]["level3"]["value"] == "deep_nested"
        assert retrieved_metadata["tags"] == ["tag1", "tag2", "tag3"]
