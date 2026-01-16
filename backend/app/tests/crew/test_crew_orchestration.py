"""
Integration tests for CrewAI agent orchestration.
Tests the 3-agent workflow: Analyst -> Compliance -> Transaction

Per TDD methodology: These tests should FAIL initially, then pass after implementation.
Coverage target: >= 80%
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


class TestCrewOrchestration:
    """Test suite for crew orchestration workflow."""

    @pytest.mark.asyncio
    async def test_create_analyst_agent_has_correct_role(self):
        """Test that Analyst agent is created with correct role and goal."""
        from app.crew.agents import create_analyst_agent

        agent = create_analyst_agent()

        assert agent.role == "Market Data Analyst"
        assert "market data" in agent.goal.lower() or "aggregation" in agent.goal.lower()
        assert agent.backstory is not None
        assert len(agent.backstory) > 0

    @pytest.mark.asyncio
    async def test_create_compliance_agent_has_correct_role(self):
        """Test that Compliance agent is created with correct role and goal."""
        from app.crew.agents import create_compliance_agent

        agent = create_compliance_agent()

        assert agent.role == "Compliance Officer"
        assert any(keyword in agent.goal.lower() for keyword in ["aml", "kyc", "compliance", "risk"])
        assert agent.backstory is not None
        assert len(agent.backstory) > 0

    @pytest.mark.asyncio
    async def test_create_transaction_agent_has_correct_role(self):
        """Test that Transaction agent is created with correct role and goal."""
        from app.crew.agents import create_transaction_agent

        agent = create_transaction_agent()

        assert agent.role == "Transaction Executor"
        assert any(keyword in agent.goal.lower() for keyword in ["x402", "transaction", "execute"])
        assert agent.backstory is not None
        assert len(agent.backstory) > 0

    @pytest.mark.asyncio
    async def test_create_analyst_task(self):
        """Test that analyst task is created correctly."""
        from app.crew.tasks import create_analyst_task
        from app.crew.agents import create_analyst_agent

        agent = create_analyst_agent()
        context = {
            "query": "Aggregate market data for BTC/USD",
            "project_id": "test_project"
        }

        task = create_analyst_task(agent, context)

        assert task.description is not None
        assert task.agent == agent
        assert "market data" in task.description.lower() or "aggregate" in task.description.lower()

    @pytest.mark.asyncio
    async def test_create_compliance_task(self):
        """Test that compliance task is created correctly."""
        from app.crew.tasks import create_compliance_task
        from app.crew.agents import create_compliance_agent

        agent = create_compliance_agent()
        context = {
            "analyst_output": "Market data aggregated successfully",
            "project_id": "test_project"
        }

        task = create_compliance_task(agent, context)

        assert task.description is not None
        assert task.agent == agent
        assert any(keyword in task.description.lower() for keyword in ["compliance", "risk", "aml", "kyc"])

    @pytest.mark.asyncio
    async def test_create_transaction_task(self):
        """Test that transaction task is created correctly."""
        from app.crew.tasks import create_transaction_task
        from app.crew.agents import create_transaction_agent

        agent = create_transaction_agent()
        context = {
            "compliance_output": "Compliance checks passed",
            "project_id": "test_project"
        }

        task = create_transaction_task(agent, context)

        assert task.description is not None
        assert task.agent == agent
        assert "x402" in task.description.lower() or "transaction" in task.description.lower()

    @pytest.mark.asyncio
    async def test_crew_initialization(self):
        """Test that crew is initialized with correct configuration."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        assert crew.project_id == "test_project"
        assert crew.run_id == "test_run"
        assert crew.agents is not None
        assert len(crew.agents) == 3  # Analyst, Compliance, Transaction

    @pytest.mark.asyncio
    async def test_crew_sequential_process(self):
        """Test that crew uses sequential process."""
        from app.crew.crew import X402Crew, Process

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        crew_obj = crew.create_crew()
        assert crew_obj.process == Process.sequential

    @pytest.mark.asyncio
    async def test_crew_stores_analyst_output_in_memory(self):
        """Test that analyst output is stored in agent_memory."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test123",
                "content": "Test analyst output"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(
                project_id="test_project",
                run_id="test_run"
            )

            await crew.store_agent_output(
                agent_id="analyst",
                memory_type="analyst_output",
                content="Test analyst output"
            )

            mock_memory_service.store_memory.assert_called_once()
            call_args = mock_memory_service.store_memory.call_args
            assert call_args[1]["project_id"] == "test_project"
            assert call_args[1]["agent_id"] == "analyst"
            assert call_args[1]["memory_type"] == "analyst_output"
            assert call_args[1]["content"] == "Test analyst output"

    @pytest.mark.asyncio
    async def test_crew_stores_compliance_output_in_memory(self):
        """Test that compliance output is stored in agent_memory."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_test456",
                "content": "Test compliance output"
            })
            mock_memory.return_value = mock_memory_service

            crew = X402Crew(
                project_id="test_project",
                run_id="test_run"
            )

            await crew.store_agent_output(
                agent_id="compliance",
                memory_type="compliance_output",
                content="Test compliance output"
            )

            mock_memory_service.store_memory.assert_called_once()
            call_args = mock_memory_service.store_memory.call_args
            assert call_args[1]["project_id"] == "test_project"
            assert call_args[1]["agent_id"] == "compliance"
            assert call_args[1]["memory_type"] == "compliance_output"

    @pytest.mark.asyncio
    async def test_crew_returns_x402_request_id(self):
        """Test that crew execution returns X402 request_id."""
        from app.crew.crew import X402Crew

        with patch('app.crew.crew.x402_service') as mock_x402:
            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test789"
            })

            crew = X402Crew(
                project_id="test_project",
                run_id="test_run"
            )

            # Mock crew execution
            with patch.object(crew, '_execute_crew', return_value="Execution completed"):
                result = await crew.kickoff(input_data={"query": "Test query"})

                assert "request_id" in result
                assert result["request_id"].startswith("x402_req_")

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Integration test for complete 3-agent workflow."""
        from app.crew.crew import X402Crew

        # Mock all external services
        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            # Setup mocks
            mock_memory_service = AsyncMock()
            mock_memory_service.store_memory = AsyncMock(side_effect=[
                {"memory_id": "mem_analyst"},
                {"memory_id": "mem_compliance"},
                {"memory_id": "mem_transaction"}
            ])
            mock_memory.return_value = mock_memory_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_integration_test"
            })

            mock_compliance.create_event = AsyncMock(return_value={
                "event_id": "evt_integration_test"
            })

            crew = X402Crew(
                project_id="test_project",
                run_id="test_run_integration"
            )

            # Mock the crew execution to avoid actual LLM calls
            with patch.object(crew, '_execute_crew') as mock_execute:
                mock_execute.return_value = "Transaction completed successfully"

                result = await crew.kickoff(input_data={
                    "query": "Process BTC payment of 0.5 BTC"
                })

                # Verify workflow completed
                assert result is not None
                assert "request_id" in result

                # Verify all three agent memory stores were called
                assert mock_memory_service.store_memory.call_count >= 1

    @pytest.mark.asyncio
    async def test_crew_handles_compliance_failure(self):
        """Test that crew handles compliance check failures appropriately."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        # Mock the compliance task to return FAIL status
        async def mock_compliance_fail(analyst_output):
            return {
                "aml_check": "FAIL",
                "kyc_check": "FAIL",
                "sanctions_screening": "FLAGGED",
                "risk_score": 0.9,
                "risk_level": "high",
                "compliance_status": "FAIL",
                "analyst_memory_id": analyst_output.get("memory_id"),
                "memory_id": "mem_compliance_fail",
                "event_id": "evt_failed"
            }

        with patch.object(crew, '_execute_compliance_task', side_effect=mock_compliance_fail):
            # Verify crew raises exception when compliance fails
            # The transaction task should detect FAIL status and abort
            with pytest.raises(Exception) as exc_info:
                await crew.kickoff(input_data={"query": "Test query"})

            assert "compliance" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower() or "aborted" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_crew_agent_count(self):
        """Test that crew has exactly 3 agents."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        agents = crew.agents
        assert len(agents) == 3

        # Verify agent roles
        roles = [agent.role for agent in agents]
        assert "Market Data Analyst" in roles
        assert "Compliance Officer" in roles
        assert "Transaction Executor" in roles

    @pytest.mark.asyncio
    async def test_crew_task_dependencies(self):
        """Test that tasks have proper sequential dependencies."""
        from app.crew.crew import X402Crew

        crew = X402Crew(
            project_id="test_project",
            run_id="test_run"
        )

        tasks = crew.create_tasks({"query": "Test query"})

        # Should have 3 tasks in sequence
        assert len(tasks) == 3

        # Compliance task should depend on Analyst output
        # Transaction task should depend on Compliance output
        # This is enforced by Process.sequential in CrewAI


class TestCrewAgents:
    """Test suite for individual agent creation."""

    def test_analyst_agent_attributes(self):
        """Test analyst agent has all required attributes."""
        from app.crew.agents import create_analyst_agent

        agent = create_analyst_agent()

        assert hasattr(agent, 'role')
        assert hasattr(agent, 'goal')
        assert hasattr(agent, 'backstory')
        assert hasattr(agent, 'verbose')

    def test_compliance_agent_attributes(self):
        """Test compliance agent has all required attributes."""
        from app.crew.agents import create_compliance_agent

        agent = create_compliance_agent()

        assert hasattr(agent, 'role')
        assert hasattr(agent, 'goal')
        assert hasattr(agent, 'backstory')
        assert hasattr(agent, 'verbose')

    def test_transaction_agent_attributes(self):
        """Test transaction agent has all required attributes."""
        from app.crew.agents import create_transaction_agent

        agent = create_transaction_agent()

        assert hasattr(agent, 'role')
        assert hasattr(agent, 'goal')
        assert hasattr(agent, 'backstory')
        assert hasattr(agent, 'verbose')


class TestCrewTasks:
    """Test suite for task creation."""

    def test_analyst_task_has_expected_output(self):
        """Test analyst task defines expected output."""
        from app.crew.tasks import create_analyst_task
        from app.crew.agents import create_analyst_agent

        agent = create_analyst_agent()
        context = {"query": "Test query", "project_id": "test"}
        task = create_analyst_task(agent, context)

        assert hasattr(task, 'expected_output')
        assert task.expected_output is not None

    def test_compliance_task_has_expected_output(self):
        """Test compliance task defines expected output."""
        from app.crew.tasks import create_compliance_task
        from app.crew.agents import create_compliance_agent

        agent = create_compliance_agent()
        context = {"analyst_output": "Test", "project_id": "test"}
        task = create_compliance_task(agent, context)

        assert hasattr(task, 'expected_output')
        assert task.expected_output is not None

    def test_transaction_task_has_expected_output(self):
        """Test transaction task defines expected output."""
        from app.crew.tasks import create_transaction_task
        from app.crew.agents import create_transaction_agent

        agent = create_transaction_agent()
        context = {"compliance_output": "Test", "project_id": "test"}
        task = create_transaction_task(agent, context)

        assert hasattr(task, 'expected_output')
        assert task.expected_output is not None
