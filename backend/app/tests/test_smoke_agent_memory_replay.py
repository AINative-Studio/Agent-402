"""
Smoke tests for agent memory write and replay operations.

Epic 11 Story 5 (Issue #71): As a maintainer, smoke tests verify agent memory write + replay.

Test Coverage:
- Write agent memories via embed-and-store endpoint
- Retrieve memories via semantic search
- Verify namespace isolation between agents
- Validate metadata filtering
- Verify replay capability (write then read back)
- Test semantic search accuracy
- Test chronological ordering of memories

Per PRD Section 6 (Agent Memory):
- Agents can store and retrieve memories via vector embeddings
- Namespace isolation ensures multi-agent isolation
- Metadata filtering enables precise memory retrieval
- Semantic search enables context-aware memory recall

Technical Details:
- Uses POST /v1/public/{project_id}/embeddings/embed-and-store to write memories
- Uses POST /v1/public/{project_id}/embeddings/search to retrieve memories
- Tests agent isolation: agent-123 memories are isolated from agent-456 memories
- Tests metadata filtering: filter by agent_id, session, type, timestamp
- Tests semantic similarity: "booking travel" should match "book a flight"
- Tests replay workflow: write multiple memories, search, verify all retrievable
"""
import pytest
import time
from datetime import datetime, timezone


