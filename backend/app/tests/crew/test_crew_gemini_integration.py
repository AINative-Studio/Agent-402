"""
Tests for Gemini LLM integration in crew workflow.

Validates the integration between X402Crew and Gemini service:
- use_llm flag behavior (True/False modes)
- Backward compatibility with simulation mode
- LLM-powered execution paths
- Error handling when Gemini is unavailable
- Fallback behavior from LLM to simulation

Test Style: BDD (describe/it pattern)
Coverage Target: >= 80%
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json


class TestX402CrewUseLLMFlag:
    """Test suite for use_llm flag behavior."""

    def test_crew_defaults_to_simulation_mode(self):
        """
        It should default to simulation mode (use_llm=False).
        This ensures backward compatibility with existing tests.
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(project_id="test_project")

        assert crew.use_llm is False

    def test_crew_accepts_use_llm_true(self):
        """
        It should accept use_llm=True for LLM-powered mode.
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(project_id="test_project", use_llm=True)

        assert crew.use_llm is True

    def test_crew_gemini_service_lazy_loaded(self):
        """
        It should not load Gemini service until needed.
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(project_id="test_project", use_llm=True)

        # Gemini service should not be loaded yet
        assert crew._gemini_service is None


class TestX402CrewSimulationMode:
    """Test suite for simulation mode (use_llm=False)."""

    @pytest.mark.asyncio
    async def test_analyst_task_uses_simulation_when_use_llm_false(self):
        """
        Given: use_llm=False
        When: Analyst task executes
        Then: Simulated response is returned
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_123"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(project_id="test_project", use_llm=False)
            result = await crew._execute_analyst_task("Test query")

            # Should have simulated data
            assert result["data_sources"] == ["CoinGecko", "Binance", "Kraken"]
            assert result["quality_score"] == 0.95
            assert "llm_model" not in result

    @pytest.mark.asyncio
    async def test_compliance_task_uses_simulation_when_use_llm_false(self):
        """
        Given: use_llm=False
        When: Compliance task executes
        Then: Simulated response is returned
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_456"
            })
            mock_memory.return_value = mock_memory_service

            mock_compliance.create_event = AsyncMock(return_value={
                "event_id": "evt_test_456"
            })

            crew = X402Crew(project_id="test_project", use_llm=False)
            analyst_output = {"memory_id": "mem_analyst_123"}

            result = await crew._execute_compliance_task(analyst_output)

            # Should have simulated data
            assert result["aml_check"] == "PASS"
            assert result["risk_score"] == 0.15
            assert result["compliance_status"] == "PASS"
            assert "llm_model" not in result

    @pytest.mark.asyncio
    async def test_transaction_task_uses_simulation_when_use_llm_false(self):
        """
        Given: use_llm=False
        When: Transaction task executes
        Then: Direct execution without LLM guidance
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_789"
            })
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test"
            })

            crew = X402Crew(project_id="test_project", use_llm=False)

            compliance_output = {
                "compliance_status": "PASS",
                "risk_score": 0.15,
                "memory_id": "mem_compliance_123",
                "event_id": "evt_123"
            }
            analyst_output = {
                "market_data": {},
                "memory_id": "mem_analyst_123"
            }

            result = await crew._execute_transaction_task(
                compliance_output, analyst_output, {"query": "Test"}
            )

            assert result["status"] == "SUCCESS"
            assert "llm_action" not in result


class TestX402CrewLLMMode:
    """Test suite for LLM mode (use_llm=True)."""

    @pytest.fixture
    def mock_gemini_service(self):
        """Create a mocked Gemini service."""
        mock = MagicMock()
        mock.generate_structured = AsyncMock(return_value={
            "parsed": {
                "data_sources": ["LLM Source 1", "LLM Source 2"],
                "market_data": {"BTC_USD": 50000.0},
                "quality_score": 0.92,
                "recommendation": "LLM recommendation"
            },
            "model": "gemini-pro",
            "latency_ms": 150.5
        })
        return mock

    @pytest.mark.asyncio
    async def test_analyst_task_uses_llm_when_use_llm_true(self, mock_gemini_service):
        """
        Given: use_llm=True and Gemini service available
        When: Analyst task executes
        Then: LLM-generated response is returned
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_123"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(project_id="test_project", use_llm=True)
            crew._gemini_service = mock_gemini_service

            result = await crew._execute_analyst_task("Analyze BTC market")

            # Should have LLM data
            assert result["data_sources"] == ["LLM Source 1", "LLM Source 2"]
            assert result["llm_model"] == "gemini-pro"
            assert result["llm_latency_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_compliance_task_uses_llm_when_use_llm_true(self, mock_gemini_service):
        """
        Given: use_llm=True and Gemini service available
        When: Compliance task executes
        Then: LLM-generated response is returned
        """
        from app.crew.crew import X402Crew

        # Update mock for compliance response
        mock_gemini_service.generate_structured = AsyncMock(return_value={
            "parsed": {
                "aml_check": "PASS",
                "kyc_check": "PASS",
                "sanctions_screening": "CLEAR",
                "risk_score": 0.12,
                "risk_level": "low",
                "compliance_status": "PASS",
                "justification": "All checks passed"
            },
            "model": "gemini-pro",
            "latency_ms": 200.0
        })

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_456"
            })
            mock_memory.return_value = mock_memory_service

            mock_compliance.create_event = AsyncMock(return_value={
                "event_id": "evt_test"
            })

            crew = X402Crew(project_id="test_project", use_llm=True)
            crew._gemini_service = mock_gemini_service

            analyst_output = {"memory_id": "mem_analyst_123"}
            result = await crew._execute_compliance_task(analyst_output)

            assert result["risk_score"] == 0.12
            assert result["justification"] == "All checks passed"
            assert result["llm_model"] == "gemini-pro"

    @pytest.mark.asyncio
    async def test_transaction_task_gets_llm_guidance(self, mock_gemini_service):
        """
        Given: use_llm=True and Gemini service available
        When: Transaction task executes
        Then: LLM guidance is included in output
        """
        from app.crew.crew import X402Crew

        # Update mock for transaction guidance
        mock_gemini_service.generate_structured = AsyncMock(return_value={
            "parsed": {
                "action": "execute",
                "transaction_details": {"priority": "high"},
                "signature_verified": True,
                "notes": "Proceeding with transaction"
            },
            "model": "gemini-1.5-flash",
            "latency_ms": 50.0
        })

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_789"
            })
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test"
            })

            crew = X402Crew(project_id="test_project", use_llm=True)
            crew._gemini_service = mock_gemini_service

            compliance_output = {
                "compliance_status": "PASS",
                "risk_score": 0.1,
                "memory_id": "mem_compliance",
                "event_id": "evt_123"
            }
            analyst_output = {
                "market_data": {},
                "memory_id": "mem_analyst"
            }

            result = await crew._execute_transaction_task(
                compliance_output, analyst_output, {"query": "Test"}
            )

            assert result["llm_action"] == "execute"
            assert result["llm_model"] == "gemini-1.5-flash"


