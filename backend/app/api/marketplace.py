"""
Marketplace API router.
Exposes marketplace publish/browse/search/install endpoints.

Issues #214–#216.

Built by AINative Dev Team
Refs #214, #215, #216
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.schemas.marketplace import (
    BrowseAgentsResponse,
    InstallAgentRequest,
    InstalledAgentResponse,
    MarketplaceAgentResponse,
    PublishAgentRequest,
    SearchAgentsRequest,
    UpdateListingRequest,
)
from app.services.marketplace_service import (
    MarketplaceNotFoundError,
    marketplace_service,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.post("/agents", response_model=Dict[str, Any], status_code=201)
async def publish_agent(body: PublishAgentRequest) -> Dict[str, Any]:
    """Publish an agent configuration to the marketplace."""
    return await marketplace_service.publish_agent(
        agent_config=body.agent_config,
        publisher_did=body.publisher_did,
        pricing=body.pricing.dict(),
        category=body.category.value,
        description=body.description,
        tags=body.tags,
    )


@router.get("/agents/{marketplace_id}", response_model=Dict[str, Any])
async def get_agent(marketplace_id: str) -> Dict[str, Any]:
    """Retrieve a marketplace listing by ID."""
    try:
        return await marketplace_service.get_published_agent(marketplace_id)
    except MarketplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/agents/{marketplace_id}", response_model=Dict[str, Any])
async def update_listing(
    marketplace_id: str, body: UpdateListingRequest
) -> Dict[str, Any]:
    """Update a marketplace listing's pricing/description."""
    try:
        updates = body.dict(exclude_none=True)
        if "pricing" in updates:
            updates["pricing"] = updates["pricing"]  # already a dict via pydantic
        return await marketplace_service.update_listing(marketplace_id, updates)
    except MarketplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/agents/{marketplace_id}", response_model=Dict[str, Any])
async def unpublish_agent(marketplace_id: str) -> Dict[str, Any]:
    """Remove an agent from the marketplace."""
    try:
        return await marketplace_service.unpublish_agent(marketplace_id)
    except MarketplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/browse", response_model=Dict[str, Any])
async def browse_agents(
    category: Optional[str] = Query(None),
    sort_by: str = Query("newest"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Browse all marketplace listings with optional category filter."""
    return await marketplace_service.browse_agents(
        category=category, sort_by=sort_by, limit=limit, offset=offset
    )


@router.post("/search", response_model=Dict[str, Any])
async def search_agents(body: SearchAgentsRequest) -> Dict[str, Any]:
    """Search agents by text query and filters."""
    filters: Dict[str, Any] = {}
    if body.capability:
        filters["capability"] = body.capability
    if body.price_range:
        filters["price_range"] = body.price_range
    if body.min_reputation is not None:
        filters["min_reputation"] = body.min_reputation
    if body.category:
        filters["category"] = body.category.value

    return await marketplace_service.search_agents(query=body.query, filters=filters)


@router.get("/categories", response_model=List[str])
async def get_categories() -> List[str]:
    """Return all available agent categories."""
    return await marketplace_service.get_categories()


@router.post("/install", response_model=Dict[str, Any], status_code=201)
async def install_agent(body: InstallAgentRequest) -> Dict[str, Any]:
    """Install a marketplace agent into a project."""
    try:
        return await marketplace_service.install_agent(
            project_id=body.project_id,
            marketplace_agent_id=body.marketplace_agent_id,
        )
    except MarketplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/agents", response_model=List[Dict[str, Any]])
async def list_installed(project_id: str) -> List[Dict[str, Any]]:
    """List all agents installed in a project."""
    return await marketplace_service.list_installed(project_id)


@router.delete(
    "/projects/{project_id}/agents/{agent_id}", response_model=Dict[str, Any]
)
async def uninstall_agent(project_id: str, agent_id: str) -> Dict[str, Any]:
    """Uninstall an agent from a project."""
    try:
        return await marketplace_service.uninstall_agent(
            project_id=project_id, agent_id=agent_id
        )
    except MarketplaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
