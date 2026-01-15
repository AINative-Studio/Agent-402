"""
Enhanced test coverage for crew orchestration.
Tests all execution paths to achieve >= 80% coverage.
"""
import sys
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, '.')

from app.crew.agents import create_analyst_agent, create_compliance_agent, create_transaction_agent
from app.crew.tasks import create_analyst_task, create_compliance_task, create_transaction_task
from app.crew.crew import X402Crew, Process, Crew


class TestCrewCoverage:
    """Comprehensive test suite for crew orchestration."""

    def test_analyst_agent_creation(self):
        """Test analyst agent creation."""
        agent = create_analyst_agent()
        assert agent.role == "Market Data Analyst"
        assert "market data" in agent.goal.lower()
        assert len(agent.backstory) > 100
        assert agent.verbose is True
        assert agent.allow_delegation is False

    def test_compliance_agent_creation(self):
        """Test compliance agent creation."""
        agent = create_compliance_agent()
        assert agent.role == "Compliance Officer"
        assert any(kw in agent.goal.lower() for kw in ["aml", "kyc", "compliance"])
        assert len(agent.backstory) > 100

    def test_transaction_agent_creation(self):
        """Test transaction agent creation."""
        agent = create_transaction_agent()
        assert agent.role == "Transaction Executor"
        assert "x402" in agent.goal.lower()
        assert len(agent.backstory) > 100

    def test_analyst_task_with_context(self):
        """Test analyst task with full context."""
        agent = create_analyst_agent()
        context = {
            "query": "Get BTC/USD price from multiple exchanges",
            "project_id": "proj_123",
            "run_id": "run_456"
        }
        task = create_analyst_task(agent, context)

        assert task.agent == agent
        assert "BTC/USD" in task.description or "multiple exchanges" in task.description.lower()
        assert task.expected_output is not None
        assert task.context == context

    def test_compliance_task_with_context(self):
        """Test compliance task with full context."""
        agent = create_compliance_agent()
        context = {
            "analyst_output": "Market data verified",
            "project_id": "proj_123",
            "run_id": "run_456"
        }
        task = create_compliance_task(agent, context)

        assert task.agent == agent
        assert "compliance" in task.description.lower()
        assert task.expected_output is not None

    def test_transaction_task_with_context(self):
        """Test transaction task with full context."""
        agent = create_transaction_agent()
        context = {
            "compliance_output": "All checks passed",
            "project_id": "proj_123",
            "run_id": "run_456"
        }
        task = create_transaction_task(agent, context)

        assert task.agent == agent
        assert "x402" in task.description.lower()
        assert task.expected_output is not None

    def test_crew_initialization_with_generated_run_id(self):
        """Test crew initialization without run_id."""
        crew = X402Crew(project_id="test_project")

        assert crew.project_id == "test_project"
        assert crew.run_id is not None
        assert crew.run_id.startswith("run_")
        assert len(crew.agents) == 3

    def test_crew_initialization_with_provided_run_id(self):
        """Test crew initialization with run_id."""
        crew = X402Crew(project_id="test_project", run_id="custom_run_123")

        assert crew.project_id == "test_project"
        assert crew.run_id == "custom_run_123"

    def test_crew_agent_ids(self):
        """Test crew agent IDs are set correctly."""
        crew = X402Crew(project_id="test_project")

        assert "analyst" in crew.agent_ids
        assert "compliance" in crew.agent_ids
        assert "transaction" in crew.agent_ids
        assert crew.agent_ids["analyst"] == "agent_analyst"

    def test_crew_object_creation(self):
        """Test Crew object creation."""
        analyst = create_analyst_agent()
        task = create_analyst_task(analyst, {"query": "test", "project_id": "test"})

        crew = Crew(
            agents=[analyst],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )

        assert crew.agents == [analyst]
        assert crew.tasks == [task]
        assert crew.process == Process.sequential
        assert crew.verbose is True

    def test_crew_kickoff_sequential(self):
        """Test crew kickoff with sequential process."""
        analyst = create_analyst_agent()
        task = create_analyst_task(analyst, {"query": "test", "project_id": "test"})

        crew = Crew(
            agents=[analyst],
            tasks=[task],
            process=Process.sequential
        )

        output = crew.kickoff()
        assert output is not None
        assert "Market Data Analyst" in output

    def test_crew_kickoff_hierarchical_not_supported(self):
        """Test that hierarchical process raises error."""
        analyst = create_analyst_agent()
        task = create_analyst_task(analyst, {"query": "test", "project_id": "test"})

        crew = Crew(
            agents=[analyst],
            tasks=[task],
            process=Process.hierarchical
        )

        try:
            crew.kickoff()
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

    def test_x402crew_create_tasks(self):
        """Test X402Crew task creation."""
        crew = X402Crew(project_id="test_proj")
        input_data = {"query": "Test market data query"}

        tasks = crew.create_tasks(input_data)

        assert len(tasks) == 3
        assert tasks[0].agent.role == "Market Data Analyst"
        assert tasks[1].agent.role == "Compliance Officer"
        assert tasks[2].agent.role == "Transaction Executor"

    def test_x402crew_create_crew_object(self):
        """Test X402Crew creates proper Crew object."""
        crew_mgr = X402Crew(project_id="test_proj")
        crew_obj = crew_mgr.create_crew()

        assert isinstance(crew_obj, Crew)
        assert len(crew_obj.agents) == 3
        assert len(crew_obj.tasks) == 3
        assert crew_obj.process == Process.sequential

    @pytest.mark.asyncio
    async def test_store_agent_output_full(self):
        """Test storing agent output with full parameters."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_service = AsyncMock()
            mock_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_123",
                "content": "Test content",
                "timestamp": "2026-01-14T00:00:00Z"
            })
            mock_memory.return_value = mock_service

            result = await crew.store_agent_output(
                agent_id="agent_analyst",
                memory_type="analyst_output",
                content="Market data aggregated successfully",
                metadata={"source": "test"}
            )

            assert result["memory_id"] == "mem_123"
            mock_service.store_memory.assert_called_once()

            call_kwargs = mock_service.store_memory.call_args[1]
            assert call_kwargs["project_id"] == "test_project"
            assert call_kwargs["agent_id"] == "agent_analyst"
            assert call_kwargs["run_id"] == "test_run"
            assert call_kwargs["memory_type"] == "analyst_output"
            assert call_kwargs["namespace"] == "x402_workflow"
            assert call_kwargs["metadata"] == {"source": "test"}

    @pytest.mark.asyncio
    async def test_execute_analyst_task_full(self):
        """Test analyst task execution."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
            mock_service = AsyncMock()
            mock_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_analyst_123"
            })
            mock_memory.return_value = mock_service

            result = await crew._execute_analyst_task("Get BTC price")

            assert "query" in result
            assert result["query"] == "Get BTC price"
            assert "data_sources" in result
            assert "market_data" in result
            assert "quality_score" in result
            assert "recommendation" in result
            assert "memory_id" in result
            assert result["memory_id"] == "mem_analyst_123"

    @pytest.mark.asyncio
    async def test_execute_compliance_task_pass(self):
        """Test compliance task execution with PASS."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        analyst_output = {
            "query": "test",
            "memory_id": "mem_analyst_123"
        }

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            mock_service = AsyncMock()
            mock_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_compliance_456"
            })
            mock_memory.return_value = mock_service

            mock_compliance.create_event = AsyncMock(return_value=Mock(
                event_id="evt_789"
            ))

            result = await crew._execute_compliance_task(analyst_output)

            assert result["compliance_status"] == "PASS"
            assert result["risk_score"] < 0.5
            assert result["aml_check"] == "PASS"
            assert result["kyc_check"] == "PASS"
            assert result["event_id"] == "evt_789"
            assert result["memory_id"] == "mem_compliance_456"

    @pytest.mark.asyncio
    async def test_execute_transaction_task_success(self):
        """Test transaction task execution with success."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        analyst_output = {"memory_id": "mem_analyst", "market_data": {"BTC_USD": 45000}}
        compliance_output = {
            "compliance_status": "PASS",
            "memory_id": "mem_compliance",
            "event_id": "evt_123",
            "risk_score": 0.1
        }
        input_data = {"query": "Test query"}

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402:

            mock_service = AsyncMock()
            mock_service.store_memory = AsyncMock(return_value={
                "memory_id": "mem_transaction_789"
            })
            mock_memory.return_value = mock_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_abc123"
            })

            result = await crew._execute_transaction_task(
                compliance_output, analyst_output, input_data
            )

            assert result["status"] == "SUCCESS"
            assert result["request_id"] == "x402_req_abc123"
            assert result["memory_id"] == "mem_transaction_789"

    @pytest.mark.asyncio
    async def test_execute_transaction_task_compliance_fail(self):
        """Test transaction task aborts when compliance fails."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        analyst_output = {"memory_id": "mem_analyst"}
        compliance_output = {
            "compliance_status": "FAIL",
            "risk_score": 0.9
        }
        input_data = {"query": "Test query"}

        try:
            await crew._execute_transaction_task(
                compliance_output, analyst_output, input_data
            )
            assert False, "Should have raised exception"
        except Exception as e:
            assert "compliance" in str(e).lower() or "failed" in str(e).lower()

    @pytest.mark.asyncio
    async def test_full_kickoff_workflow(self):
        """Test full kickoff workflow end-to-end."""
        crew = X402Crew(project_id="test_project", run_id="test_run")

        with patch('app.crew.crew.get_agent_memory_service') as mock_memory, \
             patch('app.crew.crew.x402_service') as mock_x402, \
             patch('app.crew.crew.compliance_service') as mock_compliance:

            # Mock all services
            mock_service = AsyncMock()
            mock_service.store_memory = AsyncMock(side_effect=[
                {"memory_id": "mem_analyst"},
                {"memory_id": "mem_compliance"},
                {"memory_id": "mem_transaction"}
            ])
            mock_memory.return_value = mock_service

            mock_x402.create_request = AsyncMock(return_value={
                "request_id": "x402_req_final"
            })

            mock_compliance.create_event = AsyncMock(return_value=Mock(
                event_id="evt_final"
            ))

            # Execute workflow
            result = await crew.kickoff(input_data={"query": "Process BTC payment"})

            # Verify result structure
            assert result["status"] == "completed"
            assert result["run_id"] == "test_run"
            assert result["request_id"] == "x402_req_final"
            assert "analyst_output" in result
            assert "compliance_output" in result
            assert "transaction_output" in result
            assert len(result["memory_ids"]) == 3

            # Verify all services were called
            assert mock_service.store_memory.call_count == 3
            mock_x402.create_request.assert_called_once()
            mock_compliance.create_event.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app/crew", "--cov-report=term-missing"])
