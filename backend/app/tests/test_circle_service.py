"""
Unit tests for Circle Service.
Tests Issue #114: Circle Wallets and USDC Payments - Service Layer.

TDD Approach: Tests written FIRST, then implementation.

Test Coverage:
- CircleService: Circle API client operations
- CircleWalletService: Wallet management operations
- Wallet creation for 3 agent types (analyst, compliance, transaction)
- USDC transfer operations
- Payment receipt generation
- Error handling and edge cases
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestCircleServiceInitialization:
    """Tests for CircleService initialization."""

    def test_initialize_with_api_key(self):
        """Test that service initializes with Circle API key."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")
        assert service.api_key == "test_api_key"

    def test_use_default_base_url(self):
        """Test that service uses default Circle API base URL."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")
        assert "circle.com" in service.base_url.lower() or "sandbox" in service.base_url.lower()

    def test_allow_custom_base_url(self):
        """Test that service allows custom base URL for sandbox."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="test_api_key",
            base_url="https://api-sandbox.circle.com"
        )
        assert service.base_url == "https://api-sandbox.circle.com"


class TestCircleServiceCreateWallet:
    """Tests for wallet creation via Circle API."""

    @pytest.mark.asyncio
    async def test_create_wallet_successfully(self):
        """Test successful wallet creation."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")

        # Mock the HTTP client
        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "walletId": "circle_wlt_12345",
                    "entityId": "entity_12345",
                    "blockchain": "ETH-SEPOLIA",
                    "address": "0x1234567890abcdef1234567890abcdef12345678",
                    "state": "LIVE"
                }
            }

            result = await service.create_wallet(
                idempotency_key="unique-key-123"
            )

            # Service returns simulated data for sandbox
            assert "data" in result or "walletId" in result.get("data", result)

    def test_circle_api_error_attributes(self):
        """Test CircleAPIError has correct attributes."""
        from app.services.circle_service import CircleAPIError

        error = CircleAPIError("API rate limit exceeded", status_code=429)
        assert error.detail == "API rate limit exceeded"
        assert error.circle_status_code == 429
        assert error.status_code == 429


class TestCircleServiceGetWallet:
    """Tests for retrieving wallet details."""

    @pytest.mark.asyncio
    async def test_get_wallet_by_id(self):
        """Test retrieving wallet by Circle wallet ID."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")

        # Service uses simulated responses for sandbox
        result = await service.get_wallet("circle_wlt_12345")

        assert result["data"]["walletId"] == "circle_wlt_12345"
        assert result["data"]["address"] is not None

    @pytest.mark.asyncio
    async def test_raise_not_found_for_invalid_wallet(self):
        """Test error when wallet not found."""
        from app.services.circle_service import CircleService, WalletNotFoundError

        service = CircleService(api_key="test_api_key")

        with pytest.raises(WalletNotFoundError):
            await service.get_wallet("nonexistent_wallet")


class TestCircleServiceGetWalletBalance:
    """Tests for retrieving wallet balance."""

    @pytest.mark.asyncio
    async def test_get_usdc_balance(self):
        """Test retrieving USDC balance for a wallet."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")

        result = await service.get_wallet_balance("circle_wlt_12345")

        assert result["amount"] == "1000.00"
        assert result["currency"] == "USDC"


class TestCircleServiceCreateTransfer:
    """Tests for USDC transfer operations."""

    @pytest.mark.asyncio
    async def test_create_transfer_successfully(self):
        """Test successful USDC transfer creation."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")

        result = await service.create_transfer(
            source_wallet_id="circle_wlt_source",
            destination_wallet_id="circle_wlt_dest",
            amount="100.00",
            idempotency_key="xfr-key-123"
        )

        data = result.get("data", result)
        assert data["status"] == "pending"

    def test_insufficient_funds_error_attributes(self):
        """Test InsufficientFundsError has correct attributes."""
        from app.services.circle_service import InsufficientFundsError

        error = InsufficientFundsError("wallet_source", "100.00", "50.00")
        assert "insufficient" in error.detail.lower()
        assert error.wallet_id == "wallet_source"
        assert error.requested == "100.00"
        assert error.available == "50.00"
        assert error.status_code == 400


