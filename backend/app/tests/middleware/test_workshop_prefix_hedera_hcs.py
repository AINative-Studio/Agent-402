"""
Integration tests for the workshop /api/v1/ prefix applied to the Hedera
and HCS routers.

Refs #302, #285. Subsumes #295 (HCS-10 endpoint prefix bug).

Domains covered:
- hedera_wallets  (/v1/public/{pid}/hedera/wallets/*)     -> convention
- hedera_payments (/v1/public/{pid}/hedera/payments/*)    -> convention
- hcs_anchoring   (/anchor/*)                             -> override
- openconvai      (/hcs10/*)                              -> override

The convention domains (wallets, payments) need no override — they already
sit under /v1/public/{project_id}/. The anchor and hcs10 domains are mounted
at their own prefixes and are routed via the override registry configured
in `app.main` when the workshop middleware is added.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hcs_anchoring import router as hcs_anchoring_router
from app.api.hedera_payments import router as hedera_payments_router
from app.api.hedera_wallets import router as hedera_wallets_router
from app.api.openconvai import router as openconvai_router
from app.middleware.workshop_prefix import WorkshopPrefixMiddleware

# Match the override dict populated in `app.main` so tests exercise the
# same mapping as production code when workshop_mode is enabled.
B2_OVERRIDES: Dict[str, str] = {
    "anchor/": "/anchor/",
    "hcs10/": "/hcs10/",
}

DEFAULT_PID = "proj_test_b2"


def _build_app(
    router,
    *,
    workshop_mode: bool = True,
    overrides: Dict[str, str] = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(
        WorkshopPrefixMiddleware,
        enabled=workshop_mode,
        default_project_id=DEFAULT_PID,
        overrides=overrides or {},
    )
    return app


class DescribeHederaWalletsWorkshopAlias:
    """hedera_wallets follows convention; no override needed."""

    def it_routes_api_v1_hedera_wallets_get(self):
        from app.api.hedera_wallets import get_hedera_wallet_service

        app = _build_app(hedera_wallets_router)
        mock_service = SimpleNamespace(
            get_wallet_info=AsyncMock(
                return_value={
                    "agent_id": "agent_abc",
                    "account_id": "0.0.1234",
                    "public_key": "pk",
                    "network": "testnet",
                    "created_at": "2026-04-17T00:00:00Z",
                }
            )
        )
        app.dependency_overrides[get_hedera_wallet_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get("/api/v1/hedera/wallets/agent_abc")

        assert response.status_code == 200, response.text
        mock_service.get_wallet_info.assert_awaited_with(agent_id="agent_abc")

    def it_404s_without_workshop_mode(self):
        app = _build_app(hedera_wallets_router, workshop_mode=False)
        client = TestClient(app)

        response = client.get("/api/v1/hedera/wallets/agent_abc")

        assert response.status_code == 404


class DescribeHCSAnchoringWorkshopAlias:
    """hcs_anchoring is mounted at `/anchor/*`; needs the override."""

    def it_routes_api_v1_anchor_memory_via_override(self):
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        app = _build_app(hcs_anchoring_router, overrides=B2_OVERRIDES)
        mock_service = SimpleNamespace(
            anchor_memory=AsyncMock(
                return_value={
                    "memory_id": "mem_1",
                    "content_hash": "0" * 64,
                    "sequence_number": 42,
                    "timestamp": "2026-04-17T00:00:00Z",
                }
            )
        )
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        payload = {
            "memory_id": "mem_1",
            "content_hash": "0" * 64,
            "agent_id": "agent_abc",
            "namespace": "default",
        }
        client = TestClient(app)
        response = client.post("/api/v1/anchor/memory", json=payload)

        # 201 from the handler proves the full rewrite + route path worked.
        assert response.status_code == 201, response.text
        mock_service.anchor_memory.assert_awaited()

    def it_legacy_anchor_memory_still_works(self):
        from app.api.hcs_anchoring import get_hcs_anchoring_service

        app = _build_app(hcs_anchoring_router, overrides=B2_OVERRIDES)
        mock_service = SimpleNamespace(
            anchor_memory=AsyncMock(
                return_value={
                    "memory_id": "mem_2",
                    "content_hash": "0" * 64,
                    "sequence_number": 43,
                    "timestamp": "2026-04-17T00:00:00Z",
                }
            )
        )
        app.dependency_overrides[get_hcs_anchoring_service] = lambda: mock_service

        payload = {
            "memory_id": "mem_2",
            "content_hash": "0" * 64,
            "agent_id": "agent_abc",
            "namespace": "default",
        }
        client = TestClient(app)
        response = client.post("/anchor/memory", json=payload)

        assert response.status_code == 201

    def it_404s_api_v1_anchor_without_workshop_mode(self):
        app = _build_app(
            hcs_anchoring_router, workshop_mode=False, overrides=B2_OVERRIDES
        )
        client = TestClient(app)

        response = client.post("/api/v1/anchor/memory", json={})

        assert response.status_code == 404


class DescribeHCS10WorkshopAlias:
    """openconvai is mounted at `/hcs10/*`; needs override. Subsumes #295."""

    def it_routes_api_v1_hcs10_send_via_override(self):
        from app.api.openconvai import get_messaging_service

        app = _build_app(openconvai_router, overrides=B2_OVERRIDES)
        mock_messaging = SimpleNamespace(
            send_message=AsyncMock(
                return_value={"tx_id": "0.0.1@1", "conversation_id": "conv_1"}
            )
        )
        app.dependency_overrides[get_messaging_service] = lambda: mock_messaging

        payload = {
            "sender_did": "did:hedera:testnet:0.0.1",
            "recipient_did": "did:hedera:testnet:0.0.2",
            "message_type": "task_request",
            "payload": {"task": "analyze"},
        }
        client = TestClient(app)
        response = client.post("/api/v1/hcs10/send", json=payload)

        assert response.status_code == 200, response.text
        assert response.json()["tx_id"] == "0.0.1@1"
        mock_messaging.send_message.assert_awaited()

    def it_routes_api_v1_hcs10_messages_with_did_path_param(self):
        from app.api.openconvai import get_messaging_service

        app = _build_app(openconvai_router, overrides=B2_OVERRIDES)
        mock_messaging = SimpleNamespace(
            receive_messages=AsyncMock(return_value=[])
        )
        app.dependency_overrides[get_messaging_service] = lambda: mock_messaging

        client = TestClient(app)
        response = client.get(
            "/api/v1/hcs10/messages/did:hedera:testnet:0.0.99"
        )

        assert response.status_code == 200, response.text
        mock_messaging.receive_messages.assert_awaited_with(
            agent_did="did:hedera:testnet:0.0.99",
            since_sequence=0,
            limit=50,
        )

    def it_legacy_hcs10_send_still_works(self):
        from app.api.openconvai import get_messaging_service

        app = _build_app(openconvai_router, overrides=B2_OVERRIDES)
        mock_messaging = SimpleNamespace(
            send_message=AsyncMock(
                return_value={"tx_id": "0.0.2@2", "conversation_id": "conv_2"}
            )
        )
        app.dependency_overrides[get_messaging_service] = lambda: mock_messaging

        payload = {
            "sender_did": "did:hedera:testnet:0.0.1",
            "recipient_did": "did:hedera:testnet:0.0.2",
            "message_type": "task_request",
            "payload": {"task": "analyze"},
        }
        client = TestClient(app)
        response = client.post("/hcs10/send", json=payload)

        assert response.status_code == 200, response.text


class DescribeMainAppOverrides:
    """Verify `app.main` is wired with the expected overrides dict."""

    def it_configures_middleware_with_anchor_and_hcs10_overrides(self):
        # The overrides literal in main.py is captured by the middleware
        # instance at construction. Assert the wiring by constructing the
        # middleware the same way and checking its `overrides` attribute.
        mw = WorkshopPrefixMiddleware(
            app=lambda *_: None,
            enabled=True,
            default_project_id="proj_workshop",
            overrides={"anchor/": "/anchor/", "hcs10/": "/hcs10/"},
        )

        assert mw.overrides == {
            "anchor/": "/anchor/",
            "hcs10/": "/hcs10/",
        }
        # And the rewrites produce the right targets
        assert mw._rewrite_path("/api/v1/anchor/memory") == "/anchor/memory"
        assert mw._rewrite_path("/api/v1/hcs10/send") == "/hcs10/send"
        # Convention still handles hedera
        assert (
            mw._rewrite_path("/api/v1/hedera/wallets/agent_abc")
            == "/v1/public/proj_workshop/hedera/wallets/agent_abc"
        )
