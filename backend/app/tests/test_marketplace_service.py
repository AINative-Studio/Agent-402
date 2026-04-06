"""
Tests for MarketplaceService.
Issues #214 (Publish), #215 (Browse/Search), #216 (Install).

TDD Approach: Tests written FIRST, then implementation — Red-Green-Refactor.
BDD-style: class Describe* / def it_*

Coverage targets:
- publish_agent / get_published_agent / update_listing / unpublish_agent
- browse_agents / search_agents / get_categories
- install_agent / list_installed / uninstall_agent
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Issue #214 — Publish Agent Configurations
# ---------------------------------------------------------------------------


class DescribeMarketplaceServiceInit:
    """MarketplaceService initializes correctly."""

    def it_initializes_with_lazy_zerodb_client(self):
        """Service starts with no client; client is created on first use."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService()
        assert svc._client is None

    def it_accepts_injected_client(self):
        """Service accepts a pre-built client for test isolation."""
        from app.services.marketplace_service import MarketplaceService

        mock = MagicMock()
        svc = MarketplaceService(client=mock)
        assert svc.client is mock


class DescribePublishAgent:
    """Tests for publish_agent — Issue #214."""

    @pytest.mark.asyncio
    async def it_publishes_agent_and_returns_listing(self, mock_zerodb_client):
        """publish_agent stores the listing and returns a dict with marketplace_id."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        agent_config = {"name": "FinanceBot", "model": "gpt-4"}
        pricing = {"price_per_call": 0.01, "free_tier_calls": 10}

        result = await svc.publish_agent(
            agent_config=agent_config,
            publisher_did="did:hedera:testnet:pub1",
            pricing=pricing,
        )

        assert "marketplace_id" in result
        assert result["publisher_did"] == "did:hedera:testnet:pub1"
        assert result["pricing"] == pricing

    @pytest.mark.asyncio
    async def it_stores_listing_in_zerodb(self, mock_zerodb_client):
        """publish_agent inserts exactly one row into the marketplace_listings table."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        await svc.publish_agent(
            agent_config={"name": "Bot"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.05},
        )

        rows = mock_zerodb_client.get_table_data("marketplace_listings")
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def it_generates_unique_marketplace_ids(self, mock_zerodb_client):
        """Two publish_agent calls yield different marketplace_ids."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        r1 = await svc.publish_agent(
            agent_config={"name": "BotA"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        r2 = await svc.publish_agent(
            agent_config={"name": "BotB"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.02},
        )

        assert r1["marketplace_id"] != r2["marketplace_id"]


class DescribeGetPublishedAgent:
    """Tests for get_published_agent — Issue #214."""

    @pytest.mark.asyncio
    async def it_returns_listing_by_marketplace_id(self, mock_zerodb_client):
        """get_published_agent retrieves a previously published listing."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        published = await svc.publish_agent(
            agent_config={"name": "BotX"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        mid = published["marketplace_id"]

        fetched = await svc.get_published_agent(mid)

        assert fetched["marketplace_id"] == mid
        assert fetched["publisher_did"] == "did:hedera:testnet:pub1"

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_id(self, mock_zerodb_client):
        """get_published_agent raises MarketplaceNotFoundError for missing id."""
        from app.services.marketplace_service import (
            MarketplaceService,
            MarketplaceNotFoundError,
        )

        svc = MarketplaceService(client=mock_zerodb_client)

        with pytest.raises(MarketplaceNotFoundError):
            await svc.get_published_agent("nonexistent_id")


class DescribeUpdateListing:
    """Tests for update_listing — Issue #214."""

    @pytest.mark.asyncio
    async def it_updates_pricing_on_existing_listing(self, mock_zerodb_client):
        """update_listing changes pricing and returns the updated record."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        published = await svc.publish_agent(
            agent_config={"name": "BotY"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        mid = published["marketplace_id"]

        updated = await svc.update_listing(
            mid, {"pricing": {"price_per_call": 0.05}}
        )

        assert updated["pricing"]["price_per_call"] == 0.05

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_id(self, mock_zerodb_client):
        """update_listing raises MarketplaceNotFoundError for missing id."""
        from app.services.marketplace_service import (
            MarketplaceService,
            MarketplaceNotFoundError,
        )

        svc = MarketplaceService(client=mock_zerodb_client)

        with pytest.raises(MarketplaceNotFoundError):
            await svc.update_listing("nope", {"pricing": {}})


class DescribeUnpublishAgent:
    """Tests for unpublish_agent — Issue #214."""

    @pytest.mark.asyncio
    async def it_removes_listing_from_marketplace(self, mock_zerodb_client):
        """unpublish_agent deletes the row and returns success."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        published = await svc.publish_agent(
            agent_config={"name": "BotZ"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        mid = published["marketplace_id"]

        result = await svc.unpublish_agent(mid)

        assert result["success"] is True
        rows = mock_zerodb_client.get_table_data("marketplace_listings")
        assert all(r.get("marketplace_id") != mid for r in rows)

    @pytest.mark.asyncio
    async def it_raises_not_found_when_already_unpublished(self, mock_zerodb_client):
        """unpublish_agent raises MarketplaceNotFoundError for unknown id."""
        from app.services.marketplace_service import (
            MarketplaceService,
            MarketplaceNotFoundError,
        )

        svc = MarketplaceService(client=mock_zerodb_client)

        with pytest.raises(MarketplaceNotFoundError):
            await svc.unpublish_agent("ghost_id")


# ---------------------------------------------------------------------------
# Issue #215 — Browse and Search Agents
# ---------------------------------------------------------------------------


class DescribeBrowseAgents:
    """Tests for browse_agents — Issue #215."""

    @pytest.mark.asyncio
    async def it_returns_all_published_agents_when_no_category(
        self, mock_zerodb_client
    ):
        """browse_agents returns all listings when category is None."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        for i in range(3):
            await svc.publish_agent(
                agent_config={"name": f"Bot{i}"},
                publisher_did="did:hedera:testnet:pub1",
                pricing={"price_per_call": 0.01 * (i + 1)},
            )

        result = await svc.browse_agents(
            category=None, sort_by="newest", limit=10, offset=0
        )

        assert result["total"] == 3
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def it_respects_pagination_limit_and_offset(self, mock_zerodb_client):
        """browse_agents returns correct page based on limit/offset."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        for i in range(5):
            await svc.publish_agent(
                agent_config={"name": f"Bot{i}"},
                publisher_did="did:hedera:testnet:pub1",
                pricing={"price_per_call": 0.01},
            )

        page1 = await svc.browse_agents(category=None, sort_by="newest", limit=2, offset=0)
        page2 = await svc.browse_agents(category=None, sort_by="newest", limit=2, offset=2)

        assert len(page1["items"]) == 2
        assert len(page2["items"]) == 2
        ids1 = {a["marketplace_id"] for a in page1["items"]}
        ids2 = {a["marketplace_id"] for a in page2["items"]}
        assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def it_filters_by_category(self, mock_zerodb_client):
        """browse_agents filters results by category."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        await svc.publish_agent(
            agent_config={"name": "FinBot"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
            category="finance",
        )
        await svc.publish_agent(
            agent_config={"name": "DevBot"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.02},
            category="development",
        )

        result = await svc.browse_agents(
            category="finance", sort_by="newest", limit=10, offset=0
        )

        assert result["total"] == 1
        assert result["items"][0]["category"] == "finance"


class DescribeSearchAgents:
    """Tests for search_agents — Issue #215."""

    @pytest.mark.asyncio
    async def it_returns_results_matching_query(self, mock_zerodb_client):
        """search_agents returns listings whose description matches query."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        await svc.publish_agent(
            agent_config={"name": "PaymentBot"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
            description="Handles payment processing and invoicing",
        )
        await svc.publish_agent(
            agent_config={"name": "WeatherBot"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
            description="Provides weather forecasting",
        )

        result = await svc.search_agents(query="payment", filters={})

        assert any("payment" in a["description"].lower() for a in result["items"])

    @pytest.mark.asyncio
    async def it_filters_by_min_reputation(self, mock_zerodb_client):
        """search_agents excludes listings below min_reputation threshold."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        # Manually insert a row with known reputation
        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        mock_zerodb_client.data.setdefault("marketplace_listings", [])
        mock_zerodb_client.data["marketplace_listings"].append(
            {
                "marketplace_id": "mkt_low",
                "agent_id": "agent_low",
                "publisher_did": "did:hedera:testnet:p1",
                "pricing": {},
                "category": "other",
                "description": "low rep agent",
                "tags": [],
                "reputation_score": 1.5,
                "install_count": 0,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        mock_zerodb_client.data["marketplace_listings"].append(
            {
                "marketplace_id": "mkt_high",
                "agent_id": "agent_high",
                "publisher_did": "did:hedera:testnet:p1",
                "pricing": {},
                "category": "other",
                "description": "high rep agent",
                "tags": [],
                "reputation_score": 4.5,
                "install_count": 0,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        )

        result = await svc.search_agents(query="agent", filters={"min_reputation": 3.0})

        mids = [a["marketplace_id"] for a in result["items"]]
        assert "mkt_high" in mids
        assert "mkt_low" not in mids

    @pytest.mark.asyncio
    async def it_filters_by_price_range(self, mock_zerodb_client):
        """search_agents excludes listings outside price_range."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        mock_zerodb_client.data.setdefault("marketplace_listings", [])
        mock_zerodb_client.data["marketplace_listings"].append(
            {
                "marketplace_id": "mkt_cheap",
                "agent_id": "a1",
                "publisher_did": "did:hedera:testnet:p1",
                "pricing": {"price_per_call": 0.001},
                "category": "other",
                "description": "cheap agent",
                "tags": [],
                "reputation_score": 3.0,
                "install_count": 0,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        mock_zerodb_client.data["marketplace_listings"].append(
            {
                "marketplace_id": "mkt_expensive",
                "agent_id": "a2",
                "publisher_did": "did:hedera:testnet:p1",
                "pricing": {"price_per_call": 10.0},
                "category": "other",
                "description": "expensive agent",
                "tags": [],
                "reputation_score": 3.0,
                "install_count": 0,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        )

        result = await svc.search_agents(
            query="agent",
            filters={"price_range": {"min": 0.0, "max": 1.0}},
        )

        mids = [a["marketplace_id"] for a in result["items"]]
        assert "mkt_cheap" in mids
        assert "mkt_expensive" not in mids


class DescribeGetCategories:
    """Tests for get_categories — Issue #215."""

    @pytest.mark.asyncio
    async def it_returns_list_of_category_strings(self, mock_zerodb_client):
        """get_categories returns a non-empty list of category names."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        categories = await svc.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "finance" in categories


# ---------------------------------------------------------------------------
# Issue #216 — Install Agent into Project
# ---------------------------------------------------------------------------


class DescribeInstallAgent:
    """Tests for install_agent — Issue #216."""

    @pytest.mark.asyncio
    async def it_clones_agent_config_into_project(self, mock_zerodb_client):
        """install_agent creates an installation record in agent_installations."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        published = await svc.publish_agent(
            agent_config={"name": "InstallMe"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        mid = published["marketplace_id"]

        result = await svc.install_agent(
            project_id="proj_123", marketplace_agent_id=mid
        )

        assert "installation_id" in result
        assert result["project_id"] == "proj_123"
        assert result["marketplace_agent_id"] == mid
        rows = mock_zerodb_client.get_table_data("agent_installations")
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_marketplace_agent(
        self, mock_zerodb_client
    ):
        """install_agent raises MarketplaceNotFoundError for unknown agent."""
        from app.services.marketplace_service import (
            MarketplaceService,
            MarketplaceNotFoundError,
        )

        svc = MarketplaceService(client=mock_zerodb_client)

        with pytest.raises(MarketplaceNotFoundError):
            await svc.install_agent(
                project_id="proj_123", marketplace_agent_id="ghost_id"
            )


class DescribeListInstalled:
    """Tests for list_installed — Issue #216."""

    @pytest.mark.asyncio
    async def it_lists_agents_installed_in_project(self, mock_zerodb_client):
        """list_installed returns all installations for a project."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        for i in range(2):
            pub = await svc.publish_agent(
                agent_config={"name": f"Bot{i}"},
                publisher_did="did:hedera:testnet:pub1",
                pricing={"price_per_call": 0.01},
            )
            await svc.install_agent(
                project_id="proj_abc", marketplace_agent_id=pub["marketplace_id"]
            )

        installed = await svc.list_installed("proj_abc")

        assert len(installed) == 2
        assert all(item["project_id"] == "proj_abc" for item in installed)

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_project_with_no_installs(
        self, mock_zerodb_client
    ):
        """list_installed returns [] when project has no agents installed."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        result = await svc.list_installed("empty_project")

        assert result == []


class DescribeUninstallAgent:
    """Tests for uninstall_agent — Issue #216."""

    @pytest.mark.asyncio
    async def it_removes_installation_record(self, mock_zerodb_client):
        """uninstall_agent deletes the installation and returns success."""
        from app.services.marketplace_service import MarketplaceService

        svc = MarketplaceService(client=mock_zerodb_client)
        pub = await svc.publish_agent(
            agent_config={"name": "RemoveMe"},
            publisher_did="did:hedera:testnet:pub1",
            pricing={"price_per_call": 0.01},
        )
        install = await svc.install_agent(
            project_id="proj_del", marketplace_agent_id=pub["marketplace_id"]
        )

        result = await svc.uninstall_agent(
            project_id="proj_del", agent_id=install["installation_id"]
        )

        assert result["success"] is True
        rows = mock_zerodb_client.get_table_data("agent_installations")
        assert all(r.get("installation_id") != install["installation_id"] for r in rows)

    @pytest.mark.asyncio
    async def it_raises_not_found_for_unknown_installation(self, mock_zerodb_client):
        """uninstall_agent raises MarketplaceNotFoundError for unknown installation."""
        from app.services.marketplace_service import (
            MarketplaceService,
            MarketplaceNotFoundError,
        )

        svc = MarketplaceService(client=mock_zerodb_client)

        with pytest.raises(MarketplaceNotFoundError):
            await svc.uninstall_agent(project_id="proj_x", agent_id="ghost")
