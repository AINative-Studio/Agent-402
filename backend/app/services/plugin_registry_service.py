"""
Plugin Registry Service — Issues #243, #244

Manages the lifecycle of third-party tool plugins:
validate manifest schema, register/unregister tools in the global registry,
install/uninstall at runtime with ZeroDB persistence.

Built by AINative Dev Team
Refs #243, #244
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

PLUGINS_TABLE = "plugins"

# Required top-level keys in a plugin manifest
_REQUIRED_MANIFEST_KEYS = ("name", "version", "description", "author", "tools")

# Required keys inside each tool definition
_REQUIRED_TOOL_KEYS = ("name", "description", "input_schema", "handler_module")


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class PluginError(Exception):
    """Base class for all plugin-related errors."""


class PluginValidationError(PluginError):
    """Raised when a plugin manifest fails validation."""


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin does not exist."""


class PluginAlreadyExistsError(PluginError):
    """Raised when attempting to register a plugin that is already registered."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PluginRegistryService:
    """
    Manages plugin registration, retrieval, listing, and runtime
    install/uninstall.

    All plugin data is persisted to ZeroDB's ``plugins`` table.
    An in-process registry dict provides fast look-ups during a
    server session.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client
        # In-memory index: plugin_id -> plugin record dict
        self._registry: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def validate_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a plugin manifest against the required schema.

        Returns:
            ``{"valid": True, "errors": []}`` on success, or
            ``{"valid": False, "errors": [...str]}`` on failure.
        """
        errors: List[str] = []

        # Check required top-level fields
        for key in _REQUIRED_MANIFEST_KEYS:
            if key not in manifest:
                errors.append(f"Missing required field: '{key}'")

        # Validate tools list
        tools = manifest.get("tools")
        if tools is not None:
            if not isinstance(tools, list) or len(tools) == 0:
                errors.append("'tools' must be a non-empty list")
            else:
                for idx, tool in enumerate(tools):
                    for tkey in _REQUIRED_TOOL_KEYS:
                        if tkey not in tool:
                            errors.append(
                                f"Tool[{idx}] missing required field: '{tkey}'"
                            )

        return {"valid": len(errors) == 0, "errors": errors}

    async def register_plugin(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate manifest and register the plugin in the global registry.

        Raises:
            PluginValidationError: if the manifest is invalid.
            PluginAlreadyExistsError: if a plugin with the same name+version
                is already registered.

        Returns:
            ``{"plugin_id": str, "status": "active"}``
        """
        validation = await self.validate_manifest(manifest)
        if not validation["valid"]:
            raise PluginValidationError(
                f"Invalid manifest: {validation['errors']}"
            )

        name = manifest["name"]
        version = manifest["version"]

        # Duplicate detection: scan in-memory registry
        for record in self._registry.values():
            if record["name"] == name and record["version"] == version:
                raise PluginAlreadyExistsError(
                    f"Plugin '{name}@{version}' is already registered"
                )

        plugin_id = f"plugin_{uuid.uuid4().hex[:16]}"
        now = datetime.now(tz=timezone.utc).isoformat()

        record = {
            "plugin_id": plugin_id,
            "name": name,
            "version": version,
            "description": manifest.get("description", ""),
            "author": manifest.get("author", ""),
            "tools": manifest.get("tools", []),
            "permissions": manifest.get("permissions", []),
            "capabilities_required": manifest.get("capabilities_required", []),
            "status": "active",
            "project_id": None,
            "created_at": now,
            "updated_at": now,
        }

        # Persist to ZeroDB
        client = self._get_client()
        await client.insert_row(PLUGINS_TABLE, record)

        # Register in-memory
        self._registry[plugin_id] = record

        return {"plugin_id": plugin_id, "status": "active"}

    async def unregister_plugin(self, plugin_id: str) -> None:
        """
        Remove a plugin and all its tools from the registry.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        if plugin_id not in self._registry:
            # Check ZeroDB as a fallback (handles restarts)
            await self._load_plugin_from_db(plugin_id)

        record = self._registry.get(plugin_id)
        if record is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        # Remove from ZeroDB
        client = self._get_client()
        rows = await client.query_rows(
            PLUGINS_TABLE, filter={"plugin_id": plugin_id}
        )
        for row in rows.get("rows", []):
            row_id = row.get("row_id") or row.get("id")
            await client.delete_row(PLUGINS_TABLE, str(row_id))

        # Remove from in-memory registry
        del self._registry[plugin_id]

    async def get_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Retrieve full plugin info and status.

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        if plugin_id not in self._registry:
            await self._load_plugin_from_db(plugin_id)

        record = self._registry.get(plugin_id)
        if record is None:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")

        return dict(record)

    async def list_plugins(
        self, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all registered plugins, optionally filtered by status.

        Args:
            status_filter: if given, only plugins with this status are returned.

        Returns:
            List of plugin info dicts.
        """
        await self._sync_from_db()
        plugins = list(self._registry.values())
        if status_filter is not None:
            plugins = [p for p in plugins if p["status"] == status_filter]
        return plugins

    async def install_plugin(
        self,
        package_ref: str,
        project_id: str,
        manifest: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Install a plugin at runtime.

        Validates the manifest, registers the plugin, and records the
        ``project_id`` association in ZeroDB.

        Args:
            package_ref: e.g. ``"weather-tools@1.0.0"``
            project_id: the project this plugin is installed for
            manifest: the full plugin manifest dict

        Returns:
            ``{"plugin_id": str, "status": "installed", "name": str, "version": str}``
        """
        validation = await self.validate_manifest(manifest)
        if not validation["valid"]:
            raise PluginValidationError(
                f"Invalid manifest: {validation['errors']}"
            )

        # Register (may raise PluginAlreadyExistsError)
        reg_result = await self.register_plugin(manifest)
        plugin_id = reg_result["plugin_id"]

        # Attach project_id to the stored record
        self._registry[plugin_id]["project_id"] = project_id
        self._registry[plugin_id]["status"] = "active"

        # Update ZeroDB row
        client = self._get_client()
        rows = await client.query_rows(
            PLUGINS_TABLE, filter={"plugin_id": plugin_id}
        )
        for row in rows.get("rows", []):
            row_id = row.get("row_id") or row.get("id")
            await client.update_row(
                PLUGINS_TABLE,
                str(row_id),
                {**row, "project_id": project_id, "status": "active"},
            )

        return {
            "plugin_id": plugin_id,
            "status": "installed",
            "name": manifest["name"],
            "version": manifest["version"],
        }

    async def uninstall_plugin(self, plugin_id: str, project_id: str) -> None:
        """
        Uninstall a plugin at runtime, removing it from the registry
        and ZeroDB.

        Args:
            plugin_id: the plugin to uninstall
            project_id: the project context (for authorization)

        Raises:
            PluginNotFoundError: if the plugin does not exist.
        """
        await self.unregister_plugin(plugin_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return the ZeroDB client, importing the singleton if needed."""
        if self._client is None:
            from app.services.zerodb_client import get_zerodb_client
            self._client = get_zerodb_client()
        return self._client

    async def _load_plugin_from_db(self, plugin_id: str) -> None:
        """Load a single plugin from ZeroDB into the in-memory registry."""
        client = self._get_client()
        try:
            result = await client.query_rows(
                PLUGINS_TABLE, filter={"plugin_id": plugin_id}
            )
            for row in result.get("rows", []):
                self._registry[row["plugin_id"]] = row
        except Exception:
            pass  # Table may not exist yet

    async def _sync_from_db(self) -> None:
        """Sync all plugins from ZeroDB into the in-memory registry."""
        client = self._get_client()
        try:
            result = await client.query_rows(PLUGINS_TABLE, limit=1000)
            for row in result.get("rows", []):
                pid = row.get("plugin_id")
                if pid:
                    self._registry[pid] = row
        except Exception:
            pass  # Table may not exist yet
