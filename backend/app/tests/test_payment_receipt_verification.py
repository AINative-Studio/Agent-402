"""
Tests for Payment Receipt Verification — Issue #189.

Covers:
- mirror_node_url field construction in receipt responses
- agent_id and task_id fields in receipt response
- verify_receipt_on_mirror_node() method
- GET /api/v1/hedera/payments/{transaction_id}/verify endpoint
- ReceiptVerificationResponse schema fields

TDD RED phase: all tests written before implementation.

Built by AINative Dev Team
Refs #189
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, Any


# ─── Schema Tests ──────────────────────────────────────────────────────────────


class DescribeReceiptVerificationResponseSchema:
    """ReceiptVerificationResponse schema field verification."""

    def it_has_verified_field(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        schema_fields = ReceiptVerificationResponse.model_fields
        assert "verified" in schema_fields

    def it_has_transaction_status_field(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        schema_fields = ReceiptVerificationResponse.model_fields
        assert "transaction_status" in schema_fields

    def it_has_mirror_node_url_field(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        schema_fields = ReceiptVerificationResponse.model_fields
        assert "mirror_node_url" in schema_fields

    def it_has_consensus_timestamp_field(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        schema_fields = ReceiptVerificationResponse.model_fields
        assert "consensus_timestamp" in schema_fields

    def it_instantiates_with_required_fields(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        resp = ReceiptVerificationResponse(
            verified=True,
            transaction_status="SUCCESS",
            mirror_node_url="https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345-1234567890-000000000",
            consensus_timestamp="2026-04-03T12:00:00Z"
        )
        assert resp.verified is True
        assert resp.transaction_status == "SUCCESS"
        assert "mirrornode.hedera.com" in resp.mirror_node_url

    def it_allows_optional_consensus_timestamp(self):
        from app.schemas.hedera import ReceiptVerificationResponse
        resp = ReceiptVerificationResponse(
            verified=False,
            transaction_status="NOT_FOUND",
            mirror_node_url="https://testnet.mirrornode.hedera.com/api/v1/transactions/abc",
            consensus_timestamp=None
        )
        assert resp.consensus_timestamp is None


class DescribeExtendedReceiptResponseSchema:
    """HederaPaymentReceiptResponse extended with mirror_node_url, agent_id, task_id."""

    def it_has_mirror_node_url_field(self):
        from app.schemas.hedera import HederaPaymentReceiptResponse
        schema_fields = HederaPaymentReceiptResponse.model_fields
        assert "mirror_node_url" in schema_fields

    def it_has_agent_id_field(self):
        from app.schemas.hedera import HederaPaymentReceiptResponse
        schema_fields = HederaPaymentReceiptResponse.model_fields
        assert "agent_id" in schema_fields

    def it_has_task_id_field(self):
        from app.schemas.hedera import HederaPaymentReceiptResponse
        schema_fields = HederaPaymentReceiptResponse.model_fields
        assert "task_id" in schema_fields

    def it_allows_null_optional_fields(self):
        from app.schemas.hedera import HederaPaymentReceiptResponse
        resp = HederaPaymentReceiptResponse(
            transaction_id="0.0.12345@1234567890.000000000",
            status="SUCCESS",
            mirror_node_url=None,
            agent_id=None,
            task_id=None
        )
        assert resp.mirror_node_url is None
        assert resp.agent_id is None
        assert resp.task_id is None

    def it_accepts_mirror_node_url_value(self):
        from app.schemas.hedera import HederaPaymentReceiptResponse
        url = "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345-1234567890-000000000"
        resp = HederaPaymentReceiptResponse(
            transaction_id="0.0.12345@1234567890.000000000",
            status="SUCCESS",
            mirror_node_url=url,
            agent_id="agent_abc",
            task_id="task_xyz"
        )
        assert resp.mirror_node_url == url
        assert resp.agent_id == "agent_abc"
        assert resp.task_id == "task_xyz"


# ─── Mirror Node URL Construction Tests ────────────────────────────────────────


class DescribeMirrorNodeUrlConstruction:
    """mirror_node_url is constructed correctly from transaction_id."""

    def it_encodes_at_sign_as_dash(self):
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        tx_id = "0.0.12345@1234567890.000000000"
        url = service._build_mirror_node_url(tx_id)
        assert "@" not in url

    def it_includes_mirror_node_base_url(self):
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        tx_id = "0.0.12345@1234567890.000000000"
        url = service._build_mirror_node_url(tx_id)
        assert "mirrornode.hedera.com" in url

    def it_includes_encoded_transaction_id_in_path(self):
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        tx_id = "0.0.12345@1234567890.000000000"
        url = service._build_mirror_node_url(tx_id)
        # Encoded form: dots and @ replaced with dashes
        assert "0-0-12345-1234567890-000000000" in url

    def it_uses_testnet_url_by_default(self):
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        tx_id = "0.0.12345@1234567890.000000000"
        url = service._build_mirror_node_url(tx_id)
        assert "testnet" in url

    def it_includes_transactions_path_segment(self):
        from app.services.hedera_payment_service import HederaPaymentService
        service = HederaPaymentService()
        tx_id = "0.0.12345@1234567890.000000000"
        url = service._build_mirror_node_url(tx_id)
        assert "/transactions/" in url


# ─── Service: verify_receipt_on_mirror_node() ──────────────────────────────────


class DescribeVerifyReceiptOnMirrorNode:
    """HederaPaymentService.verify_receipt_on_mirror_node() behaviour."""

    @pytest.mark.asyncio
    async def it_returns_verified_true_when_transaction_is_success(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
            "hash": "0xabc123"
        })

        service = HederaPaymentService(hedera_client=mock_client)
        result = await service.verify_receipt_on_mirror_node("0.0.12345@1234567890.000000000")

        assert result["verified"] is True

    @pytest.mark.asyncio
    async def it_returns_verified_false_when_status_is_not_success(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "NOT_FOUND",
            "consensus_timestamp": None,
            "hash": None
        })

        service = HederaPaymentService(hedera_client=mock_client)
        result = await service.verify_receipt_on_mirror_node("0.0.12345@1234567890.000000000")

        assert result["verified"] is False

    @pytest.mark.asyncio
    async def it_includes_mirror_node_url_in_result(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
        })

        service = HederaPaymentService(hedera_client=mock_client)
        result = await service.verify_receipt_on_mirror_node("0.0.12345@1234567890.000000000")

        assert "mirror_node_url" in result
        assert "mirrornode.hedera.com" in result["mirror_node_url"]

    @pytest.mark.asyncio
    async def it_includes_transaction_status_in_result(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
        })

        service = HederaPaymentService(hedera_client=mock_client)
        result = await service.verify_receipt_on_mirror_node("0.0.12345@1234567890.000000000")

        assert result["transaction_status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_includes_consensus_timestamp_in_result(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
        })

        service = HederaPaymentService(hedera_client=mock_client)
        result = await service.verify_receipt_on_mirror_node("0.0.12345@1234567890.000000000")

        assert result["consensus_timestamp"] == "2026-04-03T12:00:00Z"

    @pytest.mark.asyncio
    async def it_raises_error_on_empty_transaction_id(self):
        from app.services.hedera_payment_service import (
            HederaPaymentService,
            HederaPaymentError
        )

        service = HederaPaymentService()
        with pytest.raises(HederaPaymentError):
            await service.verify_receipt_on_mirror_node("")

    @pytest.mark.asyncio
    async def it_raises_error_on_whitespace_transaction_id(self):
        from app.services.hedera_payment_service import (
            HederaPaymentService,
            HederaPaymentError
        )

        service = HederaPaymentService()
        with pytest.raises(HederaPaymentError):
            await service.verify_receipt_on_mirror_node("   ")


# ─── Service: get_payment_receipt() includes new fields ───────────────────────


class DescribeGetPaymentReceiptExtended:
    """get_payment_receipt() should include mirror_node_url in its result."""

    @pytest.mark.asyncio
    async def it_includes_mirror_node_url_in_receipt(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
            "hash": "0xabc",
            "charged_tx_fee": 500000
        })

        service = HederaPaymentService(hedera_client=mock_client)
        receipt = await service.get_payment_receipt("0.0.12345@1234567890.000000000")

        assert "mirror_node_url" in receipt
        assert "mirrornode.hedera.com" in receipt["mirror_node_url"]

    @pytest.mark.asyncio
    async def it_returns_agent_id_and_task_id_when_provided(self):
        from app.services.hedera_payment_service import HederaPaymentService

        mock_client = MagicMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
            "hash": "0xabc",
            "charged_tx_fee": 500000
        })

        service = HederaPaymentService(hedera_client=mock_client)
        receipt = await service.get_payment_receipt(
            "0.0.12345@1234567890.000000000",
            agent_id="agent_test",
            task_id="task_test"
        )

        assert receipt.get("agent_id") == "agent_test"
        assert receipt.get("task_id") == "task_test"


# ─── API Endpoint Tests ────────────────────────────────────────────────────────


class DescribeReceiptVerificationEndpoint:
    """GET /api/v1/hedera/payments/{transaction_id}/verify endpoint."""

    def it_returns_200_for_valid_transaction_id(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService

        test_app = FastAPI()
        test_app.include_router(router)

        mock_service = MagicMock(spec=HederaPaymentService)
        mock_service.verify_receipt_on_mirror_node = AsyncMock(return_value={
            "verified": True,
            "transaction_status": "SUCCESS",
            "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345-1234567890-000000000",
            "consensus_timestamp": "2026-04-03T12:00:00Z"
        })

        from app.services.hedera_payment_service import get_hedera_payment_service
        test_app.dependency_overrides[get_hedera_payment_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(
            "/v1/public/test_project/hedera/payments/0.0.12345@1234567890.000000000/verify"
        )
        assert response.status_code == 200

    def it_returns_verified_true_for_settled_transaction(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService, get_hedera_payment_service

        test_app = FastAPI()
        test_app.include_router(router)

        mock_service = MagicMock(spec=HederaPaymentService)
        mock_service.verify_receipt_on_mirror_node = AsyncMock(return_value={
            "verified": True,
            "transaction_status": "SUCCESS",
            "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345",
            "consensus_timestamp": "2026-04-03T12:00:00Z"
        })
        test_app.dependency_overrides[get_hedera_payment_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(
            "/v1/public/proj/hedera/payments/0.0.12345@1234567890.000000000/verify"
        )
        data = response.json()
        assert data["verified"] is True

    def it_returns_mirror_node_url_in_response(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService, get_hedera_payment_service

        test_app = FastAPI()
        test_app.include_router(router)

        expected_url = "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345"
        mock_service = MagicMock(spec=HederaPaymentService)
        mock_service.verify_receipt_on_mirror_node = AsyncMock(return_value={
            "verified": True,
            "transaction_status": "SUCCESS",
            "mirror_node_url": expected_url,
            "consensus_timestamp": "2026-04-03T12:00:00Z"
        })
        test_app.dependency_overrides[get_hedera_payment_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(
            "/v1/public/proj/hedera/payments/0.0.12345@1234567890.000000000/verify"
        )
        data = response.json()
        assert data["mirror_node_url"] == expected_url

    def it_returns_transaction_status_in_response(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService, get_hedera_payment_service

        test_app = FastAPI()
        test_app.include_router(router)

        mock_service = MagicMock(spec=HederaPaymentService)
        mock_service.verify_receipt_on_mirror_node = AsyncMock(return_value={
            "verified": False,
            "transaction_status": "PENDING",
            "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/abc",
            "consensus_timestamp": None
        })
        test_app.dependency_overrides[get_hedera_payment_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(
            "/v1/public/proj/hedera/payments/some_tx_id/verify"
        )
        data = response.json()
        assert data["transaction_status"] == "PENDING"

    def it_passes_transaction_id_from_path_to_service(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.hedera_payments import router
        from app.services.hedera_payment_service import HederaPaymentService, get_hedera_payment_service

        test_app = FastAPI()
        test_app.include_router(router)

        mock_service = MagicMock(spec=HederaPaymentService)
        mock_service.verify_receipt_on_mirror_node = AsyncMock(return_value={
            "verified": True,
            "transaction_status": "SUCCESS",
            "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/abc",
            "consensus_timestamp": "2026-04-03T12:00:00Z"
        })
        test_app.dependency_overrides[get_hedera_payment_service] = lambda: mock_service

        client = TestClient(test_app)
        client.get("/v1/public/proj/hedera/payments/my_tx_id_123/verify")

        mock_service.verify_receipt_on_mirror_node.assert_called_once_with("my_tx_id_123")
