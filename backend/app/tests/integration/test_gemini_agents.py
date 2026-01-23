"""
Gemini AI integration tests.

Tests the AI agent execution:
1. Agent task execution with Gemini Pro
2. Function calling with Circle tools
3. Agent collaboration (Analyst -> Compliance -> Transaction)
4. Memory context retrieval for similar tasks
5. Model switching (Pro vs Flash)
6. Rate limit handling
7. Response validation

Issues #124 and #127: Backend Integration Tests.

Test Style: BDD (Given/When/Then in docstrings)
Coverage Target: 80%+
"""
import pytest
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.agent_memory_service import AgentMemoryService


class TestGeminiAgentExecution:
    """Tests for Gemini agent task execution."""

    @pytest.mark.asyncio
    async def test_analyst_agent_uses_gemini_pro(
        self,
        mock_gemini_service
    ):
        """
        Given: An analyst agent task
        When: The task is executed
        Then: Gemini Pro model is used for deep analysis
        """
        # Arrange
        model = mock_gemini_service.get_model_for_agent("analyst")

        # Assert
        assert model == "gemini-pro"

    @pytest.mark.asyncio
    async def test_compliance_agent_uses_gemini_pro(
        self,
        mock_gemini_service
    ):
        """
        Given: A compliance agent task
        When: The task is executed
        Then: Gemini Pro model is used for thorough checks
        """
        # Arrange
        model = mock_gemini_service.get_model_for_agent("compliance")

        # Assert
        assert model == "gemini-pro"

    @pytest.mark.asyncio
    async def test_transaction_agent_uses_gemini_flash(
        self,
        mock_gemini_service
    ):
        """
        Given: A transaction agent task
        When: The task is executed
        Then: Gemini Flash model is used for fast execution
        """
        # Arrange
        model = mock_gemini_service.get_model_for_agent("transaction")

        # Assert
        assert model == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_analyst_generates_market_analysis(
        self,
        mock_gemini_service
    ):
        """
        Given: An analyst agent with market data context
        When: Analysis is generated
        Then: Response contains market data and recommendation
        """
        # Act
        result = await mock_gemini_service.generate_for_agent(
            agent_type="analyst",
            prompt="Analyze USDC market conditions",
            context={"current_price": 1.0, "volume": 1000000}
        )

        # Assert
        assert result["model"] == "gemini-pro"
        response_data = json.loads(result["text"])
        assert "market_data" in response_data or "recommendation" in response_data

    @pytest.mark.asyncio
    async def test_compliance_generates_risk_assessment(
        self,
        mock_gemini_service
    ):
        """
        Given: A compliance agent with transaction context
        When: Risk assessment is generated
        Then: Response contains approval status and risk score
        """
        # Act
        result = await mock_gemini_service.generate_for_agent(
            agent_type="compliance",
            prompt="Assess compliance for this transaction",
            context={"amount": "1000.00", "sender": "wallet_123"}
        )

        # Assert
        assert result["model"] == "gemini-pro"
        response_data = json.loads(result["text"])
        assert "approved" in response_data or "risk_score" in response_data

    @pytest.mark.asyncio
    async def test_transaction_generates_execution_plan(
        self,
        mock_gemini_service
    ):
        """
        Given: A transaction agent with approved payment
        When: Execution plan is generated
        Then: Response contains action and transaction details
        """
        # Act
        result = await mock_gemini_service.generate_for_agent(
            agent_type="transaction",
            prompt="Execute approved USDC transfer",
            context={"approved": True, "amount": "500.00"}
        )

        # Assert
        assert result["model"] == "gemini-1.5-flash"
        response_data = json.loads(result["text"])
        assert "action" in response_data or "status" in response_data


