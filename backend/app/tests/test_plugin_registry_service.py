"""
Tests for PluginRegistryService — Issues #243, #244

Third-Party Tool Plugin API: register, unregister, get, list, validate,
install (runtime), and uninstall plugins.

BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #243, #244
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


VALID_MANIFEST: Dict[str, Any] = {
    "name": "weather-tools",
    "version": "1.0.0",
    "description": "Provides weather data tools",
    "author": "dev@example.com",
    "tools": [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                },
                "required": ["location"],
            },
            "handler_module": "weather_tools.handlers.get_weather",
        }
    ],
    "capabilities_required": [],
    "permissions": ["network:read"],
}


class DescribePluginRegistryServiceValidateManifest:
    """Specification: manifest validation rules."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_accepts_a_valid_manifest(self, service):
        """validate_manifest returns True for a fully valid manifest."""
        result = await service.validate_manifest(VALID_MANIFEST)
        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def it_rejects_manifest_missing_name(self, service):
        """validate_manifest catches missing 'name' field."""
        bad = {**VALID_MANIFEST}
        del bad["name"]
        result = await service.validate_manifest(bad)
        assert result["valid"] is False
        assert any("name" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def it_rejects_manifest_missing_version(self, service):
        """validate_manifest catches missing 'version' field."""
        bad = {**VALID_MANIFEST}
        del bad["version"]
        result = await service.validate_manifest(bad)
        assert result["valid"] is False
        assert any("version" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def it_rejects_manifest_with_empty_tools_list(self, service):
        """validate_manifest catches empty tools array."""
        bad = {**VALID_MANIFEST, "tools": []}
        result = await service.validate_manifest(bad)
        assert result["valid"] is False
        assert any("tool" in e.lower() for e in result["errors"])

    @pytest.mark.asyncio
    async def it_rejects_tool_missing_handler_module(self, service):
        """validate_manifest catches tool without handler_module."""
        bad_tool = {
            "name": "no_handler",
            "description": "broken tool",
            "input_schema": {"type": "object", "properties": {}},
        }
        bad = {**VALID_MANIFEST, "tools": [bad_tool]}
        result = await service.validate_manifest(bad)
        assert result["valid"] is False
        assert any("handler_module" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def it_rejects_manifest_missing_author(self, service):
        """validate_manifest catches missing 'author' field."""
        bad = {**VALID_MANIFEST}
        del bad["author"]
        result = await service.validate_manifest(bad)
        assert result["valid"] is False
        assert any("author" in e for e in result["errors"])


class DescribePluginRegistryServiceRegisterPlugin:
    """Specification: plugin registration."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_registers_a_valid_plugin_and_returns_plugin_id(self, service):
        """register_plugin returns a plugin_id on success."""
        result = await service.register_plugin(VALID_MANIFEST)
        assert "plugin_id" in result
        assert result["plugin_id"].startswith("plugin_")
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def it_stores_plugin_in_zerodb(self, service, mock_zerodb_client):
        """register_plugin persists plugin data to ZeroDB."""
        await service.register_plugin(VALID_MANIFEST)
        rows = mock_zerodb_client.get_table_data("plugins")
        assert len(rows) == 1
        assert rows[0]["name"] == "weather-tools"

    @pytest.mark.asyncio
    async def it_raises_on_invalid_manifest_during_registration(self, service):
        """register_plugin raises ValueError if manifest is invalid."""
        from app.services.plugin_registry_service import PluginValidationError
        bad = {**VALID_MANIFEST}
        del bad["name"]
        with pytest.raises(PluginValidationError):
            await service.register_plugin(bad)

    @pytest.mark.asyncio
    async def it_prevents_duplicate_registration(self, service):
        """register_plugin raises if same name+version already registered."""
        from app.services.plugin_registry_service import PluginAlreadyExistsError
        await service.register_plugin(VALID_MANIFEST)
        with pytest.raises(PluginAlreadyExistsError):
            await service.register_plugin(VALID_MANIFEST)


class DescribePluginRegistryServiceGetPlugin:
    """Specification: retrieving a single plugin."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_returns_plugin_info_by_id(self, service):
        """get_plugin returns full plugin info including tools."""
        reg = await service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]

        info = await service.get_plugin(plugin_id)
        assert info["plugin_id"] == plugin_id
        assert info["name"] == "weather-tools"
        assert info["status"] == "active"
        assert "tools" in info
        assert len(info["tools"]) == 1

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_plugin(self, service):
        """get_plugin raises PluginNotFoundError for unknown IDs."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await service.get_plugin("plugin_does_not_exist")


class DescribePluginRegistryServiceListPlugins:
    """Specification: listing plugins."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_returns_all_registered_plugins(self, service):
        """list_plugins returns every registered plugin."""
        second_manifest = {
            **VALID_MANIFEST,
            "name": "image-tools",
            "version": "2.0.0",
        }
        await service.register_plugin(VALID_MANIFEST)
        await service.register_plugin(second_manifest)

        result = await service.list_plugins(status_filter=None)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def it_filters_plugins_by_status(self, service):
        """list_plugins filters to only matching-status plugins."""
        await service.register_plugin(VALID_MANIFEST)
        result = await service.list_plugins(status_filter="active")
        assert len(result) == 1
        assert result[0]["status"] == "active"

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_plugins(self, service):
        """list_plugins returns [] when no plugins are registered."""
        result = await service.list_plugins(status_filter=None)
        assert result == []


class DescribePluginRegistryServiceUnregisterPlugin:
    """Specification: unregistering a plugin."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_removes_plugin_and_its_tools(self, service):
        """unregister_plugin removes the plugin record."""
        reg = await service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]

        await service.unregister_plugin(plugin_id)

        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await service.get_plugin(plugin_id)

    @pytest.mark.asyncio
    async def it_raises_not_found_when_unregistering_unknown_plugin(self, service):
        """unregister_plugin raises PluginNotFoundError for unknown IDs."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await service.unregister_plugin("plugin_ghost")


class DescribePluginRegistryServiceInstallUninstall:
    """Specification: runtime install/uninstall (Issue #244)."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.mark.asyncio
    async def it_installs_plugin_from_package_ref(self, service, mock_zerodb_client):
        """install_plugin downloads manifest, validates, registers, stores in ZeroDB."""
        result = await service.install_plugin(
            package_ref="weather-tools@1.0.0",
            project_id="proj_test_001",
            manifest=VALID_MANIFEST,
        )
        assert result["status"] == "installed"
        assert "plugin_id" in result
        rows = mock_zerodb_client.get_table_data("plugins")
        assert any(r.get("project_id") == "proj_test_001" for r in rows)

    @pytest.mark.asyncio
    async def it_uninstalls_plugin_and_removes_from_zerodb(self, service, mock_zerodb_client):
        """uninstall_plugin removes plugin from registry and ZeroDB."""
        install = await service.install_plugin(
            package_ref="weather-tools@1.0.0",
            project_id="proj_test_001",
            manifest=VALID_MANIFEST,
        )
        plugin_id = install["plugin_id"]

        await service.uninstall_plugin(plugin_id=plugin_id, project_id="proj_test_001")

        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await service.get_plugin(plugin_id)
