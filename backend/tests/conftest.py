"""
Pytest fixtures for backend tests.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client for testing."""
    client = MagicMock()
    client.query_rows = AsyncMock(return_value={"rows": []})
    client.insert_row = AsyncMock(return_value={"row_id": "test_row_123"})
    client.update_row = AsyncMock(return_value={"row_id": "test_row_123"})
    client.delete_row = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_circle_service():
    """Mock Circle service for testing."""
    service = MagicMock()

    # Mock wallet set creation
    service.create_wallet_set = AsyncMock(return_value={
        "data": {
            "walletSet": {
                "id": "ws_test_123",
                "custodyType": "DEVELOPER",
                "createDate": datetime.now(timezone.utc).isoformat()
            }
        }
    })

    # Mock wallet creation
    service.create_wallet = AsyncMock(return_value={
        "data": {
            "wallets": [{
                "id": "circle_wallet_test_123",
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "blockchain": "ARC-TESTNET",
                "state": "LIVE"
            }]
        }
    })

    # Mock wallet balance
    service.get_wallet_balance = AsyncMock(return_value={
        "amount": "1000.00",
        "currency": "USDC",
        "data": {
            "tokenBalances": [{
                "amount": "1000.00",
                "token": {"symbol": "USDC"}
            }]
        }
    })

    # Mock transfer creation
    service.create_transfer = AsyncMock(return_value={
        "data": {
            "id": "circle_transfer_test_123",
            "state": "INITIATED"
        }
    })

    # Mock transfer status
    service.get_transfer = AsyncMock(return_value={
        "data": {
            "id": "circle_transfer_test_123",
            "state": "COMPLETE",
            "txHash": "0xabc123def456"
        }
    })

    return service


@pytest.fixture
def sample_wallet_data() -> Dict[str, Any]:
    """Sample wallet data for testing."""
    return {
        "wallet_id": "wallet_test_123",
        "project_id": "proj_test",
        "circle_wallet_id": "circle_wallet_test_123",
        "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "wallet_type": "analyst",
        "status": "active",
        "blockchain_address": "0x1234567890abcdef1234567890abcdef12345678",
        "blockchain": "ARC-TESTNET",
        "balance": "100.00",
        "description": "Test wallet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_transfer_data() -> Dict[str, Any]:
    """Sample transfer data for testing."""
    return {
        "transfer_id": "transfer_test_123",
        "project_id": "proj_test",
        "circle_transfer_id": "circle_xfr_test_123",
        "source_wallet_id": "wallet_source_123",
        "destination_wallet_id": "wallet_dest_456",
        "amount": "10.00",
        "currency": "USD",
        "status": "pending",
        "circle_state": "INITIATED",
        "x402_request_id": None,
        "transaction_hash": None,
        "metadata": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }


@pytest.fixture
def sample_payment_data() -> Dict[str, Any]:
    """Sample agent payment data for testing."""
    return {
        "payment_id": "payment_test_123",
        "project_id": "proj_test",
        "agent_id": "agent_test_001",
        "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "amount": "10.00",
        "currency": "USD",
        "reason": "Task completion payment",
        "task_id": "task_test_123",
        "transfer_id": "transfer_test_123",
        "circle_transfer_id": "circle_xfr_test_123",
        "status": "pending",
        "transaction_hash": None,
        "source_wallet_id": "wallet_treasury",
        "destination_wallet_id": "wallet_agent_001",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
