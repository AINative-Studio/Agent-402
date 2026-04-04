"""
Tests for Hedera Payments API router — Issue #187.

BDD-style tests for FastAPI endpoints.
Tests are written BEFORE implementation (RED phase).

Endpoints under test:
- POST /v1/public/{project_id}/hedera/payments
- GET  /v1/public/{project_id}/hedera/payments/{payment_id}
- POST /v1/public/{project_id}/hedera/payments/verify
- GET  /v1/public/{project_id}/hedera/payments/{payment_id}/receipt

Built by AINative Dev Team
Refs #187
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ─── Helpers ─────────────────────────────────────────────────────────────────────

VALID_API_KEY = "demo_key_user1_agent402_dev"
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY}
PROJECT_ID = "test_project_001"


def make_mock_payment_service():
    """Create a mock HederaPaymentService for dependency injection."""
    svc = AsyncMock()
    svc.create_x402_payment = AsyncMock(return_value={
        "payment_id": "hdr_pay_abc123",
        "agent_id": "agent_abc123",
        "task_id": "task_xyz789",
        "amount": 5000000,
        "recipient": "0.0.22222",
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "created_at": "2026-04-03T12:00:00Z"
    })
    svc.transfer_usdc = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "hash": "0xabcdef1234567890"
    })
    svc.verify_settlement = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "settled": True,
        "status": "SUCCESS"
    })
    svc.get_payment_receipt = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "hash": "0xabcdef1234567890",
        "status": "SUCCESS",
        "consensus_timestamp": "2026-04-03T12:00:00Z"
    })
    return svc


# ─── Describe: POST /hedera/payments ────────────────────────────────────────────

class DescribeCreateHederaPayment:
    """Tests for POST /v1/public/{project_id}/hedera/payments."""

    def test_creates_payment_returns_201(self):
        """Should return 201 Created when payment is successfully initiated."""
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService, get_hedera_payment_service
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments",
                json={
                    "agent_id": "agent_abc123",
                    "amount": 5000000,
                    "recipient": "0.0.22222",
                    "task_id": "task_xyz789"
                },
                headers=AUTH_HEADERS
            )
        assert response.status_code == 201

    def test_creates_payment_returns_payment_id(self):
        """Should return a payment_id in the response body."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments",
                json={
                    "agent_id": "agent_abc123",
                    "amount": 5000000,
                    "recipient": "0.0.22222",
                    "task_id": "task_xyz789"
                },
                headers=AUTH_HEADERS
            )
        assert response.status_code == 201
        data = response.json()
        assert "payment_id" in data

    def test_returns_422_when_amount_missing(self):
        """Should return 422 Unprocessable Entity when amount is missing."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments",
                json={
                    "agent_id": "agent_abc123",
                    "recipient": "0.0.22222",
                    "task_id": "task_xyz789"
                },
                headers=AUTH_HEADERS
            )
        assert response.status_code == 422

    def test_returns_422_when_recipient_missing(self):
        """Should return 422 when recipient is missing."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments",
                json={
                    "agent_id": "agent_abc123",
                    "amount": 5000000,
                    "task_id": "task_xyz789"
                },
                headers=AUTH_HEADERS
            )
        assert response.status_code == 422


# ─── Describe: GET /hedera/payments/{payment_id}/receipt ────────────────────────

class DescribeGetPaymentReceipt:
    """Tests for GET /v1/public/{project_id}/hedera/payments/{payment_id}/receipt."""

    def test_returns_receipt_with_hash(self):
        """Should return 200 with a receipt including the transaction hash."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                f"/v1/public/{PROJECT_ID}/hedera/payments/hdr_pay_abc123/receipt",
                headers=AUTH_HEADERS
            )
        assert response.status_code == 200
        data = response.json()
        assert "hash" in data


# ─── Describe: POST /hedera/payments/verify ─────────────────────────────────────

class DescribeVerifySettlement:
    """Tests for POST /v1/public/{project_id}/hedera/payments/verify."""

    def test_returns_settled_true_for_completed_transaction(self):
        """Should return 200 with settled=True for a completed transaction."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments/verify",
                json={"transaction_id": "0.0.12345@1234567890.000000000"},
                headers=AUTH_HEADERS
            )
        assert response.status_code == 200
        data = response.json()
        assert data["settled"] is True

    def test_returns_422_when_transaction_id_missing(self):
        """Should return 422 when transaction_id is missing from request body."""
        from app.api.hedera_payments import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_svc = make_mock_payment_service()

        with patch("app.api.hedera_payments.get_hedera_payment_service", return_value=mock_svc):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                f"/v1/public/{PROJECT_ID}/hedera/payments/verify",
                json={},
                headers=AUTH_HEADERS
            )
        assert response.status_code == 422
