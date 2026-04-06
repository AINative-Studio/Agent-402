"""
Marketplace API schemas for request/response validation.

Issues #214–#216: Agent Marketplace (publish, browse, install).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentCategory(str, Enum):
    """Categories for marketplace agents."""

    FINANCE = "finance"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"
    DEVELOPMENT = "development"
    RESEARCH = "research"
    AUTOMATION = "automation"
    OTHER = "other"


class MarketplaceSortBy(str, Enum):
    """Sort order for marketplace browsing."""

    NEWEST = "newest"
    OLDEST = "oldest"
    HIGHEST_RATED = "highest_rated"
    LOWEST_PRICE = "lowest_price"
    HIGHEST_PRICE = "highest_price"
    MOST_INSTALLED = "most_installed"


class PricingModel(BaseModel):
    """Pricing configuration for a marketplace agent."""

    price_per_call: float = Field(ge=0.0, description="Price in USDC per API call")
    price_per_hour: Optional[float] = Field(None, ge=0.0, description="Price in USDC per hour")
    free_tier_calls: int = Field(default=0, ge=0, description="Number of free calls per day")


class PublishAgentRequest(BaseModel):
    """Request body for publishing an agent to the marketplace."""

    agent_config: Dict[str, Any] = Field(description="Agent configuration object")
    publisher_did: str = Field(description="Publisher DID (decentralized identifier)")
    pricing: PricingModel
    category: AgentCategory = AgentCategory.OTHER
    description: str = Field(default="", description="Human-readable description")
    tags: List[str] = Field(default_factory=list)


class UpdateListingRequest(BaseModel):
    """Request body for updating a marketplace listing."""

    pricing: Optional[PricingModel] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[AgentCategory] = None


class MarketplaceAgentResponse(BaseModel):
    """Response representing a marketplace agent listing."""

    marketplace_id: str
    agent_id: str
    publisher_did: str
    pricing: Dict[str, Any]
    category: str
    description: str
    tags: List[str]
    reputation_score: float
    install_count: int
    created_at: str
    updated_at: str


class BrowseAgentsResponse(BaseModel):
    """Paginated browse response."""

    items: List[MarketplaceAgentResponse]
    total: int
    limit: int
    offset: int


class SearchAgentsRequest(BaseModel):
    """Request body for searching agents."""

    query: str = Field(description="Free-text search query")
    capability: Optional[str] = None
    price_range: Optional[Dict[str, float]] = Field(
        None, description='{"min": 0.0, "max": 1.0}'
    )
    min_reputation: Optional[float] = Field(None, ge=0.0, le=5.0)
    category: Optional[AgentCategory] = None


class InstallAgentRequest(BaseModel):
    """Request body for installing an agent into a project."""

    project_id: str
    marketplace_agent_id: str


class InstalledAgentResponse(BaseModel):
    """Response representing an installed agent."""

    installation_id: str
    project_id: str
    marketplace_agent_id: str
    agent_id: str
    installed_at: str
    config_snapshot: Dict[str, Any]
