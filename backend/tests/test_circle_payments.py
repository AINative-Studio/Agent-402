"""
Tests for Circle agent payment functionality.

Tests cover:
- Agent payment schemas validation
- Agent payment service methods
- Agent payment API endpoint

Uses BDD-style test structure with pytest-describe style.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError


# ============================================================================
# Schema Tests
# ============================================================================

class TestAgentPaymentRequestSchema:
    """Tests for AgentPaymentRequest validation."""

    def test_accepts_valid_payment_request(self):
        """Should accept a valid payment request."""
        from app.schemas.circle import AgentPaymentRequest

        request = AgentPaymentRequest(
            amount="10.00",
            reason="Task completion payment",
            task_id="task_123"
        )

        assert request.amount == "10.00"
        assert request.reason == "Task completion payment"
        assert request.task_id == "task_123"

    def test_accepts_payment_without_task_id(self):
        """Should accept payment request without optional task_id."""
        from app.schemas.circle import AgentPaymentRequest

        request = AgentPaymentRequest(
            amount="50.00",
            reason="Bonus payment"
        )

        assert request.amount == "50.00"
        assert request.reason == "Bonus payment"
        assert request.task_id is None

    def test_rejects_negative_amount(self):
        """Should reject negative payment amounts."""
        from app.schemas.circle import AgentPaymentRequest

        with pytest.raises(ValidationError) as exc_info:
            AgentPaymentRequest(
                amount="-10.00",
                reason="Invalid payment"
            )

        errors = exc_info.value.errors()
        assert any("positive" in str(e).lower() for e in errors)

    def test_rejects_zero_amount(self):
        """Should reject zero payment amounts."""
        from app.schemas.circle import AgentPaymentRequest

        with pytest.raises(ValidationError) as exc_info:
            AgentPaymentRequest(
                amount="0.00",
                reason="Invalid payment"
            )

        errors = exc_info.value.errors()
        assert any("positive" in str(e).lower() for e in errors)

    def test_rejects_amount_exceeding_limit(self):
        """Should reject amounts exceeding $10,000 limit."""
        from app.schemas.circle import AgentPaymentRequest

        with pytest.raises(ValidationError) as exc_info:
            AgentPaymentRequest(
                amount="15000.00",
                reason="Large payment"
            )

        errors = exc_info.value.errors()
        assert any("maximum" in str(e).lower() for e in errors)

    def test_rejects_invalid_amount_format(self):
        """Should reject non-numeric amount strings."""
        from app.schemas.circle import AgentPaymentRequest

        with pytest.raises(ValidationError) as exc_info:
            AgentPaymentRequest(
                amount="not_a_number",
                reason="Invalid payment"
            )

        errors = exc_info.value.errors()
        assert any("decimal" in str(e).lower() for e in errors)

    def test_requires_reason_field(self):
        """Should require reason field."""
        from app.schemas.circle import AgentPaymentRequest

        with pytest.raises(ValidationError) as exc_info:
            AgentPaymentRequest(amount="10.00")

        errors = exc_info.value.errors()
        assert any("reason" in str(e).lower() for e in errors)


class TestAgentPaymentResponseSchema:
    """Tests for AgentPaymentResponse schema."""

    def test_creates_valid_response(self):
        """Should create a valid payment response."""
        from app.schemas.circle import AgentPaymentResponse, TransferStatus

        response = AgentPaymentResponse(
            payment_id="payment_test_123",
            agent_id="agent_001",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            amount="10.00",
            currency="USD",
            reason="Task completion",
            transfer_id="transfer_123",
            circle_transfer_id="circle_xfr_123",
            status=TransferStatus.PENDING,
            source_wallet_id="wallet_treasury",
            destination_wallet_id="wallet_agent",
            created_at=datetime.now(timezone.utc)
        )

        assert response.payment_id == "payment_test_123"
        assert response.status == TransferStatus.PENDING
        assert response.transaction_hash is None
        assert response.completed_at is None

    def test_response_with_complete_status(self):
        """Should create response with complete status and transaction hash."""
        from app.schemas.circle import AgentPaymentResponse, TransferStatus

        now = datetime.now(timezone.utc)
        response = AgentPaymentResponse(
            payment_id="payment_test_123",
            agent_id="agent_001",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            amount="10.00",
            currency="USD",
            reason="Task completion",
            transfer_id="transfer_123",
            circle_transfer_id="circle_xfr_123",
            status=TransferStatus.COMPLETE,
            transaction_hash="0xabc123def456",
            source_wallet_id="wallet_treasury",
            destination_wallet_id="wallet_agent",
            created_at=now,
            completed_at=now
        )

        assert response.status == TransferStatus.COMPLETE
        assert response.transaction_hash == "0xabc123def456"
        assert response.completed_at is not None


# ============================================================================
# Service Tests
# ============================================================================

class TestCircleWalletServicePayments:
    """Tests for CircleWalletService payment methods."""

    @pytest.fixture
    def mock_zerodb_client(self):
        """Mock ZeroDB client for testing."""
        client = MagicMock()
        client.query_rows = AsyncMock(return_value={"rows": []})
        client.insert_row = AsyncMock(return_value={"row_id": "test_row_123"})
        client.update_row = AsyncMock(return_value={"row_id": "test_row_123"})
        return client

    @pytest.fixture
    def mock_circle_service(self):
        """Mock Circle service for testing."""
        service = MagicMock()
        service.create_transfer = AsyncMock(return_value={
            "data": {
                "id": "circle_transfer_test_123",
                "state": "INITIATED"
            }
        })
        service.get_transfer = AsyncMock(return_value={
            "data": {
                "id": "circle_transfer_test_123",
                "state": "COMPLETE",
                "txHash": "0xabc123def456"
            }
        })
        service.get_wallet_balance = AsyncMock(return_value={
            "amount": "1000.00",
            "currency": "USDC"
        })
        return service

    @pytest.fixture
    def wallet_service(self, mock_zerodb_client, mock_circle_service):
        """Create wallet service with mocked dependencies."""
        from app.services.circle_wallet_service import CircleWalletService

        service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        return service

    @pytest.fixture
    def sample_wallet_data(self):
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

    @pytest.mark.asyncio
    async def test_get_treasury_wallet_by_type(
        self,
        wallet_service,
        mock_zerodb_client,
        sample_wallet_data
    ):
        """Should return wallet with treasury type."""
        treasury_wallet = {**sample_wallet_data}
        treasury_wallet["wallet_type"] = "treasury"

        mock_zerodb_client.query_rows = AsyncMock(
            return_value={"rows": [treasury_wallet]}
        )

        result = await wallet_service.get_treasury_wallet("proj_test")

        assert result["wallet_type"] == "treasury"

    @pytest.mark.asyncio
    async def test_get_treasury_wallet_by_description(
        self,
        wallet_service,
        mock_zerodb_client,
        sample_wallet_data
    ):
        """Should return wallet with treasury in description."""
        treasury_wallet = {**sample_wallet_data}
        treasury_wallet["wallet_type"] = "other"
        treasury_wallet["description"] = "Platform Treasury"

        mock_zerodb_client.query_rows = AsyncMock(side_effect=[
            {"rows": []},  # First query by type
            {"rows": [treasury_wallet]}  # Second query for all wallets
        ])

        result = await wallet_service.get_treasury_wallet("proj_test")

        assert "treasury" in result["description"].lower()

    @pytest.mark.asyncio
    async def test_get_treasury_wallet_raises_error_when_not_found(
        self,
        wallet_service,
        mock_zerodb_client
    ):
        """Should raise error when no treasury wallet exists."""
        from app.services.circle_service import WalletNotFoundError

        mock_zerodb_client.query_rows = AsyncMock(
            return_value={"rows": []}
        )

        with pytest.raises(WalletNotFoundError):
            await wallet_service.get_treasury_wallet("proj_test")

    @pytest.mark.asyncio
    async def test_pay_agent_raises_error_when_wallet_not_found(
        self,
        wallet_service,
        mock_zerodb_client
    ):
        """Should raise error when agent has no wallet."""
        from app.services.circle_service import WalletNotFoundError

        # Setup: No wallet found for agent
        mock_zerodb_client.query_rows = AsyncMock(return_value={"rows": []})

        # Execute & Verify
        with pytest.raises(WalletNotFoundError):
            await wallet_service.pay_agent(
                project_id="proj_test",
                agent_id="agent_nonexistent",
                amount="10.00",
                reason="Payment"
            )


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestAgentPaymentEndpoint:
    """Tests for agent payment API endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    def test_pay_agent_requires_authentication(self, test_client):
        """Should require X-API-Key header."""
        response = test_client.post(
            "/v1/public/proj_test/agents/agent_001/pay",
            json={
                "amount": "10.00",
                "reason": "Task completion"
            }
        )

        # Should return 401 without API key
        assert response.status_code == 401

    def test_pay_agent_validates_request_body(self, test_client):
        """Should validate request body schema."""
        response = test_client.post(
            "/v1/public/proj_test/agents/agent_001/pay",
            headers={"X-API-Key": "demo_key_user1_abc123"},
            json={
                "amount": "-10.00",  # Invalid negative amount
                "reason": "Task completion"
            }
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_get_payment_requires_authentication(self, test_client):
        """Should require X-API-Key header."""
        response = test_client.get(
            "/v1/public/proj_test/agents/agent_001/payments/payment_123"
        )

        assert response.status_code == 401


# ============================================================================
# Script Tests
# ============================================================================

class TestCreateAgentWalletsScript:
    """Tests for the create_agent_wallets.py script."""

    def test_defines_three_agents(self):
        """Should define the 3 agents with correct properties."""
        import sys
        from pathlib import Path

        # Add scripts directory to path
        scripts_path = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))

        from create_agent_wallets import AGENTS

        assert len(AGENTS) == 3

        agent_roles = {agent["role"] for agent in AGENTS}
        assert agent_roles == {"analyst", "compliance", "transaction"}

        wallet_types = {agent["wallet_type"] for agent in AGENTS}
        assert wallet_types == {"analyst", "compliance", "transaction"}

        # All agents should have valid DIDs
        for agent in AGENTS:
            assert agent["did"].startswith("did:key:z6Mk")
            assert len(agent["did"]) > 20

    def test_has_correct_agent_dids(self):
        """Should have the correct agent DIDs from deployment."""
        import sys
        from pathlib import Path

        scripts_path = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))

        from create_agent_wallets import AGENTS

        # Verify DIDs match the arc-testnet.json deployment
        expected_dids = {
            "analyst": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            "compliance": "did:key:z6Mki9E8kZT3ybvrYqVqJQrW9vHn6YuVjAVdHqzBGbYQk2Jp",
            "transaction": "did:key:z6MkkKQ3EbHjE4VPZqL6LS2b4kXy7nZvJqW9vHn6YuVjAVdH"
        }

        for agent in AGENTS:
            role = agent["role"]
            assert agent["did"] == expected_dids[role], f"DID mismatch for {role}"

    def test_default_project_id_defined(self):
        """Should have a default project ID defined."""
        import sys
        from pathlib import Path

        scripts_path = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))

        from create_agent_wallets import DEFAULT_PROJECT_ID

        assert DEFAULT_PROJECT_ID is not None
        assert len(DEFAULT_PROJECT_ID) > 0
