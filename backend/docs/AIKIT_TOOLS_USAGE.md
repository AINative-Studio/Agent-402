# AIKit Tools Usage Guide

This guide demonstrates how to use the AIKit tool wrappers for Agent-402.

## Overview

Per PRD Section 8, AIKit standardizes agent tooling with:
- Shared tools across all agents
- Automatic tracing and logging
- Backend-swappable implementations
- Future-ready for IDE, CLI, or web execution

## Available Tools

### 1. x402.request - X402 Signed Request Tool

Submit signed X402 payment requests with automatic DID verification.

#### Parameters

- `did` (required): Agent DID that signs the request (format: `did:ethr:0x...`)
- `signature` (required): ECDSA signature in hex format (format: `0x...`)
- `payload` (required): X402 protocol payment details (object)
- `linked_memory_ids` (optional): List of agent_memory IDs to link
- `linked_compliance_ids` (optional): List of compliance_event IDs to link

#### Usage Example

```python
from tools.x402_request import X402RequestTool
from tools.base import ToolExecutionContext

# Initialize tool
tool = X402RequestTool(
    event_service=event_service,  # optional
    memory_service=memory_service  # optional
)

# Create execution context
context = ToolExecutionContext(
    project_id="proj_123",
    agent_id="did:ethr:0xtransaction001",
    run_id="run_456",
    task_id="task_789"
)

# Execute tool
result = await tool.execute(
    context=context,
    did="did:ethr:0xtransaction001",
    signature="0xsignature123...",
    payload={
        "type": "payment_authorization",
        "amount": "100.00",
        "currency": "USD",
        "recipient": "did:ethr:0xrecipient123",
        "memo": "Payment for services"
    }
)

# Check result
if result.success:
    print(f"X402 Request ID: {result.data['request_id']}")
    print(f"Status: {result.data['status']}")
    print(f"Memory ID: {result.memory_id}")
    print(f"Event ID: {result.event_id}")
else:
    print(f"Error: {result.error}")
```

#### Response Structure

```python
{
    "success": True,
    "data": {
        "request_id": "x402_req_abc123",
        "project_id": "proj_123",
        "agent_id": "did:ethr:0xtransaction001",
        "task_id": "task_789",
        "run_id": "run_456",
        "request_payload": {...},
        "signature": "0xsignature123...",
        "status": "PENDING",
        "timestamp": "2026-01-14T12:34:56.789Z",
        "linked_memory_ids": [],
        "linked_compliance_ids": [],
        "metadata": {
            "signature_verified": True,
            "verification_did": "did:ethr:0xtransaction001"
        }
    },
    "error": None,
    "metadata": {
        "tool_name": "x402.request",
        "request_id": "x402_req_abc123",
        "verification_status": "verified",
        "duration_ms": 45
    },
    "memory_id": "mem_xyz789",
    "event_id": "event_001"
}
```

### 2. market.data - Market Data Tool

Fetch market data for financial instruments (mock implementation).

#### Parameters

- `symbol` (required): Financial instrument symbol (e.g., `BTC-USD`, `AAPL`)
- `data_type` (required): Type of data - `price`, `volume`, `ohlc`, or `stats`
- `timeframe` (optional): Data timeframe - `1m`, `5m`, `1h`, `1d`, `1w` (default: `1d`)

#### Usage Example

```python
from tools.market_data import MarketDataTool
from tools.base import ToolExecutionContext

# Initialize tool
tool = MarketDataTool(
    event_service=event_service,  # optional
    memory_service=memory_service  # optional
)

# Create execution context
context = ToolExecutionContext(
    project_id="proj_123",
    agent_id="did:ethr:0xanalyst001",
    run_id="run_456",
    task_id="task_789"
)

# Fetch price data
result = await tool.execute(
    context=context,
    symbol="BTC-USD",
    data_type="price"
)

if result.success:
    print(f"Price: ${result.data['price']}")
    print(f"Change 24h: {result.data['change_pct_24h']}%")
```

#### Data Types

