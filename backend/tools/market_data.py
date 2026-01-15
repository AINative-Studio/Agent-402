"""
MarketDataTool: AIKit tool for fetching placeholder market data.

This is a demonstration tool that provides mock market data for agent demos.
It shows how to create custom AIKit tools following the BaseTool pattern.

Purpose:
- Provide demo/placeholder market data for agent workflows
- Demonstrate tool creation patterns
- Enable agent scenarios without external API dependencies

Tool Integration:
- Compatible with CrewAI agents
- Compatible with other AIKit frameworks
- Follows BaseTool interface
- Automatic tracing and logging

Usage:
    from backend.tools import MarketDataTool
    from backend.tools.base import ToolExecutionContext

    # Initialize tool
    tool = MarketDataTool()

    # Create execution context
    context = ToolExecutionContext(
        project_id="proj_001",
        agent_id="agent_001",
        run_id="run_001"
    )

    # Execute tool
    result = await tool.execute(
        context,
        symbol="BTC-USD",
        data_type="price"
    )

    # Check result
    if result.success:
        print(f"Market data: {result.data}")
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from random import uniform

from tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)


# Mock market data for demonstration
MOCK_PRICES = {
    "BTC-USD": 45000.00,
    "ETH-USD": 2500.00,
    "SOL-USD": 100.00,
    "MATIC-USD": 0.85,
    "USDC-USD": 1.00
}


class MarketDataTool(BaseTool):
    """
    AIKit tool for fetching placeholder market data.

    Provides mock market data for agent demonstrations and testing.
    In production, this would connect to a real market data API.

    Features:
    - Fetch current price for crypto pairs
    - Get mock volume data
    - Simulate market data API responses
    - Automatic logging and tracing

    Tool Parameters:
    - symbol: Trading pair symbol (e.g., "BTC-USD") (required)
    - data_type: Type of data to fetch ("price", "volume") (optional, default: "price")

    Returns:
    - success: Boolean indicating success/failure
    - data: Market data including symbol, value, and timestamp
    - error: Error message if failed
    - metadata: Timing and execution metadata
    """

    def __init__(
        self,
        event_service_instance: Optional[Any] = None,
        memory_service_instance: Optional[Any] = None
    ):
        """
        Initialize MarketDataTool.

        Args:
            event_service_instance: Optional EventService for testing
            memory_service_instance: Optional AgentMemoryService for testing
        """
        from app.services.event_service import event_service
        from app.services.agent_memory_service import agent_memory_service

        super().__init__(
            event_service=event_service_instance or event_service,
            memory_service=memory_service_instance or agent_memory_service
        )

    @property
    def name(self) -> str:
        """
        Tool name for AIKit registration.

        Returns:
            Tool name: "market.data"
        """
        return "market.data"

    @property
    def description(self) -> str:
        """
        Human-readable tool description for agent decision-making.

        Returns:
            Tool description explaining market data capabilities
        """
        return (
            "Fetch current market data for cryptocurrency trading pairs. "
            "Provides price and volume information for supported symbols. "
            "Use this tool when you need market data to make informed decisions "
            "about payments, valuations, or financial calculations. "
            "Supported symbols: BTC-USD, ETH-USD, SOL-USD, MATIC-USD, USDC-USD."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        """
        JSON Schema for tool parameters.

        Returns:
            JSON Schema dictionary
        """
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": (
                        "Trading pair symbol (e.g., 'BTC-USD', 'ETH-USD'). "
                        "Must be in format: BASE-QUOTE"
                    ),
                    "pattern": "^[A-Z]+-[A-Z]+$",
                    "examples": ["BTC-USD", "ETH-USD", "SOL-USD"]
                },
                "data_type": {
                    "type": "string",
                    "description": (
                        "Type of market data to fetch. "
                        "Options: 'price' (current price), 'volume' (24h volume)"
                    ),
                    "enum": ["price", "volume"],
                    "default": "price"
                }
            },
            "required": ["symbol"]
        }

    async def _execute(
        self,
        context: ToolExecutionContext,
        **parameters: Any
    ) -> ToolResult:
        """
        Execute market data tool logic.

        Workflow:
        1. Extract and validate parameters
        2. Fetch mock market data
        3. Format structured response
        4. Return ToolResult with timing metadata

        Args:
            context: Tool execution context
            **parameters: Tool parameters (symbol, data_type)

        Returns:
            ToolResult with market data

        Raises:
            Exception: Any errors during data fetch
        """
        start_time = datetime.utcnow()

        try:
            # Extract parameters
            symbol = parameters.get("symbol")
            data_type = parameters.get("data_type", "price")

            # Validate required parameters
            if not symbol:
                raise ValueError("Parameter 'symbol' is required")

            # Validate symbol format
            if not isinstance(symbol, str) or "-" not in symbol:
                raise ValueError("Parameter 'symbol' must be in format 'BASE-QUOTE' (e.g., 'BTC-USD')")

            symbol_upper = symbol.upper()

            logger.info(
                f"Fetching market data: {symbol_upper} ({data_type})",
                extra={
                    "agent_id": context.agent_id,
                    "symbol": symbol_upper,
                    "data_type": data_type
                }
            )

            # Fetch mock market data
            if data_type == "price":
                # Get price from mock data or generate random
                base_price = MOCK_PRICES.get(symbol_upper, uniform(1.0, 50000.0))
                # Add small random variation (+/- 2%)
                variation = uniform(-0.02, 0.02)
                value = base_price * (1 + variation)

                result_data = {
                    "symbol": symbol_upper,
                    "data_type": "price",
                    "value": round(value, 2),
                    "currency": symbol_upper.split("-")[1],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "mock_data"
                }

            elif data_type == "volume":
                # Generate mock 24h volume
                base_price = MOCK_PRICES.get(symbol_upper, 1000.0)
                # Volume proportional to price
                volume = base_price * uniform(1000, 10000)

                result_data = {
                    "symbol": symbol_upper,
                    "data_type": "volume",
                    "value": round(volume, 2),
                    "period": "24h",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "mock_data"
                }

            else:
                raise ValueError(f"Unsupported data_type: {data_type}. Must be 'price' or 'volume'")

            # Calculate timing
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"Market data fetched successfully: {symbol_upper}",
                extra={
                    "symbol": symbol_upper,
                    "value": result_data["value"],
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
                        "symbol": symbol_upper,
                        "data_type": data_type
                    }
                }
            )

        except ValueError as e:
            # Parameter validation errors
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.warning(
                f"Market data tool parameter validation failed: {str(e)}",
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
                f"Market data tool execution failed: {str(e)}",
                extra={"agent_id": context.agent_id, "error": str(e)},
                exc_info=True
            )

            return ToolResult(
                success=False,
                error=f"Market data fetch failed: {str(e)}",
                metadata={
                    "tool_name": self.name,
                    "error_type": type(e).__name__,
                    "start_time": start_time.isoformat() + "Z",
                    "end_time": end_time.isoformat() + "Z",
                    "duration_ms": duration_ms
                }
            )


# Export tool class
__all__ = ["MarketDataTool"]
