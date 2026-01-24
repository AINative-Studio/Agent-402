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
import uuid
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
        assert "circle.com" in service.base_url.lower()

    def test_allow_custom_base_url(self):
        """Test that service allows custom base URL for sandbox."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="test_api_key",
            base_url="https://api-sandbox.circle.com"
        )
        assert service.base_url == "https://api-sandbox.circle.com"

    def test_initialize_with_entity_secret(self):
        """Test that service accepts entity secret."""
        from app.services.circle_service import CircleService

        entity_secret = "a" * 64  # 32 bytes hex
        service = CircleService(
            api_key="test_api_key",
            entity_secret=entity_secret
        )
        assert service.entity_secret == entity_secret


class TestCircleServiceCreateWalletSet:
    """Tests for wallet set creation via Circle API."""

    @pytest.mark.asyncio
    async def test_create_wallet_set_successfully(self):
        """Test successful wallet set creation."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="TEST_API_KEY:123:456",
            entity_secret="a" * 64
        )

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request, \
             patch.object(service, '_get_entity_secret_ciphertext', new_callable=AsyncMock) as mock_cipher:
            mock_cipher.return_value = "encrypted_ciphertext_base64"
            mock_request.return_value = {
                "data": {
                    "walletSet": {
                        "id": str(uuid.uuid4()),
                        "custodyType": "DEVELOPER",
                        "createDate": "2024-01-01T00:00:00Z",
                        "updateDate": "2024-01-01T00:00:00Z"
                    }
                }
            }

            result = await service.create_wallet_set(
                idempotency_key="unique-key-123",
                name="Test Wallet Set"
            )

            assert "data" in result
            assert "walletSet" in result["data"]
            mock_request.assert_called_once()


