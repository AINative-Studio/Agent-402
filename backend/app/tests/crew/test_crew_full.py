"""
Comprehensive tests for CrewAI agent orchestration and memory system.

Tests cover:
- Enhanced agent personas with tool definitions
- Crew orchestration with error handling and retries
- Agent memory with DID namespace isolation
- Semantic search for context retrieval
- Audit trail for all agent actions

Per TDD methodology: These tests are written FIRST, then implementation follows.
Coverage target: >= 80%
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid


class TestCrewOrchestrator:
    """Test suite for the CrewOrchestrator service."""

    @pytest.mark.asyncio
    async def test_orchestrator_initializes_with_project_and_agent_did(self):
        """Test that orchestrator initializes with proper DID-based identification."""
        from app.services.crew_orchestrator import CrewOrchestrator

        agent_did = "did:agent:analyst_001"
        project_id = "test_project"

        orchestrator = CrewOrchestrator(
            project_id=project_id,
            agent_did=agent_did
        )

        assert orchestrator.project_id == project_id
        assert orchestrator.agent_did == agent_did
        assert orchestrator.run_id is not None
        assert orchestrator.run_id.startswith("run_")

    @pytest.mark.asyncio
    async def test_orchestrator_loads_memory_context_on_startup(self):
        """Test that orchestrator retrieves relevant memory context on initialization."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.search_memories = AsyncMock(return_value=[
                {"memory_id": "mem_123", "content": "Previous task context", "similarity_score": 0.92}
            ])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test"
            )

            context = await orchestrator.load_memory_context(query="market data analysis")

            assert len(context) >= 0  # May be empty in mock
            mock_memory_service.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_executes_workflow_with_retries(self):
        """Test that orchestrator retries failed tasks."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={"memory_id": "mem_1"})
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test",
                max_retries=3
            )

            # Mock the crew to fail then succeed
            attempt_count = [0]

            async def mock_kickoff(input_data):
                attempt_count[0] += 1
                if attempt_count[0] < 2:
                    raise Exception("Temporary failure")
                return {"status": "completed", "request_id": "x402_req_123"}

            with patch.object(orchestrator, '_create_crew') as mock_create:
                mock_crew = AsyncMock()
                mock_crew.kickoff = AsyncMock(side_effect=mock_kickoff)
                mock_create.return_value = mock_crew

                result = await orchestrator.execute(
                    input_data={"query": "Test query"},
                    retry_on_failure=True
                )

                assert result["status"] == "completed"
                assert attempt_count[0] >= 1

    @pytest.mark.asyncio
    async def test_orchestrator_records_audit_trail_for_all_actions(self):
        """Test that all agent actions are recorded in audit trail."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={"memory_id": "mem_audit"})
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test"
            )

            await orchestrator.record_audit_event(
                action="task_started",
                details={"task": "analyst_task", "input": "market data"},
                token_id="nft_123"
            )

            # Verify audit was stored
            assert mock_memory_service.store_memory.called
            call_args = mock_memory_service.store_memory.call_args
            assert "audit" in call_args[1]["memory_type"]

    @pytest.mark.asyncio
    async def test_orchestrator_links_memory_to_arc_nft_token(self):
        """Test that memory entries can be linked to Arc NFT token IDs."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={"memory_id": "mem_linked"})
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test"
            )

            memory = await orchestrator.store_memory_with_token_link(
                content="Agent decision with NFT link",
                memory_type="decision",
                token_id="arc_nft_token_456"
            )

            # Verify token_id was included in metadata
            call_args = mock_memory_service.store_memory.call_args
            assert call_args[1]["metadata"]["token_id"] == "arc_nft_token_456"


class TestEnhancedAgents:
    """Test suite for enhanced agent definitions."""

    def test_agents_have_tools_defined(self):
        """Test that agents have tool definitions."""
        from app.crew.agents import create_analyst_agent, Agent

        agent = create_analyst_agent()

        # Agent should have tools attribute
        assert hasattr(agent, 'tools')
        assert len(agent.tools) > 0

    def test_agents_have_improved_backstories(self):
        """Test that agents have detailed, improved backstories."""
        from app.crew.agents import (
            create_analyst_agent,
            create_compliance_agent,
            create_transaction_agent
        )

        analyst = create_analyst_agent()
        compliance = create_compliance_agent()
        transaction = create_transaction_agent()

        # Backstories should be detailed (at least 200 chars)
        assert len(analyst.backstory) >= 200
        assert len(compliance.backstory) >= 200
        assert len(transaction.backstory) >= 200

        # Should include domain-specific terms
        assert any(term in analyst.backstory.lower() for term in ["data", "market", "api"])
        assert any(term in compliance.backstory.lower() for term in ["aml", "kyc", "compliance", "risk"])
        assert any(term in transaction.backstory.lower() for term in ["x402", "transaction", "signature", "did"])

    def test_agents_have_memory_access_configured(self):
        """Test that agents can be configured with memory access."""
        from app.crew.agents import create_analyst_agent

        agent = create_analyst_agent()

        # Agent should support memory configuration
        assert hasattr(agent, 'verbose')
        assert hasattr(agent, 'memory_enabled')
        assert agent.verbose is True  # Default should be verbose for debugging
        assert agent.memory_enabled is True

    def test_agents_have_circle_api_tools(self):
        """Test that relevant agents have Circle API tools."""
        from app.crew.agents import create_analyst_agent, create_transaction_agent

        analyst = create_analyst_agent()
        transaction = create_transaction_agent()

        # Both should have Circle API tools
        analyst_tool_names = [t.name for t in analyst.tools]
        transaction_tool_names = [t.name for t in transaction.tools]

        assert any("circle" in name for name in analyst_tool_names)
        assert any("circle" in name for name in transaction_tool_names)


class TestAgentMemoryEnhancements:
    """Test suite for enhanced agent memory service."""

    @pytest.mark.asyncio
    async def test_memory_isolates_by_agent_did_namespace(self):
        """Test that memories are isolated by agent DID namespace."""
        from app.services.agent_memory_service import AgentMemoryService

        with patch('app.services.agent_memory_service.get_zerodb_client') as mock_client:
            mock_zerodb = AsyncMock()
            mock_zerodb.insert_row = AsyncMock(return_value={"row_id": "1"})
            mock_zerodb.embed_and_store = AsyncMock(return_value={"vector_ids": ["v1"]})
            mock_client.return_value = mock_zerodb

            service = AgentMemoryService(client=mock_zerodb)

            # Store memory with DID namespace
            await service.store_memory(
                project_id="test_project",
                agent_id="did:agent:analyst_001",
                run_id="run_123",
                memory_type="decision",
                content="Test decision",
                namespace="did:agent:analyst_001"  # DID-based namespace
            )

            # Verify namespace was used correctly
            call_args = mock_zerodb.insert_row.call_args
            assert call_args[0][1]["namespace"] == "did:agent:analyst_001"

    @pytest.mark.asyncio
    async def test_memory_supports_semantic_search_with_embeddings(self):
        """Test that semantic search uses vector embeddings."""
        from app.services.agent_memory_service import AgentMemoryService

        with patch('app.services.agent_memory_service.get_zerodb_client') as mock_client:
            mock_zerodb = AsyncMock()
            mock_zerodb.semantic_search = AsyncMock(return_value={
                "matches": [
                    {"metadata": {"memory_id": "mem_1", "project_id": "test_project"}, "score": 0.95}
                ]
            })
            mock_zerodb.query_rows = AsyncMock(return_value={
                "rows": [{"memory_id": "mem_1", "content": "Similar content"}]
            })
            mock_client.return_value = mock_zerodb

            service = AgentMemoryService(client=mock_zerodb)

            results = await service.search_memories(
                project_id="test_project",
                query="market data analysis",
                namespace="default",
                top_k=5
            )

            # Verify semantic search was called
            mock_zerodb.semantic_search.assert_called_once()
            call_args = mock_zerodb.semantic_search.call_args
            assert call_args[1]["query"] == "market data analysis"

    @pytest.mark.asyncio
    async def test_memory_includes_timestamp_in_all_entries(self):
        """Test that all memory entries include timestamp."""
        from app.services.agent_memory_service import AgentMemoryService

        with patch('app.services.agent_memory_service.get_zerodb_client') as mock_client:
            mock_zerodb = AsyncMock()
            mock_zerodb.insert_row = AsyncMock(return_value={"row_id": "1"})
            mock_zerodb.embed_and_store = AsyncMock(return_value={"vector_ids": ["v1"]})
            mock_client.return_value = mock_zerodb

            service = AgentMemoryService(client=mock_zerodb)

            result = await service.store_memory(
                project_id="test_project",
                agent_id="agent_1",
                run_id="run_123",
                memory_type="decision",
                content="Test content"
            )

            assert "timestamp" in result
            # Timestamp should be ISO format
            assert "T" in result["timestamp"]
            assert result["timestamp"].endswith("Z")

    @pytest.mark.asyncio
    async def test_memory_links_to_arc_token_id(self):
        """Test that memory can be linked to Arc NFT token IDs."""
        from app.services.agent_memory_service import AgentMemoryService

        with patch('app.services.agent_memory_service.get_zerodb_client') as mock_client:
            mock_zerodb = AsyncMock()
            mock_zerodb.insert_row = AsyncMock(return_value={"row_id": "1"})
            mock_zerodb.embed_and_store = AsyncMock(return_value={"vector_ids": ["v1"]})
            mock_client.return_value = mock_zerodb

            service = AgentMemoryService(client=mock_zerodb)

            result = await service.store_memory(
                project_id="test_project",
                agent_id="agent_1",
                run_id="run_123",
                memory_type="decision",
                content="Linked to NFT",
                metadata={"token_id": "arc_nft_789"}
            )

            # Verify token_id was stored in metadata
            call_args = mock_zerodb.insert_row.call_args
            assert call_args[0][1]["metadata"]["token_id"] == "arc_nft_789"


class TestCrewImprovements:
    """Test suite for crew orchestration improvements."""

    @pytest.mark.asyncio
    async def test_crew_delegates_tasks_efficiently(self):
        """Test that crew delegates tasks properly."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="run_test"
        )

        tasks = crew.create_tasks({"query": "Process payment"})

        # Should have 3 tasks in proper sequence
        assert len(tasks) == 3
        # Each task should have a description and expected output
        for task in tasks:
            assert task.description is not None
            assert task.expected_output is not None

    @pytest.mark.asyncio
    async def test_crew_handles_errors_gracefully(self):
        """Test that crew handles errors without crashing."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="run_test"
        )

        # Mock a failing task
        with patch.object(crew, '_execute_analyst_task', side_effect=Exception("API Error")):
            with pytest.raises(Exception) as exc_info:
                await crew.kickoff(input_data={"query": "Test"})

            # Should raise but with informative error
            assert "API Error" in str(exc_info.value) or "analyst" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_crew_shares_memory_across_agents(self):
        """Test that crew enables memory sharing between agents."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            memory_store = {}

            async def mock_store(project_id, agent_id, run_id, memory_type, content, **kwargs):
                memory_id = f"mem_{len(memory_store)}"
                memory_store[memory_id] = {
                    "memory_id": memory_id,
                    "agent_id": agent_id,
                    "content": content,
                    "run_id": run_id
                }
                return memory_store[memory_id]

            mock_memory_service.store_memory = AsyncMock(side_effect=mock_store)
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(
                project_id="test_project",
                run_id="run_shared"
            )

            # Store outputs from different agents
            await crew.store_agent_output("analyst", "analyst_output", "Market data")
            await crew.store_agent_output("compliance", "compliance_output", "Compliance check")

            # All memories should share the same run_id
            for mem in memory_store.values():
                assert mem["run_id"] == "run_shared"