class TestX402CrewGeminiFallback:
    """Test suite for Gemini fallback behavior."""

    @pytest.mark.asyncio
    async def test_falls_back_to_simulation_when_gemini_unavailable(self):
        """
        Given: use_llm=True but Gemini service fails to initialize
        When: Analyst task executes
        Then: Falls back to simulation mode
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.services.gemini_service.get_gemini_service') as mock_get_gemini:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_123"
            })
            mock_memory.return_value = mock_memory_service

            # Gemini service raises exception
            mock_get_gemini.side_effect = Exception("Gemini unavailable")

            crew = X402Crew(project_id="test_project", use_llm=True)
            result = await crew._execute_analyst_task("Test query")

            # Should fall back to simulation
            assert result["data_sources"] == ["CoinGecko", "Binance", "Kraken"]
            assert "llm_model" not in result

    @pytest.mark.asyncio
    async def test_falls_back_when_llm_generate_fails(self):
        """
        Given: use_llm=True and Gemini is available
        When: LLM generation fails
        Then: Falls back to simulation mode
        """
        from app.crew.crew import X402Crew

        mock_gemini = MagicMock()
        mock_gemini.generate_structured = AsyncMock(
            side_effect=Exception("LLM generation failed")
        )

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test_123"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(project_id="test_project", use_llm=True)
            crew._gemini_service = mock_gemini

            result = await crew._execute_analyst_task("Test query")

            # Should fall back to simulation
            assert result["data_sources"] == ["CoinGecko", "Binance", "Kraken"]
            assert "llm_model" not in result


class TestX402CrewBackwardCompatibility:
    """Test suite for backward compatibility."""

    @pytest.mark.asyncio
    async def test_existing_workflow_still_works(self):
        """
        Given: Existing code using X402Crew without use_llm parameter
        When: Workflow executes
        Then: Works exactly as before (simulation mode)
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(side_effect=[
                {"memory_id": "mem_analyst"},
                {"memory_id": "mem_compliance"},
                {"memory_id": "mem_transaction"}
            ])
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_compat_test"
            })

            mock_compliance.create_event = AsyncMock(return_value={
                "event_id": "evt_compat_test"
            })

            # Create crew WITHOUT specifying use_llm
            crew = X402Crew(
                project_id="test_project",
                run_id="test_run"
            )

            result = await crew.kickoff({"query": "Backward compat test"})

            assert result["status"] == "completed"
            assert result["request_id"] == "x402_req_compat_test"
            # Verify simulation outputs
            assert result["analyst_output"]["data_sources"] == ["CoinGecko", "Binance", "Kraken"]
            assert result["compliance_output"]["compliance_status"] == "PASS"

    def test_crew_initialization_unchanged(self):
        """
        Given: X402Crew initialized without use_llm
        When: Checking attributes
        Then: All existing attributes are present and correct
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        assert crew.project_id == "test_project"
        assert crew.run_id == "test_run"
        assert len(crew.agents) == 3
        assert "analyst" in crew.agent_ids
        assert "compliance" in crew.agent_ids
        assert "transaction" in crew.agent_ids


class TestX402CrewToolConversion:
    """Test suite for agent tool conversion to Gemini format."""

    def test_convert_agent_tools_to_gemini_format(self):
        """
        Given: An agent with tools defined
        When: Converting tools to Gemini format
        Then: Tools are properly converted
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(project_id="test_project")

        # Get analyst agent (has market data tools)
        analyst_agent = crew.agents[0]

        gemini_tools = crew._convert_agent_tools_to_gemini_format(analyst_agent)

        # Should have converted tools
        assert isinstance(gemini_tools, list)
        assert len(gemini_tools) > 0

        # Each tool should have name, description, parameters
        for tool in gemini_tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool


