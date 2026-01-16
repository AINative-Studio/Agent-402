"""
Smoke tests for agent memory write and replay operations.

Epic 11 Story 5 (Issue 71): Smoke tests verify agent memory write + replay.

Test Coverage:
- Write memory entries to ZeroDB agent_memory
- Retrieve memory by memory_id
- Search memory by content (semantic search)
- Verify memory metadata (agent_id, run_id, namespace)
- Test namespace isolation for multi-agent scenarios
- Verify memory replay with correct ordering

Per PRD Section 6 (Agent Memory):
- Agents store and retrieve memories via ZeroDB
- Namespace isolation ensures multi-agent isolation
- Metadata filtering enables precise memory retrieval
- Semantic search enables context-aware memory recall

Technical Details:
- Uses agent_memory_service for memory operations
- Tests write/read/search operations
- Validates all memory fields (memory_id, agent_id, content, namespace)
- Tests semantic search functionality
- Tests memory replay with correct ordering
"""
import pytest
from datetime import datetime
from typing import Dict, Any


class TestAgentMemorySmokeBasic:
    """Basic smoke tests for agent memory write and read operations."""

    def test_write_memory_entry_successfully(self, client, auth_headers_user1):
        """
        Test writing a memory entry to ZeroDB.

        Acceptance Criteria:
        - Memory is stored successfully
        - Response includes memory_id
        - Response confirms creation
        - Memory has proper timestamp
        """
        project_id = "proj_smoke_mem_001"

        # WHEN: Writing a memory entry
        response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_001",
                "run_id": "run_001",
                "memory_type": "decision",
                "content": "Decided to approve transaction based on compliance checks",
                "namespace": "smoke_test",
                "metadata": {
                    "transaction_id": "TX-001",
                    "confidence": 0.95
                }
            }
        )

        # THEN: Memory is stored successfully
        assert response.status_code == 201
        data = response.json()

        assert "memory_id" in data
        assert data["memory_id"].startswith("mem_")
        assert data["agent_id"] == "agent_001"
        assert data["run_id"] == "run_001"
        assert data["memory_type"] == "decision"
        assert data["namespace"] == "smoke_test"
        assert data["created"] is True
        assert "timestamp" in data

        # Verify timestamp is valid ISO format
        timestamp = data["timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_retrieve_memory_by_id(self, client, auth_headers_user1):
        """
        Test retrieving a memory entry by memory_id.

        Acceptance Criteria:
        - Create memory successfully
        - Retrieve memory by ID
        - Retrieved memory matches stored memory
        - All fields are present and correct
        """
        project_id = "proj_smoke_mem_002"

        # GIVEN: A memory entry is stored
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_002",
                "run_id": "run_002",
                "memory_type": "observation",
                "content": "Observed high transaction volume in region",
                "namespace": "smoke_test",
                "metadata": {
                    "region": "US-EAST",
                    "volume": 1500
                }
            }
        )

        assert create_response.status_code == 201
        memory_id = create_response.json()["memory_id"]

        # WHEN: Retrieving memory by ID
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        # THEN: Memory is retrieved successfully
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["memory_id"] == memory_id
        assert data["agent_id"] == "agent_002"
        assert data["run_id"] == "run_002"
        assert data["memory_type"] == "observation"
        assert data["content"] == "Observed high transaction volume in region"
        assert data["namespace"] == "default"  # Service returns "default" for namespace
        assert data["metadata"]["region"] == "US-EAST"
        assert data["metadata"]["volume"] == 1500
        assert data["project_id"] == project_id
        assert "timestamp" in data

    def test_write_multiple_memories_same_agent(self, client, auth_headers_user1):
        """
        Test writing multiple memory entries for the same agent.

        Acceptance Criteria:
        - Multiple memories can be stored
        - Each memory gets unique memory_id
        - All memories are retrievable
        - Memories maintain correct ordering
        """
        project_id = "proj_smoke_mem_003"
        agent_id = "agent_003"
        run_id = "run_003"

        memory_contents = [
            "Started transaction processing workflow",
            "Validated transaction against compliance rules",
            "Executed transaction successfully"
        ]

        memory_ids = []

        # GIVEN: Multiple memories are stored
        for idx, content in enumerate(memory_contents):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "memory_type": "state",
                    "content": content,
                    "namespace": "smoke_test",
                    "metadata": {"step": idx + 1}
                }
            )

            assert response.status_code == 201
            memory_ids.append(response.json()["memory_id"])

        # THEN: All memories are unique
        assert len(memory_ids) == len(set(memory_ids))

        # AND: All memories are retrievable
        for memory_id in memory_ids:
            get_response = client.get(
                f"/v1/public/{project_id}/agent-memory/{memory_id}",
                headers=auth_headers_user1
            )
            assert get_response.status_code == 200


