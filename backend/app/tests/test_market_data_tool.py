"""
Test suite for MarketDataTool.

Tests Issue #74: AIKit tool primitives for agent workflows.

Test Coverage:
- Tool instantiation and configuration
- Market data fetching (mock implementation)
- Error handling (invalid parameters, etc.)
- Tool execution context and metadata
- Various data types (price, volume, ohlc, stats)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from tools.base import BaseTool, ToolExecutionContext, ToolResult
from tools.market_data import MarketDataTool


class TestMarketDataToolInstantiation:
    """Test tool instantiation and configuration."""

    def test_tool_class_exists(self):
        """Test that MarketDataTool class exists."""
        assert MarketDataTool is not None
        assert issubclass(MarketDataTool, BaseTool)

    def test_tool_has_correct_name(self):
        """Test that tool has correct name."""
        tool = MarketDataTool()
        assert tool.name == "market.data"

    def test_tool_has_description(self):
        """Test that tool has human-readable description."""
        tool = MarketDataTool()
        assert tool.description is not None
        assert len(tool.description) > 0
        assert "market" in tool.description.lower()

    def test_tool_has_schema(self):
        """Test that tool has parameter schema."""
        tool = MarketDataTool()
        schema = tool.schema
        assert schema is not None
        assert "properties" in schema

        # Required parameters
        assert "symbol" in schema["properties"]
        assert "data_type" in schema["properties"]

    def test_tool_can_be_instantiated_with_services(self):
        """Test tool instantiation with service dependencies."""
        mock_event_service = MagicMock()
        mock_memory_service = MagicMock()

        tool = MarketDataTool(
            event_service=mock_event_service,
            memory_service=mock_memory_service
        )

        assert tool._event_service == mock_event_service
        assert tool._memory_service == mock_memory_service


class TestMarketDataToolExecution:
    """Test tool execution with various scenarios."""

    @pytest.fixture
    def tool(self):
        """Create MarketDataTool instance."""
        return MarketDataTool()

    @pytest.fixture
    def execution_context(self):
        """Create execution context."""
        return ToolExecutionContext(
            project_id="proj_test_001",
            agent_id="did:ethr:0xanalyst001",
            run_id="run_test_001",
            task_id="task_test_001"
        )

    @pytest.mark.asyncio
    async def test_tool_execution_price_data(self, tool, execution_context):
        """Test successful price data fetch."""
        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD",
            data_type="price"
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["symbol"] == "BTC-USD"
        assert "price" in result.data
        assert "timestamp" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_tool_execution_volume_data(self, tool, execution_context):
        """Test successful volume data fetch."""
        result = await tool.execute(
            context=execution_context,
            symbol="ETH-USD",
            data_type="volume"
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["symbol"] == "ETH-USD"
        assert "volume_24h" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_tool_execution_ohlc_data(self, tool, execution_context):
        """Test successful OHLC data fetch."""
        result = await tool.execute(
            context=execution_context,
            symbol="AAPL",
            data_type="ohlc",
            timeframe="1d"
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["symbol"] == "AAPL"
        assert "open" in result.data
        assert "high" in result.data
        assert "low" in result.data
        assert "close" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_tool_execution_stats_data(self, tool, execution_context):
        """Test successful stats data fetch."""
        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD",
            data_type="stats"
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["symbol"] == "BTC-USD"
        assert "market_cap" in result.data
        assert "volume_24h" in result.data
        assert result.error is None

    @pytest.mark.asyncio
    async def test_tool_execution_with_missing_symbol(self, tool, execution_context):
        """Test tool execution fails with missing symbol."""
        result = await tool.execute(
            context=execution_context,
            data_type="price"
        )

        assert result.success is False
        assert result.error is not None
        assert "symbol" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_missing_data_type(self, tool, execution_context):
        """Test tool execution fails with missing data_type."""
        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD"
        )

        assert result.success is False
        assert result.error is not None
        assert "data_type" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_invalid_data_type(self, tool, execution_context):
        """Test tool execution fails with invalid data_type."""
        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD",
            data_type="invalid_type"
        )

        assert result.success is False
        assert result.error is not None
        assert "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_unknown_symbol(self, tool, execution_context):
        """Test tool execution with unknown symbol returns default price."""
        result = await tool.execute(
            context=execution_context,
            symbol="UNKNOWN-SYMBOL",
            data_type="price"
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["symbol"] == "UNKNOWN-SYMBOL"
        assert result.data["price"] == 100.00  # Default price

    @pytest.mark.asyncio
    async def test_tool_execution_stores_in_memory(self, execution_context):
        """Test that successful tool execution stores result in agent_memory."""
        mock_memory_service = AsyncMock()
        mock_memory_service.store_memory = AsyncMock(return_value={
            "memory_id": "mem_test_001",
            "project_id": execution_context.project_id,
            "agent_id": execution_context.agent_id
        })

        tool = MarketDataTool(memory_service=mock_memory_service)

        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD",
            data_type="price"
        )

        assert result.success is True
        assert result.memory_id == "mem_test_001"

        # Verify memory service was called
        mock_memory_service.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_execution_logs_events(self, execution_context):
        """Test that tool execution logs events."""
        mock_event_service = AsyncMock()
        mock_event_service.store_agent_tool_call = AsyncMock(return_value={
            "id": "event_test_001"
        })

        tool = MarketDataTool(event_service=mock_event_service)

        result = await tool.execute(
            context=execution_context,
            symbol="BTC-USD",
            data_type="price"
        )

        assert result.success is True
        assert result.event_id == "event_test_001"

        # Verify event service was called
        assert mock_event_service.store_agent_tool_call.call_count >= 1


class TestMarketDataToolToDict:
    """Test tool serialization for API responses."""

    def test_tool_to_dict_returns_correct_structure(self):
        """Test that to_dict returns correct structure."""
        tool = MarketDataTool()
        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "market.data"
        assert "description" in tool_dict
        assert "schema" in tool_dict
        assert "properties" in tool_dict["schema"]


class TestMarketDataToolMetadata:
    """Test tool metadata and configuration."""

    @pytest.mark.asyncio
    async def test_tool_execution_includes_timing_metadata(self):
        """Test that execution result includes timing information."""
        tool = MarketDataTool()

        context = ToolExecutionContext(
            project_id="proj_timing_001",
            agent_id="did:ethr:0xanalyst001",
            run_id="run_timing_001"
        )

        result = await tool.execute(
            context=context,
            symbol="BTC-USD",
            data_type="price"
        )

        # Check timing metadata
        assert "duration_ms" in result.metadata
        assert isinstance(result.metadata["duration_ms"], int)
        assert result.metadata["duration_ms"] >= 0
        assert result.metadata["tool_name"] == "market.data"

    @pytest.mark.asyncio
    async def test_tool_execution_includes_source_metadata(self):
        """Test that execution result includes source metadata."""
        tool = MarketDataTool()

        context = ToolExecutionContext(
            project_id="proj_meta_001",
            agent_id="did:ethr:0xanalyst001",
            run_id="run_meta_001"
        )

        result = await tool.execute(
            context=context,
            symbol="BTC-USD",
            data_type="price"
        )

        # Check source metadata
        assert result.metadata["source"] == "mock"
        assert result.metadata["symbol"] == "BTC-USD"
        assert result.metadata["data_type"] == "price"


class TestMarketDataToolDeterminism:
    """Test deterministic behavior for testing and replay."""

    @pytest.mark.asyncio
    async def test_price_data_is_deterministic(self):
        """Test that same symbol returns same price."""
        tool = MarketDataTool()

        context = ToolExecutionContext(
            project_id="proj_det_001",
            agent_id="did:ethr:0xanalyst001",
            run_id="run_det_001"
        )

        result1 = await tool.execute(
            context=context,
            symbol="BTC-USD",
            data_type="price"
        )

        result2 = await tool.execute(
            context=context,
            symbol="BTC-USD",
            data_type="price"
        )

        assert result1.success is True
        assert result2.success is True
        assert result1.data["price"] == result2.data["price"]

    @pytest.mark.asyncio
    async def test_different_symbols_have_different_prices(self):
        """Test that different symbols return different prices."""
        tool = MarketDataTool()

        context = ToolExecutionContext(
            project_id="proj_diff_001",
            agent_id="did:ethr:0xanalyst001",
            run_id="run_diff_001"
        )

        btc_result = await tool.execute(
            context=context,
            symbol="BTC-USD",
            data_type="price"
        )

        eth_result = await tool.execute(
            context=context,
            symbol="ETH-USD",
            data_type="price"
        )

        assert btc_result.success is True
        assert eth_result.success is True
        assert btc_result.data["price"] != eth_result.data["price"]
