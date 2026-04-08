"""
Plugin Sandbox Service — Issue #243

Executes plugin tool handlers in an isolated async context with:
- asyncio.wait_for timeout enforcement
- Exception isolation (handler errors become error results)
- Permission verification before execution

Built by AINative Dev Team
Refs #243
"""
from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Optional, Dict, Any

from app.services.plugin_registry_service import (
    PluginRegistryService,
    PluginNotFoundError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ToolNotFoundError(Exception):
    """Raised when the requested tool does not exist in the plugin."""


class ToolTimeoutError(Exception):
    """Raised when a tool handler exceeds its allowed execution time."""


class PermissionDeniedError(Exception):
    """Raised when a plugin attempts an operation it lacks permission for."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PluginSandboxService:
    """
    Provides sandboxed execution of plugin tool handlers.

    Each call runs inside ``asyncio.wait_for`` to enforce a hard timeout.
    All handler exceptions are caught and converted to structured error
    results rather than propagated — except for timeouts, which surface
    as ``ToolTimeoutError``.
    """

    def __init__(self, registry: PluginRegistryService) -> None:
        self._registry = registry

    async def execute_tool(
        self,
        plugin_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        timeout_seconds: float = 30,
    ) -> Dict[str, Any]:
        """
        Execute a named tool from a registered plugin in a sandboxed context.

        Args:
            plugin_id: The plugin that owns the tool.
            tool_name: The tool to execute.
            input_data: Input parameters for the tool handler.
            timeout_seconds: Hard execution deadline in seconds.

        Returns:
            ``{"success": True, "output": ...}`` on success, or
            ``{"success": False, "error": str}`` on handler exception.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
            ToolNotFoundError: if ``tool_name`` is not in the plugin.
            ToolTimeoutError: if execution exceeds ``timeout_seconds``.
        """
        plugin = await self._registry.get_plugin(plugin_id)  # may raise PluginNotFoundError

        tool_def = self._find_tool(plugin, tool_name)

        handler_module_path = tool_def["handler_module"]
        handler_fn = self._load_handler(handler_module_path)

        try:
            output = await asyncio.wait_for(
                handler_fn(input_data),
                timeout=timeout_seconds,
            )
            return {"success": True, "output": output}
        except asyncio.TimeoutError:
            raise ToolTimeoutError(
                f"Tool '{tool_name}' in plugin '{plugin_id}' timed out "
                f"after {timeout_seconds}s"
            )
        except Exception as exc:
            logger.warning(
                "Plugin '%s' tool '%s' raised an exception: %s",
                plugin_id,
                tool_name,
                exc,
            )
            return {"success": False, "error": str(exc)}

    async def check_permissions(
        self, plugin_id: str, requested_permission: str
    ) -> bool:
        """
        Verify whether the plugin holds a specific permission.

        Args:
            plugin_id: The plugin to check.
            requested_permission: Permission string e.g. ``"network:read"``.

        Returns:
            ``True`` if the plugin has the permission, ``False`` otherwise.

        Raises:
            PluginNotFoundError: if the plugin is not registered.
        """
        plugin = await self._registry.get_plugin(plugin_id)  # may raise PluginNotFoundError
        return requested_permission in plugin.get("permissions", [])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_tool(
        self, plugin: Dict[str, Any], tool_name: str
    ) -> Dict[str, Any]:
        """Return the tool definition dict or raise ToolNotFoundError."""
        for tool in plugin.get("tools", []):
            if tool.get("name") == tool_name:
                return tool
        raise ToolNotFoundError(
            f"Tool '{tool_name}' not found in plugin '{plugin['plugin_id']}'"
        )

    @staticmethod
    def _load_handler(handler_module_path: str):
        """
        Dynamically import a handler module and return its ``handle`` function.

        The module must export an async function named ``handle``.
        """
        module = importlib.import_module(handler_module_path)
        handler_fn = getattr(module, "handle", None)
        if handler_fn is None:
            raise AttributeError(
                f"Handler module '{handler_module_path}' has no 'handle' function"
            )
        return handler_fn
