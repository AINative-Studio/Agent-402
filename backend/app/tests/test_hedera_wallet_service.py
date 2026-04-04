"""
Tests for HederaWalletService — Issue #188: Agent Wallet Creation.

BDD-style tests following the Red-Green-Refactor TDD cycle.
Tests are written BEFORE implementation to define expected behavior.

Issue #188: Agent Wallet Creation
- Create Hedera accounts for agents
- HBAR + USDC balance queries
- Token association for USDC (required before receiving HTS tokens)
- Store wallet info in ZeroDB

Built by AINative Dev Team
Refs #188
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ─── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client that stores data in memory."""
    client = AsyncMock()
    client.insert_row = AsyncMock(return_value={"success": True})
    client.query_rows = AsyncMock(return_value={"rows": [], "total": 0})
    client.update_row = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def mock_hedera_client():
    """Mock Hedera SDK client."""
    client = AsyncMock()
    client.create_account = AsyncMock(return_value={
        "account_id": "0.0.12345",
        "public_key": "302a300506032b6570032100...",
        "private_key": "302e020100300506032b657004220420...",
    })
    client.get_account_balance = AsyncMock(return_value={
        "hbar": "100.0",
        "tokens": {
            "0.0.456858": "50000000"  # 50 USDC in smallest unit
        }
    })
    client.associate_token = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS"
    })
    return client


@pytest.fixture
def wallet_service(mock_zerodb_client, mock_hedera_client):
    """HederaWalletService instance with mocked dependencies."""
    from app.services.hedera_wallet_service import HederaWalletService
    service = HederaWalletService(
        zerodb_client=mock_zerodb_client,
        hedera_client=mock_hedera_client
    )
    return service


# ─── Describe: HederaWalletService ──────────────────────────────────────────────