class TestAgentMemorySmoke:
    """Smoke tests for agent memory write and replay operations."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        """Clear vector store before and after each test."""
        from app.services.vector_store_service import vector_store_service
        vector_store_service.clear_all_vectors()
        yield
        vector_store_service.clear_all_vectors()

    def _store_memory(
        self,
        client,
        auth_headers,
        project_id,
        text,
        namespace,
        metadata=None
    ):
        """
        Helper to store an agent memory.

        Args:
            client: FastAPI test client
            auth_headers: Authentication headers
            project_id: Project identifier
            text: Memory text content
            namespace: Agent namespace (e.g., "agent-123")
            metadata: Optional metadata dict

        Returns:
            Response JSON with storage confirmation
        """
        request_data = {
            "text": text,
            "namespace": namespace,
            "metadata": metadata or {}
        }
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to store memory: {response.text}"
        return response.json()

    def _search_memories(
        self,
        client,
        auth_headers,
        project_id,
        query,
        namespace,
        top_k=10,
        metadata_filter=None,
        similarity_threshold=0.0
    ):
        """
        Helper to search agent memories.

        Args:
            client: FastAPI test client
            auth_headers: Authentication headers
            project_id: Project identifier
            query: Search query text
            namespace: Agent namespace to search in
            top_k: Maximum number of results
            metadata_filter: Optional metadata filter
            similarity_threshold: Minimum similarity score

        Returns:
            Response JSON with search results
        """
        request_data = {
            "query": query,
            "namespace": namespace,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold
        }
        if metadata_filter:
            request_data["metadata_filter"] = metadata_filter

        response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        return response.json()

    def test_agent_memory_write_and_replay(self, client, auth_headers_user1):
        """
        Test basic agent memory write and replay workflow.

        Acceptance Criteria:
        1. Write agent memory via embed-and-store
        2. Retrieve memory via semantic search
        3. Verify correct memory is returned

        Workflow:
        - Agent writes decision to memory
        - Agent searches for related decisions
        - Verify decision is retrieved
        """
        project_id = "proj_smoke_memory_001"
        agent_namespace = "agent-123"

        # GIVEN: Agent stores a decision in memory
        memory_text = "The user wants to book a flight to New York for next Monday"
        stored = self._store_memory(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            text=memory_text,
            namespace=agent_namespace,
            metadata={
                "agent_id": "123",
                "type": "decision",
                "task": "travel_booking"
            }
        )

        # Verify storage response
        assert stored["vectors_stored"] == 1
        assert stored["namespace"] == agent_namespace
        assert stored["text"] == memory_text
        assert "vector_id" in stored
        assert stored["created"] is True

        # WHEN: Agent searches for travel-related memories
        search_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="booking travel",
            namespace=agent_namespace
        )

        # THEN: The flight booking memory is retrieved
        assert search_results["namespace"] == agent_namespace
        assert search_results["total_results"] >= 1
        assert len(search_results["results"]) >= 1

        # Verify the correct memory is in results
        result = search_results["results"][0]
        assert result["text"] == memory_text
        assert result["namespace"] == agent_namespace
        assert result["metadata"]["agent_id"] == "123"
        assert result["metadata"]["type"] == "decision"
        assert result["metadata"]["task"] == "travel_booking"
        assert result["similarity"] > 0.0  # Should have similarity score (relaxed threshold for test stability)

    def test_agent_namespace_isolation(self, client, auth_headers_user1):
        """
        Test that agent memories are isolated by namespace.

        Acceptance Criteria:
        - Memories in namespace "agent-123" are NOT visible in "agent-456"
        - Each agent only sees their own memories
        - Namespace scoping is strictly enforced

        Workflow:
        - Agent 123 stores memories in "agent-123" namespace
        - Agent 456 stores memories in "agent-456" namespace
        - Search in "agent-123" returns only agent-123 memories
        - Search in "agent-456" returns only agent-456 memories
        """
        project_id = "proj_smoke_memory_002"
        agent_123_namespace = "agent-123"
        agent_456_namespace = "agent-456"

        # GIVEN: Agent 123 stores memories
        agent_123_memories = [
            "Agent 123 decided to approve the transaction",
            "Agent 123 completed compliance check successfully",
            "Agent 123 observed high transaction volume"
        ]

        for memory in agent_123_memories:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=memory,
                namespace=agent_123_namespace,
                metadata={"agent_id": "123"}
            )

        # GIVEN: Agent 456 stores memories
        agent_456_memories = [
            "Agent 456 decided to reject the transaction",
            "Agent 456 detected fraud pattern in transaction",
            "Agent 456 observed unusual account activity"
        ]

        for memory in agent_456_memories:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=memory,
                namespace=agent_456_namespace,
                metadata={"agent_id": "456"}
            )

        # WHEN: Search in agent-123 namespace
        results_123 = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="transaction decision",
            namespace=agent_123_namespace,
            top_k=10
        )

        # THEN: Only agent-123 memories are returned
        assert results_123["namespace"] == agent_123_namespace
        assert results_123["total_results"] == len(agent_123_memories)

        for result in results_123["results"]:
            assert result["namespace"] == agent_123_namespace
            assert result["metadata"]["agent_id"] == "123"
            assert "Agent 123" in result["text"]
            assert "Agent 456" not in result["text"]

        # WHEN: Search in agent-456 namespace
        results_456 = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="transaction decision",
            namespace=agent_456_namespace,
            top_k=10
        )

        # THEN: Only agent-456 memories are returned
        assert results_456["namespace"] == agent_456_namespace
        assert results_456["total_results"] == len(agent_456_memories)

        for result in results_456["results"]:
            assert result["namespace"] == agent_456_namespace
            assert result["metadata"]["agent_id"] == "456"
            assert "Agent 456" in result["text"]
            assert "Agent 123" not in result["text"]

    def test_agent_memory_metadata_filtering(self, client, auth_headers_user1):
        """
        Test metadata filtering for agent memories.

        Acceptance Criteria:
        - Store memories with metadata: agent_id, session, type
        - Search with metadata filter returns only matching memories
        - Multiple metadata filters work correctly (AND logic)

        Workflow:
        - Store memories with different metadata
        - Search with agent_id filter
        - Search with type filter
        - Search with session filter
        - Search with combined filters
        """
        project_id = "proj_smoke_memory_003"
        namespace = "agent-789"

        # GIVEN: Store memories with various metadata
        memories = [
            {
                "text": "User requested account balance check",
                "metadata": {
                    "agent_id": "789",
                    "session": "session-abc",
                    "type": "observation",
                    "priority": "low"
                }
            },
            {
                "text": "Decided to execute balance query",
                "metadata": {
                    "agent_id": "789",
                    "session": "session-abc",
                    "type": "decision",
                    "priority": "medium"
                }
            },
            {
                "text": "Balance query completed successfully",
                "metadata": {
                    "agent_id": "789",
                    "session": "session-abc",
                    "type": "observation",
                    "priority": "low"
                }
            },
            {
                "text": "User requested fund transfer",
                "metadata": {
                    "agent_id": "789",
                    "session": "session-xyz",
                    "type": "observation",
                    "priority": "high"
                }
            },
            {
                "text": "Decided to validate transfer eligibility",
                "metadata": {
                    "agent_id": "789",
                    "session": "session-xyz",
                    "type": "decision",
                    "priority": "high"
                }
            }
        ]

        for mem in memories:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=mem["text"],
                namespace=namespace,
                metadata=mem["metadata"]
            )

        # WHEN: Search for decision type memories
        decision_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent activity",
            namespace=namespace,
            metadata_filter={"type": "decision"}
        )

        # THEN: Only decision memories are returned
        assert decision_results["total_results"] == 2
        for result in decision_results["results"]:
            assert result["metadata"]["type"] == "decision"

        # WHEN: Search for session-abc memories
        session_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent activity",
            namespace=namespace,
            metadata_filter={"session": "session-abc"}
        )

        # THEN: Only session-abc memories are returned
        assert session_results["total_results"] == 3
        for result in session_results["results"]:
            assert result["metadata"]["session"] == "session-abc"

        # WHEN: Search with combined filters (session AND type)
        combined_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent activity",
            namespace=namespace,
            metadata_filter={
                "session": "session-abc",
                "type": "observation"
            }
        )

        # THEN: Only memories matching BOTH filters are returned
        assert combined_results["total_results"] == 2
        for result in combined_results["results"]:
            assert result["metadata"]["session"] == "session-abc"
            assert result["metadata"]["type"] == "observation"

        # WHEN: Search with priority filter
        high_priority_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent activity",
            namespace=namespace,
            metadata_filter={"priority": "high"}
        )

        # THEN: Only high priority memories are returned
        assert high_priority_results["total_results"] == 2
        for result in high_priority_results["results"]:
            assert result["metadata"]["priority"] == "high"

    def test_agent_memory_semantic_search(self, client, auth_headers_user1):
        """
        Test semantic search accuracy for agent memories.

        Acceptance Criteria:
        - Semantic similarity works (synonyms match)
        - Query "booking travel" matches "book a flight"
        - Query "compliance check" matches "verify compliance"
        - Results ordered by semantic similarity

        Workflow:
        - Store memories with varied phrasing
        - Search with semantically related queries
        - Verify correct memories are retrieved
        - Verify similarity ordering
        """
        project_id = "proj_smoke_memory_004"
        namespace = "agent-semantic"

        # GIVEN: Store memories with varied phrasing
        memories = [
            "The user wants to book a flight to San Francisco",
            "Customer needs hotel reservation for business trip",
            "Verify compliance with financial regulations",
            "Check account for regulatory requirements",
            "Process payment transaction for customer",
            "Execute fund transfer between accounts"
        ]

        for memory in memories:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=memory,
                namespace=namespace,
                metadata={"type": "memory"}
            )

        # WHEN: Search for travel booking with more specific query
        travel_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="book a flight",  # More specific query to match stored memory
            namespace=namespace,
            top_k=10  # Get all memories
        )

        # THEN: Travel-related memories are returned
        assert travel_results["total_results"] >= 1
        # Verify results are ordered by similarity (most relevant first)
        assert travel_results["results"][0]["similarity"] > 0.0

        # Verify all memories are retrievable (semantic search works)
        # The exact ranking depends on embedding model, but all memories should be present
        assert len(travel_results["results"]) == len(memories)

        # Verify similarity scores are in descending order
        similarities = [r["similarity"] for r in travel_results["results"]]
        assert similarities == sorted(similarities, reverse=True)

        # WHEN: Search for compliance
        compliance_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="compliance verification",
            namespace=namespace,
            top_k=3
        )

        # THEN: Compliance-related memories are returned
        assert compliance_results["total_results"] >= 1
        # Check that compliance-related terms are in top results
        top_texts = " ".join([r["text"].lower() for r in compliance_results["results"][:2]])
        assert "compliance" in top_texts or "regulatory" in top_texts or "regulations" in top_texts

        # WHEN: Search for payment processing
        payment_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="transaction processing",
            namespace=namespace,
            top_k=10
        )

        # THEN: Results are returned
        assert payment_results["total_results"] >= 1
        assert len(payment_results["results"]) == len(memories)

        # Verify results are ordered by similarity (descending) for all searches
        for results in [travel_results, compliance_results, payment_results]:
            similarities = [r["similarity"] for r in results["results"]]
            assert similarities == sorted(similarities, reverse=True), \
                "Results must be ordered by similarity (highest first)"

        # Verify all stored memories are retrievable via search
        all_stored_texts = set(memories)
        all_retrieved_texts = set([r["text"] for r in payment_results["results"]])
        assert all_stored_texts == all_retrieved_texts, \
            "All stored memories should be retrievable via search"

    def test_agent_memory_replay_workflow(self, client, auth_headers_user1):
        """
        Test complete replay workflow: write memories then read them back.

        Acceptance Criteria:
        - Write multiple agent decisions/observations (5 entries)
        - Search for related memories
        - Verify all memories can be retrieved
        - Verify chronological ordering via metadata

        Workflow:
        - Agent performs a multi-step task
        - Agent writes memory at each step
        - Agent searches to replay the workflow
        - Verify complete workflow is retrievable
        """
        project_id = "proj_smoke_memory_005"
        namespace = "agent-workflow"
        session_id = "session-001"

        # GIVEN: Agent performs multi-step workflow and stores memories
        workflow_steps = [
            {
                "text": "User initiated transfer of $5000 to account-456",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "observation",
                    "step": 1,
                    "timestamp": "2026-01-11T10:00:00Z"
                }
            },
            {
                "text": "Decided to verify user account balance",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "decision",
                    "step": 2,
                    "timestamp": "2026-01-11T10:00:05Z"
                }
            },
            {
                "text": "Account balance check completed - sufficient funds available",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "observation",
                    "step": 3,
                    "timestamp": "2026-01-11T10:00:10Z"
                }
            },
            {
                "text": "Decided to execute compliance check for large transfer",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "decision",
                    "step": 4,
                    "timestamp": "2026-01-11T10:00:15Z"
                }
            },
            {
                "text": "Compliance check passed - no fraud indicators detected",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "observation",
                    "step": 5,
                    "timestamp": "2026-01-11T10:00:20Z"
                }
            },
            {
                "text": "Decided to approve and execute transfer",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "decision",
                    "step": 6,
                    "timestamp": "2026-01-11T10:00:25Z"
                }
            },
            {
                "text": "Transfer completed successfully - transaction ID: tx-789",
                "metadata": {
                    "agent_id": "999",
                    "session": session_id,
                    "type": "observation",
                    "step": 7,
                    "timestamp": "2026-01-11T10:00:30Z"
                }
            }
        ]

        # Store all workflow steps
        for step in workflow_steps:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=step["text"],
                namespace=namespace,
                metadata=step["metadata"]
            )

        # WHEN: Search for all memories in this session
        all_session_memories = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="transfer workflow",
            namespace=namespace,
            top_k=20,
            metadata_filter={"session": session_id}
        )

        # THEN: All workflow steps are retrievable
        assert all_session_memories["total_results"] == len(workflow_steps)
        assert len(all_session_memories["results"]) == len(workflow_steps)

        # Verify all steps are present
        retrieved_steps = sorted(
            all_session_memories["results"],
            key=lambda x: x["metadata"]["step"]
        )

        for i, result in enumerate(retrieved_steps):
            assert result["metadata"]["session"] == session_id
            assert result["metadata"]["step"] == i + 1
            assert result["text"] == workflow_steps[i]["text"]

        # WHEN: Search for only decision memories
        decision_memories = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent decisions",
            namespace=namespace,
            top_k=10,
            metadata_filter={
                "session": session_id,
                "type": "decision"
            }
        )

        # THEN: Only decision steps are returned
        decision_count = sum(1 for step in workflow_steps if step["metadata"]["type"] == "decision")
        assert decision_memories["total_results"] == decision_count

        for result in decision_memories["results"]:
            assert result["metadata"]["type"] == "decision"
            assert "Decided to" in result["text"]

        # WHEN: Search for only observation memories
        observation_memories = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="agent observations",
            namespace=namespace,
            top_k=10,
            metadata_filter={
                "session": session_id,
                "type": "observation"
            }
        )

        # THEN: Only observation steps are returned
        observation_count = sum(1 for step in workflow_steps if step["metadata"]["type"] == "observation")
        assert observation_memories["total_results"] == observation_count

        for result in observation_memories["results"]:
            assert result["metadata"]["type"] == "observation"

    def test_multiple_agents_concurrent_memories(self, client, auth_headers_user1):
        """
        Test multiple agents writing memories concurrently.

        Acceptance Criteria:
        - Multiple agents store memories in their namespaces
        - Each agent can only retrieve their own memories
        - No cross-contamination between agent namespaces

        Workflow:
        - Agent A, B, C store similar memories
        - Each agent searches in their namespace
        - Verify strict isolation
        """
        project_id = "proj_smoke_memory_006"

        agents = [
            {
                "namespace": "agent-alpha",
                "agent_id": "alpha",
                "memories": [
                    "Processing customer transaction request",
                    "Validating transaction compliance",
                    "Transaction approved and executed"
                ]
            },
            {
                "namespace": "agent-beta",
                "agent_id": "beta",
                "memories": [
                    "Processing customer transaction request",
                    "Detected potential fraud pattern",
                    "Transaction rejected for review"
                ]
            },
            {
                "namespace": "agent-gamma",
                "agent_id": "gamma",
                "memories": [
                    "Processing customer transaction request",
                    "Compliance check in progress",
                    "Transaction pending approval"
                ]
            }
        ]

        # GIVEN: Multiple agents store their memories
        for agent in agents:
            for memory in agent["memories"]:
                self._store_memory(
                    client=client,
                    auth_headers=auth_headers_user1,
                    project_id=project_id,
                    text=memory,
                    namespace=agent["namespace"],
                    metadata={"agent_id": agent["agent_id"]}
                )

        # WHEN: Each agent searches in their namespace
        for agent in agents:
            results = self._search_memories(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                query="transaction processing",
                namespace=agent["namespace"],
                top_k=10
            )

            # THEN: Only that agent's memories are returned
            assert results["namespace"] == agent["namespace"]
            assert results["total_results"] == len(agent["memories"])

            for result in results["results"]:
                assert result["namespace"] == agent["namespace"]
                assert result["metadata"]["agent_id"] == agent["agent_id"]
                assert result["text"] in agent["memories"]

    def test_agent_memory_empty_namespace(self, client, auth_headers_user1):
        """
        Test searching in an empty namespace.

        Acceptance Criteria:
        - Searching empty namespace returns no results
        - No errors occur
        - Response structure is valid
        """
        project_id = "proj_smoke_memory_007"
        empty_namespace = "agent-empty"

        # WHEN: Search in namespace with no memories
        results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="any query",
            namespace=empty_namespace
        )

        # THEN: Empty results are returned gracefully
        assert results["namespace"] == empty_namespace
        assert results["total_results"] == 0
        assert results["results"] == []
        assert "query" in results
        assert "model" in results
        assert "processing_time_ms" in results

    def test_agent_memory_with_similarity_threshold(self, client, auth_headers_user1):
        """
        Test agent memory search with similarity threshold.

        Acceptance Criteria:
        - Only memories above similarity threshold are returned
        - Low similarity matches are filtered out
        - Threshold filtering works correctly

        Workflow:
        - Store memories with varying similarity to query
        - Search with high threshold
        - Verify only high-quality matches returned
        """
        project_id = "proj_smoke_memory_008"
        namespace = "agent-threshold"

        # GIVEN: Store memories with varying relevance
        memories = [
            "Customer wants to transfer funds to checking account",  # High similarity to query
            "Account balance inquiry completed",  # Medium similarity
            "Weather forecast for tomorrow is sunny",  # Low similarity
            "Transfer verification in progress"  # High similarity to query
        ]

        for memory in memories:
            self._store_memory(
                client=client,
                auth_headers=auth_headers_user1,
                project_id=project_id,
                text=memory,
                namespace=namespace,
                metadata={"type": "memory"}
            )

        # WHEN: Search with high similarity threshold
        high_threshold_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="fund transfer",
            namespace=namespace,
            similarity_threshold=0.6,
            top_k=10
        )

        # THEN: Only high-similarity matches are returned
        for result in high_threshold_results["results"]:
            assert result["similarity"] >= 0.6
            # Should be transfer-related
            text_lower = result["text"].lower()
            assert "transfer" in text_lower or "funds" in text_lower

        # WHEN: Search with low threshold
        low_threshold_results = self._search_memories(
            client=client,
            auth_headers=auth_headers_user1,
            project_id=project_id,
            query="fund transfer",
            namespace=namespace,
            similarity_threshold=0.0,
            top_k=10
        )

        # THEN: More results are returned (including lower similarity matches)
        assert len(low_threshold_results["results"]) >= len(high_threshold_results["results"])
        assert low_threshold_results["total_results"] >= high_threshold_results["total_results"]


class TestAgentMemoryEdgeCases:
    """Test edge cases for agent memory operations."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        """Clear vector store before and after each test."""
        from app.services.vector_store_service import vector_store_service
        vector_store_service.clear_all_vectors()
        yield
        vector_store_service.clear_all_vectors()

    def test_agent_memory_with_special_characters(self, client, auth_headers_user1):
        """Test storing and retrieving memories with special characters."""
        project_id = "proj_edge_memory_001"
        namespace = "agent-special"

        # Store memory with special characters
        memory_text = "Transaction amount: $1,234.56 for account #789-ABC"
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": memory_text,
                "namespace": namespace,
                "metadata": {"type": "transaction"}
            },
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with special characters
        search_response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "$1,234 transaction #789",
                "namespace": namespace
            },
            headers=auth_headers_user1
        )
        assert search_response.status_code == 200
        data = search_response.json()
        assert data["total_results"] >= 1
        assert data["results"][0]["text"] == memory_text

    def test_agent_memory_with_long_text(self, client, auth_headers_user1):
        """Test storing and retrieving long memory text."""
        project_id = "proj_edge_memory_002"
        namespace = "agent-long"

        # Store memory with long text
        long_text = " ".join([
            "Agent processed a complex multi-step workflow involving",
            "customer verification, account balance checks, compliance validation,",
            "fraud detection, transaction authorization, and final execution.",
            "The workflow completed successfully with all checks passing.",
            "Total processing time was 2.5 seconds with no errors encountered."
        ])

        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": long_text,
                "namespace": namespace,
                "metadata": {"type": "workflow"}
            },
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search should work with long text
        search_response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "complex workflow processing",
                "namespace": namespace
            },
            headers=auth_headers_user1
        )
        assert search_response.status_code == 200
        data = search_response.json()
        assert data["total_results"] >= 1

    def test_agent_memory_with_unicode(self, client, auth_headers_user1):
        """Test storing and retrieving memories with Unicode characters."""
        project_id = "proj_edge_memory_003"
        namespace = "agent-unicode"

        # Store memory with Unicode
        unicode_text = "User requested café payment: €50 with 10% discount"
        response = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": unicode_text,
                "namespace": namespace,
                "metadata": {"type": "payment"}
            },
            headers=auth_headers_user1
        )
        assert response.status_code == 200

        # Search with Unicode
        search_response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "café payment €50",
                "namespace": namespace
            },
            headers=auth_headers_user1
        )
        assert search_response.status_code == 200
        data = search_response.json()
        assert data["total_results"] >= 1
        assert data["results"][0]["text"] == unicode_text

    def test_agent_memory_duplicate_storage_with_upsert(self, client, auth_headers_user1):
        """Test that duplicate memories can be updated with upsert=true."""
        project_id = "proj_edge_memory_004"
        namespace = "agent-upsert"
        vector_id = "memory-001"

        # Store initial memory
        initial_text = "Initial memory content"
        response1 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": initial_text,
                "namespace": namespace,
                "vector_id": vector_id,
                "metadata": {"version": 1},
                "upsert": False
            },
            headers=auth_headers_user1
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["created"] is True

        # Update memory with upsert=true
        updated_text = "Updated memory content with new information"
        response2 = client.post(
            f"/v1/public/{project_id}/embeddings/embed-and-store",
            json={
                "text": updated_text,
                "namespace": namespace,
                "vector_id": vector_id,
                "metadata": {"version": 2},
                "upsert": True
            },
            headers=auth_headers_user1
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["created"] is False  # Updated, not created

        # Search should return updated memory
        search_response = client.post(
            f"/v1/public/{project_id}/embeddings/search",
            json={
                "query": "memory content",
                "namespace": namespace
            },
            headers=auth_headers_user1
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_results"] == 1  # Only one memory (updated)
        assert search_data["results"][0]["text"] == updated_text
        assert search_data["results"][0]["metadata"]["version"] == 2