class TestCircleServiceCreateWallet:
    """Tests for wallet creation via Circle API."""

    @pytest.mark.asyncio
    async def test_create_wallet_successfully(self):
        """Test successful wallet creation."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="TEST_API_KEY:123:456",
            entity_secret="a" * 64
        )

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request, \
             patch.object(service, '_get_entity_secret_ciphertext', new_callable=AsyncMock) as mock_cipher:
            mock_cipher.return_value = "encrypted_ciphertext_base64"
            mock_request.return_value = {
                "data": {
                    "wallets": [{
                        "id": str(uuid.uuid4()),
                        "address": "0x1234567890abcdef1234567890abcdef12345678",
                        "blockchain": "ARC-TESTNET",
                        "state": "LIVE",
                        "walletSetId": str(uuid.uuid4())
                    }]
                }
            }

            result = await service.create_wallet(
                idempotency_key="unique-key-123",
                wallet_set_id=str(uuid.uuid4())
            )

            assert "data" in result
            assert "wallets" in result["data"]
            assert len(result["data"]["wallets"]) > 0
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_wallet_requires_wallet_set_id(self):
        """Test that wallet creation requires wallet_set_id."""
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(
            api_key="TEST_API_KEY:123:456",
            entity_secret="a" * 64
        )

        with pytest.raises(CircleAPIError) as exc_info:
            await service.create_wallet(
                idempotency_key="unique-key-123"
            )

        assert "wallet_set_id is required" in exc_info.value.detail

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

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            wallet_id = str(uuid.uuid4())
            mock_request.return_value = {
                "data": {
                    "wallet": {
                        "id": wallet_id,
                        "address": "0x1234567890abcdef1234567890abcdef12345678",
                        "blockchain": "ARC-TESTNET",
                        "state": "LIVE"
                    }
                }
            }

            result = await service.get_wallet(wallet_id)

            assert "data" in result
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_raise_not_found_for_invalid_wallet(self):
        """Test error when wallet not found."""
        from app.services.circle_service import CircleService, WalletNotFoundError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = WalletNotFoundError("nonexistent_wallet")

            with pytest.raises(WalletNotFoundError):
                await service.get_wallet("nonexistent_wallet")


class TestCircleServiceGetWalletBalance:
    """Tests for retrieving wallet balance."""

    @pytest.mark.asyncio
    async def test_get_usdc_balance(self):
        """Test retrieving USDC balance for a wallet."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "tokenBalances": [{
                        "token": {
                            "id": str(uuid.uuid4()),
                            "symbol": "USDC",
                            "name": "USD Coin"
                        },
                        "amount": "1000.00"
                    }]
                }
            }

            result = await service.get_wallet_balance(str(uuid.uuid4()))

            assert result["amount"] == "1000.00"
            assert result["currency"] == "USDC"

    @pytest.mark.asyncio
    async def test_get_balance_empty_wallet(self):
        """Test balance for empty wallet returns zero."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "tokenBalances": []
                }
            }

            result = await service.get_wallet_balance(str(uuid.uuid4()))

            assert result["amount"] == "0"
            assert result["currency"] == "USDC"


class TestCircleServiceCreateTransfer:
    """Tests for USDC transfer operations."""

    @pytest.mark.asyncio
    async def test_create_transfer_successfully(self):
        """Test successful USDC transfer creation."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="TEST_API_KEY:123:456",
            entity_secret="a" * 64
        )

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request, \
             patch.object(service, '_get_entity_secret_ciphertext', new_callable=AsyncMock) as mock_cipher:
            mock_cipher.return_value = "encrypted_ciphertext_base64"
            mock_request.return_value = {
                "data": {
                    "id": str(uuid.uuid4()),
                    "state": "INITIATED"
                }
            }

            result = await service.create_transfer(
                source_wallet_id=str(uuid.uuid4()),
                destination_address="0x1234567890abcdef1234567890abcdef12345678",
                amount="100.00",
                idempotency_key="xfr-key-123"
            )

            assert "data" in result
            assert result["data"]["state"] == "INITIATED"

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

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            transfer_id = str(uuid.uuid4())
            mock_request.return_value = {
                "data": {
                    "id": transfer_id,
                    "state": "COMPLETE",
                    "txHash": "0xabcdef1234567890"
                }
            }

            result = await service.get_transfer(transfer_id)

            assert "data" in result
            assert result["data"]["state"] == "COMPLETE"
            assert result["data"]["txHash"] is not None

    @pytest.mark.asyncio
    async def test_raise_not_found_for_invalid_transfer(self):
        """Test error when transfer not found."""
        from app.services.circle_service import CircleService, TransferNotFoundError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = TransferNotFoundError("nonexistent_transfer")

            with pytest.raises(TransferNotFoundError):
                await service.get_transfer("nonexistent_transfer")


def create_mock_circle_service():
    """Create a mock Circle service for testing wallet service."""
    from app.services.circle_service import CircleService

    mock_service = MagicMock(spec=CircleService)

    # Mock create_wallet_set
    async def mock_create_wallet_set(idempotency_key, name=None):
        return {
            "data": {
                "walletSet": {
                    "id": str(uuid.uuid4()),
                    "custodyType": "DEVELOPER"
                }
            }
        }
    mock_service.create_wallet_set = AsyncMock(side_effect=mock_create_wallet_set)

    # Mock create_wallet
    async def mock_create_wallet(idempotency_key, blockchain="ARC-TESTNET", wallet_set_id=None, count=1, metadata=None):
        return {
            "data": {
                "wallets": [{
                    "id": str(uuid.uuid4()),
                    "address": f"0x{uuid.uuid4().hex}",
                    "blockchain": blockchain,
                    "state": "LIVE",
                    "walletSetId": wallet_set_id
                }]
            }
        }
    mock_service.create_wallet = AsyncMock(side_effect=mock_create_wallet)

    # Mock get_wallet_balance
    async def mock_get_wallet_balance(wallet_id):
        return {
            "data": {"tokenBalances": [{"token": {"symbol": "USDC"}, "amount": "1000.00"}]},
            "amount": "1000.00",
            "currency": "USDC"
        }
    mock_service.get_wallet_balance = AsyncMock(side_effect=mock_get_wallet_balance)

    # Mock create_transfer
    async def mock_create_transfer(source_wallet_id, destination_address, amount, idempotency_key, blockchain="ARC-TESTNET", token_address=None, fee_level="MEDIUM"):
        return {
            "data": {
                "id": str(uuid.uuid4()),
                "state": "INITIATED"
            }
        }
    mock_service.create_transfer = AsyncMock(side_effect=mock_create_transfer)

    # Mock get_transfer
    async def mock_get_transfer(transfer_id):
        return {
            "data": {
                "id": transfer_id,
                "state": "COMPLETE",
                "txHash": f"0x{uuid.uuid4().hex}"
            }
        }
    mock_service.get_transfer = AsyncMock(side_effect=mock_get_transfer)

    return mock_service


