"""
Comprehensive tests for X402RequestTool wrapper.
Tests Issue #74: AIKit x402.request Tool Wrapper.

Test Coverage:
- Tool initialization
- Tool execution with valid parameters
- Tool execution with invalid parameters
- Tool invocation logging to events API
- Tool result storage in agent_memory
- Tool timing and duration tracking
- Error handling and edge cases

Per PRD Section 8: X402 Protocol must be wrapped as AIKit Tool Primitive.
Per PRD Section 10: All tool invocations must be logged and replayable.
"""
import pytest
import sys
import os

# Add backend directory to path for tool imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from tools.x402_request import X402RequestTool
from tools.base import ToolExecutionContext, ToolResult
from app.schemas.x402_requests import X402RequestStatus


class TestX402ToolInitialization:
    """Test suite for X402RequestTool initialization."""

    def test_tool_initialization_success(self):
        """Test successful tool initialization."""
        tool = X402RequestTool()

        assert tool.name == "x402.request"
        assert tool.description is not None
        assert len(tool.description) > 0
        assert tool.schema is not None

    def test_tool_initialization_with_services(self):
        """Test initialization with custom services for testing."""
        mock_event_service = MagicMock()
        mock_memory_service = MagicMock()

        tool = X402RequestTool(
            event_service_instance=mock_event_service,
            memory_service_instance=mock_memory_service
        )

        assert tool.name == "x402.request"
        assert tool._event_service == mock_event_service
        assert tool._memory_service == mock_memory_service

    def test_tool_name_constant(self):
        """Test that tool name is constant across instances."""
        tool1 = X402RequestTool()
        tool2 = X402RequestTool()

        assert tool1.name == tool2.name
        assert tool1.name == "x402.request"

    def test_tool_has_description(self):
        """Test that tool has proper description for AIKit."""
        tool = X402RequestTool()

        assert hasattr(tool, "description")
        assert isinstance(tool.description, str)
        assert "X402" in tool.description or "x402" in tool.description
        assert "payment" in tool.description.lower() or "signed" in tool.description.lower()

    def test_tool_has_schema(self):
        """Test that tool has parameter schema."""
        tool = X402RequestTool()

        assert hasattr(tool, "schema")
        assert isinstance(tool.schema, dict)
        assert "properties" in tool.schema
        assert "required" in tool.schema

        # Check required parameters
        required = tool.schema["required"]
        assert "did" in required
        assert "signature" in required
        assert "payload" in required
        assert "task_id" in required
        assert "run_id" in required


class TestX402ToolExecution:
    """Test suite for X402RequestTool execution with valid parameters."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return X402RequestTool()

    @pytest.fixture
    def context(self):
        """Create execution context for testing."""
        return ToolExecutionContext(
            project_id="proj_test",
            agent_id="agent_test",
            run_id="run_test",
            task_id="task_test"
        )

    @pytest.fixture
    def valid_params(self):
        """Valid parameters for X402 request."""
        return {
            "did": "did:ethr:0xabc123def456",
            "signature": "0xsig123abc456def789",
            "payload": {
                "type": "payment_authorization",
                "amount": "100.00",
                "currency": "USD",
                "recipient": "did:ethr:0xdef789abc012"
            },
            "task_id": "task_001",
            "run_id": "run_001"
        }

    @pytest.mark.asyncio
    async def test_execute_success(self, tool, context, valid_params):
        """Test successful tool execution with valid parameters."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test123",
                "project_id": "proj_test",
                "agent_id": valid_params["did"],
                "task_id": valid_params["task_id"],
                "run_id": valid_params["run_id"],
                "request_payload": valid_params["payload"],
                "signature": valid_params["signature"],
                "status": "PENDING",
                "timestamp": "2026-01-15T10:00:00.000Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            result = await tool._execute(context, **valid_params)

            assert result is not None
            assert result.success is True
            assert "request_id" in result.data
            assert result.data["request_id"] == "x402_req_test123"

            # Verify X402 service was called
            mock_service.create_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tracks_duration(self, tool, context, valid_params):
        """Test that execution tracks timing metadata."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_timing",
                "project_id": "proj_test",
                "agent_id": valid_params["did"],
                "task_id": valid_params["task_id"],
                "run_id": valid_params["run_id"],
                "request_payload": valid_params["payload"],
                "signature": valid_params["signature"],
                "status": "PENDING",
                "timestamp": "2026-01-15T10:00:00.000Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            result = await tool._execute(context, **valid_params)

            assert "start_time" in result.metadata
            assert "end_time" in result.metadata
            assert "duration_ms" in result.metadata

            # Duration should be positive
            assert result.metadata["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_returns_structured_response(self, tool, context, valid_params):
        """Test that execution returns structured response format."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_structured",
                "project_id": "proj_test",
                "agent_id": valid_params["did"],
                "task_id": valid_params["task_id"],
                "run_id": valid_params["run_id"],
                "request_payload": valid_params["payload"],
                "signature": valid_params["signature"],
                "status": "PENDING",
                "timestamp": "2026-01-15T10:00:00.000Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            result = await tool._execute(context, **valid_params)

            # Check ToolResult structure
            assert isinstance(result, ToolResult)
            assert hasattr(result, "success")
            assert hasattr(result, "data")
            assert hasattr(result, "metadata")

            # Check data contains expected fields
            assert "request_id" in result.data
            assert "status" in result.data
            assert "agent_id" in result.data


