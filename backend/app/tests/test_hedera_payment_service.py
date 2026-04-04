"""
Tests for HederaPaymentService — Issue #187: USDC Payment Settlement via HTS.

BDD-style tests following the Red-Green-Refactor TDD cycle.
Tests are written BEFORE implementation to define expected behavior.

Issue #187: USDC Payment Settlement via Hedera Token Service (HTS)
- USDC transfer via HTS (native token, NOT smart contract/ERC-20)
- Uses TransferTransaction pattern from Hedera SDK
- Sub-3 second settlement verification
- Payment receipt with Hedera transaction hash
- Integration with existing X402 protocol flow

Built by AINative Dev Team
Refs #187
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ─── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_hedera_client():
    """Mock Hedera SDK client for payment operations."""
    client = AsyncMock()
    client.transfer_token = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "hash": "0xabcdef1234567890abcdef1234567890",
    })
    client.get_transaction_receipt = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "consensus_timestamp": "2026-04-03T12:00:00Z",
        "hash": "0xabcdef1234567890abcdef1234567890",
    })
    return client


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client for payment record storage."""
    client = AsyncMock()
    client.insert_row = AsyncMock(return_value={"success": True})
    client.query_rows = AsyncMock(return_value={"rows": [], "total": 0})
    return client


@pytest.fixture
def payment_service(mock_hedera_client, mock_zerodb_client):
    """HederaPaymentService instance with mocked dependencies."""
    from app.services.hedera_payment_service import HederaPaymentService
    service = HederaPaymentService(
        hedera_client=mock_hedera_client,
        zerodb_client=mock_zerodb_client
    )
    return service


# ─── Describe: HederaPaymentService ─────────────────────────────────────────────