class TestCircleWalletServiceCreateAgentWallet:
    """Tests for creating wallets linked to agents."""

    @pytest.mark.asyncio
    async def test_create_analyst_wallet(self):
        """Test creating wallet for analyst agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        result = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnCompliance",
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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        result = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnTransaction",
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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

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

    def test_define_transfer_not_found_error(self):
        """Test TransferNotFoundError is properly defined."""
        from app.services.circle_service import TransferNotFoundError

        error = TransferNotFoundError("transfer_123")
        assert "transfer_123" in error.detail


class TestCircleCryptoModule:
    """Tests for the circle_crypto module."""

    def test_generate_entity_secret(self):
        """Test entity secret generation."""
        from app.services.circle_crypto import generate_entity_secret

        secret = generate_entity_secret()
        assert len(secret) == 64  # 32 bytes = 64 hex chars
        # Verify it's valid hex
        bytes.fromhex(secret)

    def test_encrypt_entity_secret_validates_length(self):
        """Test that encryption validates secret length."""
        from app.services.circle_crypto import encrypt_entity_secret, CircleCryptoError

        # Too short
        with pytest.raises(CircleCryptoError) as exc_info:
            encrypt_entity_secret("abcd", "fake_pem_key")
        assert "64 hex characters" in exc_info.value.message

    def test_encrypt_entity_secret_validates_hex(self):
        """Test that encryption validates hex format."""
        from app.services.circle_crypto import encrypt_entity_secret, CircleCryptoError

        # Invalid hex (contains 'g')
        with pytest.raises(CircleCryptoError) as exc_info:
            encrypt_entity_secret("g" * 64, "fake_pem_key")
        assert "Invalid hex string" in exc_info.value.message

    def test_clear_public_key_cache(self):
        """Test clearing the public key cache."""
        from app.services import circle_crypto as crypto_module

        # Set some values in cache
        crypto_module._public_key_cache["key"] = "test_key"
        crypto_module._public_key_cache["fetched_at"] = 12345

        # Clear it
        crypto_module.clear_public_key_cache()

        assert crypto_module._public_key_cache["key"] is None
        assert crypto_module._public_key_cache["fetched_at"] == 0

    def test_circle_crypto_error_with_cause(self):
        """Test CircleCryptoError with cause exception."""
        from app.services.circle_crypto import CircleCryptoError

        cause = ValueError("Original error")
        error = CircleCryptoError("Encryption failed", cause=cause)
        assert error.message == "Encryption failed"
        assert error.cause == cause


class TestCircleServiceMakeRequest:
    """Tests for the _make_request internal method."""

    @pytest.mark.asyncio
    async def test_make_request_handles_timeout(self):
        """Test that timeouts are handled properly."""
        import httpx
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        # Create a mock client and set it directly on the private attribute
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        service._client = mock_client

        with pytest.raises(CircleAPIError) as exc_info:
            await service._make_request("GET", "/test")

        assert "timed out" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_make_request_handles_connection_error(self):
        """Test that connection errors are handled properly."""
        import httpx
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        # Create a mock client and set it directly on the private attribute
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        service._client = mock_client

        with pytest.raises(CircleAPIError) as exc_info:
            await service._make_request("GET", "/test")

        assert "connection error" in exc_info.value.detail.lower()


class TestCircleServiceListMethods:
    """Tests for list_wallets and list_transactions methods."""

    @pytest.mark.asyncio
    async def test_list_wallets(self):
        """Test listing wallets."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "wallets": [
                        {"id": "wallet1", "address": "0x1234"},
                        {"id": "wallet2", "address": "0x5678"}
                    ]
                }
            }

            result = await service.list_wallets(
                wallet_set_id="ws_123",
                blockchain="ARC-TESTNET",
                page_size=10
            )

            assert "data" in result
            assert len(result["data"]["wallets"]) == 2

    @pytest.mark.asyncio
    async def test_list_transactions(self):
        """Test listing transactions."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "transactions": [
                        {"id": "tx1", "state": "COMPLETE"},
                        {"id": "tx2", "state": "PENDING"}
                    ]
                }
            }

            result = await service.list_transactions(
                wallet_id="wallet_123",
                blockchain="ARC-TESTNET"
            )

            assert "data" in result
            assert len(result["data"]["transactions"]) == 2


class TestCircleServiceEntitySecretCiphertext:
    """Tests for entity secret ciphertext generation."""

    @pytest.mark.asyncio
    async def test_get_entity_secret_ciphertext_without_secret(self):
        """Test that missing entity secret raises error."""
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="TEST_API_KEY:123:456")
        # No entity_secret set

        with pytest.raises(CircleAPIError) as exc_info:
            await service._get_entity_secret_ciphertext()

        assert "Entity secret not configured" in exc_info.value.detail


class TestCircleWalletServiceListMethods:
    """Tests for wallet service list methods."""

    @pytest.mark.asyncio
    async def test_list_wallets_with_filters(self):
        """Test listing wallets with filters."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        # Create some wallets
        await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkTest1",
            wallet_type="analyst"
        )
        await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkTest2",
            wallet_type="compliance"
        )

        # List with filter
        wallets, total = await service.list_wallets(
            project_id="proj_test",
            wallet_type="analyst"
        )

        assert len(wallets) == 1
        assert wallets[0]["wallet_type"] == "analyst"

    @pytest.mark.asyncio
    async def test_list_transfers_with_filters(self):
        """Test listing transfers with filters."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        # Create wallets and transfers
        source = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkSourceList",
            wallet_type="transaction"
        )
        dest = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkDestList",
            wallet_type="analyst"
        )

        await service.initiate_transfer(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="50.00"
        )

        # List transfers
        transfers, total = await service.list_transfers(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"]
        )

        assert len(transfers) == 1


class TestCircleWalletServiceGetWalletByAgent:
    """Tests for get_wallet_by_agent method."""

    @pytest.mark.asyncio
    async def test_get_wallet_by_agent_not_found(self):
        """Test error when wallet not found for agent."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.services.circle_service import WalletNotFoundError
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        with pytest.raises(WalletNotFoundError):
            await service.get_wallet_by_agent(
                agent_did="did:key:nonexistent",
                wallet_type="analyst",
                project_id="proj_test"
            )

    @pytest.mark.asyncio
    async def test_get_wallet_by_agent_success(self):
        """Test getting wallet by agent DID."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        # Create wallet first
        await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkAgentSearch",
            wallet_type="analyst"
        )

        # Get by agent
        result = await service.get_wallet_by_agent(
            agent_did="did:key:z6MkAgentSearch",
            wallet_type="analyst",
            project_id="proj_test"
        )

        assert result["agent_did"] == "did:key:z6MkAgentSearch"
        assert result["wallet_type"] == "analyst"


class TestCircleServiceClose:
    """Tests for closing the HTTP client."""

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the HTTP client."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        # Initialize the client
        _ = service.client

        # Close it
        await service.close()

        # Client should be None after close
        assert service._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test close when client was never initialized."""
        from app.services.circle_service import CircleService

        service = CircleService(api_key="TEST_API_KEY:123:456")

        # Close without initializing client (should not raise)
        await service.close()

        assert service._client is None