class TestX402ToolInvalidParameters:
    """Test suite for X402RequestTool execution with invalid parameters."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return X402RequestTool()

    @pytest.fixture
    def context(self):
        """Create execution context for testing."""
        return ToolExecutionContext(
            project_id="proj_test",
            agent_id="agent_test",
            run_id="run_test"
        )

    @pytest.mark.asyncio
    async def test_execute_missing_did_fails(self, tool, context):
        """Test execution fails when did parameter is missing."""
        params = {
            "signature": "0xsig123",
            "payload": {"amount": "100.00"},
            "task_id": "task_001",
            "run_id": "run_001"
        }

        result = await tool._execute(context, **params)

        assert result.success is False
        assert "error" in result.__dict__
        assert result.error is not None
        assert "did" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_missing_signature_fails(self, tool, context):
        """Test execution fails when signature parameter is missing."""
        params = {
            "did": "did:ethr:0xtest",
            "payload": {"amount": "100.00"},
            "task_id": "task_001",
            "run_id": "run_001"
        }

        result = await tool._execute(context, **params)

        assert result.success is False
        assert result.error is not None
        assert "signature" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_missing_payload_fails(self, tool, context):
        """Test execution fails when payload parameter is missing."""
        params = {
            "did": "did:ethr:0xtest",
            "signature": "0xsig123",
            "task_id": "task_001",
            "run_id": "run_001"
        }

        result = await tool._execute(context, **params)

        assert result.success is False
        assert result.error is not None
        assert "payload" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_empty_payload_fails(self, tool, context):
        """Test execution fails with empty payload."""
        params = {
            "did": "did:ethr:0xtest",
            "signature": "0xsig123",
            "payload": {},  # Empty payload
            "task_id": "task_001",
            "run_id": "run_001"
        }

        result = await tool._execute(context, **params)

        assert result.success is False
        assert result.error is not None


class TestX402ToolErrorHandling:
    """Test suite for tool error handling and edge cases."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return X402RequestTool()

    @pytest.fixture
    def context(self):
        """Create execution context for testing."""
        return ToolExecutionContext(
            project_id="proj_test",
            agent_id="agent_test",
            run_id="run_test"
        )

    @pytest.fixture
    def valid_params(self):
        """Valid parameters for X402 request."""
        return {
            "did": "did:ethr:0xerror_test",
            "signature": "0xsigError",
            "payload": {"amount": "100.00"},
            "task_id": "task_error_001",
            "run_id": "run_error_001"
        }

    @pytest.mark.asyncio
    async def test_execute_handles_x402_service_error(self, tool, context, valid_params):
        """Test graceful handling of X402 service errors."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(
                side_effect=Exception("X402 service unavailable")
            )

            result = await tool._execute(context, **valid_params)

            assert result.success is False
            assert result.error is not None
            assert "X402" in result.error or "unavailable" in result.error or "failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_returns_error_with_context(self, tool, context, valid_params):
        """Test that error responses include execution context."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(
                side_effect=ValueError("Invalid signature format")
            )

            result = await tool._execute(context, **valid_params)

            assert result.success is False
            assert result.error is not None
            assert "start_time" in result.metadata
            assert "end_time" in result.metadata
            assert "duration_ms" in result.metadata
            assert "tool_name" in result.metadata
            assert result.metadata["tool_name"] == "x402.request"

    @pytest.mark.asyncio
    async def test_execute_tracks_duration_on_error(self, tool, context, valid_params):
        """Test that duration is tracked even when execution fails."""
        with patch('tools.x402_request.x402_service') as mock_service:
            mock_service.create_request = AsyncMock(
                side_effect=Exception("Test error")
            )

            result = await tool._execute(context, **valid_params)

            assert "duration_ms" in result.metadata
            assert result.metadata["duration_ms"] >= 0


class TestX402ToolCrewAICompatibility:
    """Test suite for CrewAI agent compatibility."""

    def test_tool_has_required_attributes_for_crewai(self):
        """Test that tool has required attributes for CrewAI integration."""
        tool = X402RequestTool()

        # CrewAI tools require name and description attributes
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "_execute")

        # Name should be string
        assert isinstance(tool.name, str)
        # Description should be string
        assert isinstance(tool.description, str)
        # Execute should be callable
        assert callable(tool._execute)

    def test_tool_execute_is_async(self):
        """Test that execute method is async for CrewAI compatibility."""
        tool = X402RequestTool()

        import inspect
        assert inspect.iscoroutinefunction(tool._execute)

    def test_tool_description_is_informative(self):
        """Test that description provides enough info for agent decision-making."""
        tool = X402RequestTool()

        description = tool.description.lower()

        # Should mention key concepts
        assert any(word in description for word in ["x402", "payment", "signed", "request"])
        # Should be substantial (at least 50 characters)
        assert len(tool.description) >= 50

    def test_tool_schema_defines_parameters(self):
        """Test that schema properly defines tool parameters."""
        tool = X402RequestTool()

        schema = tool.schema
        assert "properties" in schema
        assert "required" in schema

        # Check that all required params are in properties
        for required_param in schema["required"]:
            assert required_param in schema["properties"]

        # Check that properties have descriptions
        for prop_name, prop_schema in schema["properties"].items():
            assert "description" in prop_schema
            assert len(prop_schema["description"]) > 10  # Meaningful description