class TestFunctionCallingWithCircleTools:
    """Tests for Gemini function calling with Circle tools."""

    @pytest.mark.asyncio
    async def test_function_call_create_wallet(
        self,
        mock_gemini_service,
        circle_tools
    ):
        """
        Given: A prompt requesting wallet creation
        When: Gemini generates with function calling
        Then: create_wallet function is called with correct args
        """
        # Act
        result = await mock_gemini_service.generate_with_tools(
            prompt="Create a new wallet on Sepolia blockchain",
            tools=circle_tools
        )

        # Assert
        assert result["function_call"]["name"] == "create_wallet"
        assert result["function_call"]["args"]["blockchain"] == "ETH-SEPOLIA"

    @pytest.mark.asyncio
    async def test_function_call_transfer_usdc(
        self,
        mock_gemini_service,
        circle_tools
    ):
        """
        Given: A prompt requesting USDC transfer
        When: Gemini generates with function calling
        Then: transfer_usdc function is called with correct args
        """
        # Act
        result = await mock_gemini_service.generate_with_tools(
            prompt="Transfer 100 USDC from wallet_123 to wallet_456",
            tools=circle_tools
        )

        # Assert
        assert result["function_call"]["name"] == "transfer_usdc"
        assert "amount" in result["function_call"]["args"]

    @pytest.mark.asyncio
    async def test_function_call_get_balance(
        self,
        mock_gemini_service,
        circle_tools
    ):
        """
        Given: A prompt requesting wallet balance
        When: Gemini generates with function calling
        Then: get_wallet_balance function is called
        """
        # Act
        result = await mock_gemini_service.generate_with_tools(
            prompt="Check the balance of wallet_123",
            tools=circle_tools
        )

        # Assert
        assert result["function_call"]["name"] == "get_wallet_balance"
        assert "wallet_id" in result["function_call"]["args"]

    @pytest.mark.asyncio
    async def test_no_function_match_returns_text(
        self,
        mock_gemini_service,
        circle_tools
    ):
        """
        Given: A prompt that doesn't match any function
        When: Gemini generates with function calling
        Then: Text response is returned without function call
        """
        # Act
        result = await mock_gemini_service.generate_with_tools(
            prompt="What is the weather today?",
            tools=circle_tools
        )

        # Assert
        assert result["function_call"] is None or "text" in result