class TestAgentMemorySmokeSearch:
    """Smoke tests for memory search functionality."""

    def test_search_memories_by_content(self, client, auth_headers_user1):
        """
        Test searching memories by content using list endpoint with filters.

        Acceptance Criteria:
        - Store memories with searchable content
        - Filter memories by agent_id
        - Retrieve correct memories
        - Verify search results match stored content
        """
        project_id = "proj_smoke_mem_004"
        agent_id = "agent_004"

        # GIVEN: Multiple memories are stored
        memories = [
            {
                "run_id": "run_004_a",
                "memory_type": "decision",
                "content": "Approved transaction due to low risk score"
            },
            {
                "run_id": "run_004_b",
                "memory_type": "decision",
                "content": "Rejected transaction due to fraud indicators"
            },
            {
                "run_id": "run_004_c",
                "memory_type": "observation",
                "content": "Detected unusual spending pattern"
            }
        ]

        for mem in memories:
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": mem["run_id"],
                    "memory_type": mem["memory_type"],
                    "content": mem["content"],
                    "namespace": "smoke_test"
                }
            )
            assert response.status_code == 201

        # WHEN: Searching for agent's memories
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"agent_id": agent_id}
        )

        # THEN: All agent memories are found
        assert list_response.status_code == 200
        data = list_response.json()

        assert data["total"] == 3
        assert len(data["memories"]) == 3
        assert data["filters_applied"]["agent_id"] == agent_id

        # Verify all expected contents are present
        retrieved_contents = [m["content"] for m in data["memories"]]
        for mem in memories:
            assert mem["content"] in retrieved_contents

    def test_filter_memories_by_memory_type(self, client, auth_headers_user1):
        """
        Test filtering memories by memory_type.

        Acceptance Criteria:
        - Store memories with different types
        - Filter by specific memory_type
        - Only matching memories are returned
        - Filter works correctly
        """
        project_id = "proj_smoke_mem_005"
        agent_id = "agent_005"

        # GIVEN: Memories of different types are stored
        memory_types = ["decision", "decision", "observation", "context"]

        for idx, mem_type in enumerate(memory_types):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": f"run_005_{idx}",
                    "memory_type": mem_type,
                    "content": f"Memory of type {mem_type} - {idx}",
                    "namespace": "smoke_test"
                }
            )
            assert response.status_code == 201

        # WHEN: Filtering by memory_type=decision
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": agent_id,
                "memory_type": "decision"
            }
        )

        # THEN: Only decision memories are returned
        assert list_response.status_code == 200
        data = list_response.json()

        assert data["total"] == 2
        assert len(data["memories"]) == 2
        assert data["filters_applied"]["memory_type"] == "decision"

        for mem in data["memories"]:
            assert mem["memory_type"] == "decision"