class TestGetCircleService:
    """Tests for the get_circle_service factory function."""

    def test_get_circle_service_from_settings(self):
        """Test getting service from settings."""
        from app.services.circle_service import get_circle_service

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.circle_api_key = "TEST_API_KEY:123:456"
            mock_settings.circle_base_url = "https://api.circle.com"
            mock_settings.circle_entity_secret = "a" * 64

            service = get_circle_service()

            assert service.api_key == "TEST_API_KEY:123:456"
            assert service.entity_secret == "a" * 64


class TestCircleServiceApiErrorParsing:
    """Tests for API error response parsing."""

    @pytest.mark.asyncio
    async def test_parse_404_wallet_error(self):
        """Test 404 error parsing for wallet endpoints."""
        from app.services.circle_service import CircleService, WalletNotFoundError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{}'
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        service._client = mock_client

        with pytest.raises(WalletNotFoundError):
            await service._make_request("GET", "/v1/w3s/wallets/test_id")

    @pytest.mark.asyncio
    async def test_parse_404_transaction_error(self):
        """Test 404 error parsing for transaction endpoints."""
        from app.services.circle_service import CircleService, TransferNotFoundError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b'{}'
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        service._client = mock_client

        with pytest.raises(TransferNotFoundError):
            await service._make_request("GET", "/v1/w3s/transactions/test_id")

    @pytest.mark.asyncio
    async def test_parse_400_error_with_message(self):
        """Test 400 error response with message."""
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="TEST_API_KEY:123:456")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"message": "Invalid parameters"}'
        mock_response.json.return_value = {"message": "Invalid parameters"}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        service._client = mock_client

        with pytest.raises(CircleAPIError) as exc_info:
            await service._make_request("POST", "/v1/w3s/developer/wallets")

        assert "Invalid parameters" in exc_info.value.detail