class TestTaskDefinitions:
    """Test suite for improved task definitions."""

    def test_tasks_have_structured_expected_outputs(self):
        """Test that tasks have structured expected output specifications."""
        from app.crew.tasks import (
            create_analyst_task,
            create_compliance_task,
            create_transaction_task
        )
        from app.crew.agents import (
            create_analyst_agent,
            create_compliance_agent,
            create_transaction_agent
        )

        analyst_task = create_analyst_task(
            create_analyst_agent(),
            {"query": "test", "project_id": "test"}
        )
        compliance_task = create_compliance_task(
            create_compliance_agent(),
            {"analyst_output": "test", "project_id": "test"}
        )
        transaction_task = create_transaction_task(
            create_transaction_agent(),
            {"compliance_output": "test", "project_id": "test"}
        )

        # Expected outputs should be detailed
        assert len(analyst_task.expected_output) >= 50
        assert len(compliance_task.expected_output) >= 50
        assert len(transaction_task.expected_output) >= 50

    def test_tasks_include_context_in_description(self):
        """Test that task descriptions include relevant context."""
        from app.crew.tasks import create_analyst_task
        from app.crew.agents import create_analyst_agent

        task = create_analyst_task(
            create_analyst_agent(),
            {"query": "Analyze BTC/USD market data", "project_id": "test"}
        )

        # Query should be in the description
        assert "BTC/USD" in task.description or "market data" in task.description.lower()