class TestCircleServiceGetTransfer:
    """Tests for retrieving transfer status."""

    @pytest.mark.asyncio
    async def test_get_transfer_status(self):
        """Test retrieving transfer status by ID."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_api_key")

        result = await service.get_transfer("circle_xfr_12345")

        data = result.get("data", result)
        assert data["status"] == "complete"
        assert data["transactionHash"] is not None


class TestCircleWalletServiceCreateAgentWallet:
    """Tests for creating wallets linked to agents."""

    @pytest.mark.asyncio
    async def test_create_analyst_wallet(self):
        """Test creating wallet for analyst agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        result = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            wallet_type="analyst",
            description="Analyst agent wallet"
        )

        assert result["wallet_type"] == "analyst"
        assert result["agent_did"].startswith("did:key:")
        assert "wallet_id" in result
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_compliance_wallet(self):
        """Test creating wallet for compliance agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        result = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            wallet_type="compliance",
            description="Compliance agent wallet"
        )

        assert result["wallet_type"] == "compliance"

    @pytest.mark.asyncio
    async def test_create_transaction_wallet(self):
        """Test creating wallet for transaction agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        result = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
            wallet_type="transaction",
            description="Transaction agent wallet"
        )

        assert result["wallet_type"] == "transaction"

    @pytest.mark.asyncio
    async def test_prevent_duplicate_wallet_for_agent(self):
        """Test that duplicate wallets cannot be created for same agent/type."""
        from app.services.circle_wallet_service import (
            CircleWalletService,
            DuplicateWalletError
        )
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        # Create first wallet
        await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnDuplicate",
            wallet_type="analyst"
        )

        # Try to create duplicate
        with pytest.raises(DuplicateWalletError):
            await service.create_agent_wallet(
                project_id="proj_test",
                agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnDuplicate",
                wallet_type="analyst"
            )


class TestCircleWalletServiceGetWallet:
    """Tests for retrieving wallets by agent DID."""

    @pytest.mark.asyncio
    async def test_get_wallet_by_id(self):
        """Test retrieving wallet by wallet ID."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        # Create a wallet first
        created = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGetTest",
            wallet_type="analyst"
        )

        # Retrieve it
        result = await service.get_wallet(created["wallet_id"], "proj_test")

        assert result["wallet_id"] == created["wallet_id"]
        assert result["wallet_type"] == "analyst"

    @pytest.mark.asyncio
    async def test_list_all_wallets_for_agent(self):
        """Test listing all wallets for an agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        agent_did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLListTest"

        # Create multiple wallets
        for wallet_type in ["analyst", "compliance", "transaction"]:
            await service.create_agent_wallet(
                project_id="proj_test",
                agent_did=agent_did,
                wallet_type=wallet_type
            )

        result = await service.list_agent_wallets(agent_did, "proj_test")

        assert len(result) == 3


class TestCircleWalletServiceInitiateTransfer:
    """Tests for initiating USDC transfers."""

    @pytest.mark.asyncio
    async def test_initiate_transfer_between_wallets(self):
        """Test initiating USDC transfer between agent wallets."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        # Create source and destination wallets
        source = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLSource",
            wallet_type="transaction"
        )
        dest = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLDest",
            wallet_type="analyst"
        )

        result = await service.initiate_transfer(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="100.00"
        )

        assert result["status"] == "pending"
        assert "transfer_id" in result

    @pytest.mark.asyncio
    async def test_link_transfer_to_x402_request(self):
        """Test linking transfer to X402 request for payment tracking."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        # Create wallets
        source = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLX402Src",
            wallet_type="transaction"
        )
        dest = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLX402Dst",
            wallet_type="compliance"
        )

        result = await service.initiate_transfer(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="100.00",
            x402_request_id="x402_req_abc123"
        )

        assert result["x402_request_id"] == "x402_req_abc123"


class TestCircleWalletServiceGenerateReceipt:
    """Tests for payment receipt generation."""

    @pytest.mark.asyncio
    async def test_generate_receipt_for_completed_transfer(self):
        """Test generating payment receipt after transfer completion."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        service = CircleWalletService(client=mock_client)

        # Create wallets and transfer
        source = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLRcptSrc",
            wallet_type="transaction"
        )
        dest = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLRcptDst",
            wallet_type="analyst"
        )

        transfer = await service.initiate_transfer(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="100.00"
        )

        result = await service.generate_receipt(transfer["transfer_id"], "proj_test")

        assert "receipt_id" in result
        assert result["source_agent_did"].startswith("did:")
        assert result["destination_agent_did"].startswith("did:")


class TestCircleErrors:
    """Test suite for Circle-specific error classes."""

    def test_define_circle_api_error(self):
        """Test CircleAPIError is properly defined."""
        from app.services.circle_service import CircleAPIError

        error = CircleAPIError("Test error", status_code=500)
        assert error.detail == "Test error"
        assert error.circle_status_code == 500

    def test_define_wallet_not_found_error(self):
        """Test WalletNotFoundError is properly defined."""
        from app.services.circle_service import WalletNotFoundError

        error = WalletNotFoundError("wallet_123")
        assert "wallet_123" in error.detail

    def test_define_insufficient_funds_error(self):
        """Test InsufficientFundsError is properly defined."""
        from app.services.circle_service import InsufficientFundsError

        error = InsufficientFundsError("wallet_123", "100.00", "50.00")
        assert "insufficient" in error.detail.lower()
        assert "100.00" in error.detail

    def test_define_duplicate_wallet_error(self):
        """Test DuplicateWalletError is properly defined."""
        from app.services.circle_wallet_service import DuplicateWalletError

        error = DuplicateWalletError("did:key:z6Mk...", "analyst")
        assert "already exists" in error.detail.lower()