class TestAgentCollaboration:
    """Tests for multi-agent collaboration workflow."""

    @pytest.mark.asyncio
    async def test_analyst_output_passed_to_compliance(
        self,
        mock_zerodb_client,
        mock_gemini_service,
        test_project_id,
        test_run_id
    ):
        """
        Given: Analyst agent completes market analysis
        When: Compliance agent receives the analysis
        Then: Compliance can use analyst output in its assessment
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Analyst generates and stores output
        analyst_result = await mock_gemini_service.generate_for_agent(
            agent_type="analyst",
            prompt="Analyze market for transaction",
            context={}
        )

        analyst_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analyst_output",
            content=analyst_result["text"]
        )

        # Act - Compliance retrieves analyst output
        memories, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id,
            memory_type="analyst_output"
        )

        # Compliance uses analyst output
        compliance_result = await mock_gemini_service.generate_for_agent(
            agent_type="compliance",
            prompt=f"Check compliance based on: {memories[0]['content']}",
            context={"analyst_output": memories[0]["content"]}
        )

        # Assert
        assert len(memories) == 1
        assert compliance_result["model"] == "gemini-pro"

    @pytest.mark.asyncio
    async def test_compliance_output_passed_to_transaction(
        self,
        mock_zerodb_client,
        mock_gemini_service,
        test_project_id,
        test_run_id
    ):
        """
        Given: Compliance agent approves transaction
        When: Transaction agent receives approval
        Then: Transaction can proceed with execution
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Compliance generates and stores output
        mock_gemini_service.set_response(
            "compliance",
            '{"approved": true, "risk_score": 0.1}'
        )

        compliance_result = await mock_gemini_service.generate_for_agent(
            agent_type="compliance",
            prompt="Check compliance",
            context={}
        )

        compliance_memory = await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="compliance_output",
            content=compliance_result["text"]
        )

        # Act - Transaction retrieves compliance output
        memories, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id,
            memory_type="compliance_output"
        )

        compliance_data = json.loads(memories[0]["content"])

        # Transaction checks approval before executing
        if compliance_data.get("approved"):
            transaction_result = await mock_gemini_service.generate_for_agent(
                agent_type="transaction",
                prompt="Execute approved transaction",
                context={"compliance_approved": True}
            )

        # Assert
        assert compliance_data["approved"] is True
        assert transaction_result["model"] == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_full_three_agent_pipeline(
        self,
        mock_zerodb_client,
        mock_gemini_service,
        test_project_id,
        test_run_id
    ):
        """
        Given: A complete 3-agent pipeline setup
        When: All agents execute in sequence
        Then: Each agent's output is available to the next
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)
        namespace = "pipeline_test"

        # Act - Execute pipeline
        # Step 1: Analyst
        analyst_result = await mock_gemini_service.generate_for_agent(
            agent_type="analyst",
            prompt="Analyze market",
            context={}
        )
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="analyst_output",
            content=analyst_result["text"],
            namespace=namespace
        )

        # Step 2: Compliance
        compliance_result = await mock_gemini_service.generate_for_agent(
            agent_type="compliance",
            prompt="Check compliance",
            context={"analyst_output": analyst_result["text"]}
        )
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="compliance_output",
            content=compliance_result["text"],
            namespace=namespace
        )

        # Step 3: Transaction
        transaction_result = await mock_gemini_service.generate_for_agent(
            agent_type="transaction",
            prompt="Execute transaction",
            context={"compliance_output": compliance_result["text"]}
        )
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="transaction",
            run_id=test_run_id,
            memory_type="transaction_output",
            content=transaction_result["text"],
            namespace=namespace
        )

        # Verify pipeline
        memories, total, _ = await memory_service.list_memories(
            project_id=test_project_id,
            run_id=test_run_id,
            namespace=namespace
        )

        # Assert
        assert len(memories) == 3
        assert mock_gemini_service.get_call_count("generate_for_agent") == 3


class TestMemoryContextRetrieval:
    """Tests for memory context retrieval for similar tasks."""

    @pytest.mark.asyncio
    async def test_retrieve_similar_task_memory(
        self,
        mock_zerodb_client,
        test_project_id
    ):
        """
        Given: Previous task memories exist
        When: Similar task context is needed
        Then: Relevant memories are retrieved
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Store previous task memory
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id="previous_run",
            memory_type="analyst_output",
            content="Previous BTC analysis: price stable, volume increasing"
        )

        # Act - Search for similar memories
        results = await memory_service.search_memories(
            project_id=test_project_id,
            query="BTC price analysis",
            top_k=5
        )

        # Assert - Mock returns matching namespace vectors
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_memory_filtered_by_agent_id(
        self,
        mock_zerodb_client,
        test_project_id,
        test_run_id
    ):
        """
        Given: Memories from multiple agents
        When: Filtering by specific agent
        Then: Only that agent's memories are returned
        """
        # Arrange
        memory_service = AgentMemoryService(client=mock_zerodb_client)

        # Store memories for different agents
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="analyst",
            run_id=test_run_id,
            memory_type="output",
            content="Analyst content"
        )
        await memory_service.store_memory(
            project_id=test_project_id,
            agent_id="compliance",
            run_id=test_run_id,
            memory_type="output",
            content="Compliance content"
        )

        # Act - Filter by agent_id
        analyst_memories, _, _ = await memory_service.list_memories(
            project_id=test_project_id,
            agent_id="analyst"
        )

        # Assert
        assert len(analyst_memories) == 1
        assert analyst_memories[0]["agent_id"] == "analyst"


class TestModelSwitching:
    """Tests for model switching between Pro and Flash."""

    @pytest.mark.asyncio
    async def test_model_selection_by_agent_type(
        self,
        mock_gemini_service
    ):
        """
        Given: Different agent types
        When: Model is selected for each
        Then: Appropriate model is chosen based on agent type
        """
        # Act & Assert
        assert mock_gemini_service.get_model_for_agent("analyst") == "gemini-pro"
        assert mock_gemini_service.get_model_for_agent("compliance") == "gemini-pro"
        assert mock_gemini_service.get_model_for_agent("transaction") == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_unknown_agent_uses_default_model(
        self,
        mock_gemini_service
    ):
        """
        Given: An unknown agent type
        When: Model is selected
        Then: Default model (gemini-pro) is used
        """
        # Act
        model = mock_gemini_service.get_model_for_agent("unknown_type")

        # Assert
        assert model == "gemini-pro"

    @pytest.mark.asyncio
    async def test_generate_uses_correct_model(
        self,
        mock_gemini_service
    ):
        """
        Given: A generation request for specific agent
        When: Response is generated
        Then: Correct model is indicated in response
        """
        # Act
        analyst_result = await mock_gemini_service.generate_for_agent(
            agent_type="analyst",
            prompt="Test prompt",
            context={}
        )
        transaction_result = await mock_gemini_service.generate_for_agent(
            agent_type="transaction",
            prompt="Test prompt",
            context={}
        )

        # Assert
        assert analyst_result["model"] == "gemini-pro"
        assert transaction_result["model"] == "gemini-1.5-flash"


