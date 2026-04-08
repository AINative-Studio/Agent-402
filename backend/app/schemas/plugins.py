"""
Plugin system schemas — Issues #243, #244, #245

Pydantic models for request/response validation across the plugin API.

Built by AINative Dev Team
Refs #243, #244, #245
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class PluginTool(BaseModel):
    """A single tool provided by a plugin."""

    name: str = Field(..., description="Tool name (unique within the plugin)")
    description: str = Field(..., description="Human-readable description of what the tool does")
    input_schema: Dict[str, Any] = Field(
        ..., description="JSON Schema describing the tool's input parameters"
    )
    handler_module: str = Field(
        ...,
        description="Dotted Python module path that exports an async handle() function",
    )


class PluginManifest(BaseModel):
    """
    Plugin manifest describing a third-party tool package.

    This is the authoritative definition of a plugin's identity, tools,
    and required capabilities/permissions.
    """

    name: str = Field(..., description="Plugin package name (unique per author)")
    version: str = Field(..., description="Semantic version string (e.g. '1.2.3')")
    description: str = Field(..., description="Short description of the plugin's purpose")
    author: str = Field(..., description="Author identifier (email or handle)")
    tools: List[PluginTool] = Field(
        ..., min_length=1, description="List of tools provided by this plugin"
    )
    capabilities_required: List[str] = Field(
        default_factory=list,
        description="Platform capabilities the plugin depends on",
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Permissions the plugin requests (e.g. 'network:read')",
    )


class PluginInfo(BaseModel):
    """Full plugin record returned by GET /plugins/{id}."""

    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    status: str
    tools: List[Dict[str, Any]]
    permissions: List[str]
    capabilities_required: List[str]
    project_id: Optional[str] = None
    created_at: str
    updated_at: str


class PluginInstallRequest(BaseModel):
    """Request body for POST /plugins/install."""

    package_ref: str = Field(
        ..., description="Package reference string e.g. 'weather-tools@1.0.0'"
    )
    project_id: str = Field(..., description="Project to associate the plugin with")
    manifest: PluginManifest = Field(..., description="Full plugin manifest")


class PluginInstallResult(BaseModel):
    """Response from POST /plugins/install."""

    plugin_id: str
    status: str
    name: str
    version: str


class PluginUninstallResult(BaseModel):
    """Response from DELETE /plugins/{id}."""

    plugin_id: str
    status: str


class PluginReview(BaseModel):
    """A marketplace plugin review."""

    review_id: str
    plugin_id: str
    reviewer_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    created_at: str


class PluginReviewRequest(BaseModel):
    """Request body for POST /plugins/{id}/review."""

    reviewer_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (worst) to 5 (best)")
    comment: Optional[str] = None


class PluginListingMetadata(BaseModel):
    """Marketplace-specific metadata for a published plugin."""

    category: str
    description: str
    screenshots: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    price: str = Field(default="free")


class PluginPublishRequest(BaseModel):
    """Request body for POST /plugins/marketplace/publish."""

    plugin_id: str
    listing_metadata: PluginListingMetadata


class PluginStats(BaseModel):
    """Aggregated statistics for a marketplace plugin."""

    plugin_id: str
    install_count: int
    review_count: int
    average_rating: Optional[float] = None