**Price Data:**
```python
{
    "symbol": "BTC-USD",
    "price": 43750.50,
    "currency": "USD",
    "timestamp": "2026-01-14T12:34:56.789Z",
    "change_24h": 2.5,
    "change_pct_24h": 1.8
}
```

**Volume Data:**
```python
{
    "symbol": "BTC-USD",
    "volume_24h": 1234567890.50,
    "volume_currency": "USD",
    "timestamp": "2026-01-14T12:34:56.789Z"
}
```

**OHLC Data:**
```python
{
    "symbol": "BTC-USD",
    "open": 42855.49,
    "high": 45063.01,
    "low": 41562.98,
    "close": 43750.50,
    "timeframe": "1d",
    "timestamp": "2026-01-14T12:34:56.789Z"
}
```

**Stats Data:**
```python
{
    "symbol": "BTC-USD",
    "price": 43750.50,
    "market_cap": 43750500000000.0,
    "volume_24h": 1234567890.50,
    "circulating_supply": 21000000,
    "all_time_high": 65625.75,
    "all_time_low": 4375.05,
    "timestamp": "2026-01-14T12:34:56.789Z"
}
```

## Tool Registry

Access tools via the global registry:

```python
from tools import tool_registry

# List available tools
tools = tool_registry.list_tools()
print(tools)  # ['x402.request', 'market.data']

# Get tool class
X402Tool = tool_registry.get("x402.request")

# Create tool instance
tool = tool_registry.create_tool(
    "x402.request",
    event_service=event_service,
    memory_service=memory_service
)
```

## Integration with CrewAI Agents

Tools can be registered with CrewAI agents:

```python
from crew import create_transaction_agent
from tools import tool_registry

# Create agent
agent = await create_transaction_agent(project_id="proj_123")

# Get tools from registry
x402_tool = tool_registry.create_tool("x402.request")
market_tool = tool_registry.create_tool("market.data")

# Add tools to agent
agent.tools = [x402_tool, market_tool]
```

## Automatic Logging and Tracing

All tool executions are automatically:

1. **Logged to Events API:** Tool calls are logged as events with start/complete timestamps
2. **Stored in Agent Memory:** Successful executions are stored for replay and audit
3. **Tracked with Correlation IDs:** All related operations share a correlation ID
4. **Measured for Performance:** Execution duration is recorded in metadata

Example log output:
```
INFO: Tool executed: x402.request
  tool_name: x402.request
  agent_id: did:ethr:0xtransaction001
  run_id: run_456
  success: True
  duration_ms: 45
  event_id: event_001
  memory_id: mem_xyz789
```

## Error Handling

Tools return structured error results instead of raising exceptions:

```python
result = await tool.execute(context=context, did="invalid", signature="0x123", payload={})

if not result.success:
    print(f"Error Type: {result.metadata.get('error_type')}")
    print(f"Error Message: {result.error}")
    # Output:
    # Error Type: InvalidDIDError
    # Error Message: Invalid DID format: ...
```

## Testing

Tools are designed for testability:

```python
from unittest.mock import AsyncMock

# Mock services
mock_event_service = AsyncMock()
mock_memory_service = AsyncMock()

# Create tool with mocks
tool = X402RequestTool(
    event_service=mock_event_service,
    memory_service=mock_memory_service
)

# Execute and verify
result = await tool.execute(...)
assert result.success is True
mock_event_service.store_agent_tool_call.assert_called_once()
```

## Future Enhancements

- **Real Market Data API:** Replace mock implementation with real API (Alpha Vantage, Polygon, etc.)
- **Additional Tools:** Add more tool primitives (compliance checks, data validation, etc.)
- **Tool Permissions:** Add role-based access control for tools
- **Tool Versioning:** Support multiple versions of tools
- **Hot Reloading:** Dynamic tool updates without restart
- **Tool Composition:** Chain tools together for complex workflows

## References

- PRD Section 8: AIKit Integration
- Issue #74: AIKit x402.request Tool Wrapper
- Issue #75: DID-based ECDSA Signing and Verification
