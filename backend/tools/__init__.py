"""
AIKit Tool Abstraction Layer.

Implements PRD Section 8: AIKit Integration.

Purpose:
- Standardize agent tooling across all agents (CrewAI, future frameworks)
- Wrap backend services as AIKit Tool Primitives
- Automatically trace and log all tool invocations
- Store tool results in agent_memory for auditability
- Enable backend-swappable implementations (mock vs real)

Architecture:
- BaseTool: Abstract base class for all tools
- ToolRegistry: Central registry for tool discovery
- X402RequestTool: Core tool for X402 protocol requests
- MarketDataTool: Demo tool for market data fetching

Per PRD Section 8:
- Tools are shared across all agents
- All invocations automatically traced and logged
- Backend-swappable (mock → real fintech API)
- Portable across CLI, server, or future UI
"""

from tools.base import BaseTool, ToolExecutionContext, ToolResult
from tools.x402_request import X402RequestTool
from tools.market_data import MarketDataTool


class ToolRegistry:
    """
    Central registry for tool discovery and management.

    Enables:
    - Dynamic tool registration
    - Tool discovery by name
    - Tool listing for agent configuration
    - Future: Hot-reloading, versioning, permissions
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: dict[str, type[BaseTool]] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register built-in tools."""
        self.register("x402.request", X402RequestTool)
        self.register("market.data", MarketDataTool)

    def register(self, name: str, tool_class: type[BaseTool]):
        """
        Register a tool class.

        Args:
            name: Tool name (e.g., "x402.request")
            tool_class: Tool class (subclass of BaseTool)
        """
        self._tools[name] = tool_class

    def get(self, name: str) -> type[BaseTool] | None:
        """
        Get a tool class by name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def create_tool(self, name: str, **kwargs) -> BaseTool | None:
        """
        Create a tool instance by name.

        Args:
            name: Tool name
            **kwargs: Tool initialization parameters

        Returns:
            Tool instance or None if not found
        """
        tool_class = self.get(name)
        if tool_class:
            return tool_class(**kwargs)
        return None


# Global tool registry instance
tool_registry = ToolRegistry()


# Export public API
__all__ = [
    "BaseTool",
    "ToolExecutionContext",
    "ToolResult",
    "X402RequestTool",
    "MarketDataTool",
    "ToolRegistry",
    "tool_registry",
]