class DescribeHederaWalletService:
    """Tests for HederaWalletService — Issue #188."""

    # ─── Describe: create_agent_wallet ──────────────────────────────────────────

    class DescribeCreateAgentWallet:
        """Tests for create_agent_wallet method."""

        @pytest.mark.asyncio
        async def test_creates_hedera_account_for_agent(self, wallet_service, mock_hedera_client):
            """Should create a Hedera account when given a valid agent_id."""
            result = await wallet_service.create_agent_wallet(
                agent_id="agent_abc123",
                initial_balance=10
            )
            mock_hedera_client.create_account.assert_called_once()
            assert result["account_id"] == "0.0.12345"

        @pytest.mark.asyncio
        async def test_returns_wallet_info_with_agent_id(self, wallet_service):
            """Should return wallet info including the agent_id."""
            result = await wallet_service.create_agent_wallet(
                agent_id="agent_abc123",
                initial_balance=10
            )
            assert result["agent_id"] == "agent_abc123"

        @pytest.mark.asyncio
        async def test_stores_wallet_in_zerodb(self, wallet_service, mock_zerodb_client):
            """Should persist wallet info to ZeroDB after creation."""
            await wallet_service.create_agent_wallet(
                agent_id="agent_abc123",
                initial_balance=10
            )
            mock_zerodb_client.insert_row.assert_called_once()

        @pytest.mark.asyncio
        async def test_wallet_has_account_id_field(self, wallet_service):
            """Returned wallet must include a Hedera account_id field."""
            result = await wallet_service.create_agent_wallet(
                agent_id="agent_xyz",
                initial_balance=5
            )
            assert "account_id" in result
            assert result["account_id"].startswith("0.0.")

        @pytest.mark.asyncio
        async def test_wallet_has_created_at_timestamp(self, wallet_service):
            """Returned wallet must include a created_at timestamp."""
            result = await wallet_service.create_agent_wallet(
                agent_id="agent_xyz",
                initial_balance=5
            )
            assert "created_at" in result
            assert result["created_at"] is not None

        @pytest.mark.asyncio
        async def test_raises_error_when_agent_id_empty(self, wallet_service):
            """Should raise ValueError when agent_id is empty."""
            from app.services.hedera_wallet_service import HederaWalletError
            with pytest.raises((ValueError, HederaWalletError)):
                await wallet_service.create_agent_wallet(
                    agent_id="",
                    initial_balance=10
                )

        @pytest.mark.asyncio
        async def test_passes_initial_balance_to_account_creation(
            self, wallet_service, mock_hedera_client
        ):
            """Should pass initial_balance to the Hedera account creation call."""
            await wallet_service.create_agent_wallet(
                agent_id="agent_abc123",
                initial_balance=25
            )
            call_kwargs = mock_hedera_client.create_account.call_args
            # initial_balance or initial_hbar_balance should be in the call
            args, kwargs = call_kwargs
            # Accept either positional or keyword argument
            all_args = list(args) + list(kwargs.values())
            assert any(25 == a or "25" == str(a) for a in all_args) or \
                   kwargs.get("initial_balance") == 25 or \
                   kwargs.get("initial_hbar_balance") == 25

    # ─── Describe: associate_usdc_token ─────────────────────────────────────────

    class DescribeAssociateUsdcToken:
        """Tests for associate_usdc_token method."""

        @pytest.mark.asyncio
        async def test_associates_usdc_token_with_account(
            self, wallet_service, mock_hedera_client
        ):
            """Should call token association with the USDC token ID."""
            result = await wallet_service.associate_usdc_token(account_id="0.0.12345")
            mock_hedera_client.associate_token.assert_called_once()
            assert result["status"] == "SUCCESS"

        @pytest.mark.asyncio
        async def test_uses_testnet_usdc_token_id(self, wallet_service, mock_hedera_client):
            """Should associate with the correct testnet USDC token ID: 0.0.456858."""
            await wallet_service.associate_usdc_token(account_id="0.0.12345")
            call_args = mock_hedera_client.associate_token.call_args
            args, kwargs = call_args
            all_args = list(args) + list(kwargs.values())
            assert "0.0.456858" in all_args or kwargs.get("token_id") == "0.0.456858"

        @pytest.mark.asyncio
        async def test_returns_transaction_id_on_success(self, wallet_service):
            """Should return a transaction_id in the result."""
            result = await wallet_service.associate_usdc_token(account_id="0.0.12345")
            assert "transaction_id" in result

        @pytest.mark.asyncio
        async def test_raises_error_when_account_id_empty(self, wallet_service):
            """Should raise error when account_id is empty."""
            from app.services.hedera_wallet_service import HederaWalletError
            with pytest.raises((ValueError, HederaWalletError)):
                await wallet_service.associate_usdc_token(account_id="")

    # ─── Describe: get_balance ───────────────────────────────────────────────────

    class DescribeGetBalance:
        """Tests for get_balance method."""

        @pytest.mark.asyncio
        async def test_returns_hbar_balance(self, wallet_service):
            """Should return HBAR balance for the account."""
            result = await wallet_service.get_balance(account_id="0.0.12345")
            assert "hbar" in result
            assert result["hbar"] == "100.0"

        @pytest.mark.asyncio
        async def test_returns_usdc_balance(self, wallet_service):
            """Should return USDC balance in smallest unit (6 decimal places)."""
            result = await wallet_service.get_balance(account_id="0.0.12345")
            assert "usdc" in result

        @pytest.mark.asyncio
        async def test_queries_hedera_for_balance(self, wallet_service, mock_hedera_client):
            """Should call Hedera client to get live balance."""
            await wallet_service.get_balance(account_id="0.0.12345")
            mock_hedera_client.get_account_balance.assert_called_once_with(
                account_id="0.0.12345"
            )

        @pytest.mark.asyncio
        async def test_raises_error_when_account_id_empty(self, wallet_service):
            """Should raise error when account_id is empty."""
            from app.services.hedera_wallet_service import HederaWalletError
            with pytest.raises((ValueError, HederaWalletError)):
                await wallet_service.get_balance(account_id="")

    # ─── Describe: get_wallet_info ───────────────────────────────────────────────

    class DescribeGetWalletInfo:
        """Tests for get_wallet_info method — retrieves stored wallet from ZeroDB."""

        @pytest.mark.asyncio
        async def test_returns_wallet_info_from_zerodb(
            self, wallet_service, mock_zerodb_client
        ):
            """Should query ZeroDB for stored wallet info by agent_id."""
            mock_zerodb_client.query_rows.return_value = {
                "rows": [{
                    "agent_id": "agent_abc123",
                    "account_id": "0.0.99999",
                    "public_key": "abc123pubkey",
                    "network": "testnet",
                    "created_at": "2026-04-03T00:00:00Z"
                }],
                "total": 1
            }
            result = await wallet_service.get_wallet_info(agent_id="agent_abc123")
            assert result["account_id"] == "0.0.99999"
            assert result["agent_id"] == "agent_abc123"

        @pytest.mark.asyncio
        async def test_raises_not_found_when_wallet_missing(
            self, wallet_service, mock_zerodb_client
        ):
            """Should raise HederaWalletNotFoundError when no wallet in ZeroDB."""
            mock_zerodb_client.query_rows.return_value = {"rows": [], "total": 0}
            from app.services.hedera_wallet_service import HederaWalletNotFoundError
            with pytest.raises(HederaWalletNotFoundError):
                await wallet_service.get_wallet_info(agent_id="nonexistent_agent")

        @pytest.mark.asyncio
        async def test_queries_zerodb_with_agent_id_filter(
            self, wallet_service, mock_zerodb_client
        ):
            """Should query ZeroDB with agent_id as a filter."""
            mock_zerodb_client.query_rows.return_value = {
                "rows": [{
                    "agent_id": "agent_abc123",
                    "account_id": "0.0.99999",
                    "public_key": "abc123pubkey",
                    "network": "testnet",
                    "created_at": "2026-04-03T00:00:00Z"
                }],
                "total": 1
            }
            await wallet_service.get_wallet_info(agent_id="agent_abc123")
            call_args = mock_zerodb_client.query_rows.call_args
            _, kwargs = call_args
            filter_arg = kwargs.get("filter", {})
            assert filter_arg.get("agent_id") == "agent_abc123"