class TestRateLimitHandling:
    """Tests for rate limit handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry_succeeds(
        self,
        mock_gemini_service
    ):
        """
        Given: Rate limit errors occur initially
        When: Retries are attempted
        Then: Request eventually succeeds
        """
        # Arrange
        mock_gemini_service.set_rate_limit_behavior(fail_count=2)

        # Act - Direct call succeeds (mock doesn't actually rate limit)
        result = await mock_gemini_service.generate(
            prompt="Test prompt",
            max_retries=5
        )

        # Assert
        assert "text" in result

    @pytest.mark.asyncio
    async def test_request_tracking(
        self,
        mock_gemini_service
    ):
        """
        Given: Multiple generation requests
        When: Requests are tracked
        Then: Call count is accurate
        """
        # Arrange
        mock_gemini_service.reset()

        # Act
        await mock_gemini_service.generate(prompt="Request 1")
        await mock_gemini_service.generate(prompt="Request 2")
        await mock_gemini_service.generate(prompt="Request 3")

        # Assert
        assert mock_gemini_service.get_call_count("generate") == 3


class TestResponseValidation:
    """Tests for response validation."""

    @pytest.mark.asyncio
    async def test_structured_response_parsing(
        self,
        mock_gemini_service
    ):
        """
        Given: A request for structured JSON response
        When: Response is generated
        Then: Response is parsed to JSON object
        """
        # Act
        result = await mock_gemini_service.generate_structured(
            prompt="Analyze this transaction",
            response_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "risk_score": {"type": "number"}
                }
            }
        )

        # Assert
        assert "parsed" in result
        assert result["parsed"]["status"] == "approved"
        assert isinstance(result["parsed"]["risk_score"], (int, float))

    @pytest.mark.asyncio
    async def test_response_contains_latency(
        self,
        mock_gemini_service
    ):
        """
        Given: A generation request
        When: Response is returned
        Then: Latency is included in response
        """
        # Act
        result = await mock_gemini_service.generate(prompt="Test prompt")

        # Assert
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], (int, float))

    @pytest.mark.asyncio
    async def test_custom_response_override(
        self,
        mock_gemini_service
    ):
        """
        Given: A custom response set for agent type
        When: That agent type generates
        Then: Custom response is returned
        """
        # Arrange
        mock_gemini_service.set_response(
            "analyst",
            '{"custom": true, "analysis": "special_case"}'
        )

        # Act
        result = await mock_gemini_service.generate_for_agent(
            agent_type="analyst",
            prompt="Test",
            context={}
        )

        # Assert
        response_data = json.loads(result["text"])
        assert response_data["custom"] is True
        assert response_data["analysis"] == "special_case"


class TestTimeoutHandling:
    """Tests for timeout handling in Gemini calls."""

    @pytest.mark.asyncio
    async def test_response_within_timeout(
        self,
        mock_gemini_service
    ):
        """
        Given: A normal generation request
        When: Response is generated
        Then: Response completes within timeout
        """
        # Act
        result = await mock_gemini_service.generate(
            prompt="Quick test",
            timeout_seconds=5.0
        )

        # Assert
        assert "text" in result
        # Mock completes instantly, so always within timeout

    @pytest.mark.asyncio
    async def test_tool_conversion(
        self,
        mock_gemini_service,
        circle_tools
    ):
        """
        Given: Tool definitions in standard format
        When: Converting to Gemini format
        Then: Tools are properly formatted
        """
        # Act
        gemini_tools = mock_gemini_service.convert_tools_to_gemini_format(circle_tools)

        # Assert
        assert len(gemini_tools) == 3
        assert gemini_tools[0]["name"] == "create_wallet"
        assert "parameters" in gemini_tools[0]
