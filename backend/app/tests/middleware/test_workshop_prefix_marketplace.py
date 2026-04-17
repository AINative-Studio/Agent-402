"""
Integration tests for the workshop /api/v1/ prefix applied to the
marketplace router.

Refs #303, #285.

The marketplace router lives at `/marketplace/*` (no project prefix), so
an override entry `"marketplace/": "/marketplace/"` is required in the
WorkshopPrefixMiddleware configuration.
"""
from __future__ import annotations

from typing import Dict
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.marketplace import router as marketplace_router
from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

B3_OVERRIDES: Dict[str, str] = {
    "marketplace/": "/marketplace/",
}

DEFAULT_PID = "proj_test_b3"


def _build_app(workshop_mode: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(marketplace_router)
    app.add_middleware(
        WorkshopPrefixMiddleware,
        enabled=workshop_mode,
        default_project_id=DEFAULT_PID,
        overrides=B3_OVERRIDES,
    )
    return app


class DescribeMarketplaceWorkshopAlias:
    """`/api/v1/marketplace/*` must resolve to the marketplace router."""

    def it_routes_api_v1_marketplace_categories(self):
        app = _build_app()
        with patch(
            "app.api.marketplace.marketplace_service.get_categories",
            new=AsyncMock(return_value=["trading", "compliance", "analytics"]),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/marketplace/categories")

        assert response.status_code == 200, response.text
        assert response.json() == ["trading", "compliance", "analytics"]

    def it_routes_api_v1_marketplace_browse_with_query(self):
        app = _build_app()
        with patch(
            "app.api.marketplace.marketplace_service.browse_agents",
            new=AsyncMock(
                return_value={"agents": [{"marketplace_id": "mp_1"}], "total": 1}
            ),
        ) as mock_browse:
            client = TestClient(app)
            response = client.get(
                "/api/v1/marketplace/browse?category=trading&limit=10"
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["agents"][0]["marketplace_id"] == "mp_1"
        mock_browse.assert_awaited()

    def it_routes_api_v1_marketplace_agent_detail(self):
        app = _build_app()
        with patch(
            "app.api.marketplace.marketplace_service.get_published_agent",
            new=AsyncMock(
                return_value={"marketplace_id": "mp_123", "name": "Listed agent"}
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/marketplace/agents/mp_123")

        assert response.status_code == 200, response.text
        assert response.json()["marketplace_id"] == "mp_123"

    def it_legacy_marketplace_path_still_works(self):
        app = _build_app()
        with patch(
            "app.api.marketplace.marketplace_service.get_categories",
            new=AsyncMock(return_value=["legacy"]),
        ):
            client = TestClient(app)
            response = client.get("/marketplace/categories")

        assert response.status_code == 200
        assert response.json() == ["legacy"]

    def it_404s_api_v1_marketplace_without_workshop_mode(self):
        app = _build_app(workshop_mode=False)
        client = TestClient(app)

        response = client.get("/api/v1/marketplace/categories")

        assert response.status_code == 404


class DescribeMainAppMarketplaceOverride:
    """Verify the B3 override is present in the tested mapping."""

    def it_rewrites_api_v1_marketplace_via_override(self):
        mw = WorkshopPrefixMiddleware(
            app=lambda *_: None,
            enabled=True,
            default_project_id="proj_workshop",
            overrides={
                "anchor/": "/anchor/",
                "hcs10/": "/hcs10/",
                "marketplace/": "/marketplace/",
            },
        )

        assert (
            mw._rewrite_path("/api/v1/marketplace/categories")
            == "/marketplace/categories"
        )
        assert (
            mw._rewrite_path("/api/v1/marketplace/agents/mp_1")
            == "/marketplace/agents/mp_1"
        )
        # Co-existing overrides still work
        assert mw._rewrite_path("/api/v1/anchor/memory") == "/anchor/memory"
        assert mw._rewrite_path("/api/v1/hcs10/send") == "/hcs10/send"