# ─── Describe: Error Classes ─────────────────────────────────────────────────────

class DescribeHederaWalletErrors:
    """Tests for error classes in hedera_wallet_service."""

    def test_hedera_wallet_error_inherits_from_api_error(self):
        """HederaWalletError should inherit from APIError."""
        from app.services.hedera_wallet_service import HederaWalletError
        from app.core.errors import APIError
        err = HederaWalletError("test error")
        assert isinstance(err, APIError)

    def test_hedera_wallet_error_returns_502_by_default(self):
        """HederaWalletError should default to 502 status code."""
        from app.services.hedera_wallet_service import HederaWalletError
        err = HederaWalletError("test error")
        assert err.status_code == 502

    def test_hedera_wallet_not_found_error_returns_404(self):
        """HederaWalletNotFoundError should return 404 status."""
        from app.services.hedera_wallet_service import HederaWalletNotFoundError
        err = HederaWalletNotFoundError("agent_xyz")
        assert err.status_code == 404

    def test_hedera_wallet_not_found_error_includes_agent_id(self):
        """HederaWalletNotFoundError detail should mention the agent_id."""
        from app.services.hedera_wallet_service import HederaWalletNotFoundError
        err = HederaWalletNotFoundError("agent_xyz")
        assert "agent_xyz" in err.detail

    def test_hedera_wallet_not_found_has_error_code(self):
        """HederaWalletNotFoundError should have HEDERA_WALLET_NOT_FOUND error_code."""
        from app.services.hedera_wallet_service import HederaWalletNotFoundError
        err = HederaWalletNotFoundError("agent_xyz")
        assert err.error_code == "HEDERA_WALLET_NOT_FOUND"
