"""
Tests for Webhooks API Router — Issue #167

POST /webhooks/register, POST /webhooks/test, GET /webhooks/{id}/history
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #167
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch
from typing import Optional, Dict, List, Any


@pytest.fixture
def webhooks_app():
    """Isolated FastAPI app with only the webhooks router mounted."""
    from app.api.webhooks import router
    app = FastAPI()
    app.include_router(router, prefix="/webhooks")
    return app


@pytest.fixture
def webhooks_client(webhooks_app):
    return TestClient(webhooks_app)


@pytest.fixture
def mock_webhook_service():
    svc = AsyncMock()
    svc.register_webhook.return_value = {
        "webhook_id": "wh-001",
        "project_id": "proj-001",
        "url": "https://example.com/hook",
        "event_types": ["payment.settled"],
        "active": True,
    }
    svc.deliver_event.return_value = {
        "deliveries": [{"webhook_id": "wh-001", "status": "success", "status_code": 200}]
    }
    svc.get_delivery_history.return_value = [
        {
            "attempt_id": "att-001",
            "webhook_id": "wh-001",
            "status": "success",
            "status_code": 200,
            "created_at": "2026-04-01T00:00:00Z",
        }
    ]
    return svc


class DescribeWebhooksRegisterEndpoint:
    """POST /webhooks/register"""

    def it_returns_201_with_webhook_config(self, webhooks_client, mock_webhook_service):
        """POST /webhooks/register returns 201 with webhook_id."""
        with patch(
            "app.api.webhooks.get_webhook_delivery_service",
            return_value=mock_webhook_service,
        ):
            resp = webhooks_client.post(
                "/webhooks/register",
                json={
                    "project_id": "proj-001",
                    "url": "https://example.com/hook",
                    "event_types": ["payment.settled"],
                    "secret": "my-secret",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "webhook_id" in data

    def it_returns_422_when_url_missing(self, webhooks_client, mock_webhook_service):
        """POST /webhooks/register returns 422 when url is missing."""
        with patch(
            "app.api.webhooks.get_webhook_delivery_service",
            return_value=mock_webhook_service,
        ):
            resp = webhooks_client.post(
                "/webhooks/register",
                json={
                    "project_id": "proj-001",
                    "event_types": ["payment.settled"],
                    "secret": "my-secret",
                },
            )

        assert resp.status_code == 422

    def it_returns_422_when_project_id_missing(self, webhooks_client, mock_webhook_service):
        """POST /webhooks/register returns 422 when project_id is missing."""
        with patch(
            "app.api.webhooks.get_webhook_delivery_service",
            return_value=mock_webhook_service,
        ):
            resp = webhooks_client.post(
                "/webhooks/register",
                json={
                    "url": "https://example.com/hook",
                    "event_types": ["payment.settled"],
                    "secret": "my-secret",
                },
            )

        assert resp.status_code == 422


class DescribeWebhooksTestEndpoint:
    """POST /webhooks/test"""

    def it_returns_200_with_delivery_results(self, webhooks_client, mock_webhook_service):
        """POST /webhooks/test returns 200 with delivery attempt results."""
        with patch(
            "app.api.webhooks.get_webhook_delivery_service",
            return_value=mock_webhook_service,
        ):
            resp = webhooks_client.post(
                "/webhooks/test",
                json={
                    "project_id": "proj-001",
                    "event_type": "payment.settled",
                    "payload": {"test": True},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "deliveries" in data

    def it_returns_422_when_event_type_missing(self, webhooks_client, mock_webhook_service):
        """POST /webhooks/test returns 422 when event_type is missing."""
        with patch(
            "app.api.webhooks.get_webhook_delivery_service",
            return_value=mock_webhook_service,
        ):
            resp = webhooks_client.post(
                "/webhooks/test",
                json={"project_id": "proj-001", "payload": {}},
            )

        assert resp.status_code == 422


class DescribeWebhooksHistoryEndpoint:
    """GET /webhooks/{id}/history"""

    def it_returns_200_with_delivery_history(self, webhooks_app, mock_webhook_service):
        """GET /webhooks/{id}/history returns 200 with attempt list."""
        from app.api.webhooks import get_webhook_delivery_service

        webhooks_app.dependency_overrides[get_webhook_delivery_service] = lambda: mock_webhook_service
        try:
            client = TestClient(webhooks_app)
            resp = client.get("/webhooks/wh-001/history")
        finally:
            webhooks_app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def it_passes_limit_param_to_service(self, webhooks_app, mock_webhook_service):
        """GET /webhooks/{id}/history forwards limit query param."""
        from app.api.webhooks import get_webhook_delivery_service

        webhooks_app.dependency_overrides[get_webhook_delivery_service] = lambda: mock_webhook_service
        try:
            client = TestClient(webhooks_app)
            resp = client.get("/webhooks/wh-001/history?limit=5")
        finally:
            webhooks_app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_webhook_service.get_delivery_history.assert_called_once_with(
            webhook_id="wh-001", limit=5
        )
