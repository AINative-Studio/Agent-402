"""
Tests for Hedera Wallets API router — Issue #188.

BDD-style tests for FastAPI endpoints.
Tests are written BEFORE implementation (RED phase).

Endpoints under test:
- POST /v1/public/{project_id}/hedera/wallets
- GET  /v1/public/{project_id}/hedera/wallets/{agent_id}
- GET  /v1/public/{project_id}/hedera/wallets/{account_id}/balance
- POST /v1/public/{project_id}/hedera/wallets/{account_id}/associate-usdc

Built by AINative Dev Team
Refs #188
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


# ─── Helpers ─────────────────────────────────────────────────────────────────────

VALID_API_KEY = "demo_key_user1_agent402_dev"
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY}
PROJECT_ID = "test_project_001"


def make_mock_wallet_service():
    """Create a mock HederaWalletService for dependency injection."""
    svc = AsyncMock()
    svc.create_agent_wallet = AsyncMock(return_value={
        "agent_id": "agent_abc123",
        "account_id": "0.0.12345",
        "public_key": "302a300506032b6570032100...",
        "network": "testnet",
        "created_at": "2026-04-03T12:00:00Z"
    })
    svc.get_wallet_info = AsyncMock(return_value={
        "agent_id": "agent_abc123",
        "account_id": "0.0.12345",
        "public_key": "302a300506032b6570032100...",
        "network": "testnet",
        "created_at": "2026-04-03T12:00:00Z"
    })
    svc.get_balance = AsyncMock(return_value={
        "account_id": "0.0.12345",
        "hbar": "100.0",
        "usdc": "50.000000"
    })
    svc.associate_usdc_token = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "account_id": "0.0.12345"
    })
    return svc


# ─── Describe: POST /hedera/wallets ─────────────────────────────────────────────

class DescribeCreateHederaWallet:
    """Tests for POST /v1/public/{project_id}/hedera/wallets."""

    def test_creates_wallet_returns_201(self):
        """Should return 201 Created when wallet is successfully created."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/wallets",
                json={"agent_id": "agent_abc123", "initial_balance": 10},
                headers=AUTH_HEADERS
            )
        assert response.status_code == 201

    def test_returns_account_id_in_response(self):
        """Should return account_id in the created wallet response."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/wallets",
                json={"agent_id": "agent_abc123", "initial_balance": 10},
                headers=AUTH_HEADERS
            )
        assert response.status_code == 201
        data = response.json()
        assert "account_id" in data

    def test_returns_422_when_agent_id_missing(self):
        """Should return 422 when agent_id is missing from request body."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/wallets",
                json={"initial_balance": 10},
                headers=AUTH_HEADERS
            )
        assert response.status_code == 422


# ─── Describe: GET /hedera/wallets/{agent_id} ────────────────────────────────────

class DescribeGetWalletInfo:
    """Tests for GET /v1/public/{project_id}/hedera/wallets/{agent_id}."""

    def test_returns_wallet_info_with_200(self):
        """Should return 200 with wallet info for valid agent_id."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                f"/v1/public/{PROJECT_ID}/hedera/wallets/agent_abc123",
                headers=AUTH_HEADERS
            )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent_abc123"

    def test_returns_404_when_wallet_not_found(self):
        """Should return 404 when no wallet exists for agent_id."""
        from app.api.hedera_wallets import router
        from app.services.hedera_wallet_service import HederaWalletNotFoundError
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()
        mock_svc.get_wallet_info.side_effect = HederaWalletNotFoundError("nonexistent_agent")

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                f"/v1/public/{PROJECT_ID}/hedera/wallets/nonexistent_agent",
                headers=AUTH_HEADERS
            )
        assert response.status_code == 404


# ─── Describe: GET /hedera/wallets/{account_id}/balance ──────────────────────────

class DescribeGetWalletBalance:
    """Tests for GET /v1/public/{project_id}/hedera/wallets/{account_id}/balance."""

    def test_returns_balance_with_200(self):
        """Should return 200 with HBAR and USDC balances."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                f"/v1/public/{PROJECT_ID}/hedera/wallets/0.0.12345/balance",
                headers=AUTH_HEADERS
            )
        assert response.status_code == 200
        data = response.json()
        assert "hbar" in data
        assert "usdc" in data


# ─── Describe: POST /hedera/wallets/{account_id}/associate-usdc ──────────────────

class DescribeAssociateUsdc:
    """Tests for POST /v1/public/{project_id}/hedera/wallets/{account_id}/associate-usdc."""

    def test_associates_usdc_returns_200(self):
        """Should return 200 with SUCCESS status after USDC token association."""
        from app.api.hedera_wallets import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_wallet_service()

        with patch("app.api.hedera_wallets.get_hedera_wallet_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/wallets/0.0.12345/associate-usdc",
                headers=AUTH_HEADERS
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
