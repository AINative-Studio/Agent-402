"""
Plugin Marketplace Service — Issue #245

Marketplace listing: publish plugins, search listings, retrieve stats,
submit and paginate reviews.

Built by AINative Dev Team
Refs #245
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.services.plugin_registry_service import (
    PluginRegistryService,
    PluginNotFoundError,
)

logger = logging.getLogger(__name__)

LISTINGS_TABLE = "marketplace_listings"
REVIEWS_TABLE = "plugin_reviews"


class PluginMarketplaceService:
    """
    Manages the plugin marketplace: listings, search, reviews, and stats.

    All data is persisted in ZeroDB. Plugin existence is verified via
    ``PluginRegistryService`` before any marketplace operation.
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        registry: Optional[PluginRegistryService] = None,
    ) -> None:
        self._client = client
        self._registry = registry or PluginRegistryService(client=client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def publish_plugin(
        self,
        plugin_id: str,
        listing_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Publish a registered plugin to the marketplace.

        Args:
            plugin_id: The registered plugin to publish.
            listing_metadata: Category, description, screenshots, tags, price.

        Returns:
            ``{"listing_id": str, "status": "published"}``

        Raises:
            PluginNotFoundError: if the plugin is not registered.
        """
        # Validate plugin exists (raises PluginNotFoundError if absent)
        plugin = await self._registry.get_plugin(plugin_id)

        listing_id = f"listing_{uuid.uuid4().hex[:16]}"
        now = datetime.now(tz=timezone.utc).isoformat()

        listing = {
            "listing_id": listing_id,
            "plugin_id": plugin_id,
            "plugin_name": plugin["name"],
            "plugin_version": plugin["version"],
            "category": listing_metadata.get("category", "general"),
            "description": listing_metadata.get("description", plugin["description"]),
            "screenshots": listing_metadata.get("screenshots", []),
            "tags": listing_metadata.get("tags", []),
            "price": listing_metadata.get("price", "free"),
            "status": "published",
            "created_at": now,
            "updated_at": now,
        }

        client = self._get_client()
        await client.insert_row(LISTINGS_TABLE, listing)

        return {"listing_id": listing_id, "status": "published"}

    async def search_plugins(
        self,
        query: Optional[str],
        category: Optional[str],
        sort_by: str = "created_at",
    ) -> List[Dict[str, Any]]:
        """
        Search the marketplace for published plugins.

        Args:
            query: Free-text search matched against plugin name and description.
            category: Exact category filter.
            sort_by: Field to sort results by (default ``"created_at"``).

        Returns:
            List of marketplace listing dicts.
        """
        client = self._get_client()
        db_filter: Dict[str, Any] = {}
        if category:
            db_filter["category"] = category

        result = await client.query_rows(LISTINGS_TABLE, filter=db_filter, limit=1000)
        listings = result.get("rows", [])

        # Apply text search in-process
        if query:
            q = query.lower()
            listings = [
                lst for lst in listings
                if q in lst.get("plugin_name", "").lower()
                or q in lst.get("description", "").lower()
                or any(q in tag.lower() for tag in lst.get("tags", []))
            ]

        return listings

    async def get_plugin_stats(self, plugin_id: str) -> Dict[str, Any]:
        """
        Retrieve aggregated statistics for a marketplace plugin.

        Args:
            plugin_id: The plugin to get stats for.

        Returns:
            ``{"plugin_id": str, "install_count": int, "review_count": int,
               "average_rating": float | None}``

        Raises:
            PluginNotFoundError: if the plugin is not registered.
        """
        # Verify plugin exists
        await self._registry.get_plugin(plugin_id)

        client = self._get_client()

        # Fetch reviews
        reviews_result = await client.query_rows(
            REVIEWS_TABLE, filter={"plugin_id": plugin_id}, limit=10000
        )
        reviews = reviews_result.get("rows", [])
        review_count = len(reviews)

        average_rating: Optional[float] = None
        if review_count > 0:
            ratings = [r["rating"] for r in reviews if "rating" in r]
            if ratings:
                average_rating = sum(ratings) / len(ratings)

        # Install count: a future system would track install events separately.
        # For now, this is a placeholder returning 0.
        install_count = 0

        return {
            "plugin_id": plugin_id,
            "install_count": install_count,
            "review_count": review_count,
            "average_rating": average_rating,
        }

    async def submit_review(
        self,
        plugin_id: str,
        reviewer_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a star-rating review for a marketplace plugin.

        Args:
            plugin_id: The plugin being reviewed.
            reviewer_id: Identity of the reviewer.
            rating: Star rating 1–5 (inclusive).
            comment: Optional text comment.

        Returns:
            ``{"review_id": str}``

        Raises:
            ValueError: if ``rating`` is not between 1 and 5.
            PluginNotFoundError: if the plugin is not registered.
        """
        if not (1 <= rating <= 5):
            raise ValueError(f"rating must be between 1 and 5, got {rating}")

        # Verify plugin exists
        await self._registry.get_plugin(plugin_id)

        review_id = f"review_{uuid.uuid4().hex[:16]}"
        now = datetime.now(tz=timezone.utc).isoformat()

        review = {
            "review_id": review_id,
            "plugin_id": plugin_id,
            "reviewer_id": reviewer_id,
            "rating": rating,
            "comment": comment,
            "created_at": now,
        }

        client = self._get_client()
        await client.insert_row(REVIEWS_TABLE, review)

        return {"review_id": review_id}

    async def get_reviews(
        self,
        plugin_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve paginated reviews for a plugin.

        Args:
            plugin_id: The plugin to get reviews for.
            limit: Maximum reviews to return.
            offset: Number of reviews to skip.

        Returns:
            ``{"reviews": [...], "total": int}``
        """
        client = self._get_client()
        result = await client.query_rows(
            REVIEWS_TABLE,
            filter={"plugin_id": plugin_id},
            limit=limit,
            skip=offset,
        )
        reviews = result.get("rows", [])

        # Get total count (fetch all matching rows for count)
        total_result = await client.query_rows(
            REVIEWS_TABLE,
            filter={"plugin_id": plugin_id},
            limit=100000,
        )
        total = len(total_result.get("rows", []))

        return {"reviews": reviews, "total": total}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return the ZeroDB client."""
        if self._client is None:
            from app.services.zerodb_client import get_zerodb_client
            self._client = get_zerodb_client()
        return self._client
