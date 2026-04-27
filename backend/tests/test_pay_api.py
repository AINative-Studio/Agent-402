"""
Tests for POST /v1/public/pay — stablecoin payment acceptance.

Refs AINative-Studio/core#2584
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PAY_URL = "/v1/public/pay"

VALID_PAYLOAD = {
    "wallet_address": "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
    "amount": 10.0,
    "currency": "USDC",
    "network": "hedera-testnet",
    "tx_hash": "0.0.123456@1234567890.000000000",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_zerodb_insert():
    """Patch ZeroDB insert so persistence does not fail."""
    mock_client = MagicMock()
    mock_client.insert_row = AsyncMock(return_value={"row_id": "test_row"})
    return patch("app.api.pay.get_zerodb_client", return_value=mock_client)


# ---------------------------------------------------------------------------
# Payment proof required
# ---------------------------------------------------------------------------

def test_pay_no_proof_returns_402():
    payload = {
        "wallet_address": "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
        "amount": 5.0,
    }
    resp = client.post(PAY_URL, json=payload)
    assert resp.status_code == 402
    body = resp.json()
    assert body["error_code"] == "PAYMENT_PROOF_REQUIRED"


# ---------------------------------------------------------------------------
# Hedera tx_hash path
# ---------------------------------------------------------------------------

def test_pay_hedera_verified():
    verified_result = {"status": "SUCCESS", "verified": True}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_hedera_payment", new=AsyncMock(return_value=verified_result)):
        resp = client.post(PAY_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 201
    body = resp.json()
    assert body["tx_status"] == "SUCCESS"
    assert body["credits_added"] == 1000  # 10 USDC * 100
    assert body["receipt_id"].startswith("rcpt_")
    assert body["wallet_address"] == VALID_PAYLOAD["wallet_address"].lower()


def test_pay_hedera_unverified_marks_pending():
    unverified_result = {"status": "UNKNOWN", "verified": False}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_hedera_payment", new=AsyncMock(return_value=unverified_result)):
        resp = client.post(PAY_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 201
    assert resp.json()["tx_status"] == "pending"


# ---------------------------------------------------------------------------
# Circle transfer_id path
# ---------------------------------------------------------------------------

def test_pay_circle_verified():
    payload = {
        "wallet_address": "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
        "amount": 5.0,
        "currency": "USDC",
        "network": "arc-testnet",
        "transfer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    }
    verified_result = {"status": "complete", "verified": True}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_circle_payment", new=AsyncMock(return_value=verified_result)):
        resp = client.post(PAY_URL, json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["tx_status"] == "complete"
    assert body["credits_added"] == 500  # 5 USDC * 100


# ---------------------------------------------------------------------------
# Gasless / X-Payment-Signature path
# ---------------------------------------------------------------------------

def test_pay_gasless_signature_verified():
    payload = {
        "wallet_address": "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
        "amount": 2.0,
        "currency": "USDC",
        "network": "arc-testnet",
    }
    verified_result = {"status": "gasless_verified", "verified": True, "data": {}}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_gasless_signature", new=AsyncMock(return_value=verified_result)):
        resp = client.post(
            PAY_URL,
            json=payload,
            headers={"X-Payment-Signature": "sig_mock_value"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["tx_status"] == "gasless_verified"
    assert body["credits_added"] == 200


# ---------------------------------------------------------------------------
# Credit calculation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("amount,expected_credits", [
    (1.0, 100),
    (0.5, 50),
    (100.0, 10000),
    (0.01, 1),
])
def test_pay_credit_calculation(amount, expected_credits):
    payload = {**VALID_PAYLOAD, "amount": amount}
    verified_result = {"status": "SUCCESS", "verified": True}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_hedera_payment", new=AsyncMock(return_value=verified_result)):
        resp = client.post(PAY_URL, json=payload)

    assert resp.status_code == 201
    assert resp.json()["credits_added"] == expected_credits


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_pay_zero_amount_rejected():
    payload = {**VALID_PAYLOAD, "amount": 0}
    resp = client.post(PAY_URL, json=payload)
    assert resp.status_code == 422


def test_pay_negative_amount_rejected():
    payload = {**VALID_PAYLOAD, "amount": -5.0}
    resp = client.post(PAY_URL, json=payload)
    assert resp.status_code == 422


def test_pay_missing_wallet_rejected():
    payload = {"amount": 10.0, "tx_hash": "some_tx"}
    resp = client.post(PAY_URL, json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Wallet address normalised to lowercase
# ---------------------------------------------------------------------------

def test_pay_wallet_lowercased():
    payload = {**VALID_PAYLOAD, "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"}
    verified_result = {"status": "SUCCESS", "verified": True}
    with _mock_zerodb_insert(), \
         patch("app.api.pay._verify_hedera_payment", new=AsyncMock(return_value=verified_result)):
        resp = client.post(PAY_URL, json=payload)

    assert resp.status_code == 201
    assert resp.json()["wallet_address"] == payload["wallet_address"].lower()


# ---------------------------------------------------------------------------
# ZeroDB persistence failure is non-fatal
# ---------------------------------------------------------------------------

def test_pay_zerodb_failure_still_returns_201():
    mock_client = MagicMock()
    mock_client.insert_row = AsyncMock(side_effect=Exception("ZeroDB down"))
    verified_result = {"status": "SUCCESS", "verified": True}
    with patch("app.api.pay.get_zerodb_client", return_value=mock_client), \
         patch("app.api.pay._verify_hedera_payment", new=AsyncMock(return_value=verified_result)):
        resp = client.post(PAY_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 201