class TestX402CrewResponseSchemas:
    """Test suite for response schemas."""

    def test_analyst_response_schema_structure(self):
        """
        Given: ANALYST_RESPONSE_SCHEMA constant
        When: Checking structure
        Then: Has required fields for analyst output
        """
        from app.crew.crew import ANALYST_RESPONSE_SCHEMA

        assert ANALYST_RESPONSE_SCHEMA["type"] == "object"
        assert "data_sources" in ANALYST_RESPONSE_SCHEMA["properties"]
        assert "market_data" in ANALYST_RESPONSE_SCHEMA["properties"]
        assert "quality_score" in ANALYST_RESPONSE_SCHEMA["properties"]
        assert "recommendation" in ANALYST_RESPONSE_SCHEMA["properties"]

    def test_compliance_response_schema_structure(self):
        """
        Given: COMPLIANCE_RESPONSE_SCHEMA constant
        When: Checking structure
        Then: Has required fields for compliance output
        """
        from app.crew.crew import COMPLIANCE_RESPONSE_SCHEMA

        assert COMPLIANCE_RESPONSE_SCHEMA["type"] == "object"
        assert "aml_check" in COMPLIANCE_RESPONSE_SCHEMA["properties"]
        assert "kyc_check" in COMPLIANCE_RESPONSE_SCHEMA["properties"]
        assert "risk_score" in COMPLIANCE_RESPONSE_SCHEMA["properties"]
        assert "compliance_status" in COMPLIANCE_RESPONSE_SCHEMA["properties"]

    def test_transaction_response_schema_structure(self):
        """
        Given: TRANSACTION_RESPONSE_SCHEMA constant
        When: Checking structure
        Then: Has required fields for transaction output
        """
        from app.crew.crew import TRANSACTION_RESPONSE_SCHEMA

        assert TRANSACTION_RESPONSE_SCHEMA["type"] == "object"
        assert "action" in TRANSACTION_RESPONSE_SCHEMA["properties"]
        # Action should have enum
        action_prop = TRANSACTION_RESPONSE_SCHEMA["properties"]["action"]
        assert "enum" in action_prop
        assert "execute" in action_prop["enum"]
        assert "abort" in action_prop["enum"]