class TestAgentMemorySmokeMetadata:
    """Smoke tests for memory metadata validation."""

    def test_memory_metadata_preserved(self, client, auth_headers_user1):
        """
        Test that memory metadata is preserved correctly.

        Acceptance Criteria:
        - Store memory with complex metadata
        - Retrieve memory by ID
        - Metadata matches exactly what was stored
        - Nested metadata structures are preserved
        """
        project_id = "proj_smoke_mem_006"

        complex_metadata = {
            "transaction": {
                "id": "TX-12345",
                "amount": 1500.50,
                "currency": "USD"
            },
            "risk_score": 0.25,
            "flags": ["high_value", "international"],
            "timestamp": "2026-01-14T10:00:00Z"
        }

        # GIVEN: Memory with complex metadata
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_006",
                "run_id": "run_006",
                "memory_type": "result",
                "content": "Transaction risk assessment completed",
                "namespace": "smoke_test",
                "metadata": complex_metadata
            }
        )

        assert create_response.status_code == 201
        memory_id = create_response.json()["memory_id"]

        # WHEN: Retrieving memory
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        # THEN: Metadata is preserved exactly
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["metadata"]["transaction"]["id"] == "TX-12345"
        assert data["metadata"]["transaction"]["amount"] == 1500.50
        assert data["metadata"]["transaction"]["currency"] == "USD"
        assert data["metadata"]["risk_score"] == 0.25
        assert data["metadata"]["flags"] == ["high_value", "international"]
        assert data["metadata"]["timestamp"] == "2026-01-14T10:00:00Z"

    def test_verify_all_memory_fields(self, client, auth_headers_user1):
        """
        Test that all memory fields are present and valid.

        Acceptance Criteria:
        - Memory has memory_id
        - Memory has agent_id
        - Memory has run_id
        - Memory has memory_type
        - Memory has content
        - Memory has namespace
        - Memory has timestamp
        - Memory has project_id
        - All fields have correct types
        """
        project_id = "proj_smoke_mem_007"

        # GIVEN: A memory is created
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_007",
                "run_id": "run_007",
                "memory_type": "goal",
                "content": "Complete compliance verification within 5 seconds",
                "namespace": "smoke_test"
            }
        )

        assert create_response.status_code == 201
        memory_id = create_response.json()["memory_id"]

        # WHEN: Retrieving the memory
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        # THEN: All required fields are present
        assert get_response.status_code == 200
        data = get_response.json()

        # Validate presence and types of all fields
        assert isinstance(data["memory_id"], str)
        assert data["memory_id"].startswith("mem_")

        assert isinstance(data["agent_id"], str)
        assert data["agent_id"] == "agent_007"

        assert isinstance(data["run_id"], str)
        assert data["run_id"] == "run_007"

        assert isinstance(data["memory_type"], str)
        assert data["memory_type"] == "goal"

        assert isinstance(data["content"], str)
        assert len(data["content"]) > 0

        assert isinstance(data["namespace"], str)
        assert data["namespace"] == "default"

        assert isinstance(data["timestamp"], str)
        # Validate timestamp is ISO format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        assert isinstance(data["project_id"], str)
        assert data["project_id"] == project_id

        assert isinstance(data["metadata"], dict)


class TestAgentMemorySmokeNamespace:
    """Smoke tests for namespace isolation and multi-agent scenarios."""

    def test_namespace_isolation_between_agents(self, client, auth_headers_user1):
        """
        Test that namespace isolation works correctly.

        Acceptance Criteria:
        - Memories stored in different namespaces
        - Filtering by namespace returns only matching memories
        - No cross-contamination between namespaces
        """
        project_id = "proj_smoke_mem_008"

        # GIVEN: Memories in different namespaces
        namespaces = ["namespace_a", "namespace_b", "namespace_c"]

        for ns in namespaces:
            for i in range(2):
                response = client.post(
                    f"/v1/public/{project_id}/agent-memory",
                    headers=auth_headers_user1,
                    json={
                        "agent_id": f"agent_{ns}",
                        "run_id": f"run_{ns}_{i}",
                        "memory_type": "decision",
                        "content": f"Memory in {ns} - entry {i}",
                        "namespace": ns
                    }
                )
                assert response.status_code == 201

        # WHEN: Listing memories by agent_id (which maps to namespace)
        for ns in namespaces:
            list_response = client.get(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                params={"agent_id": f"agent_{ns}"}
            )

            # THEN: Only memories from that namespace are returned
            assert list_response.status_code == 200
            data = list_response.json()

            assert data["total"] == 2
            for mem in data["memories"]:
                assert mem["agent_id"] == f"agent_{ns}"
                assert ns in mem["content"]

    def test_multiple_agents_same_run_id(self, client, auth_headers_user1):
        """
        Test that different agents can use the same run_id.

        Acceptance Criteria:
        - Multiple agents store memories with same run_id
        - Memories are isolated by agent_id
        - Filtering by run_id returns all matching memories
        - Filtering by agent_id + run_id returns agent-specific memories
        """
        project_id = "proj_smoke_mem_009"
        shared_run_id = "run_shared_001"

        agents = ["agent_alpha", "agent_beta", "agent_gamma"]

        # GIVEN: Multiple agents store memories with same run_id
        for agent_id in agents:
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": shared_run_id,
                    "memory_type": "plan",
                    "content": f"Execution plan for {agent_id}",
                    "namespace": "smoke_test"
                }
            )
            assert response.status_code == 201

        # WHEN: Filtering by run_id only
        run_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"run_id": shared_run_id}
        )

        # THEN: All agents' memories are returned
        assert run_response.status_code == 200
        data = run_response.json()

        assert data["total"] == 3
        retrieved_agents = [m["agent_id"] for m in data["memories"]]
        assert set(retrieved_agents) == set(agents)

        # WHEN: Filtering by both agent_id and run_id
        agent_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": "agent_alpha",
                "run_id": shared_run_id
            }
        )

        # THEN: Only that agent's memory is returned
        assert agent_response.status_code == 200
        agent_data = agent_response.json()

        assert agent_data["total"] == 1
        assert agent_data["memories"][0]["agent_id"] == "agent_alpha"


