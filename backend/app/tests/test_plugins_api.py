"""
Tests for Plugin API endpoints — Issues #243, #244, #245

Covers: POST /plugins/install, DELETE /plugins/{id}, GET /plugins,
GET /plugins/{id}, POST /plugins/{id}/review,
GET /plugins/marketplace/search, POST /plugins/marketplace/publish

BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #243, #244, #245
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch


VALID_MANIFEST: Dict[str, Any] = {
    "name": "api-test-tools",
    "version": "1.0.0",
    "description": "Tools for API testing",
    "author": "dev@example.com",
    "tools": [
        {
            "name": "ping",
            "description": "Ping tool",
            "input_schema": {"type": "object", "properties": {}},
            "handler_module": "api_test_tools.handlers.ping",
        }
    ],
    "capabilities_required": [],
    "permissions": [],
}

VALID_LISTING_METADATA: Dict[str, Any] = {
    "category": "utilities",
    "description": "Utility tools for API testing",
    "screenshots": [],
    "tags": ["api", "test"],
    "price": "free",
}


@pytest.fixture
def plugin_client(mock_zerodb_client):
    """
    Test client with plugin router mounted on an isolated app.
    Services are injected with the mock ZeroDB client.
    Module-level singletons are reset after each test for isolation.
    """
    from app.api.plugins import router
    from app.services.plugin_registry_service import PluginRegistryService
    from app.services.plugin_sandbox_service import PluginSandboxService
    from app.services.plugin_marketplace_service import PluginMarketplaceService
    import app.api.plugins as plugins_module

    # Build fresh service instances backed by the mock client
    registry = PluginRegistryService(client=mock_zerodb_client)
    sandbox = PluginSandboxService(registry=registry)
    marketplace = PluginMarketplaceService(
        client=mock_zerodb_client, registry=registry
    )

    # Inject into the module-level singletons the router uses
    plugins_module._registry_service = registry
    plugins_module._sandbox_service = sandbox
    plugins_module._marketplace_service = marketplace

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    yield client

    # Reset module-level singletons after each test for isolation
    plugins_module._registry_service = None
    plugins_module._sandbox_service = None
    plugins_module._marketplace_service = None


class DescribeInstallPluginEndpoint:
    """Specification: POST /plugins/install."""

    def it_installs_plugin_and_returns_201(self, plugin_client):
        """POST /plugins/install returns 201 with plugin_id."""
        payload = {
            "package_ref": "api-test-tools@1.0.0",
            "project_id": "proj_test_001",
            "manifest": VALID_MANIFEST,
        }
        response = plugin_client.post("/plugins/install", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "plugin_id" in data
        assert data["status"] == "installed"

    def it_returns_422_for_missing_manifest(self, plugin_client):
        """POST /plugins/install returns 422 when manifest is absent."""
        payload = {
            "package_ref": "api-test-tools@1.0.0",
            "project_id": "proj_test_001",
        }
        response = plugin_client.post("/plugins/install", json=payload)
        assert response.status_code == 422

    def it_returns_422_for_invalid_manifest_schema(self, plugin_client):
        """POST /plugins/install returns 422 when manifest fails validation."""
        payload = {
            "package_ref": "bad-tools@1.0.0",
            "project_id": "proj_test_001",
            "manifest": {"name": "bad-tools"},  # missing required fields
        }
        response = plugin_client.post("/plugins/install", json=payload)
        assert response.status_code in (400, 422)


class DescribeDeletePluginEndpoint:
    """Specification: DELETE /plugins/{id}."""

    def it_uninstalls_plugin_and_returns_200(self, plugin_client):
        """DELETE /plugins/{id} returns 200 after successful uninstall."""
        # First install
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        response = plugin_client.delete(
            f"/plugins/{plugin_id}",
            params={"project_id": "proj_test_001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uninstalled"

    def it_returns_404_for_unknown_plugin(self, plugin_client):
        """DELETE /plugins/{id} returns 404 for unknown plugin."""
        response = plugin_client.delete(
            "/plugins/plugin_ghost",
            params={"project_id": "proj_test_001"},
        )
        assert response.status_code == 404


class DescribeGetPluginsEndpoint:
    """Specification: GET /plugins."""

    def it_returns_list_of_installed_plugins(self, plugin_client):
        """GET /plugins returns all registered plugins."""
        plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        response = plugin_client.get("/plugins")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def it_returns_empty_list_when_no_plugins(self, plugin_client):
        """GET /plugins returns [] when no plugins are installed."""
        response = plugin_client.get("/plugins")
        assert response.status_code == 200
        assert response.json() == []

    def it_filters_by_status_query_param(self, plugin_client):
        """GET /plugins?status=active filters results."""
        plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        response = plugin_client.get("/plugins", params={"status": "active"})
        assert response.status_code == 200
        data = response.json()
        assert all(p["status"] == "active" for p in data)


class DescribeGetSinglePluginEndpoint:
    """Specification: GET /plugins/{id}."""

    def it_returns_plugin_detail(self, plugin_client):
        """GET /plugins/{id} returns full plugin info."""
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        response = plugin_client.get(f"/plugins/{plugin_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_id"] == plugin_id
        assert data["name"] == "api-test-tools"

    def it_returns_404_for_unknown_plugin(self, plugin_client):
        """GET /plugins/{id} returns 404 for unknown plugin."""
        response = plugin_client.get("/plugins/plugin_ghost")
        assert response.status_code == 404


class DescribeSubmitReviewEndpoint:
    """Specification: POST /plugins/{id}/review."""

    def it_accepts_valid_review_and_returns_201(self, plugin_client):
        """POST /plugins/{id}/review returns 201 with review_id."""
        # Install and publish
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        # Publish to marketplace
        plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": plugin_id,
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )

        review_payload = {
            "reviewer_id": "user_reviewer_01",
            "rating": 5,
            "comment": "Outstanding tools!",
        }
        response = plugin_client.post(
            f"/plugins/{plugin_id}/review", json=review_payload
        )
        assert response.status_code == 201
        data = response.json()
        assert "review_id" in data

    def it_returns_400_for_invalid_rating(self, plugin_client):
        """POST /plugins/{id}/review returns 400 for out-of-range rating."""
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": plugin_id,
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )

        response = plugin_client.post(
            f"/plugins/{plugin_id}/review",
            json={"reviewer_id": "user_01", "rating": 10, "comment": "Too many stars"},
        )
        assert response.status_code in (400, 422)


class DescribeMarketplaceSearchEndpoint:
    """Specification: GET /plugins/marketplace/search."""

    def it_returns_published_listings(self, plugin_client):
        """GET /plugins/marketplace/search returns published listings."""
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": plugin_id,
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )

        response = plugin_client.get("/plugins/marketplace/search")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def it_filters_by_category_query_param(self, plugin_client):
        """GET /plugins/marketplace/search?category= returns filtered results."""
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": plugin_id,
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )

        response = plugin_client.get(
            "/plugins/marketplace/search", params={"category": "utilities"}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["category"] == "utilities" for item in data)


class DescribeMarketplacePublishEndpoint:
    """Specification: POST /plugins/marketplace/publish."""

    def it_publishes_installed_plugin_and_returns_201(self, plugin_client):
        """POST /plugins/marketplace/publish returns 201 with listing_id."""
        install_resp = plugin_client.post(
            "/plugins/install",
            json={
                "package_ref": "api-test-tools@1.0.0",
                "project_id": "proj_test_001",
                "manifest": VALID_MANIFEST,
            },
        )
        plugin_id = install_resp.json()["plugin_id"]

        response = plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": plugin_id,
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "listing_id" in data
        assert data["status"] == "published"

    def it_returns_404_for_unregistered_plugin(self, plugin_client):
        """POST /plugins/marketplace/publish returns 404 for unknown plugin_id."""
        response = plugin_client.post(
            "/plugins/marketplace/publish",
            json={
                "plugin_id": "plugin_ghost",
                "listing_metadata": VALID_LISTING_METADATA,
            },
        )
        assert response.status_code == 404
