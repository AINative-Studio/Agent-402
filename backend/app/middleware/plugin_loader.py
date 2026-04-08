"""
Plugin Loader Middleware — Issue #244

Watches the ZeroDB ``plugins`` table for install/remove events and
dynamically loads or unloads plugin modules without requiring a server
restart.

Built by AINative Dev Team
Refs #244
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from typing import Optional, Any

logger = logging.getLogger(__name__)

_WATCH_INTERVAL_SECONDS = 10
_PLUGINS_TABLE = "plugins"


class PluginLoaderMiddleware:
    """
    Background watcher that polls ZeroDB for plugin install/remove events.

    On detecting an install event, it dynamically imports the plugin module
    and calls the registry to register the tool handlers.

    On detecting a remove event, it unregisters the tools and cleans up
    module references from ``sys.modules``.

    Usage (attach to FastAPI lifespan)::

        loader = PluginLoaderMiddleware(registry=plugin_registry_service)
        asyncio.create_task(loader.start())
    """

    def __init__(
        self,
        registry: Any,
        client: Optional[Any] = None,
        poll_interval: float = _WATCH_INTERVAL_SECONDS,
    ) -> None:
        from app.services.plugin_registry_service import PluginRegistryService
        self._registry: PluginRegistryService = registry
        self._client = client
        self._poll_interval = poll_interval
        self._running = False
        # Track which plugin_ids are already loaded in this session
        self._loaded: set[str] = set()

    async def start(self) -> None:
        """Begin the polling loop. Call via ``asyncio.create_task``."""
        self._running = True
        logger.info("PluginLoaderMiddleware: starting poll loop (interval=%ss)", self._poll_interval)
        while self._running:
            try:
                await self._poll()
            except Exception as exc:
                logger.warning("PluginLoaderMiddleware: poll error: %s", exc)
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        """Signal the polling loop to stop after its current iteration."""
        self._running = False

    async def on_install(self, manifest: dict, project_id: str) -> str:
        """
        Handle a plugin install event directly (bypasses polling).

        Validates the manifest, registers tools, and returns the plugin_id.
        Intended for use by the install API endpoint for immediate feedback.
        """
        result = await self._registry.install_plugin(
            package_ref=f"{manifest.get('name')}@{manifest.get('version')}",
            project_id=project_id,
            manifest=manifest,
        )
        plugin_id = result["plugin_id"]
        self._loaded.add(plugin_id)
        self._import_plugin_modules(manifest)
        logger.info("PluginLoaderMiddleware: installed plugin '%s'", plugin_id)
        return plugin_id

    async def on_remove(self, plugin_id: str, project_id: str) -> None:
        """
        Handle a plugin remove event directly.

        Unregisters tools and cleans up module references.
        """
        try:
            plugin_info = await self._registry.get_plugin(plugin_id)
        except Exception:
            plugin_info = None

        await self._registry.uninstall_plugin(
            plugin_id=plugin_id, project_id=project_id
        )

        if plugin_info:
            self._cleanup_plugin_modules(plugin_info)

        self._loaded.discard(plugin_id)
        logger.info("PluginLoaderMiddleware: removed plugin '%s'", plugin_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _poll(self) -> None:
        """
        Compare the ZeroDB plugins table with the local loaded set and
        reconcile differences.
        """
        client = self._get_client()
        result = await client.query_rows(_PLUGINS_TABLE, limit=1000)
        db_plugins = {
            row["plugin_id"]: row
            for row in result.get("rows", [])
            if "plugin_id" in row
        }

        db_ids = set(db_plugins.keys())

        # New installs
        for plugin_id in db_ids - self._loaded:
            try:
                manifest = db_plugins[plugin_id]
                self._import_plugin_modules(manifest)
                self._loaded.add(plugin_id)
                logger.info("PluginLoaderMiddleware: loaded plugin '%s'", plugin_id)
            except Exception as exc:
                logger.warning(
                    "PluginLoaderMiddleware: failed to load plugin '%s': %s",
                    plugin_id, exc
                )

        # Removed plugins
        for plugin_id in self._loaded - db_ids:
            self._loaded.discard(plugin_id)
            logger.info(
                "PluginLoaderMiddleware: unloaded plugin '%s' (no longer in DB)",
                plugin_id,
            )

    @staticmethod
    def _import_plugin_modules(manifest: dict) -> None:
        """
        Attempt to import all handler modules declared in the manifest's tools.

        Silently skips modules that cannot be found (third-party modules may
        not be installed in the test environment).
        """
        for tool in manifest.get("tools", []):
            handler_path = tool.get("handler_module", "")
            if handler_path and handler_path not in sys.modules:
                try:
                    importlib.import_module(handler_path)
                except ImportError:
                    logger.debug(
                        "PluginLoaderMiddleware: could not import '%s' (may not be installed)",
                        handler_path,
                    )

    @staticmethod
    def _cleanup_plugin_modules(plugin_info: dict) -> None:
        """Remove plugin handler modules from sys.modules on uninstall."""
        for tool in plugin_info.get("tools", []):
            handler_path = tool.get("handler_module", "")
            if handler_path and handler_path in sys.modules:
                del sys.modules[handler_path]
                logger.debug(
                    "PluginLoaderMiddleware: removed module '%s' from sys.modules",
                    handler_path,
                )

    def _get_client(self) -> Any:
        if self._client is None:
            from app.services.zerodb_client import get_zerodb_client
            self._client = get_zerodb_client()
        return self._client
