"""
BaseTool: Abstract base class for all AIKit tools.

Implements PRD Section 8: AIKit Integration.

Design:
- All tools inherit from BaseTool
- Automatic logging and tracing
- Integration with agent_memory and events API
- Structured input/output schemas
- Error handling and validation

Per PRD Section 10 (Testing & Verification):
- Tools must be testable in isolation
- Deterministic behavior for smoke tests
- Replay-friendly design
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionContext:
    """
    Context for tool execution.

    Provides:
    - Project and agent identification
    - Run and task tracking
    - Correlation ID for event linking
    - Optional user override for testing
    """

    project_id: str
    agent_id: str
    run_id: str
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None  # For API key context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate correlation_id if not provided."""
        if not self.correlation_id:
            self.correlation_id = f"corr_{uuid.uuid4().hex[:16]}"


@dataclass
class ToolResult:
    """
    Structured result from tool execution.

    Fields:
    - success: Whether execution succeeded
    - data: Result data (tool-specific)
    - error: Error message if failed
    - metadata: Additional metadata (timing, versions, etc.)
    - memory_id: ID of stored memory record (if applicable)
    - event_id: ID of logged event (if applicable)
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_id: Optional[str] = None
    event_id: Optional[str] = None


class BaseTool(ABC):
    """
    Abstract base class for all AIKit tools.

    Responsibilities:
    - Define tool schema (name, description, parameters)
    - Execute tool logic
    - Automatically log to events API
    - Automatically store in agent_memory
    - Handle errors gracefully

    Subclasses must implement:
    - name: Tool name (e.g., "x402.request")
    - description: Human-readable description
    - schema: Parameter schema (dict or Pydantic model)
    - _execute: Tool execution logic

    Per PRD Section 8:
    - Shared across all agents
    - Automatically traced and logged
    - Backend-swappable
    """

    def __init__(
        self,
        event_service: Optional[Any] = None,
        memory_service: Optional[Any] = None
    ):
        """
        Initialize the tool.

        Args:
            event_service: EventService instance (for logging)
            memory_service: AgentMemoryService instance (for storage)
        """
        self._event_service = event_service
        self._memory_service = memory_service

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name.

        Format: category.action (e.g., "x402.request", "market.data")

        Returns:
            Tool name
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable tool description.

        Used by agents to understand tool capabilities.

        Returns:
            Tool description
        """
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """
        Tool parameter schema.

        JSON Schema or Pydantic model definition.

        Example:
        {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."},
                "param2": {"type": "number", "description": "..."}
            },
            "required": ["param1"]
        }

        Returns:
            Parameter schema
        """
        pass

    async def execute(
        self,
        context: ToolExecutionContext,
        **parameters: Any
    ) -> ToolResult:
        """
        Execute the tool with automatic logging and tracing.

        Workflow:
        1. Log tool_call_start event
        2. Execute tool logic (_execute)
        3. Store result in agent_memory
        4. Log tool_call_complete event
        5. Return structured result

        Args:
            context: Execution context
            **parameters: Tool-specific parameters

        Returns:
            ToolResult with success/error and data
        """
        start_time = datetime.utcnow()
        event_id = None
        memory_id = None
        result = None

        try:
            # Log tool call start
            if self._event_service:
                try:
                    event = await self._event_service.store_agent_tool_call(
                        agent_id=context.agent_id,
                        tool_name=self.name,
                        parameters=parameters,
                        correlation_id=context.correlation_id
                    )
                    event_id = event.get("id")
                except Exception as e:
                    logger.warning(f"Failed to log tool call start: {e}")

            # Execute tool logic
            result = await self._execute(context, **parameters)

            # Calculate execution time
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            result.metadata["duration_ms"] = duration_ms
            result.metadata["tool_name"] = self.name

            # Store in agent_memory if successful
            if result.success and self._memory_service:
                try:
                    memory = await self._memory_service.store_memory(
                        project_id=context.project_id,
                        agent_id=context.agent_id,
                        run_id=context.run_id,
                        memory_type="tool_execution",
                        content=f"Tool: {self.name}\nParameters: {parameters}\nResult: {result.data}",
                        metadata={
                            "tool_name": self.name,
                            "parameters": parameters,
                            "result": result.data,
                            "task_id": context.task_id,
                            "correlation_id": context.correlation_id,
                            "duration_ms": duration_ms
                        }
                    )
                    memory_id = memory.get("memory_id")
                    result.memory_id = memory_id
                except Exception as e:
                    logger.warning(f"Failed to store tool result in memory: {e}")

            # Log tool call complete
            if self._event_service:
                try:
                    complete_event = await self._event_service.store_agent_tool_call(
                        agent_id=context.agent_id,
                        tool_name=self.name,
                        parameters=parameters,
                        result=result.data,
                        correlation_id=context.correlation_id
                    )
                    if not event_id:
                        event_id = complete_event.get("id")
                    result.event_id = event_id
                except Exception as e:
                    logger.warning(f"Failed to log tool call complete: {e}")

            logger.info(
                f"Tool executed: {self.name}",
                extra={
                    "tool_name": self.name,
                    "agent_id": context.agent_id,
                    "run_id": context.run_id,
                    "success": result.success,
                    "duration_ms": duration_ms,
                    "event_id": event_id,
                    "memory_id": memory_id
                }
            )

            return result

        except Exception as e:
            # Log error
            error_msg = str(e)
            logger.error(
                f"Tool execution failed: {self.name}",
                extra={
                    "tool_name": self.name,
                    "agent_id": context.agent_id,
                    "error": error_msg
                },
                exc_info=True
            )

            # Log error event
            if self._event_service:
                try:
                    await self._event_service.store_agent_error(
                        agent_id=context.agent_id,
                        error_type="TOOL_EXECUTION_ERROR",
                        error_message=f"{self.name}: {error_msg}",
                        context={
                            "tool_name": self.name,
                            "parameters": parameters,
                            "task_id": context.task_id
                        },
                        correlation_id=context.correlation_id
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log tool error: {log_error}")

            # Return error result
            return ToolResult(
                success=False,
                error=error_msg,
                metadata={
                    "tool_name": self.name,
                    "error_type": type(e).__name__
                }
            )

    @abstractmethod
    async def _execute(
        self,
        context: ToolExecutionContext,
        **parameters: Any
    ) -> ToolResult:
        """
        Execute the tool logic.

        Subclasses must implement this method.

        Args:
            context: Execution context
            **parameters: Tool-specific parameters

        Returns:
            ToolResult with success/error and data

        Raises:
            Exception: Tool-specific errors
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tool to dictionary representation.

        Used for:
        - API responses
        - Agent configuration
        - Tool discovery

        Returns:
            Dictionary with tool metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema
        }