class DescribeHederaPaymentService:
    """Tests for HederaPaymentService — Issue #187."""

    # ─── Describe: transfer_usdc ─────────────────────────────────────────────────

    class DescribeTransferUsdc:
        """Tests for transfer_usdc method."""

        @pytest.mark.asyncio
        async def test_executes_usdc_transfer_successfully(self, payment_service):
            """Should execute a USDC transfer and return success result."""
            result = await payment_service.transfer_usdc(
                from_account="0.0.11111",
                to_account="0.0.22222",
                amount=1000000,  # 1 USDC in smallest unit
                memo="Test transfer"
            )
            assert result["status"] == "SUCCESS"

        @pytest.mark.asyncio
        async def test_returns_transaction_id(self, payment_service):
            """Should return a Hedera transaction ID after transfer."""
            result = await payment_service.transfer_usdc(
                from_account="0.0.11111",
                to_account="0.0.22222",
                amount=1000000,
                memo="Test transfer"
            )
            assert "transaction_id" in result
            assert result["transaction_id"] is not None

        @pytest.mark.asyncio
        async def test_calls_hedera_client_transfer_token(
            self, payment_service, mock_hedera_client
        ):
            """Should delegate to the Hedera client's transfer_token method."""
            await payment_service.transfer_usdc(
                from_account="0.0.11111",
                to_account="0.0.22222",
                amount=1000000,
                memo="Test transfer"
            )
            mock_hedera_client.transfer_token.assert_called_once()

        @pytest.mark.asyncio
        async def test_uses_usdc_token_id_in_transfer(
            self, payment_service, mock_hedera_client
        ):
            """Should use the USDC HTS token ID (0.0.456858) in the transfer."""
            await payment_service.transfer_usdc(
                from_account="0.0.11111",
                to_account="0.0.22222",
                amount=1000000,
                memo="Test"
            )
            call_args = mock_hedera_client.transfer_token.call_args
            args, kwargs = call_args
            all_args = list(args) + list(kwargs.values())
            assert "0.0.456858" in all_args or kwargs.get("token_id") == "0.0.456858"

        @pytest.mark.asyncio
        async def test_raises_error_when_amount_is_zero(self, payment_service):
            """Should raise an error when transfer amount is zero."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.transfer_usdc(
                    from_account="0.0.11111",
                    to_account="0.0.22222",
                    amount=0,
                    memo="Test"
                )

        @pytest.mark.asyncio
        async def test_raises_error_when_amount_is_negative(self, payment_service):
            """Should raise an error when transfer amount is negative."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.transfer_usdc(
                    from_account="0.0.11111",
                    to_account="0.0.22222",
                    amount=-100,
                    memo="Test"
                )

        @pytest.mark.asyncio
        async def test_raises_error_when_from_account_empty(self, payment_service):
            """Should raise an error when from_account is empty."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.transfer_usdc(
                    from_account="",
                    to_account="0.0.22222",
                    amount=1000000,
                    memo="Test"
                )

        @pytest.mark.asyncio
        async def test_raises_error_when_to_account_empty(self, payment_service):
            """Should raise an error when to_account is empty."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.transfer_usdc(
                    from_account="0.0.11111",
                    to_account="",
                    amount=1000000,
                    memo="Test"
                )

        @pytest.mark.asyncio
        async def test_passes_memo_to_transfer(
            self, payment_service, mock_hedera_client
        ):
            """Should include the memo in the transfer call."""
            await payment_service.transfer_usdc(
                from_account="0.0.11111",
                to_account="0.0.22222",
                amount=1000000,
                memo="Payment for agent task abc"
            )
            call_args = mock_hedera_client.transfer_token.call_args
            args, kwargs = call_args
            all_args = list(args) + list(kwargs.values())
            assert "Payment for agent task abc" in all_args or \
                   kwargs.get("memo") == "Payment for agent task abc"

    # ─── Describe: verify_settlement ─────────────────────────────────────────────

    class DescribeVerifySettlement:
        """Tests for verify_settlement method."""

        @pytest.mark.asyncio
        async def test_returns_true_when_transaction_settled(self, payment_service):
            """Should return settled=True when transaction status is SUCCESS."""
            result = await payment_service.verify_settlement(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert result["settled"] is True

        @pytest.mark.asyncio
        async def test_returns_status_field(self, payment_service):
            """Should return a status field in the verification result."""
            result = await payment_service.verify_settlement(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert "status" in result

        @pytest.mark.asyncio
        async def test_queries_hedera_for_receipt(
            self, payment_service, mock_hedera_client
        ):
            """Should call Hedera client to get transaction receipt."""
            await payment_service.verify_settlement(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            mock_hedera_client.get_transaction_receipt.assert_called_once()

        @pytest.mark.asyncio
        async def test_returns_false_when_transaction_not_found(
            self, payment_service, mock_hedera_client
        ):
            """Should return settled=False when transaction is not found."""
            mock_hedera_client.get_transaction_receipt.return_value = {
                "status": "NOT_FOUND"
            }
            result = await payment_service.verify_settlement(
                transaction_id="0.0.12345@0000000000.000000000"
            )
            assert result["settled"] is False

        @pytest.mark.asyncio
        async def test_raises_error_when_transaction_id_empty(self, payment_service):
            """Should raise an error when transaction_id is empty."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.verify_settlement(transaction_id="")

    # ─── Describe: get_payment_receipt ───────────────────────────────────────────

    class DescribeGetPaymentReceipt:
        """Tests for get_payment_receipt method."""

        @pytest.mark.asyncio
        async def test_returns_receipt_with_transaction_hash(self, payment_service):
            """Should return a receipt containing the Hedera transaction hash."""
            result = await payment_service.get_payment_receipt(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert "hash" in result
            assert result["hash"] is not None

        @pytest.mark.asyncio
        async def test_returns_receipt_with_transaction_id(self, payment_service):
            """Should return a receipt containing the transaction_id."""
            result = await payment_service.get_payment_receipt(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert "transaction_id" in result

        @pytest.mark.asyncio
        async def test_returns_receipt_with_consensus_timestamp(self, payment_service):
            """Should return a receipt containing the consensus_timestamp."""
            result = await payment_service.get_payment_receipt(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert "consensus_timestamp" in result

        @pytest.mark.asyncio
        async def test_receipt_status_is_success(self, payment_service):
            """Should return status SUCCESS in the receipt."""
            result = await payment_service.get_payment_receipt(
                transaction_id="0.0.12345@1234567890.000000000"
            )
            assert result["status"] == "SUCCESS"

        @pytest.mark.asyncio
        async def test_raises_error_when_transaction_id_empty(self, payment_service):
            """Should raise an error when transaction_id is empty."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.get_payment_receipt(transaction_id="")

    # ─── Describe: create_x402_payment ───────────────────────────────────────────

    class DescribeCreateX402Payment:
        """Tests for create_x402_payment — X402 protocol integration."""

        @pytest.mark.asyncio
        async def test_creates_payment_and_returns_payment_id(self, payment_service):
            """Should return a unique payment_id after creating an X402 payment."""
            result = await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,  # 5 USDC
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            assert "payment_id" in result
            assert result["payment_id"] is not None

        @pytest.mark.asyncio
        async def test_payment_id_has_hedera_prefix(self, payment_service):
            """Payment ID should use a recognizable prefix."""
            result = await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            assert result["payment_id"].startswith("hdr_pay_")

        @pytest.mark.asyncio
        async def test_links_payment_to_agent_id(self, payment_service):
            """Created payment should reference the agent_id."""
            result = await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            assert result["agent_id"] == "agent_abc123"

        @pytest.mark.asyncio
        async def test_links_payment_to_task_id(self, payment_service):
            """Created payment should reference the task_id."""
            result = await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            assert result["task_id"] == "task_xyz789"

        @pytest.mark.asyncio
        async def test_executes_transfer_during_x402_payment(
            self, payment_service, mock_hedera_client
        ):
            """X402 payment should trigger actual USDC transfer on Hedera."""
            await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            mock_hedera_client.transfer_token.assert_called_once()

        @pytest.mark.asyncio
        async def test_stores_payment_in_zerodb(
            self, payment_service, mock_zerodb_client
        ):
            """X402 payment should be persisted to ZeroDB."""
            await payment_service.create_x402_payment(
                agent_id="agent_abc123",
                amount=5000000,
                recipient="0.0.22222",
                task_id="task_xyz789"
            )
            mock_zerodb_client.insert_row.assert_called_once()

        @pytest.mark.asyncio
        async def test_raises_error_when_amount_invalid(self, payment_service):
            """Should raise error when amount is not positive."""
            from app.services.hedera_payment_service import HederaPaymentError
            with pytest.raises((ValueError, HederaPaymentError)):
                await payment_service.create_x402_payment(
                    agent_id="agent_abc123",
                    amount=0,
                    recipient="0.0.22222",
                    task_id="task_xyz789"
                )


# ─── Describe: Error Classes ─────────────────────────────────────────────────────

class DescribeHederaPaymentErrors:
    """Tests for Hedera payment error classes."""

    def test_hedera_payment_error_inherits_from_api_error(self):
        """HederaPaymentError should inherit from APIError."""
        from app.services.hedera_payment_service import HederaPaymentError
        from app.core.errors import APIError
        err = HederaPaymentError("test error")
        assert isinstance(err, APIError)

    def test_hedera_payment_error_returns_502_by_default(self):
        """HederaPaymentError should default to HTTP 502."""
        from app.services.hedera_payment_service import HederaPaymentError
        err = HederaPaymentError("test error")
        assert err.status_code == 502

    def test_hedera_payment_error_has_error_code(self):
        """HederaPaymentError should have HEDERA_PAYMENT_ERROR error_code."""
        from app.services.hedera_payment_service import HederaPaymentError
        err = HederaPaymentError("test error")
        assert err.error_code == "HEDERA_PAYMENT_ERROR"

    def test_hedera_settlement_timeout_error_is_payment_error(self):
        """HederaSettlementTimeoutError should inherit from HederaPaymentError."""
        from app.services.hedera_payment_service import (
            HederaSettlementTimeoutError, HederaPaymentError
        )
        err = HederaSettlementTimeoutError("0.0.12345@1234567890.000000000")
        assert isinstance(err, HederaPaymentError)

    def test_hedera_settlement_timeout_error_returns_504(self):
        """HederaSettlementTimeoutError should return HTTP 504."""
        from app.services.hedera_payment_service import HederaSettlementTimeoutError
        err = HederaSettlementTimeoutError("0.0.12345@1234567890.000000000")
        assert err.status_code == 504
