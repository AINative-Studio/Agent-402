"""
MarketDataTool: AIKit tool wrapper for market data fetching.

Implements Issue #74: AIKit tool primitives for agent workflows.

Per PRD Section 8 (AIKit Integration):
- Standardized tool abstraction for market data access
- Automatic event logging and memory storage
- Backend-swappable (mock → real market data API)
- Integration with agent workflows

Architecture:
- Inherits from BaseTool for standardized behavior
- Mock implementation for demo/testing
- Placeholder for future real market data integration
- Automatically logs to events API
- Automatically stores in agent_memory

Usage:
    tool = MarketDataTool(event_service=event_service, memory_service=memory_service)

    context = ToolExecutionContext(
        project_id="proj_123",
        agent_id="did:ethr:0xanalyst001",
        run_id="run_456",
        task_id="task_789"
    )

    result = await tool.execute(
        context=context,
        symbol="BTC-USD",
        data_type="price"
    )

    if result.success:
        print(f"Market data: {result.data}")
    else:
        print(f"Error: {result.error}")
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime
from tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)


class MarketDataTool(BaseTool):
    """
    AIKit tool wrapper for market data fetching.

    Per PRD Section 8:
    - Tool name: "market.data"
    - Parameters: symbol, data_type
    - Runtime: FastAPI backend
    - Backend-swappable (mock → real API)
    - Automatically traced and logged
    - Shared across all agents

    Current Implementation:
    - Mock data for demo/testing
    - Deterministic responses for smoke tests
    - Ready for real API integration

    Future Integration:
    - Connect to real market data API (e.g., Alpha Vantage, Polygon, CoinGecko)
    - Add rate limiting and caching
    - Support multiple data types (price, volume, OHLC, etc.)
    """

    def __init__(
        self,
        event_service: Optional[Any] = None,
        memory_service: Optional[Any] = None
    ):
        """
        Initialize MarketDataTool.

        Args:
            event_service: EventService instance (optional)
            memory_service: AgentMemoryService instance (optional)
        """
        super().__init__(event_service=event_service, memory_service=memory_service)

    @property
    def name(self) -> str:
        """
        Tool name per PRD Section 8.

        Returns:
            "market.data"
        """
        return "market.data"

    @property
    def description(self) -> str:
        """
        Human-readable tool description.

        Returns:
            Tool description for agent use
        """
        return (
            "Fetch market data for financial instruments. "
            "Supports price data, trading volume, and market statistics. "
            "Required parameters: symbol (e.g., 'BTC-USD', 'AAPL'), "
            "data_type (e.g., 'price', 'volume', 'ohlc')."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        """
        Tool parameter schema.

        Returns:
            JSON Schema for tool parameters
        """
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": (
                        "Financial instrument symbol. "
                        "Examples: 'BTC-USD', 'ETH-USD', 'AAPL', 'TSLA'. "
                        "Format: [BASE]-[QUOTE] for crypto, [TICKER] for stocks."
                    ),
                    "pattern": "^[A-Z0-9]+-?[A-Z0-9]*$"
                },
                "data_type": {
                    "type": "string",
                    "description": (
                        "Type of market data to fetch. "
                        "Options: 'price', 'volume', 'ohlc', 'stats'."
                    ),
                    "enum": ["price", "volume", "ohlc", "stats"]
                },
                "timeframe": {
                    "type": "string",
                    "description": (
                        "Optional timeframe for data. "
                        "Options: '1m', '5m', '1h', '1d', '1w'. "
                        "Default: '1d'."
                    ),
                    "enum": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
                }
            },
            "required": ["symbol", "data_type"]
        }

    async def _execute(
        self,
        context: ToolExecutionContext,
        **parameters: Any
    ) -> ToolResult:
        """
        Execute the market data tool.

        Workflow:
        1. Validate required parameters
        2. Fetch market data (mock or real API)
        3. Return structured result

        Args:
            context: Execution context (project, agent, run, task IDs)
            **parameters: Tool parameters (symbol, data_type, timeframe)

        Returns:
            ToolResult with success/error and market data

        Raises:
            No exceptions raised - errors returned in ToolResult
        """
        try:
            # Validate required parameters
            symbol = parameters.get("symbol")
            data_type = parameters.get("data_type")

            if not symbol:
                return ToolResult(
                    success=False,
                    error="Missing required parameter: 'symbol'",
                    metadata={"tool_name": self.name}
                )

            if not data_type:
                return ToolResult(
                    success=False,
                    error="Missing required parameter: 'data_type'",
                    metadata={"tool_name": self.name}
                )

            # Validate data_type
            valid_types = ["price", "volume", "ohlc", "stats"]
            if data_type not in valid_types:
                return ToolResult(
                    success=False,
                    error=f"Invalid data_type. Must be one of: {', '.join(valid_types)}",
                    metadata={"tool_name": self.name}
                )

            # Get optional timeframe
            timeframe = parameters.get("timeframe", "1d")

            # Fetch market data (mock implementation)
            # TODO: Replace with real market data API integration
            market_data = self._fetch_mock_data(symbol, data_type, timeframe)

            logger.info(
                f"Market data fetched: {symbol} ({data_type})",
                extra={
                    "tool_name": self.name,
                    "agent_id": context.agent_id,
                    "symbol": symbol,
                    "data_type": data_type,
                    "timeframe": timeframe
                }
            )

            return ToolResult(
                success=True,
                data=market_data,
                metadata={
                    "tool_name": self.name,
                    "symbol": symbol,
                    "data_type": data_type,
                    "timeframe": timeframe,
                    "source": "mock"  # TODO: Update when real API is integrated
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to fetch market data: {str(e)}",
                extra={
                    "tool_name": self.name,
                    "agent_id": context.agent_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return ToolResult(
                success=False,
                error=f"Failed to fetch market data: {str(e)}",
                metadata={
                    "tool_name": self.name,
                    "error_type": type(e).__name__
                }
            )

    def _fetch_mock_data(
        self,
        symbol: str,
        data_type: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Fetch mock market data.

        Mock data is deterministic for testing and demo purposes.

        Args:
            symbol: Financial instrument symbol
            data_type: Type of data to fetch
            timeframe: Data timeframe

        Returns:
            Mock market data dictionary
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Generate deterministic mock data based on symbol
        base_price = self._get_base_price(symbol)

        if data_type == "price":
            return {
                "symbol": symbol,
                "price": base_price,
                "currency": "USD",
                "timestamp": timestamp,
                "change_24h": 2.5,
                "change_pct_24h": 1.8
            }

        elif data_type == "volume":
            return {
                "symbol": symbol,
                "volume_24h": 1234567890.50,
                "volume_currency": "USD",
                "timestamp": timestamp
            }

        elif data_type == "ohlc":
            return {
                "symbol": symbol,
                "open": base_price * 0.98,
                "high": base_price * 1.03,
                "low": base_price * 0.95,
                "close": base_price,
                "timeframe": timeframe,
                "timestamp": timestamp
            }

        elif data_type == "stats":
            return {
                "symbol": symbol,
                "price": base_price,
                "market_cap": base_price * 1000000000,
                "volume_24h": 1234567890.50,
                "circulating_supply": 21000000,
                "all_time_high": base_price * 1.5,
                "all_time_low": base_price * 0.1,
                "timestamp": timestamp
            }

        else:
            return {
                "symbol": symbol,
                "data_type": data_type,
                "error": "Unsupported data type",
                "timestamp": timestamp
            }

    def _get_base_price(self, symbol: str) -> float:
        """
        Get deterministic base price for a symbol.

        Args:
            symbol: Financial instrument symbol

        Returns:
            Base price (float)
        """
        # Deterministic prices for common symbols
        prices = {
            "BTC-USD": 43750.50,
            "ETH-USD": 2280.25,
            "SOL-USD": 98.75,
            "AAPL": 178.50,
            "TSLA": 245.30,
            "MSFT": 389.75,
            "GOOGL": 140.50
        }

        # Default price for unknown symbols
        return prices.get(symbol, 100.00)