class TestX402CrewMetadata:
    """Test suite for metadata handling with use_llm flag."""

    @pytest.mark.asyncio
    async def test_metadata_includes_use_llm_flag(self):
        """
        Given: Crew with use_llm=True
        When: Storing memory
        Then: Metadata includes use_llm flag
        """
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(project_id="test_project", use_llm=True)
            crew._gemini_service = None  # Will fall back to simulation

            await crew._execute_analyst_task("Test")

            # Check that metadata includes use_llm
            call_args = mock_memory_service.store_memory.call_args
            metadata = call_args.kwargs.get("metadata", {})
            assert "use_llm" in metadata


class TestX402CrewComplianceFailure:
    """Test suite for compliance failure handling with LLM mode."""

    @pytest.mark.asyncio
    async def test_transaction_aborts_on_compliance_fail_llm_mode(self):
        """
        Given: use_llm=True and compliance fails
        When: Transaction task executes
        Then: Transaction is aborted
        """
        from app.crew.crew import X402Crew

        crew = X402Crew(project_id="test_project", use_llm=True)

        compliance_output = {
            "compliance_status": "FAIL",
            "risk_score": 0.85,
            "memory_id": "mem_compliance",
            "event_id": "evt_123"
        }
        analyst_output = {
            "market_data": {},
            "memory_id": "mem_analyst"
        }

        with pytest.raises(Exception) as exc_info:
            await crew._execute_transaction_task(
                compliance_output, analyst_output, {"query": "Test"}
            )

        assert "compliance" in str(exc_info.value).lower()


class TestX402CrewFullWorkflowLLM:
    """Integration test for full workflow with LLM mode."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_llm(self):
        """
        Given: use_llm=True with mocked Gemini service
        When: Full workflow executes
        Then: All outputs include LLM metadata
        """
        from app.crew.crew import X402Crew

        mock_gemini = MagicMock()

        # Different responses for each agent
        responses = [
            # Analyst response
            {
                "parsed": {
                    "data_sources": ["Source1"],
                    "market_data": {"price": 100},
                    "quality_score": 0.9,
                    "recommendation": "Go"
                },
                "model": "gemini-pro",
                "latency_ms": 100
            },
            # Compliance response
            {
                "parsed": {
                    "aml_check": "PASS",
                    "kyc_check": "PASS",
                    "sanctions_screening": "CLEAR",
                    "risk_score": 0.1,
                    "risk_level": "low",
                    "compliance_status": "PASS",
                    "justification": "All clear"
                },
                "model": "gemini-pro",
                "latency_ms": 150
            },
            # Transaction response
            {
                "parsed": {
                    "action": "execute",
                    "notes": "Executing"
                },
                "model": "gemini-1.5-flash",
                "latency_ms": 50
            }
        ]
        mock_gemini.generate_structured = AsyncMock(side_effect=responses)

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(side_effect=[
                {"memory_id": "mem_analyst"},
                {"memory_id": "mem_compliance"},
                {"memory_id": "mem_transaction"}
            ])
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_llm_test"
            })

            mock_compliance.create_event = AsyncMock(return_value={
                "event_id": "evt_llm_test"
            })

            crew = X402Crew(
                project_id="test_project",
                run_id="test_run_llm",
                use_llm=True
            )
            crew._gemini_service = mock_gemini

            result = await crew.kickoff({"query": "LLM full workflow test"})

            assert result["status"] == "completed"
            assert result["analyst_output"]["llm_model"] == "gemini-pro"
            assert result["compliance_output"]["llm_model"] == "gemini-pro"
            assert result["transaction_output"]["llm_action"] == "execute"
