"""
Standalone test runner for crew orchestration tests.
Bypasses conftest.py to avoid ecdsa dependency issues.
"""
import sys
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Ensure we can import from app
sys.path.insert(0, '.')

# Import the modules we're testing
from app.crew.agents import create_analyst_agent, create_compliance_agent, create_transaction_agent
from app.crew.tasks import create_analyst_task, create_compliance_task, create_transaction_task
from app.crew.crew import X402Crew, Process


def test_analyst_agent_attributes():
    """Test analyst agent has all required attributes."""
    agent = create_analyst_agent()

    assert hasattr(agent, 'role')
    assert hasattr(agent, 'goal')
    assert hasattr(agent, 'backstory')
    assert hasattr(agent, 'verbose')
    assert agent.role == "Market Data Analyst"
    assert "market data" in agent.goal.lower() or "aggregation" in agent.goal.lower()
    print("✓ test_analyst_agent_attributes PASSED")


def test_compliance_agent_attributes():
    """Test compliance agent has all required attributes."""
    agent = create_compliance_agent()

    assert hasattr(agent, 'role')
    assert hasattr(agent, 'goal')
    assert hasattr(agent, 'backstory')
    assert hasattr(agent, 'verbose')
    assert agent.role == "Compliance Officer"
    assert any(keyword in agent.goal.lower() for keyword in ["aml", "kyc", "compliance", "risk"])
    print("✓ test_compliance_agent_attributes PASSED")


def test_transaction_agent_attributes():
    """Test transaction agent has all required attributes."""
    agent = create_transaction_agent()

    assert hasattr(agent, 'role')
    assert hasattr(agent, 'goal')
    assert hasattr(agent, 'backstory')
    assert hasattr(agent, 'verbose')
    assert agent.role == "Transaction Executor"
    assert any(keyword in agent.goal.lower() for keyword in ["x402", "transaction", "execute"])
    print("✓ test_transaction_agent_attributes PASSED")


def test_analyst_task_creation():
    """Test analyst task creation."""
    agent = create_analyst_agent()
    context = {"query": "Test query", "project_id": "test"}
    task = create_analyst_task(agent, context)

    assert task.description is not None
    assert task.agent == agent
    assert "market data" in task.description.lower() or "aggregate" in task.description.lower()
    assert hasattr(task, 'expected_output')
    assert task.expected_output is not None
    print("✓ test_analyst_task_creation PASSED")


def test_compliance_task_creation():
    """Test compliance task creation."""
    agent = create_compliance_agent()
    context = {"analyst_output": "Test", "project_id": "test"}
    task = create_compliance_task(agent, context)

    assert task.description is not None
    assert task.agent == agent
    assert any(keyword in task.description.lower() for keyword in ["compliance", "risk", "aml", "kyc"])
    assert hasattr(task, 'expected_output')
    assert task.expected_output is not None
    print("✓ test_compliance_task_creation PASSED")


def test_transaction_task_creation():
    """Test transaction task creation."""
    agent = create_transaction_agent()
    context = {"compliance_output": "Test", "project_id": "test"}
    task = create_transaction_task(agent, context)

    assert task.description is not None
    assert task.agent == agent
    assert "x402" in task.description.lower() or "transaction" in task.description.lower()
    assert hasattr(task, 'expected_output')
    assert task.expected_output is not None
    print("✓ test_transaction_task_creation PASSED")


def test_crew_initialization():
    """Test crew initialization."""
    crew = X402Crew(
        project_id="test_project",
        run_id="test_run"
    )

    assert crew.project_id == "test_project"
    assert crew.run_id == "test_run"
    assert crew.agents is not None
    assert len(crew.agents) == 3
    print("✓ test_crew_initialization PASSED")


def test_crew_sequential_process():
    """Test crew uses sequential process."""
    crew = X402Crew(
        project_id="test_project",
        run_id="test_run"
    )

    crew_obj = crew.create_crew()
    assert crew_obj.process == Process.sequential
    print("✓ test_crew_sequential_process PASSED")


def test_crew_agent_count():
    """Test crew has exactly 3 agents."""
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
    print("✓ test_crew_agent_count PASSED")


def test_crew_task_creation():
    """Test crew creates 3 tasks."""
    crew = X402Crew(
        project_id="test_project",
        run_id="test_run"
    )

    tasks = crew.create_tasks({"query": "Test query"})
    assert len(tasks) == 3
    print("✓ test_crew_task_creation PASSED")


async def test_store_agent_output():
    """Test storing agent output in memory."""
    crew = X402Crew(
        project_id="test_project",
        run_id="test_run"
    )

    with patch('app.crew.crew.get_agent_memory_service') as mock_memory:
        mock_memory_service = AsyncMock()
        mock_memory_service.store_memory = AsyncMock(return_value={
            "memory_id": "mem_test123",
            "content": "Test analyst output"
        })
        mock_memory.return_value = mock_memory_service

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

    print("✓ test_store_agent_output PASSED")


async def test_full_workflow_integration():
    """Integration test for complete 3-agent workflow."""
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

        result = await crew.kickoff(input_data={
            "query": "Process BTC payment of 0.5 BTC"
        })

        # Verify workflow completed
        assert result is not None
        assert "request_id" in result
        assert result["request_id"] == "x402_req_integration_test"

        # Verify all three agent memory stores were called
        assert mock_memory_service.store_memory.call_count == 3

    print("✓ test_full_workflow_integration PASSED")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running CrewAI Orchestration Tests")
    print("="*60 + "\n")

    passed = 0
    failed = 0

    # Synchronous tests
    tests = [
        test_analyst_agent_attributes,
        test_compliance_agent_attributes,
        test_transaction_agent_attributes,
        test_analyst_task_creation,
        test_compliance_task_creation,
        test_transaction_task_creation,
        test_crew_initialization,
        test_crew_sequential_process,
        test_crew_agent_count,
        test_crew_task_creation,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1

    # Async tests
    async_tests = [
        test_store_agent_output,
        test_full_workflow_integration,
    ]

    for test in async_tests:
        try:
            asyncio.run(test())
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
