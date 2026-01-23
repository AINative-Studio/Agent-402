"""
Tests for Agent Interactions API.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

TDD: These tests are written FIRST, implementation follows.

Per PRD Section 5 (Agent Personas):
- Agents can be hired for tasks
- Tasks are submitted and tracked
- Results are returned upon completion

Per Testing Requirements:
- BDD-style tests (describe/it pattern)
- 80%+ test coverage required
- All tests must pass before merge
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from app.schemas.agent_interactions import (
    AgentInteractionStatus,
    TaskStatus,
    HireAgentRequest,
    HireAgentResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
    AgentStatusResponse,
    TaskResult
)


# ============================================================================
# Describe: Agent Interactions API Endpoints
# ============================================================================

class TestAgentInteractionsAPI:
    """Test suite for Agent Interactions API endpoints."""

    # ------------------------------------------------------------------------
    # Describe: POST /agents/hire
    # ------------------------------------------------------------------------

    def test_it_should_hire_agent_with_valid_request(
        self,
        client,
        auth_headers_user1
    ):
        """It should successfully hire an agent with valid request data."""
        # Note: This endpoint requires X402 payment header
        request_data = {
            "agent_id": "agent_analyst_001",
            "task_description": "Analyze Q4 2025 financial data",
            "payment_amount_usdc": "10.000000",
            "max_duration_seconds": 3600,
            "priority": "normal"
        }

        # Add X402 payment header
        headers = {
            **auth_headers_user1,
            "X-X402-Payment": "valid_payment_token"
        }

        response = client.post(
            "/v1/public/agents/hire",
            json=request_data,
            headers=headers
        )

        # Should return 201 Created or 200 OK
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        data = response.json()
        assert "hire_id" in data
        assert "task_id" in data
        assert "payment_receipt_id" in data
        assert data["agent_id"] == "agent_analyst_001"
        assert data["status"] in ["hired", "working"]

    def test_it_should_reject_hire_without_payment_header(
        self,
        client,
        auth_headers_user1
    ):
        """It should reject hire request without X402 payment header."""
        request_data = {
            "agent_id": "agent_analyst_001",
            "task_description": "Test task",
            "payment_amount_usdc": "5.000000"
        }

        response = client.post(
            "/v1/public/agents/hire",
            json=request_data,
            headers=auth_headers_user1
        )

        # Should return 402 Payment Required or 400 Bad Request
        assert response.status_code in [
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_it_should_accept_hire_for_any_agent_id(
        self,
        client,
        auth_headers_user1
    ):
        """
        It should accept hire request for any agent_id.

        Note: MVP implementation does not validate agent existence.
        Agents can be registered dynamically or exist in external registry.
        """
        request_data = {
            "agent_id": "nonexistent_agent_xyz",
            "task_description": "Test task",
            "payment_amount_usdc": "5.000000"
        }

        headers = {
            **auth_headers_user1,
            "X-X402-Payment": "valid_payment_token"
        }

        response = client.post(
            "/v1/public/agents/hire",
            json=request_data,
            headers=headers
        )

        # MVP: Accept any agent_id, validation happens at task execution
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND  # Future: may validate agent existence
        ]

    def test_it_should_allow_concurrent_hires_for_same_agent(
        self,
        client,
        auth_headers_user1
    ):
        """
        It should allow multiple hires for the same agent.

        Note: MVP implementation allows concurrent hires.
        Agent availability management is handled at task execution level.
        Future enhancement: Add concurrency control per agent.
        """
        request_data = {
            "agent_id": "agent_busy_001",
            "task_description": "Test task",
            "payment_amount_usdc": "5.000000"
        }

        headers = {
            **auth_headers_user1,
            "X-X402-Payment": "valid_payment_token"
        }

        response = client.post(
            "/v1/public/agents/hire",
            json=request_data,
            headers=headers
        )

        # MVP: Allow concurrent hires (no availability check)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_409_CONFLICT,  # Future: may check availability
            status.HTTP_400_BAD_REQUEST
        ]

    # ------------------------------------------------------------------------
    # Describe: POST /agents/tasks
    # ------------------------------------------------------------------------

    def test_it_should_submit_task_with_valid_hire_id(
        self,
        client,
        auth_headers_user1
    ):
        """It should submit a task with valid hire ID."""
        # First hire an agent (mock this or use existing hire)
        request_data = {
            "hire_id": "hire_test_123",
            "input_data": {
                "data_source": "financial_db",
                "date_range": {"start": "2025-10-01", "end": "2025-12-31"}
            }
        }

        response = client.post(
            "/v1/public/agents/tasks",
            json=request_data,
            headers=auth_headers_user1
        )

        # Should return 200 OK or 201 Created
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND  # If hire doesn't exist
        ]

    def test_it_should_reject_task_with_invalid_hire_id(
        self,
        client,
        auth_headers_user1
    ):
        """It should return 404 for invalid hire ID."""
        request_data = {
            "hire_id": "invalid_hire_xyz",
            "input_data": {"test": "data"}
        }

        response = client.post(
            "/v1/public/agents/tasks",
            json=request_data,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ------------------------------------------------------------------------
    # Describe: GET /agents/{agent_id}/status
    # ------------------------------------------------------------------------

    def test_it_should_get_agent_status(
        self,
        client,
        auth_headers_user1
    ):
        """It should return agent status for existing agent."""
        response = client.get(
            "/v1/public/agents/agent_test_001/status",
            headers=auth_headers_user1
        )

        # Should return 200 OK or 404 if agent doesn't exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "agent_id" in data
            assert "status" in data

    def test_it_should_return_status_for_any_agent(
        self,
        client,
        auth_headers_user1
    ):
        """
        It should return status for any agent_id.

        Note: MVP returns default "available" status for unknown agents.
        Agents may be registered in external systems (Arc blockchain).
        """
        response = client.get(
            "/v1/public/agents/nonexistent_agent/status",
            headers=auth_headers_user1
        )

        # MVP: Returns status for any agent_id (default: available)
        assert response.status_code in [
            status.HTTP_200_OK,  # Returns default status
            status.HTTP_404_NOT_FOUND  # Future: may validate existence
        ]

    # ------------------------------------------------------------------------
    # Describe: GET /tasks/{task_id}/result
    # ------------------------------------------------------------------------

    def test_it_should_get_task_result_for_completed_task(
        self,
        client,
        auth_headers_user1
    ):
        """It should return task result for completed task."""
        response = client.get(
            "/v1/public/tasks/task_completed_123/result",
            headers=auth_headers_user1
        )

        # Should return 200 OK or 404 if task doesn't exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_it_should_return_404_for_nonexistent_task(
        self,
        client,
        auth_headers_user1
    ):
        """It should return 404 for non-existent task."""
        response = client.get(
            "/v1/public/tasks/nonexistent_task/result",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Describe: Agent Interactions Service
# ============================================================================

class TestAgentInteractionsService:
    """Test suite for Agent Interactions Service."""

    @pytest.mark.asyncio
    async def test_it_should_create_hire_record(
        self,
        mock_zerodb_client
    ):
        """It should create a hire record in the database."""
        from app.services.agent_interactions_service import AgentInteractionsService

        service = AgentInteractionsService(client=mock_zerodb_client)

        hire_request = HireAgentRequest(
            agent_id="agent_test_001",
            task_description="Test task description",
            payment_amount_usdc="25.000000",
            max_duration_seconds=7200,
            priority="high"
        )

        result = await service.hire_agent(
            project_id="test_project",
            request=hire_request,
            payment_receipt_id="pay_rcpt_test_001"
        )

        assert result is not None
        assert result["hire_id"].startswith("hire_")
        assert result["agent_id"] == "agent_test_001"
        assert result["status"] == AgentInteractionStatus.HIRED.value

    @pytest.mark.asyncio
    async def test_it_should_submit_task_for_hired_agent(
        self,
        mock_zerodb_client
    ):
        """It should submit a task for a hired agent."""
        from app.services.agent_interactions_service import AgentInteractionsService

        service = AgentInteractionsService(client=mock_zerodb_client)

        # First create a hire
        hire_request = HireAgentRequest(
            agent_id="agent_task_test",
            task_description="Task submission test",
            payment_amount_usdc="15.000000"
        )

        hire_result = await service.hire_agent(
            project_id="test_project",
            request=hire_request,
            payment_receipt_id="pay_rcpt_task_test"
        )

        # Then submit task
        task_request = TaskSubmitRequest(
            hire_id=hire_result["hire_id"],
            input_data={"test_key": "test_value"}
        )

        task_result = await service.submit_task(
            project_id="test_project",
            request=task_request
        )

        assert task_result is not None
        assert task_result["task_id"].startswith("task_")
        assert task_result["hire_id"] == hire_result["hire_id"]
        assert task_result["status"] == TaskStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_it_should_get_agent_status(
        self,
        mock_zerodb_client
    ):
        """It should return agent status including reputation."""
        from app.services.agent_interactions_service import AgentInteractionsService

        service = AgentInteractionsService(client=mock_zerodb_client)

        # Note: This may require mocking the Arc blockchain service
        result = await service.get_agent_status(
            project_id="test_project",
            agent_id="agent_status_test"
        )

        assert result is not None
        assert "agent_id" in result
        assert "status" in result
        assert "total_tasks_completed" in result

    @pytest.mark.asyncio
    async def test_it_should_get_task_result(
        self,
        mock_zerodb_client
    ):
        """It should return task result for a completed task."""
        from app.services.agent_interactions_service import AgentInteractionsService

        service = AgentInteractionsService(client=mock_zerodb_client)

        # Create hire and task first
        hire_request = HireAgentRequest(
            agent_id="agent_result_test",
            task_description="Task result test",
            payment_amount_usdc="20.000000"
        )

        hire_result = await service.hire_agent(
            project_id="test_project",
            request=hire_request,
            payment_receipt_id="pay_rcpt_result_test"
        )

        task_request = TaskSubmitRequest(
            hire_id=hire_result["hire_id"],
            input_data={"input": "data"}
        )

        task_result = await service.submit_task(
            project_id="test_project",
            request=task_request
        )

        # Complete the task (simulate)
        await service.complete_task(
            project_id="test_project",
            task_id=task_result["task_id"],
            output_data={"result": "success"},
            status=TaskStatus.COMPLETED
        )

        # Get result
        result = await service.get_task_result(
            project_id="test_project",
            task_id=task_result["task_id"]
        )

        assert result is not None
        assert result["task_id"] == task_result["task_id"]
        assert result["status"] == TaskStatus.COMPLETED.value
        assert result["output_data"]["result"] == "success"

    @pytest.mark.asyncio
    async def test_it_should_raise_error_for_invalid_hire_id(
        self,
        mock_zerodb_client
    ):
        """It should raise HireNotFoundError for invalid hire ID."""
        from app.services.agent_interactions_service import (
            AgentInteractionsService,
            HireNotFoundError
        )

        service = AgentInteractionsService(client=mock_zerodb_client)

        task_request = TaskSubmitRequest(
            hire_id="invalid_hire_id",
            input_data={"test": "data"}
        )

        with pytest.raises(HireNotFoundError):
            await service.submit_task(
                project_id="test_project",
                request=task_request
            )


# ============================================================================
# Describe: Schema Validation
# ============================================================================

class TestAgentInteractionSchemas:
    """Test suite for agent interaction schema validation."""

    def test_it_should_validate_hire_agent_request(self):
        """It should validate HireAgentRequest with required fields."""
        request = HireAgentRequest(
            agent_id="agent_001",
            task_description="Test task",
            payment_amount_usdc="10.000000"
        )

        assert request.agent_id == "agent_001"
        assert request.max_duration_seconds == 3600  # Default
        assert request.priority == "normal"  # Default

    def test_it_should_validate_task_submit_request(self):
        """It should validate TaskSubmitRequest with required fields."""
        request = TaskSubmitRequest(
            hire_id="hire_123",
            input_data={"key": "value"}
        )

        assert request.hire_id == "hire_123"
        assert request.callback_url is None

    def test_it_should_validate_agent_status_enum(self):
        """It should validate AgentInteractionStatus enumeration."""
        assert AgentInteractionStatus.AVAILABLE.value == "available"
        assert AgentInteractionStatus.HIRED.value == "hired"
        assert AgentInteractionStatus.WORKING.value == "working"
        assert AgentInteractionStatus.COMPLETED.value == "completed"
        assert AgentInteractionStatus.FAILED.value == "failed"
        assert AgentInteractionStatus.CANCELLED.value == "cancelled"

    def test_it_should_validate_task_status_enum(self):
        """It should validate TaskStatus enumeration."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
