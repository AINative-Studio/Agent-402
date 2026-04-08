"""
Tests for PluginSandboxService — Issue #243

Isolated async execution with timeout enforcement and permission checks.

BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #243
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


class DescribePluginSandboxServiceExecuteTool:
    """Specification: sandboxed tool execution."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def sandbox(self, registry_service):
        from app.services.plugin_sandbox_service import PluginSandboxService
        return PluginSandboxService(registry=registry_service)

    @pytest.fixture
    def valid_manifest(self):
        return {
            "name": "echo-tools",
            "version": "1.0.0",
            "description": "Echo tool for testing",
            "author": "test@example.com",
            "tools": [
                {
                    "name": "echo",
                    "description": "Echoes input back",
                    "input_schema": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"],
                    },
                    "handler_module": "app.tests.fixtures.echo_tool_handler",
                }
            ],
            "capabilities_required": [],
            "permissions": ["compute:basic"],
        }

    @pytest.mark.asyncio
    async def it_executes_a_registered_tool_and_returns_output(
        self, sandbox, registry_service, valid_manifest
    ):
        """execute_tool calls handler and returns result dict."""
        reg = await registry_service.register_plugin(valid_manifest)
        plugin_id = reg["plugin_id"]

        result = await sandbox.execute_tool(
            plugin_id=plugin_id,
            tool_name="echo",
            input_data={"message": "hello"},
            timeout_seconds=5,
        )
        assert result["success"] is True
        assert "output" in result

    @pytest.mark.asyncio
    async def it_raises_when_plugin_not_found(self, sandbox):
        """execute_tool raises PluginNotFoundError for unknown plugin."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await sandbox.execute_tool(
                plugin_id="plugin_ghost",
                tool_name="echo",
                input_data={},
                timeout_seconds=5,
            )

    @pytest.mark.asyncio
    async def it_raises_when_tool_not_found_in_plugin(
        self, sandbox, registry_service, valid_manifest
    ):
        """execute_tool raises ToolNotFoundError for unknown tool name."""
        from app.services.plugin_sandbox_service import ToolNotFoundError
        reg = await registry_service.register_plugin(valid_manifest)
        plugin_id = reg["plugin_id"]

        with pytest.raises(ToolNotFoundError):
            await sandbox.execute_tool(
                plugin_id=plugin_id,
                tool_name="nonexistent_tool",
                input_data={},
                timeout_seconds=5,
            )

    @pytest.mark.asyncio
    async def it_enforces_timeout_and_raises_timeout_error(
        self, sandbox, registry_service
    ):
        """execute_tool raises ToolTimeoutError when handler exceeds timeout."""
        from app.services.plugin_sandbox_service import ToolTimeoutError
        slow_manifest = {
            "name": "slow-tools",
            "version": "1.0.0",
            "description": "A slow tool",
            "author": "test@example.com",
            "tools": [
                {
                    "name": "slow_op",
                    "description": "Takes forever",
                    "input_schema": {"type": "object", "properties": {}},
                    "handler_module": "app.tests.fixtures.slow_tool_handler",
                }
            ],
            "capabilities_required": [],
            "permissions": [],
        }
        reg = await registry_service.register_plugin(slow_manifest)
        plugin_id = reg["plugin_id"]

        with pytest.raises(ToolTimeoutError):
            await sandbox.execute_tool(
                plugin_id=plugin_id,
                tool_name="slow_op",
                input_data={},
                timeout_seconds=0.01,
            )

    @pytest.mark.asyncio
    async def it_catches_handler_exceptions_and_returns_error_result(
        self, sandbox, registry_service
    ):
        """execute_tool wraps handler exceptions in error result, does not propagate."""
        error_manifest = {
            "name": "error-tools",
            "version": "1.0.0",
            "description": "Raises on every call",
            "author": "test@example.com",
            "tools": [
                {
                    "name": "bad_op",
                    "description": "Always fails",
                    "input_schema": {"type": "object", "properties": {}},
                    "handler_module": "app.tests.fixtures.error_tool_handler",
                }
            ],
            "capabilities_required": [],
            "permissions": [],
        }
        reg = await registry_service.register_plugin(error_manifest)
        plugin_id = reg["plugin_id"]

        result = await sandbox.execute_tool(
            plugin_id=plugin_id,
            tool_name="bad_op",
            input_data={},
            timeout_seconds=5,
        )
        assert result["success"] is False
        assert "error" in result


class DescribePluginSandboxServiceCheckPermissions:
    """Specification: permission verification."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def sandbox(self, registry_service):
        from app.services.plugin_sandbox_service import PluginSandboxService
        return PluginSandboxService(registry=registry_service)

    @pytest.fixture
    def manifest_with_network_permission(self):
        return {
            "name": "net-tools",
            "version": "1.0.0",
            "description": "Network tool",
            "author": "dev@example.com",
            "tools": [
                {
                    "name": "fetch_url",
                    "description": "Fetches a URL",
                    "input_schema": {"type": "object", "properties": {}},
                    "handler_module": "app.tests.fixtures.echo_tool_handler",
                }
            ],
            "capabilities_required": [],
            "permissions": ["network:read"],
        }

    @pytest.mark.asyncio
    async def it_grants_permission_when_plugin_has_it(
        self, sandbox, registry_service, manifest_with_network_permission
    ):
        """check_permissions returns True when plugin has requested permission."""
        reg = await registry_service.register_plugin(manifest_with_network_permission)
        plugin_id = reg["plugin_id"]

        result = await sandbox.check_permissions(
            plugin_id=plugin_id,
            requested_permission="network:read",
        )
        assert result is True

    @pytest.mark.asyncio
    async def it_denies_permission_when_plugin_lacks_it(
        self, sandbox, registry_service, manifest_with_network_permission
    ):
        """check_permissions returns False when plugin lacks requested permission."""
        reg = await registry_service.register_plugin(manifest_with_network_permission)
        plugin_id = reg["plugin_id"]

        result = await sandbox.check_permissions(
            plugin_id=plugin_id,
            requested_permission="filesystem:write",
        )
        assert result is False

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_plugin_on_permission_check(
        self, sandbox
    ):
        """check_permissions raises PluginNotFoundError for unknown plugin."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await sandbox.check_permissions(
                plugin_id="plugin_ghost",
                requested_permission="network:read",
            )