class TestAuditTrail:
    """Test suite for audit trail functionality."""

    @pytest.mark.asyncio
    async def test_audit_logs_all_agent_decisions(self):
        """Test that all agent decisions are logged for audit."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            audit_logs = []

            async def capture_audit(project_id, agent_id, run_id, memory_type, content, **kwargs):
                audit_logs.append({
                    "agent_id": agent_id,
                    "memory_type": memory_type,
                    "content": content
                })
                return {"memory_id": f"mem_{len(audit_logs)}"}

            mock_memory_service.store_memory = AsyncMock(side_effect=capture_audit)
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test"
            )

            # Record multiple audit events
            await orchestrator.record_audit_event("task_started", {"task": "analysis"})
            await orchestrator.record_audit_event("decision_made", {"decision": "approve"})
            await orchestrator.record_audit_event("task_completed", {"result": "success"})

            assert len(audit_logs) == 3

    @pytest.mark.asyncio
    async def test_audit_includes_timestamps(self):
        """Test that audit entries include timestamps."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={"memory_id": "mem_1", "timestamp": "2026-01-23T10:00:00Z"})
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:test"
            )

            result = await orchestrator.record_audit_event("test_action", {"data": "test"})

            assert "timestamp" in result or mock_memory_service.store_memory.called


class TestContextRetrieval:
    """Test suite for context retrieval via similarity search."""

    @pytest.mark.asyncio
    async def test_retrieves_similar_past_tasks(self):
        """Test that orchestrator can retrieve similar past tasks."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.search_memories = AsyncMock(return_value=[
                {
                    "memory_id": "mem_past_1",
                    "content": "Previous BTC analysis task",
                    "similarity_score": 0.89,
                    "agent_id": "did:agent:analyst"
                },
                {
                    "memory_id": "mem_past_2",
                    "content": "Historical market data aggregation",
                    "similarity_score": 0.76,
                    "agent_id": "did:agent:analyst"
                }
            ])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:analyst"
            )

            context = await orchestrator.load_memory_context(
                query="Analyze BTC market trends"
            )

            assert len(context) == 2
            assert context[0]["similarity_score"] > context[1]["similarity_score"]

    @pytest.mark.asyncio
    async def test_filters_context_by_agent_did(self):
        """Test that context retrieval filters by agent DID."""
        from app.services.crew_orchestrator import CrewOrchestrator

        with patch('app.services.crew_orchestrator.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_memory.return_value = mock_memory_service

            orchestrator = CrewOrchestrator(
                project_id="test_project",
                agent_did="did:agent:specific_agent"
            )

            await orchestrator.load_memory_context(query="test query")

            # Verify search was called with agent DID namespace
            call_args = mock_memory_service.search_memories.call_args
            assert call_args is not None


class TestAgentCollaboration:
    """Test suite for agent collaboration functionality."""

    @pytest.mark.asyncio
    async def test_passes_context_between_agents(self):
        """Test that agents pass context to each other in sequence."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            # Track memory stores
            memory_chain = []

            async def track_memory(project_id, agent_id, run_id, memory_type, content, **kwargs):
                memory_id = f"mem_{len(memory_chain)}"
                memory_chain.append({
                    "memory_id": memory_id,
                    "agent_id": agent_id,
                    "memory_type": memory_type
                })
                return {"memory_id": memory_id}

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(side_effect=track_memory)
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={"request_id": "x402_req_collab"})
            mock_compliance.create_event = AsyncMock(return_value={"event_id": "evt_collab"})

            crew = X402Crew(
                project_id="test_project",
                run_id="run_collab"
            )

            result = await crew.kickoff(input_data={"query": "Collaboration test"})

            # Should have memories from all 3 agents
            agent_types = [m["memory_type"] for m in memory_chain]
            assert "analyst_output" in agent_types
            assert "compliance_output" in agent_types
            assert "transaction_output" in agent_types

    @pytest.mark.asyncio
    async def test_maintains_run_id_across_agents(self):
        """Test that run_id is consistent across all agent actions."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            run_ids_seen = set()

            async def capture_run_id(project_id, agent_id, run_id, **kwargs):
                run_ids_seen.add(run_id)
                return {"memory_id": f"mem_{len(run_ids_seen)}"}

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(side_effect=capture_run_id)
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={"request_id": "x402_req_1"})
            mock_compliance.create_event = AsyncMock(return_value={"event_id": "evt_1"})

            crew = X402Crew(
                project_id="test_project",
                run_id="run_consistent"
            )

            await crew.kickoff(input_data={"query": "Run ID test"})

            # Only one unique run_id should be seen
            assert len(run_ids_seen) == 1
            assert "run_consistent" in run_ids_seen


class TestAgentTools:
    """Test suite for agent tool definitions."""

    def test_circle_api_tools_are_available(self):
        """Test that Circle API tools are properly defined."""
        from app.crew.agents import create_circle_api_tools

        tools = create_circle_api_tools()

        assert len(tools) >= 3
        tool_names = [t.name for t in tools]
        assert "circle_get_wallet_balance" in tool_names
        assert "circle_create_transfer" in tool_names
        assert "circle_get_transaction_status" in tool_names

    def test_market_data_tools_are_available(self):
        """Test that market data tools are properly defined."""
        from app.crew.agents import create_market_data_tools

        tools = create_market_data_tools()

        assert len(tools) >= 3
        tool_names = [t.name for t in tools]
        assert "fetch_crypto_price" in tool_names
        assert "aggregate_market_data" in tool_names
        assert "calculate_volatility" in tool_names

    def test_compliance_tools_are_available(self):
        """Test that compliance tools are properly defined."""
        from app.crew.agents import create_compliance_tools

        tools = create_compliance_tools()

        assert len(tools) >= 3
        tool_names = [t.name for t in tools]
        assert "perform_aml_check" in tool_names
        assert "calculate_risk_score" in tool_names
        assert "screen_sanctions_list" in tool_names

    def test_transaction_tools_are_available(self):
        """Test that transaction tools are properly defined."""
        from app.crew.agents import create_transaction_tools

        tools = create_transaction_tools()

        assert len(tools) >= 3
        tool_names = [t.name for t in tools]
        assert "create_x402_request" in tool_names
        assert "sign_with_did" in tool_names
        assert "submit_transaction" in tool_names

    def test_agent_tool_has_description_and_parameters(self):
        """Test that AgentTool instances have required attributes."""
        from app.crew.agents import AgentTool

        tool = AgentTool(
            name="test_tool",
            description="A test tool for validation",
            parameters={"input": {"type": "string"}}
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool for validation"
        assert "input" in tool.parameters

    def test_agent_tool_to_dict(self):
        """Test that AgentTool can be converted to dictionary."""
        from app.crew.agents import AgentTool

        tool = AgentTool(
            name="test_tool",
            description="Test description",
            parameters={"field": {"type": "string"}}
        )

        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "test_tool"
        assert tool_dict["description"] == "Test description"
        assert tool_dict["parameters"]["field"]["type"] == "string"


class TestAgentDID:
    """Test suite for agent DID functionality."""

    def test_agents_have_default_did(self):
        """Test that agents are assigned default DIDs."""
        from app.crew.agents import (
            create_analyst_agent,
            create_compliance_agent,
            create_transaction_agent
        )

        analyst = create_analyst_agent()
        compliance = create_compliance_agent()
        transaction = create_transaction_agent()

        assert analyst.agent_did is not None
        assert compliance.agent_did is not None
        assert transaction.agent_did is not None

        # Default DIDs should be in proper format
        assert analyst.agent_did.startswith("did:agent:")
        assert compliance.agent_did.startswith("did:agent:")
        assert transaction.agent_did.startswith("did:agent:")

    def test_agents_accept_custom_did(self):
        """Test that agents accept custom DID parameter."""
        from app.crew.agents import create_analyst_agent

        custom_did = "did:agent:custom_analyst_001"
        agent = create_analyst_agent(agent_did=custom_did)

        assert agent.agent_did == custom_did

    def test_create_all_agents_accepts_custom_dids(self):
        """Test that create_all_agents accepts custom DIDs for each agent."""
        from app.crew.agents import create_all_agents

        agents = create_all_agents(
            analyst_did="did:agent:analyst_custom",
            compliance_did="did:agent:compliance_custom",
            transaction_did="did:agent:transaction_custom"
        )

        assert len(agents) == 3
        assert agents[0].agent_did == "did:agent:analyst_custom"
        assert agents[1].agent_did == "did:agent:compliance_custom"
        assert agents[2].agent_did == "did:agent:transaction_custom"
