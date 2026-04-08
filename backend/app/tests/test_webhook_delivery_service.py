"""
Tests for WebhookDeliveryService — Issue #167

HMAC-signed webhook delivery with retry and history.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #167
"""
from __future__ import annotations

import hmac
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Optional, Dict, List, Any


class DescribeWebhookDeliveryService:
    """Specification for WebhookDeliveryService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.webhook_delivery_service import WebhookDeliveryService
        return WebhookDeliveryService(client=mock_zerodb_client)

    # ------------------------------------------------------------------ #
    # register_webhook
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_registers_a_webhook_and_returns_config(self, service, mock_zerodb_client):
        """register_webhook persists the endpoint and returns webhook_id."""
        result = await service.register_webhook(
            project_id="proj-001",
            url="https://example.com/hook",
            event_types=["payment.settled", "anomaly.detected"],
            secret="super-secret",
        )

        assert "webhook_id" in result
        assert result["project_id"] == "proj-001"
        assert result["url"] == "https://example.com/hook"
        assert "payment.settled" in result["event_types"]

        calls = [c for c in mock_zerodb_client.call_history if c["method"] == "insert_row"]
        assert any(c["table_name"] == "webhooks" for c in calls)

    @pytest.mark.asyncio
    async def it_does_not_store_plaintext_secret(self, service, mock_zerodb_client):
        """register_webhook stores hashed secret, not the plaintext."""
        await service.register_webhook(
            project_id="proj-001",
            url="https://example.com/hook",
            event_types=["all"],
            secret="my-secret",
        )

        calls = [c for c in mock_zerodb_client.call_history
                 if c["method"] == "insert_row" and c.get("table_name") == "webhooks"]
        for call in calls:
            row = call.get("row_data", {})
            assert row.get("secret") != "my-secret"

    # ------------------------------------------------------------------ #
    # deliver_event
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_delivers_event_to_registered_webhooks(self, service, mock_zerodb_client):
        """deliver_event POSTs to all webhooks registered for the event type."""
        # Seed a registered webhook
        mock_zerodb_client.data["webhooks"] = [{
            "id": 1,
            "row_id": 1,
            "webhook_id": "wh-001",
            "project_id": "proj-001",
            "url": "https://example.com/hook",
            "event_types": json.dumps(["payment.settled"]),
            "secret_hash": "somehash",
            "active": True,
        }]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            result = await service.deliver_event(
                event_type="payment.settled",
                payload={"amount": 100.0, "agent_id": "agent-001"},
                project_id="proj-001",
            )

        assert "deliveries" in result
        assert len(result["deliveries"]) >= 1

    @pytest.mark.asyncio
    async def it_includes_hmac_signature_in_delivery_headers(self, service, mock_zerodb_client):
        """deliver_event sends X-Webhook-Signature header with HMAC-SHA256."""
        secret = "test-secret"
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()

        mock_zerodb_client.data["webhooks"] = [{
            "id": 1,
            "row_id": 1,
            "webhook_id": "wh-002",
            "project_id": "proj-sig",
            "url": "https://example.com/hook",
            "event_types": json.dumps(["anomaly.detected"]),
            "secret_hash": secret_hash,
            "active": True,
        }]

        captured_headers = {}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_headers.update(headers or {})
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = capture_post
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            await service.deliver_event(
                event_type="anomaly.detected",
                payload={"agent_id": "agent-001"},
                project_id="proj-sig",
            )

        assert "X-Webhook-Signature" in captured_headers

    @pytest.mark.asyncio
    async def it_records_delivery_attempt_in_history(self, service, mock_zerodb_client):
        """deliver_event persists a delivery attempt record."""
        mock_zerodb_client.data["webhooks"] = [{
            "id": 1,
            "row_id": 1,
            "webhook_id": "wh-003",
            "project_id": "proj-hist",
            "url": "https://example.com/hook",
            "event_types": json.dumps(["all"]),
            "secret_hash": "hash",
            "active": True,
        }]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            await service.deliver_event(
                event_type="all",
                payload={"test": True},
                project_id="proj-hist",
            )

        calls = [c for c in mock_zerodb_client.call_history
                 if c["method"] == "insert_row" and c.get("table_name") == "webhook_deliveries"]
        assert len(calls) >= 1

    # ------------------------------------------------------------------ #
    # get_delivery_history
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_delivery_attempts_for_a_webhook(self, service, mock_zerodb_client):
        """get_delivery_history returns list of attempts for webhook_id."""
        mock_zerodb_client.data["webhook_deliveries"] = [
            {
                "id": i,
                "row_id": i,
                "webhook_id": "wh-001",
                "status": "success",
                "status_code": 200,
                "created_at": "2026-04-01T00:00:00Z",
            }
            for i in range(5)
        ]

        history = await service.get_delivery_history(webhook_id="wh-001", limit=3)

        assert isinstance(history, list)
        assert len(history) <= 3

    @pytest.mark.asyncio
    async def it_returns_empty_history_for_unknown_webhook(self, service):
        """get_delivery_history returns [] for unknown webhook_id."""
        history = await service.get_delivery_history(webhook_id="no-webhook", limit=10)
        assert history == []

    # ------------------------------------------------------------------ #
    # retry_failed_deliveries
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_retries_failed_deliveries_within_max_age(self, service, mock_zerodb_client):
        """retry_failed_deliveries re-queues failed deliveries younger than max_age_hours."""
        from datetime import datetime, timedelta, timezone

        recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

        mock_zerodb_client.data["webhook_deliveries"] = [{
            "id": 1,
            "row_id": 1,
            "webhook_id": "wh-retry",
            "status": "failed",
            "status_code": 500,
            "created_at": recent,
        }]
        mock_zerodb_client.data["webhooks"] = [{
            "id": 1,
            "row_id": 1,
            "webhook_id": "wh-retry",
            "project_id": "proj-001",
            "url": "https://example.com/hook",
            "event_types": json.dumps(["all"]),
            "secret_hash": "hash",
            "active": True,
        }]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_http

            result = await service.retry_failed_deliveries(max_age_hours=24)

        assert "retried" in result
        assert isinstance(result["retried"], int)


class DescribeWebhookSchemas:
    """Schema validation for webhooks schemas."""

    def it_builds_webhook_config_with_required_fields(self):
        """WebhookConfig requires webhook_id, project_id, url, event_types."""
        from app.schemas.webhooks import WebhookConfig
        config = WebhookConfig(
            webhook_id="wh-001",
            project_id="proj-001",
            url="https://example.com/hook",
            event_types=["payment.settled"],
            active=True,
        )
        assert config.webhook_id == "wh-001"
        assert "payment.settled" in config.event_types

    def it_builds_delivery_attempt_with_status(self):
        """DeliveryAttempt requires webhook_id, status, status_code."""
        from app.schemas.webhooks import DeliveryAttempt
        attempt = DeliveryAttempt(
            attempt_id="att-001",
            webhook_id="wh-001",
            status="success",
            status_code=200,
            created_at="2026-04-03T00:00:00Z",
        )
        assert attempt.status == "success"

    def it_builds_webhook_event_with_type_and_payload(self):
        """WebhookEvent requires event_type and payload."""
        from app.schemas.webhooks import WebhookEvent
        event = WebhookEvent(
            event_id="evt-001",
            event_type="payment.settled",
            payload={"amount": 50.0},
        )
        assert event.event_type == "payment.settled"
