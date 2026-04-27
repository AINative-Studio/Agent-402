"""
Tests for zero-human provisioning endpoints.

Covers:
- POST /v1/public/provision — wallet sig → API key
- POST /v1/public/keys     — create additional key (auth required)
- GET  /v1/public/capabilities — public manifest

Refs AINative-Studio/Agent-402#363
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /v1/public/capabilities
# ---------------------------------------------------------------------------

class TestCapabilities:
    def test_returns_200_without_auth(self):
        resp = client.get("/v1/public/capabilities")
        assert resp.status_code == 200

    def test_has_required_fields(self):
        resp = client.get("/v1/public/capabilities")
        data = resp.json()
        assert "service" in data
        assert "protocols" in data
        assert "features" in data
        assert "models" in data
        assert "limits" in data
        assert "auth" in data

    def test_provision_url_present(self):
        resp = client.get("/v1/public/capabilities")
        data = resp.json()
        assert "/v1/public/provision" in data["auth"]["provision_url"]

    def test_x402_protocol_listed(self):
        resp = client.get("/v1/public/capabilities")
        data = resp.json()
        assert "x402" in data["protocols"]


# ---------------------------------------------------------------------------
# POST /v1/public/provision
# ---------------------------------------------------------------------------

class TestProvision:
    def _mock_provision_result(self):
        return {
            "api_key": "a402_testkey123",
            "user_id": "wa_abc123",
            "wallet_address": "0xdeadbeef",
            "created_at": "2026-04-27T00:00:00+00:00",
            "capabilities_url": "https://api.ainative.studio/agent402/v1/public/capabilities",
        }

    def test_provision_success(self):
        with patch(
            "app.api.provision.get_provision_service"
        ) as mock_get_svc:
            svc = MagicMock()
            svc.provision = AsyncMock(return_value=self._mock_provision_result())
            mock_get_svc.return_value = svc

            resp = client.post(
                "/v1/public/provision",
                json={
                    "wallet_address": "0xdeadbeef",
                    "message": "Agent-402 provision 1234567890",
                    "signature": "0xfakesig",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["api_key"] == "a402_testkey123"
        assert data["user_id"] == "wa_abc123"
        assert "capabilities_url" in data

    def test_provision_invalid_signature(self):
        from app.services.provision_service import InvalidSignatureError

        with patch(
            "app.api.provision.get_provision_service"
        ) as mock_get_svc:
            svc = MagicMock()
            svc.provision = AsyncMock(side_effect=InvalidSignatureError())
            mock_get_svc.return_value = svc

            resp = client.post(
                "/v1/public/provision",
                json={
                    "wallet_address": "0xbad",
                    "message": "test",
                    "signature": "0xinvalid",
                },
            )

        assert resp.status_code == 401
        data = resp.json()
        assert data["error_code"] == "INVALID_SIGNATURE"

    def test_provision_missing_fields(self):
        resp = client.post("/v1/public/provision", json={"wallet_address": "0x1"})
        assert resp.status_code == 422

    def test_provision_no_auth_required(self):
        """Provision must be callable without any X-API-Key or JWT."""
        with patch(
            "app.api.provision.get_provision_service"
        ) as mock_get_svc:
            svc = MagicMock()
            svc.provision = AsyncMock(return_value=self._mock_provision_result())
            mock_get_svc.return_value = svc

            resp = client.post(
                "/v1/public/provision",
                json={
                    "wallet_address": "0xdeadbeef",
                    "message": "test",
                    "signature": "0xsig",
                },
                # Deliberately no X-API-Key or Authorization header
            )

        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# POST /v1/public/keys
# ---------------------------------------------------------------------------

class TestCreateKey:
    def test_create_key_requires_auth(self):
        resp = client.post("/v1/public/keys", json={})
        # Without auth the middleware should return 401
        assert resp.status_code == 401

    def test_create_key_authenticated(self):
        with patch(
            "app.api.provision.get_provision_service"
        ) as mock_get_svc:
            svc = MagicMock()
            svc.create_key = AsyncMock(
                return_value={
                    "api_key": "a402_newkey",
                    "key_id": "kd123",
                    "user_id": "user_1",
                    "key_name": "my-agent",
                    "created_at": "2026-04-27T00:00:00+00:00",
                }
            )
            mock_get_svc.return_value = svc

            # Use a known demo API key so middleware passes
            from app.core.config import settings
            demo_key = settings.demo_api_key_1

            resp = client.post(
                "/v1/public/keys",
                json={"name": "my-agent"},
                headers={"X-API-Key": demo_key},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["api_key"] == "a402_newkey"
        assert data["key_name"] == "my-agent"

    def test_create_key_default_name(self):
        with patch(
            "app.api.provision.get_provision_service"
        ) as mock_get_svc:
            svc = MagicMock()
            svc.create_key = AsyncMock(
                return_value={
                    "api_key": "a402_defaultkey",
                    "key_id": "kd456",
                    "user_id": "user_1",
                    "key_name": "default",
                    "created_at": "2026-04-27T00:00:00+00:00",
                }
            )
            mock_get_svc.return_value = svc

            from app.core.config import settings
            resp = client.post(
                "/v1/public/keys",
                json={},
                headers={"X-API-Key": settings.demo_api_key_1},
            )

        assert resp.status_code == 201
        assert resp.json()["key_name"] == "default"


# ---------------------------------------------------------------------------
# ProvisionService unit tests (no HTTP layer)
# ---------------------------------------------------------------------------

class TestProvisionService:
    def test_verify_wallet_ownership_valid(self):
        """Verify a real EIP-191 signature using eth_account."""
        from eth_account import Account
        from eth_account.messages import encode_defunct

        acct = Account.create()
        message = "Agent-402 provision test"
        signable = encode_defunct(text=message)
        signed = acct.sign_message(signable)

        from app.services.provision_service import ProvisionService
        svc = ProvisionService()
        assert svc.verify_wallet_ownership(
            acct.address, message, signed.signature.hex()
        )

    def test_verify_wallet_ownership_wrong_wallet(self):
        from eth_account import Account
        from eth_account.messages import encode_defunct

        acct = Account.create()
        other = Account.create()
        message = "test"
        signable = encode_defunct(text=message)
        signed = acct.sign_message(signable)

        from app.services.provision_service import ProvisionService
        svc = ProvisionService()
        assert not svc.verify_wallet_ownership(
            other.address, message, signed.signature.hex()
        )

    def test_verify_wallet_ownership_bad_sig(self):
        from app.services.provision_service import ProvisionService
        svc = ProvisionService()
        assert not svc.verify_wallet_ownership("0x1234", "msg", "notasignature")

    def test_user_id_deterministic(self):
        from app.services.provision_service import ProvisionService
        svc = ProvisionService()
        uid1 = svc._user_id_from_wallet("0xABC")
        uid2 = svc._user_id_from_wallet("0xabc")  # case-insensitive
        assert uid1 == uid2
        assert uid1.startswith("wa_")
