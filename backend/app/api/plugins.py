"""
Plugin API router — Issues #243, #244, #245

Endpoints:
  POST   /plugins/install
  DELETE /plugins/{id}
  GET    /plugins
  GET    /plugins/{id}
  POST   /plugins/{id}/review
  GET    /plugins/marketplace/search
  POST   /plugins/marketplace/publish

NOTE: This router is NOT registered in main.py — Group C handles that.

Built by AINative Dev Team
Refs #243, #244, #245
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.plugins import (
    PluginInstallRequest,
    PluginPublishRequest,
    PluginReviewRequest,
)
from app.services.plugin_registry_service import (
    PluginNotFoundError,
    PluginValidationError,
    PluginAlreadyExistsError,
)

router = APIRouter(prefix="/plugins", tags=["plugins"])

# ---------------------------------------------------------------------------
# Module-level service singletons.
# Tests inject replacements via ``app.api.plugins._registry_service = ...``.
# ---------------------------------------------------------------------------

_registry_service: Any = None
_sandbox_service: Any = None
_marketplace_service: Any = None


def _get_registry():
    global _registry_service
    if _registry_service is None:
        from app.services.plugin_registry_service import PluginRegistryService
        _registry_service = PluginRegistryService()
    return _registry_service


def _get_sandbox():
    global _sandbox_service
    if _sandbox_service is None:
        from app.services.plugin_sandbox_service import PluginSandboxService
        _sandbox_service = PluginSandboxService(registry=_get_registry())
    return _sandbox_service


def _get_marketplace():
    global _marketplace_service
    if _marketplace_service is None:
        from app.services.plugin_marketplace_service import PluginMarketplaceService
        _marketplace_service = PluginMarketplaceService(registry=_get_registry())
    return _marketplace_service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/install", status_code=201)
async def install_plugin(body: PluginInstallRequest) -> Dict[str, Any]:
    """
    Install a plugin from a package reference.

    Validates the manifest, registers tools, and persists to ZeroDB.
    """
    registry = _get_registry()
    try:
        result = await registry.install_plugin(
            package_ref=body.package_ref,
            project_id=body.project_id,
            manifest=body.manifest.model_dump(),
        )
    except PluginValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PluginAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.delete("/{plugin_id}", status_code=200)
async def uninstall_plugin(
    plugin_id: str,
    project_id: str = Query(..., description="Project the plugin belongs to"),
) -> Dict[str, Any]:
    """
    Uninstall (remove) a plugin and clean up all its tool registrations.
    """
    registry = _get_registry()
    try:
        await registry.uninstall_plugin(plugin_id=plugin_id, project_id=project_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"plugin_id": plugin_id, "status": "uninstalled"}


@router.get("", status_code=200)
async def list_plugins(
    status: Optional[str] = Query(None, description="Filter by status e.g. 'active'"),
) -> List[Dict[str, Any]]:
    """
    List all registered plugins, optionally filtered by status.
    """
    registry = _get_registry()
    return await registry.list_plugins(status_filter=status)


# NOTE: All /marketplace/* routes MUST appear before /{plugin_id} routes
# to prevent FastAPI from treating the literal "marketplace" segment as
# a path parameter value.


@router.get("/marketplace/search", status_code=200)
async def search_marketplace(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
) -> List[Dict[str, Any]]:
    """Search the plugin marketplace."""
    marketplace = _get_marketplace()
    return await marketplace.search_plugins(
        query=query, category=category, sort_by=sort_by
    )


@router.post("/marketplace/publish", status_code=201)
async def publish_plugin(body: PluginPublishRequest) -> Dict[str, Any]:
    """
    Publish a registered plugin to the marketplace with listing metadata.
    """
    marketplace = _get_marketplace()
    try:
        return await marketplace.publish_plugin(
            plugin_id=body.plugin_id,
            listing_metadata=body.listing_metadata.model_dump(),
        )
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{plugin_id}", status_code=200)
async def get_plugin(plugin_id: str) -> Dict[str, Any]:
    """
    Retrieve full info and status for a single plugin.
    """
    registry = _get_registry()
    try:
        return await registry.get_plugin(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{plugin_id}/review", status_code=201)
async def submit_review(
    plugin_id: str, body: PluginReviewRequest
) -> Dict[str, Any]:
    """
    Submit a 1–5 star review for a marketplace plugin.
    """
    marketplace = _get_marketplace()
    try:
        return await marketplace.submit_review(
            plugin_id=plugin_id,
            reviewer_id=body.reviewer_id,
            rating=body.rating,
            comment=body.comment,
        )
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
