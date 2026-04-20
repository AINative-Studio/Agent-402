"""
API-level tests for /marketplace/browse and /marketplace/search in mock mode.

Issue #328: Before the fix, both endpoints returned HTTP 500 because the
production ZeroDBClient (in mock mode) fell through to real HTTP calls
against api.ainative.studio and raised HTTPStatusError on the 404 that
comes back for absent `mock_project` tables. With the fix, mock mode
short-circuits `query_rows` to an empty result and both endpoints return
200 with an empty items list.

Built by AINative Dev Team
Refs #328
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.marketplace import router as marketplace_router
from app.services.marketplace_service import MarketplaceService
from app.services import marketplace_service as marketplace_service_module
from app.services.zerodb_client import ZeroDBClient


@pytest.fixture
def mock_mode_marketplace_client(monkeypatch):
    """
    Build a TestClient against the marketplace router, backed by a real
    (not MockZeroDBClient) ZeroDBClient running in mock mode. This is the
    exact configuration that the workshop's local/demo deployment uses.
    """
    # Force the production client into mock mode (no creds).
    monkeypatch.delenv("ZERODB_API_KEY", raising=False)
    monkeypatch.delenv("ZERODB_PROJECT_ID", raising=False)

    real_client_in_mock_mode = ZeroDBClient(api_key=None, project_id=None)
    assert real_client_in_mock_mode._mock_mode is True

    # Replace the singleton the marketplace router resolves against.
    monkeypatch.setattr(
        marketplace_service_module,
        "marketplace_service",
        MarketplaceService(client=real_client_in_mock_mode),
    )

    app = FastAPI()
    app.include_router(marketplace_router)
    return TestClient(app)


class DescribeMarketplaceBrowseInMockMode:
    """GET /marketplace/browse must return 200 in mock mode — Issue #328."""

    def it_returns_200_with_empty_items(self, mock_mode_marketplace_client):
        response = mock_mode_marketplace_client.get("/marketplace/browse")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["limit"] == 20
        assert body["offset"] == 0

    def it_respects_pagination_params(self, mock_mode_marketplace_client):
        response = mock_mode_marketplace_client.get(
            "/marketplace/browse",
            params={"limit": 5, "offset": 10, "sort_by": "highest_rated"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"] == []
        assert body["limit"] == 5
        assert body["offset"] == 10


class DescribeMarketplaceSearchInMockMode:
    """POST /marketplace/search must return 200 in mock mode — Issue #328."""

    def it_returns_200_with_empty_items(self, mock_mode_marketplace_client):
        response = mock_mode_marketplace_client.post(
            "/marketplace/search",
            json={"query": "finance"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def it_accepts_filters_without_erroring(self, mock_mode_marketplace_client):
        response = mock_mode_marketplace_client.post(
            "/marketplace/search",
            json={
                "query": "analytics",
                "min_reputation": 0.5,
                "price_range": {"min": 0.0, "max": 1.0},
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"] == []
