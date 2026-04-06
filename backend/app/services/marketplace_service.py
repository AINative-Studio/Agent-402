"""
Marketplace Service.
Handles publishing, browsing, searching, and installing agent configurations.

Issues #214 (Publish), #215 (Browse/Search), #216 (Install).

Built by AINative Dev Team
Refs #214, #215, #216
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

MARKETPLACE_LISTINGS_TABLE = "marketplace_listings"
AGENT_INSTALLATIONS_TABLE = "agent_installations"

VALID_CATEGORIES = [
    "finance",
    "analytics",
    "communication",
    "development",
    "research",
    "automation",
    "other",
]


class MarketplaceNotFoundError(APIError):
    """Raised when a marketplace resource is not found."""

    def __init__(self, resource_id: str):
        super().__init__(
            status_code=404,
            error_code="MARKETPLACE_NOT_FOUND",
            detail=f"Marketplace resource not found: {resource_id}",
        )


class MarketplaceService:
    """
    Manages agent marketplace listings and installations.

    All state is persisted to ZeroDB tables:
    - marketplace_listings: published agent configs with pricing/metadata
    - agent_installations: per-project install records
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # ------------------------------------------------------------------
    # Issue #214 — Publish Agent Configurations
    # ------------------------------------------------------------------

    async def publish_agent(
        self,
        agent_config: Dict[str, Any],
        publisher_did: str,
        pricing: Dict[str, Any],
        category: str = "other",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Publish an agent configuration to the marketplace.

        Args:
            agent_config: Agent configuration dict
            publisher_did: Publisher DID string
            pricing: Pricing dict (price_per_call, etc.)
            category: Agent category (defaults to 'other')
            description: Human-readable description
            tags: Optional list of tag strings

        Returns:
            Published listing dict with marketplace_id
        """
        marketplace_id = f"mkt_{uuid.uuid4().hex[:16]}"
        agent_id = agent_config.get("id") or f"agent_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        row = {
            "marketplace_id": marketplace_id,
            "agent_id": agent_id,
            "publisher_did": publisher_did,
            "pricing": pricing,
            "category": category,
            "description": description,
            "tags": tags or [],
            "reputation_score": 0.0,
            "install_count": 0,
            "active": True,
            "agent_config": agent_config,
            "created_at": now,
            "updated_at": now,
        }

        await self.client.insert_row(MARKETPLACE_LISTINGS_TABLE, row)
        logger.info(f"Published agent to marketplace: {marketplace_id}")
        return self._listing_from_row(row)

    async def get_published_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Retrieve a marketplace listing by marketplace_id.

        Args:
            agent_id: The marketplace_id of the listing

        Returns:
            Listing dict

        Raises:
            MarketplaceNotFoundError: If no listing found
        """
        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter={"marketplace_id": agent_id, "active": True},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            raise MarketplaceNotFoundError(agent_id)
        return self._listing_from_row(rows[0])

    async def update_listing(
        self, agent_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a marketplace listing.

        Args:
            agent_id: marketplace_id of the listing
            updates: Dict of fields to update (pricing, description, tags, category)

        Returns:
            Updated listing dict

        Raises:
            MarketplaceNotFoundError: If no listing found
        """
        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter={"marketplace_id": agent_id, "active": True},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            raise MarketplaceNotFoundError(agent_id)

        row = rows[0]
        row_id = row.get("id") or row.get("row_id")
        now = datetime.now(timezone.utc).isoformat()

        updated_row = {**row, **updates, "updated_at": now}
        await self.client.update_row(MARKETPLACE_LISTINGS_TABLE, row_id, updated_row)
        logger.info(f"Updated marketplace listing: {agent_id}")
        return self._listing_from_row(updated_row)

    async def unpublish_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Remove an agent from the marketplace.

        Args:
            agent_id: marketplace_id to unpublish

        Returns:
            Dict with success=True

        Raises:
            MarketplaceNotFoundError: If no listing found
        """
        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter={"marketplace_id": agent_id, "active": True},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            raise MarketplaceNotFoundError(agent_id)

        row = rows[0]
        row_id = row.get("id") or row.get("row_id")
        now = datetime.now(timezone.utc).isoformat()

        await self.client.update_row(
            MARKETPLACE_LISTINGS_TABLE,
            row_id,
            {**row, "active": False, "updated_at": now},
        )
        logger.info(f"Unpublished agent: {agent_id}")
        return {"success": True, "marketplace_id": agent_id}

    # ------------------------------------------------------------------
    # Issue #215 — Browse and Search Agents
    # ------------------------------------------------------------------

    async def browse_agents(
        self,
        category: Optional[str],
        sort_by: str,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        """
        Return a paginated list of active marketplace listings.

        Args:
            category: Optional category filter
            sort_by: Sort key (newest, highest_rated, etc.)
            limit: Page size
            offset: Page offset

        Returns:
            Dict with items, total, limit, offset
        """
        query_filter: Dict[str, Any] = {"active": True}
        if category:
            query_filter["category"] = category

        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter=query_filter,
            limit=10_000,
        )
        all_rows = result.get("rows", [])

        # Sort
        if sort_by == "newest":
            all_rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        elif sort_by == "oldest":
            all_rows.sort(key=lambda r: r.get("created_at", ""))
        elif sort_by == "highest_rated":
            all_rows.sort(key=lambda r: r.get("reputation_score", 0.0), reverse=True)
        elif sort_by == "lowest_price":
            all_rows.sort(
                key=lambda r: (r.get("pricing") or {}).get("price_per_call", 0.0)
            )
        elif sort_by == "highest_price":
            all_rows.sort(
                key=lambda r: (r.get("pricing") or {}).get("price_per_call", 0.0),
                reverse=True,
            )
        elif sort_by == "most_installed":
            all_rows.sort(key=lambda r: r.get("install_count", 0), reverse=True)

        total = len(all_rows)
        page = all_rows[offset : offset + limit]

        return {
            "items": [self._listing_from_row(r) for r in page],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def search_agents(
        self,
        query: str,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Search marketplace listings by text query and optional filters.

        Args:
            query: Free-text search string (matched against name/description)
            filters: Dict with optional keys: capability, price_range, min_reputation, category

        Returns:
            Dict with items list
        """
        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter={"active": True},
            limit=10_000,
        )
        rows = result.get("rows", [])

        query_lower = query.lower()

        def _matches(row: Dict[str, Any]) -> bool:
            name = (row.get("agent_config") or {}).get("name", "").lower()
            description = (row.get("description") or "").lower()
            if query_lower and query_lower not in name and query_lower not in description:
                return False

            # min_reputation filter
            min_rep = filters.get("min_reputation")
            if min_rep is not None:
                if row.get("reputation_score", 0.0) < min_rep:
                    return False

            # price_range filter
            price_range = filters.get("price_range")
            if price_range:
                price = (row.get("pricing") or {}).get("price_per_call", 0.0)
                if price_range.get("min") is not None and price < price_range["min"]:
                    return False
                if price_range.get("max") is not None and price > price_range["max"]:
                    return False

            # category filter
            if filters.get("category"):
                if row.get("category") != filters["category"]:
                    return False

            return True

        matched = [r for r in rows if _matches(r)]
        return {"items": [self._listing_from_row(r) for r in matched], "total": len(matched)}

    async def get_categories(self) -> List[str]:
        """
        Return the list of available agent categories.

        Returns:
            List of category name strings
        """
        return list(VALID_CATEGORIES)

    # ------------------------------------------------------------------
    # Issue #216 — Install Agent into Project
    # ------------------------------------------------------------------

    async def install_agent(
        self,
        project_id: str,
        marketplace_agent_id: str,
    ) -> Dict[str, Any]:
        """
        Clone an agent config into a project.

        Args:
            project_id: Target project identifier
            marketplace_agent_id: Source marketplace listing ID

        Returns:
            Installation record dict

        Raises:
            MarketplaceNotFoundError: If marketplace listing not found
        """
        listing = await self.get_published_agent(marketplace_agent_id)

        installation_id = f"install_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        row = {
            "installation_id": installation_id,
            "project_id": project_id,
            "marketplace_agent_id": marketplace_agent_id,
            "agent_id": listing["agent_id"],
            "config_snapshot": listing.get("agent_config") or {},
            "installed_at": now,
        }

        await self.client.insert_row(AGENT_INSTALLATIONS_TABLE, row)

        # Increment install_count on the listing
        result = await self.client.query_rows(
            MARKETPLACE_LISTINGS_TABLE,
            filter={"marketplace_id": marketplace_agent_id},
            limit=1,
        )
        listing_rows = result.get("rows", [])
        if listing_rows:
            listing_row = listing_rows[0]
            row_id = listing_row.get("id") or listing_row.get("row_id")
            updated = {
                **listing_row,
                "install_count": listing_row.get("install_count", 0) + 1,
            }
            await self.client.update_row(MARKETPLACE_LISTINGS_TABLE, row_id, updated)

        logger.info(
            f"Installed agent {marketplace_agent_id} into project {project_id}"
        )
        return row

    async def list_installed(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all agents installed in a project.

        Args:
            project_id: Project identifier

        Returns:
            List of installation record dicts
        """
        result = await self.client.query_rows(
            AGENT_INSTALLATIONS_TABLE,
            filter={"project_id": project_id},
            limit=1_000,
        )
        return result.get("rows", [])

    async def uninstall_agent(
        self, project_id: str, agent_id: str
    ) -> Dict[str, Any]:
        """
        Remove an agent installation from a project.

        Args:
            project_id: Project identifier
            agent_id: installation_id to remove

        Returns:
            Dict with success=True

        Raises:
            MarketplaceNotFoundError: If installation not found
        """
        result = await self.client.query_rows(
            AGENT_INSTALLATIONS_TABLE,
            filter={"project_id": project_id, "installation_id": agent_id},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            raise MarketplaceNotFoundError(agent_id)

        row = rows[0]
        row_id = row.get("id") or row.get("row_id")
        await self.client.delete_row(AGENT_INSTALLATIONS_TABLE, row_id)
        logger.info(f"Uninstalled agent {agent_id} from project {project_id}")
        return {"success": True, "installation_id": agent_id}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _listing_from_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw ZeroDB row to a clean listing dict."""
        return {
            "marketplace_id": row.get("marketplace_id"),
            "agent_id": row.get("agent_id"),
            "publisher_did": row.get("publisher_did"),
            "pricing": row.get("pricing") or {},
            "category": row.get("category", "other"),
            "description": row.get("description", ""),
            "tags": row.get("tags") or [],
            "reputation_score": row.get("reputation_score", 0.0),
            "install_count": row.get("install_count", 0),
            "active": row.get("active", True),
            "agent_config": row.get("agent_config") or {},
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }


marketplace_service = MarketplaceService()