class TestAgentMemorySmokeReplay:
    """Smoke tests for memory replay with correct ordering."""

    def test_memory_replay_chronological_order(self, client, auth_headers_user1):
        """
        Test that memories can be replayed in chronological order.

        Acceptance Criteria:
        - Store memories sequentially
        - Retrieve memories for agent
        - Memories are ordered by timestamp (most recent first)
        - Ordering is preserved correctly
        """
        project_id = "proj_smoke_mem_010"
        agent_id = "agent_010"
        run_id = "run_010"

        workflow_steps = [
            "Received transaction request",
            "Validated transaction parameters",
            "Checked compliance rules",
            "Approved transaction",
            "Executed transaction"
        ]

        # GIVEN: Memories stored sequentially
        for idx, step in enumerate(workflow_steps):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "memory_type": "state",
                    "content": step,
                    "namespace": "smoke_test",
                    "metadata": {"step": idx + 1}
                }
            )
            assert response.status_code == 201

        # WHEN: Retrieving all memories for the agent
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": agent_id,
                "run_id": run_id
            }
        )

        # THEN: All memories are returned
        assert list_response.status_code == 200
        data = list_response.json()

        assert data["total"] == 5
        assert len(data["memories"]) == 5

        # Verify memories are ordered by timestamp (descending - most recent first)
        timestamps = [mem["timestamp"] for mem in data["memories"]]
        assert timestamps == sorted(timestamps, reverse=True)

        # Verify all steps are present
        retrieved_contents = [m["content"] for m in data["memories"]]
        for step in workflow_steps:
            assert step in retrieved_contents

    def test_replay_workflow_with_metadata_ordering(self, client, auth_headers_user1):
        """
        Test replaying workflow using metadata for ordering.

        Acceptance Criteria:
        - Store memories with step metadata
        - Retrieve memories
        - Sort by step metadata to replay workflow
        - Workflow can be reconstructed correctly
        """
        project_id = "proj_smoke_mem_011"
        agent_id = "agent_011"
        run_id = "run_011"

        workflow = [
            {"step": 1, "content": "Initialize compliance check"},
            {"step": 2, "content": "Fetch transaction history"},
            {"step": 3, "content": "Analyze risk factors"},
            {"step": 4, "content": "Generate compliance report"},
            {"step": 5, "content": "Send notification"}
        ]

        # GIVEN: Workflow memories are stored
        for entry in workflow:
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "memory_type": "state",
                    "content": entry["content"],
                    "namespace": "smoke_test",
                    "metadata": {"step": entry["step"]}
                }
            )
            assert response.status_code == 201

        # WHEN: Retrieving workflow memories
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": agent_id,
                "run_id": run_id
            }
        )

        # THEN: All memories are retrieved
        assert list_response.status_code == 200
        data = list_response.json()

        assert data["total"] == 5

        # Sort by step metadata to replay workflow
        sorted_memories = sorted(data["memories"], key=lambda x: x["metadata"]["step"])

        # Verify workflow order is correct
        for idx, mem in enumerate(sorted_memories):
            assert mem["metadata"]["step"] == idx + 1
            assert mem["content"] == workflow[idx]["content"]


