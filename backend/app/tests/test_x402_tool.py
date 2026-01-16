"""
Test suite for X402RequestTool.

Tests Issue #74: AIKit x402.request Tool Wrapper

Test Coverage:
- Tool instantiation and configuration
- DID signature verification (success and failure)
- X402 request creation via tool
- Event logging integration
- Memory storage integration
- Error handling (invalid DID, missing parameters, etc.)
- Tool execution context and correlation

TDD Approach:
1. RED: These tests will fail initially (tool doesn't exist)
2. GREEN: Implement tool to make tests pass
3. REFACTOR: Improve implementation while tests stay green
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# These imports will fail initially (RED phase)
from tools.base import BaseTool, ToolExecutionContext, ToolResult
from tools.x402_request import X402RequestTool
from app.schemas.x402_requests import X402RequestStatus


class TestX402RequestToolInstantiation:
    """Test tool instantiation and configuration."""

    def test_tool_class_exists(self):
        """Test that X402RequestTool class exists."""
        assert X402RequestTool is not None
        assert issubclass(X402RequestTool, BaseTool)

    def test_tool_has_correct_name(self):
        """Test that tool has correct name per PRD."""
        tool = X402RequestTool()
        assert tool.name == "x402.request"

    def test_tool_has_description(self):
        """Test that tool has human-readable description."""
        tool = X402RequestTool()
        assert tool.description is not None
        assert len(tool.description) > 0
        assert "X402" in tool.description

    def test_tool_has_schema(self):
        """Test that tool has parameter schema."""
        tool = X402RequestTool()
        schema = tool.schema
        assert schema is not None
        assert "properties" in schema

        # Required parameters per PRD Section 8
        assert "did" in schema["properties"]
        assert "signature" in schema["properties"]
        assert "payload" in schema["properties"]

    def test_tool_can_be_instantiated_with_services(self):
        """Test tool instantiation with service dependencies."""
        mock_event_service = MagicMock()
        mock_memory_service = MagicMock()

        tool = X402RequestTool(
            event_service=mock_event_service,
            memory_service=mock_memory_service
        )

        assert tool._event_service == mock_event_service
        assert tool._memory_service == mock_memory_service


class TestX402RequestToolExecution:
    """Test tool execution with various scenarios."""

    @pytest.fixture
    def tool(self):
        """Create X402RequestTool instance."""
        return X402RequestTool()

    @pytest.fixture
    def execution_context(self):
        """Create execution context."""
        return ToolExecutionContext(
            project_id="proj_test_001",
            agent_id="did:ethr:0xtransaction001",
            run_id="run_test_001",
            task_id="task_test_001",
            correlation_id="corr_test_001"
        )

    @pytest.fixture
    def valid_payload(self):
        """Create valid X402 request payload."""
        return {
            "type": "payment_authorization",
            "amount": "100.00",
            "currency": "USD",
            "recipient": "did:ethr:0xrecipient123",
            "memo": "Test payment"
        }

    @pytest.mark.asyncio
    async def test_tool_execution_with_valid_signature(
        self,
        tool,
        execution_context,
        valid_payload
    ):
        """Test successful tool execution with valid signature."""
        # Mock the X402 service
        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test_001",
                "project_id": execution_context.project_id,
                "agent_id": execution_context.agent_id,
                "task_id": execution_context.task_id,
                "run_id": execution_context.run_id,
                "request_payload": valid_payload,
                "signature": "0xvalidsignature123",
                "status": "PENDING",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {"signature_verified": True}
            })

            # Mock signature verification
            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=execution_context,
                    did=execution_context.agent_id,
                    signature="0xvalidsignature123",
                    payload=valid_payload
                )

                assert result.success is True
                assert result.data is not None
                assert result.data["request_id"] == "x402_req_test_001"
                assert result.error is None

                # Verify service was called
                mock_service.create_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_execution_with_invalid_signature(
        self,
        tool,
        execution_context,
        valid_payload
    ):
        """Test tool execution fails with invalid signature."""
        # Mock signature verification to return False
        with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
            mock_verify.return_value = False

            result = await tool.execute(
                context=execution_context,
                did=execution_context.agent_id,
                signature="0xinvalidsignature",
                payload=valid_payload
            )

            assert result.success is False
            assert result.error is not None
            assert "signature" in result.error.lower() or "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_invalid_did_format(
        self,
        tool,
        execution_context,
        valid_payload
    ):
        """Test tool execution fails with invalid DID format."""
        # Mock signature verification to raise InvalidDIDError
        with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
            from app.core.did_signer import InvalidDIDError
            mock_verify.side_effect = InvalidDIDError("Invalid DID format")

            result = await tool.execute(
                context=execution_context,
                did="invalid_did_format",
                signature="0xsomesignature",
                payload=valid_payload
            )

            assert result.success is False
            assert result.error is not None
            assert "DID" in result.error or "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_missing_parameters(
        self,
        tool,
        execution_context
    ):
        """Test tool execution fails with missing required parameters."""
        # Test missing 'did'
        result = await tool.execute(
            context=execution_context,
            signature="0xsignature",
            payload={"test": "data"}
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_tool_execution_with_empty_payload(
        self,
        tool,
        execution_context
    ):
        """Test tool execution fails with empty payload."""
        result = await tool.execute(
            context=execution_context,
            did=execution_context.agent_id,
            signature="0xsignature",
            payload={}
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_tool_execution_stores_in_memory(
        self,
        execution_context,
        valid_payload
    ):
        """Test that successful tool execution stores result in agent_memory."""
        mock_memory_service = AsyncMock()
        mock_memory_service.store_memory = AsyncMock(return_value={
            "memory_id": "mem_test_001",
            "project_id": execution_context.project_id,
            "agent_id": execution_context.agent_id
        })

        tool = X402RequestTool(memory_service=mock_memory_service)

        # Mock X402 service
        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test_001",
                "project_id": execution_context.project_id,
                "agent_id": execution_context.agent_id,
                "task_id": execution_context.task_id,
                "run_id": execution_context.run_id,
                "request_payload": valid_payload,
                "signature": "0xvalidsignature123",
                "status": "PENDING",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            # Mock signature verification
            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=execution_context,
                    did=execution_context.agent_id,
                    signature="0xvalidsignature123",
                    payload=valid_payload
                )

                assert result.success is True
                assert result.memory_id == "mem_test_001"

                # Verify memory service was called
                mock_memory_service.store_memory.assert_called_once()
                call_args = mock_memory_service.store_memory.call_args
                assert call_args.kwargs["memory_type"] == "tool_execution"

    @pytest.mark.asyncio
    async def test_tool_execution_logs_events(
        self,
        execution_context,
        valid_payload
    ):
        """Test that tool execution logs events."""
        mock_event_service = AsyncMock()
        mock_event_service.store_agent_tool_call = AsyncMock(return_value={
            "id": "event_test_001"
        })

        tool = X402RequestTool(event_service=mock_event_service)

        # Mock X402 service
        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_test_001",
                "project_id": execution_context.project_id,
                "agent_id": execution_context.agent_id,
                "task_id": execution_context.task_id,
                "run_id": execution_context.run_id,
                "request_payload": valid_payload,
                "signature": "0xvalidsignature123",
                "status": "PENDING",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            # Mock signature verification
            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=execution_context,
                    did=execution_context.agent_id,
                    signature="0xvalidsignature123",
                    payload=valid_payload
                )

                assert result.success is True
                assert result.event_id == "event_test_001"

                # Verify event service was called at least once
                assert mock_event_service.store_agent_tool_call.call_count >= 1


class TestX402RequestToolIntegration:
    """Integration tests with real services (mocked ZeroDB)."""

    @pytest.mark.asyncio
    async def test_tool_creates_x402_request_end_to_end(self):
        """Test complete flow from tool execution to X402 request creation."""
        tool = X402RequestTool()

        context = ToolExecutionContext(
            project_id="proj_integration_001",
            agent_id="did:ethr:0xtransaction001",
            run_id="run_integration_001",
            task_id="task_integration_001"
        )

        payload = {
            "type": "payment_authorization",
            "amount": "500.00",
            "currency": "USD",
            "recipient": "did:ethr:0xrecipient999"
        }

        # Mock the entire flow
        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_integration_001",
                "project_id": context.project_id,
                "agent_id": context.agent_id,
                "task_id": context.task_id,
                "run_id": context.run_id,
                "request_payload": payload,
                "signature": "0xintegrationtestsignature",
                "status": "PENDING",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {"signature_verified": True}
            })

            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=context,
                    did=context.agent_id,
                    signature="0xintegrationtestsignature",
                    payload=payload
                )

                # Verify result structure
                assert result.success is True
                assert result.data["request_id"] == "x402_req_integration_001"
                assert result.data["agent_id"] == context.agent_id
                assert result.data["status"] == "PENDING"
                assert "timestamp" in result.data

    @pytest.mark.asyncio
    async def test_tool_handles_service_failure_gracefully(self):
        """Test tool handles X402 service failures gracefully."""
        tool = X402RequestTool()

        context = ToolExecutionContext(
            project_id="proj_error_001",
            agent_id="did:ethr:0xtransaction001",
            run_id="run_error_001"
        )

        # Mock X402 service to raise exception
        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=context,
                    did=context.agent_id,
                    signature="0xsignature",
                    payload={"test": "data"}
                )

                # Tool should return error result, not raise exception
                assert result.success is False
                assert result.error is not None
                assert "Database connection failed" in result.error


class TestX402RequestToolToDict:
    """Test tool serialization for API responses."""

    def test_tool_to_dict_returns_correct_structure(self):
        """Test that to_dict returns correct structure."""
        tool = X402RequestTool()
        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "x402.request"
        assert "description" in tool_dict
        assert "schema" in tool_dict
        assert "properties" in tool_dict["schema"]


class TestX402RequestToolMetadata:
    """Test tool metadata and configuration."""

    @pytest.mark.asyncio
    async def test_tool_execution_includes_timing_metadata(
        self
    ):
        """Test that execution result includes timing information."""
        tool = X402RequestTool()

        context = ToolExecutionContext(
            project_id="proj_timing_001",
            agent_id="did:ethr:0xtransaction001",
            run_id="run_timing_001"
        )

        with patch("tools.x402_request.x402_service") as mock_service:
            mock_service.create_request = AsyncMock(return_value={
                "request_id": "x402_req_timing_001",
                "project_id": context.project_id,
                "agent_id": context.agent_id,
                "task_id": None,
                "run_id": context.run_id,
                "request_payload": {"test": "data"},
                "signature": "0xsig",
                "status": "PENDING",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {}
            })

            with patch("tools.x402_request.DIDSigner.verify_signature") as mock_verify:
                mock_verify.return_value = True

                result = await tool.execute(
                    context=context,
                    did=context.agent_id,
                    signature="0xsig",
                    payload={"test": "data"}
                )

                # Check timing metadata
                assert "duration_ms" in result.metadata
                assert isinstance(result.metadata["duration_ms"], int)
                assert result.metadata["duration_ms"] >= 0
                assert result.metadata["tool_name"] == "x402.request"
