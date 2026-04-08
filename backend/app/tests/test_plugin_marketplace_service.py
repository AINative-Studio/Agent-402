"""
Tests for PluginMarketplaceService — Issue #245

Marketplace listing: publish, search, stats, reviews.

BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #245
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


VALID_MANIFEST: Dict[str, Any] = {
    "name": "data-tools",
    "version": "1.0.0",
    "description": "Data processing tools",
    "author": "dev@example.com",
    "tools": [
        {
            "name": "parse_csv",
            "description": "Parse CSV files",
            "input_schema": {"type": "object", "properties": {}},
            "handler_module": "data_tools.handlers.parse_csv",
        }
    ],
    "capabilities_required": [],
    "permissions": [],
}

VALID_LISTING_METADATA: Dict[str, Any] = {
    "category": "data-processing",
    "description": "A comprehensive suite of data tools",
    "screenshots": ["https://example.com/screen1.png"],
    "tags": ["csv", "data", "parsing"],
    "price": "free",
}


class DescribePluginMarketplaceServicePublishPlugin:
    """Specification: publishing a plugin to the marketplace."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def marketplace(self, mock_zerodb_client, registry_service):
        from app.services.plugin_marketplace_service import PluginMarketplaceService
        return PluginMarketplaceService(
            client=mock_zerodb_client, registry=registry_service
        )

    @pytest.mark.asyncio
    async def it_publishes_plugin_and_returns_listing_id(
        self, marketplace, registry_service
    ):
        """publish_plugin creates a marketplace listing and returns listing_id."""
        reg = await registry_service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]

        result = await marketplace.publish_plugin(
            plugin_id=plugin_id,
            listing_metadata=VALID_LISTING_METADATA,
        )
        assert "listing_id" in result
        assert result["listing_id"].startswith("listing_")
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def it_stores_listing_in_zerodb(
        self, marketplace, registry_service, mock_zerodb_client
    ):
        """publish_plugin persists listing to the marketplace_listings table."""
        reg = await registry_service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]

        await marketplace.publish_plugin(
            plugin_id=plugin_id,
            listing_metadata=VALID_LISTING_METADATA,
        )
        rows = mock_zerodb_client.get_table_data("marketplace_listings")
        assert len(rows) == 1
        assert rows[0]["plugin_id"] == plugin_id

    @pytest.mark.asyncio
    async def it_raises_when_publishing_unknown_plugin(self, marketplace):
        """publish_plugin raises PluginNotFoundError for unregistered plugins."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await marketplace.publish_plugin(
                plugin_id="plugin_ghost",
                listing_metadata=VALID_LISTING_METADATA,
            )


class DescribePluginMarketplaceServiceSearchPlugins:
    """Specification: searching the marketplace."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def marketplace(self, mock_zerodb_client, registry_service):
        from app.services.plugin_marketplace_service import PluginMarketplaceService
        return PluginMarketplaceService(
            client=mock_zerodb_client, registry=registry_service
        )

    @pytest.fixture
    async def two_published_plugins(self, marketplace, registry_service):
        """Seed two published plugins."""
        manifests = [
            {**VALID_MANIFEST, "name": "csv-tools", "version": "1.0.0"},
            {
                **VALID_MANIFEST,
                "name": "image-tools",
                "version": "1.0.0",
                "description": "Image processing tools",
            },
        ]
        listing_metadata_list = [
            {**VALID_LISTING_METADATA, "category": "data-processing"},
            {**VALID_LISTING_METADATA, "category": "media"},
        ]
        ids = []
        for manifest, meta in zip(manifests, listing_metadata_list):
            reg = await registry_service.register_plugin(manifest)
            pub = await marketplace.publish_plugin(
                plugin_id=reg["plugin_id"], listing_metadata=meta
            )
            ids.append(pub["listing_id"])
        return ids

    @pytest.mark.asyncio
    async def it_returns_all_listings_when_no_filters(
        self, marketplace, two_published_plugins
    ):
        """search_plugins with no filters returns all published listings."""
        result = await marketplace.search_plugins(
            query=None, category=None, sort_by="created_at"
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def it_filters_by_category(self, marketplace, two_published_plugins):
        """search_plugins with category filter returns only matching listings."""
        result = await marketplace.search_plugins(
            query=None, category="media", sort_by="created_at"
        )
        assert len(result) == 1
        assert result[0]["category"] == "media"

    @pytest.mark.asyncio
    async def it_filters_by_text_query(self, marketplace, two_published_plugins):
        """search_plugins with query matches against name and description."""
        result = await marketplace.search_plugins(
            query="image", category=None, sort_by="created_at"
        )
        assert len(result) == 1
        assert "image" in result[0]["plugin_name"].lower() or "image" in result[0].get("description", "").lower()

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_match(
        self, marketplace, two_published_plugins
    ):
        """search_plugins returns [] when nothing matches query."""
        result = await marketplace.search_plugins(
            query="xyzabcnonexistent", category=None, sort_by="created_at"
        )
        assert result == []


class DescribePluginMarketplaceServiceStats:
    """Specification: plugin statistics."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def marketplace(self, mock_zerodb_client, registry_service):
        from app.services.plugin_marketplace_service import PluginMarketplaceService
        return PluginMarketplaceService(
            client=mock_zerodb_client, registry=registry_service
        )

    @pytest.mark.asyncio
    async def it_returns_zero_stats_for_new_listing(
        self, marketplace, registry_service
    ):
        """get_plugin_stats returns install_count=0 and review_count=0 initially."""
        reg = await registry_service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]
        await marketplace.publish_plugin(
            plugin_id=plugin_id, listing_metadata=VALID_LISTING_METADATA
        )

        stats = await marketplace.get_plugin_stats(plugin_id=plugin_id)
        assert stats["install_count"] == 0
        assert stats["review_count"] == 0
        assert stats["average_rating"] is None

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_plugin(self, marketplace):
        """get_plugin_stats raises PluginNotFoundError for unregistered plugin_id."""
        from app.services.plugin_registry_service import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            await marketplace.get_plugin_stats(plugin_id="plugin_ghost")


class DescribePluginMarketplaceServiceReviews:
    """Specification: plugin review submission and retrieval."""

    @pytest.fixture
    def registry_service(self, mock_zerodb_client):
        from app.services.plugin_registry_service import PluginRegistryService
        return PluginRegistryService(client=mock_zerodb_client)

    @pytest.fixture
    def marketplace(self, mock_zerodb_client, registry_service):
        from app.services.plugin_marketplace_service import PluginMarketplaceService
        return PluginMarketplaceService(
            client=mock_zerodb_client, registry=registry_service
        )

    @pytest.fixture
    async def published_plugin_id(self, marketplace, registry_service):
        reg = await registry_service.register_plugin(VALID_MANIFEST)
        plugin_id = reg["plugin_id"]
        await marketplace.publish_plugin(
            plugin_id=plugin_id, listing_metadata=VALID_LISTING_METADATA
        )
        return plugin_id

    @pytest.mark.asyncio
    async def it_accepts_valid_review_and_returns_review_id(
        self, marketplace, published_plugin_id
    ):
        """submit_review creates review record and returns review_id."""
        result = await marketplace.submit_review(
            plugin_id=published_plugin_id,
            reviewer_id="user_abc",
            rating=5,
            comment="Excellent plugin!",
        )
        assert "review_id" in result
        assert result["review_id"].startswith("review_")

    @pytest.mark.asyncio
    async def it_rejects_rating_below_1(
        self, marketplace, published_plugin_id
    ):
        """submit_review raises ValueError for rating < 1."""
        with pytest.raises(ValueError, match="rating"):
            await marketplace.submit_review(
                plugin_id=published_plugin_id,
                reviewer_id="user_abc",
                rating=0,
                comment="Bad",
            )

    @pytest.mark.asyncio
    async def it_rejects_rating_above_5(
        self, marketplace, published_plugin_id
    ):
        """submit_review raises ValueError for rating > 5."""
        with pytest.raises(ValueError, match="rating"):
            await marketplace.submit_review(
                plugin_id=published_plugin_id,
                reviewer_id="user_abc",
                rating=6,
                comment="Too good",
            )

    @pytest.mark.asyncio
    async def it_returns_paginated_reviews(
        self, marketplace, published_plugin_id
    ):
        """get_reviews returns paginated list of reviews."""
        for i in range(3):
            await marketplace.submit_review(
                plugin_id=published_plugin_id,
                reviewer_id=f"user_{i}",
                rating=4,
                comment=f"Review {i}",
            )

        result = await marketplace.get_reviews(
            plugin_id=published_plugin_id, limit=2, offset=0
        )
        assert "reviews" in result
        assert len(result["reviews"]) == 2
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def it_updates_average_rating_after_review(
        self, marketplace, published_plugin_id
    ):
        """get_plugin_stats reflects average_rating after reviews submitted."""
        await marketplace.submit_review(
            plugin_id=published_plugin_id,
            reviewer_id="user_1",
            rating=4,
            comment="Good",
        )
        await marketplace.submit_review(
            plugin_id=published_plugin_id,
            reviewer_id="user_2",
            rating=2,
            comment="OK",
        )

        stats = await marketplace.get_plugin_stats(plugin_id=published_plugin_id)
        assert stats["review_count"] == 2
        assert stats["average_rating"] == pytest.approx(3.0)
