"""
X402RequestTool: AIKit tool wrapper for X402 signed payment requests.

Implements Issue #74: AIKit x402.request Tool Wrapper
Per PRD Section 8: X402 Protocol must be wrapped as AIKit Tool Primitive

Purpose:
- Wrap X402 request API as a reusable tool for agents
- Automatically log all tool invocations to events API
- Store tool results in agent_memory for replay and audit
- Track timing metrics (start, end, duration)
- Provide structured response format

Tool Integration:
- Compatible with CrewAI agents
- Compatible with other AIKit frameworks
- Follows BaseTool interface
- Automatic tracing and logging

Usage:
    from backend.tools import X402RequestTool
    from backend.tools.base import ToolExecutionContext

    # Initialize tool
    tool = X402RequestTool()

    # Create execution context
    context = ToolExecutionContext(
        project_id="proj_001",
        agent_id="agent_001",
        run_id="run_001",
        task_id="task_001"
    )

    # Execute tool
    result = await tool.execute(
        context,
        did="did:ethr:0xabc123",
        signature="0xsig123",
        payload={"amount": "100.00", "currency": "USD"},
        task_id="task_001",
        run_id="run_001"
    )

    # Check result
    if result.success:
        print(f"X402 request created: {result.data['request_id']}")
    else:
        print(f"Error: {result.error}")
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from tools.base import BaseTool, ToolExecutionContext, ToolResult
from app.services.x402_service import x402_service
from app.services.event_service import event_service
from app.services.agent_memory_service import agent_memory_service
from app.schemas.x402_requests import X402RequestStatus

logger = logging.getLogger(__name__)


class X402RequestTool(BaseTool):
    """
    AIKit tool wrapper for X402 signed payment requests.

    Wraps the X402 request service as a reusable tool primitive.
    Automatically logs invocations and stores results in agent_memory.

    Features:
    - Submits signed X402 payment authorization requests
    - Tracks request through agent/task linkage
    - Logs all invocations for compliance and audit
    - Stores results in agent_memory for replay
    - Records timing metrics for performance monitoring

    Tool Parameters:
    - did: DID of agent creating request (required)
    - signature: Cryptographic signature (required)
    - payload: X402 protocol payload with payment details (required)
    - task_id: Task identifier (required)
    - run_id: Run identifier (required)

    Returns:
    - success: Boolean indicating success/failure
    - data: X402 request details including request_id
    - error: Error message if failed
    - metadata: Timing and execution metadata
    - memory_id: ID of stored memory record
    - event_id: ID of logged event
    """

    def __init__(
        self,
        event_service_instance: Optional[Any] = None,
        memory_service_instance: Optional[Any] = None
    ):
        """
        Initialize X402RequestTool.

        Args:
            event_service_instance: Optional EventService for testing
            memory_service_instance: Optional AgentMemoryService for testing
        """
        # Use provided services or defaults
        super().__init__(
            event_service=event_service_instance or event_service,
            memory_service=memory_service_instance or agent_memory_service
        )

    @property
    def name(self) -> str:
        """
        Tool name for AIKit registration.

        Returns:
            Tool name: "x402.request"
        """
        return "x402.request"

    @property
    def description(self) -> str:
        """
        Human-readable tool description for agent decision-making.

        Returns:
            Tool description explaining X402 request capabilities
        """
        return (
            "Submit a signed X402 payment authorization request. "
            "This tool creates a cryptographically signed payment request "
            "that is traceable to the originating agent and task. "
            "Use this tool when you need to authorize payments or financial transactions "
            "on behalf of an agent. All requests are logged for compliance and audit."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        """
        JSON Schema for tool parameters.

        Defines required and optional parameters for X402 requests.

        Returns:
            JSON Schema dictionary
        """
        return {
            "type": "object",
            "properties": {
                "did": {
                    "type": "string",
                    "description": (
                        "Decentralized Identifier (DID) of the agent creating the request. "
                        "Format: did:ethr:0x..."
                    ),
                    "pattern": "^did:.*"
                },
                "signature": {
                    "type": "string",
                    "description": (
                        "Cryptographic signature of the request payload. "
                        "Ensures authenticity and non-repudiation."
                    ),
                    "minLength": 1
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "X402 protocol payload containing payment authorization details. "
                        "Must include amount, currency, recipient, and other protocol fields."
                    ),
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Request type (e.g., 'payment_authorization')"
                        },
                        "amount": {
                            "type": "string",
                            "description": "Payment amount as decimal string"
                        },
                        "currency": {
                            "type": "string",
                            "description": "Currency code (e.g., 'USD', 'EUR')"
                        },
                        "recipient": {
                            "type": "string",
                            "description": "Recipient DID or identifier"
                        }
                    },
                    "required": ["amount"]
                },
                "task_id": {
                    "type": "string",
                    "description": (
                        "Task identifier that produced this request. "
                        "Enables correlation between tasks and payment authorizations."
                    ),
                    "minLength": 1
                },
                "run_id": {
                    "type": "string",
                    "description": (
                        "Run identifier for the agent execution context. "
                        "Groups related requests within a single agent run."
                    ),
                    "minLength": 1
                }
            },
            "required": ["did", "signature", "payload", "task_id", "run_id"]
        }

    async def _execute(
        self,
        context: ToolExecutionContext,
        **parameters: Any
    ) -> ToolResult:
        """
        Execute X402 request tool logic.

        Workflow:
        1. Extract and validate parameters
        2. Call X402 service to create request
        3. Format structured response
        4. Return ToolResult with timing metadata

        Args:
            context: Tool execution context with project/agent/run IDs
            **parameters: Tool parameters (did, signature, payload, task_id, run_id)

        Returns:
            ToolResult with success status and X402 request data

        Raises:
            Exception: Any errors during X402 request creation
        """
        start_time = datetime.utcnow()

        try:
            # Extract required parameters
            did = parameters.get("did")
            signature = parameters.get("signature")
            payload = parameters.get("payload")
            task_id = parameters.get("task_id")
            run_id = parameters.get("run_id")

            # Validate required parameters
            if not did:
                raise ValueError("Parameter 'did' is required")
            if not signature:
                raise ValueError("Parameter 'signature' is required")
            if not payload:
                raise ValueError("Parameter 'payload' is required")
            if not task_id:
                raise ValueError("Parameter 'task_id' is required")
            if not run_id:
                raise ValueError("Parameter 'run_id' is required")

            # Validate payload is not empty
            if not isinstance(payload, dict) or len(payload) == 0:
                raise ValueError("Parameter 'payload' must be a non-empty dictionary")

            logger.info(
                f"Executing X402 request tool for agent {context.agent_id}",
                extra={
                    "agent_id": context.agent_id,
                    "task_id": task_id,
                    "run_id": run_id,
                    "project_id": context.project_id
                }
            )

            # Create X402 request via service
            x402_request = await x402_service.create_request(
                project_id=context.project_id,
                agent_id=did,  # Use DID as agent_id
                task_id=task_id,
                run_id=run_id,
                request_payload=payload,
                signature=signature,
                status=X402RequestStatus.PENDING,
                linked_memory_ids=[],  # Will be populated by BaseTool
                linked_compliance_ids=[],
                metadata={
                    "tool_name": self.name,
                    "correlation_id": context.correlation_id,
                    "submitted_by_agent": context.agent_id
                }
            )

            # Calculate timing
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Format successful result
            result_data = {
                "request_id": x402_request["request_id"],
                "status": x402_request["status"],
                "timestamp": x402_request["timestamp"],
                "agent_id": x402_request["agent_id"],
                "task_id": x402_request["task_id"],
                "run_id": x402_request["run_id"],
                "payload": x402_request["request_payload"],
                "signature": x402_request["signature"]
            }

            logger.info(
                f"X402 request created successfully: {x402_request['request_id']}",
                extra={
                    "request_id": x402_request["request_id"],
                    "agent_id": context.agent_id,
                    "duration_ms": duration_ms
                }
            )

            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "tool_name": self.name,
                    "start_time": start_time.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "duration_ms": duration_ms,
                    "parameters": {
                        "did": did,
                        "task_id": task_id,
                        "run_id": run_id
                    }
                }
            )

        except ValueError as e:
            # Parameter validation errors
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.warning(
                f"X402 request tool parameter validation failed: {str(e)}",
                extra={"agent_id": context.agent_id, "error": str(e)}
            )

            return ToolResult(
                success=False,
                error=f"Parameter validation error: {str(e)}",
                metadata={
                    "tool_name": self.name,
                    "error_type": "VALIDATION_ERROR",
                    "start_time": start_time.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "duration_ms": duration_ms
                }
            )

        except Exception as e:
            # Any other errors during execution
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(
                f"X402 request tool execution failed: {str(e)}",
                extra={"agent_id": context.agent_id, "error": str(e)},
                exc_info=True
            )

            return ToolResult(
                success=False,
                error=f"X402 request failed: {str(e)}",
                metadata={
                    "tool_name": self.name,
                    "error_type": type(e).__name__,
                    "start_time": start_time.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "duration_ms": duration_ms
                }
            )


# Export tool class
__all__ = ["X402RequestTool"]