class TestCircleServiceTransferWithTokenAddress:
    """Tests for transfer with token address."""

    @pytest.mark.asyncio
    async def test_create_transfer_with_token_address(self):
        """Test creating transfer with specific token address."""
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="TEST_API_KEY:123:456",
            entity_secret="a" * 64
        )

        with patch.object(service, '_make_request', new_callable=AsyncMock) as mock_request, \
             patch.object(service, '_get_entity_secret_ciphertext', new_callable=AsyncMock) as mock_cipher:
            mock_cipher.return_value = "encrypted_ciphertext_base64"
            mock_request.return_value = {
                "data": {
                    "id": str(uuid.uuid4()),
                    "state": "INITIATED"
                }
            }

            result = await service.create_transfer(
                source_wallet_id=str(uuid.uuid4()),
                destination_address="0x1234567890abcdef1234567890abcdef12345678",
                amount="100.00",
                idempotency_key="xfr-key-123",
                token_address="0xusdc_token_address"
            )

            assert "data" in result
            # Verify the request included token_address
            call_args = mock_request.call_args
            assert call_args[1]["data"]["tokenAddress"] == "0xusdc_token_address"


class TestCircleWalletServiceGetTransfer:
    """Tests for get_transfer method."""

    @pytest.mark.asyncio
    async def test_get_transfer_success(self):
        """Test getting transfer details."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        # Create wallets and transfer
        source = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkGetTransferSrc",
            wallet_type="transaction"
        )
        dest = await service.create_agent_wallet(
            project_id="proj_test",
            agent_did="did:key:z6MkGetTransferDst",
            wallet_type="analyst"
        )

        transfer = await service.initiate_transfer(
            project_id="proj_test",
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="50.00"
        )

        # Get transfer
        result = await service.get_transfer(transfer["transfer_id"], "proj_test")

        assert result["transfer_id"] == transfer["transfer_id"]

    @pytest.mark.asyncio
    async def test_get_transfer_not_found(self):
        """Test error when transfer not found."""
        from app.services.circle_wallet_service import CircleWalletService
        from app.services.circle_service import TransferNotFoundError
        from app.tests.fixtures.zerodb_mock import MockZeroDBClient

        mock_client = MockZeroDBClient()
        mock_circle = create_mock_circle_service()
        service = CircleWalletService(client=mock_client, circle_service=mock_circle)

        with pytest.raises(TransferNotFoundError):
            await service.get_transfer("nonexistent_transfer", "proj_test")