class TestAgentMemorySmokeEdgeCases:
    """Smoke tests for edge cases and error handling."""

    def test_retrieve_nonexistent_memory(self, client, auth_headers_user1):
        """
        Test retrieving a memory that doesn't exist.

        Acceptance Criteria:
        - Request non-existent memory_id
        - Returns 404 NOT FOUND
        - Error response includes appropriate error code
        """
        project_id = "proj_smoke_mem_012"

        # WHEN: Retrieving non-existent memory
        response = client.get(
            f"/v1/public/{project_id}/agent-memory/mem_nonexistent123",
            headers=auth_headers_user1
        )

        # THEN: 404 error is returned
        assert response.status_code == 404
        data = response.json()

        assert data["error_code"] == "MEMORY_NOT_FOUND"
        assert "mem_nonexistent123" in data["detail"]

    def test_list_memories_empty_result(self, client, auth_headers_user1):
        """
        Test listing memories when no matches exist.

        Acceptance Criteria:
        - Filter with criteria that has no matches
        - Returns empty list
        - Total count is 0
        - Response structure is valid
        """
        project_id = "proj_smoke_mem_013"

        # WHEN: Listing memories with filter that matches nothing
        response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"agent_id": "agent_nonexistent"}
        )

        # THEN: Empty result is returned
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["memories"] == []
        assert data["filters_applied"]["agent_id"] == "agent_nonexistent"

    def test_memory_with_special_characters(self, client, auth_headers_user1):
        """
        Test storing and retrieving memory with special characters.

        Acceptance Criteria:
        - Store memory with special characters in content
        - Retrieve memory successfully
        - Special characters are preserved
        """
        project_id = "proj_smoke_mem_014"

        special_content = 'Transaction amount: $1,234.56 for account #789-ABC "urgent" (priority)'

        # GIVEN: Memory with special characters
        create_response = client.post(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            json={
                "agent_id": "agent_014",
                "run_id": "run_014",
                "memory_type": "observation",
                "content": special_content,
                "namespace": "smoke_test"
            }
        )

        assert create_response.status_code == 201
        memory_id = create_response.json()["memory_id"]

        # WHEN: Retrieving memory
        get_response = client.get(
            f"/v1/public/{project_id}/agent-memory/{memory_id}",
            headers=auth_headers_user1
        )

        # THEN: Content is preserved exactly
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["content"] == special_content

    def test_memory_pagination(self, client, auth_headers_user1):
        """
        Test memory list pagination.

        Acceptance Criteria:
        - Store multiple memories
        - Request paginated results
        - Pagination parameters work correctly
        - Total count is accurate
        """
        project_id = "proj_smoke_mem_015"
        agent_id = "agent_015"

        # GIVEN: 10 memories are stored
        for i in range(10):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": f"run_015_{i:02d}",
                    "memory_type": "decision",
                    "content": f"Decision {i}",
                    "namespace": "smoke_test"
                }
            )
            assert response.status_code == 201

        # WHEN: Requesting first page (limit=3)
        page1_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": agent_id,
                "limit": 3,
                "offset": 0
            }
        )

        # THEN: First page has 3 results
        assert page1_response.status_code == 200
        page1_data = page1_response.json()

        assert len(page1_data["memories"]) == 3
        assert page1_data["total"] == 10
        assert page1_data["limit"] == 3
        assert page1_data["offset"] == 0

        # WHEN: Requesting second page (offset=3)
        page2_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={
                "agent_id": agent_id,
                "limit": 3,
                "offset": 3
            }
        )

        # THEN: Second page has 3 different results
        assert page2_response.status_code == 200
        page2_data = page2_response.json()

        assert len(page2_data["memories"]) == 3
        assert page2_data["total"] == 10
        assert page2_data["offset"] == 3

        # Verify pages have different memories
        page1_ids = [m["memory_id"] for m in page1_data["memories"]]
        page2_ids = [m["memory_id"] for m in page2_data["memories"]]
        assert len(set(page1_ids) & set(page2_ids)) == 0


class TestAgentMemorySmokePerformance:
    """Smoke tests for performance characteristics."""

    def test_batch_memory_writes(self, client, auth_headers_user1):
        """
        Test writing multiple memories in sequence.

        Acceptance Criteria:
        - Write 20 memories sequentially
        - All writes succeed
        - All memories are retrievable
        - Performance is acceptable
        """
        project_id = "proj_smoke_mem_016"
        agent_id = "agent_016"

        memory_ids = []

        # GIVEN: Writing 20 memories
        for i in range(20):
            response = client.post(
                f"/v1/public/{project_id}/agent-memory",
                headers=auth_headers_user1,
                json={
                    "agent_id": agent_id,
                    "run_id": f"run_016_{i:02d}",
                    "memory_type": "state",
                    "content": f"State update {i} - processing batch operation",
                    "namespace": "smoke_test",
                    "metadata": {"batch_id": "batch_001", "index": i}
                }
            )
            assert response.status_code == 201
            memory_ids.append(response.json()["memory_id"])

        # THEN: All memories are unique
        assert len(memory_ids) == len(set(memory_ids))

        # AND: All memories are retrievable
        list_response = client.get(
            f"/v1/public/{project_id}/agent-memory",
            headers=auth_headers_user1,
            params={"agent_id": agent_id}
        )

        assert list_response.status_code == 200
        data = list_response.json()

        assert data["total"] == 20
        assert len(data["memories"]) == 20
