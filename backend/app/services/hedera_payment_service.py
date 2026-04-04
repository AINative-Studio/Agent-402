"""
Hedera Payment Service.
Implements USDC payment settlement via Hedera Token Service (HTS).

Issue #187: USDC Payment Settlement via HTS
- USDC transfer via HTS (native token, NOT smart contract/ERC-20)
- Uses TransferTransaction pattern from Hedera SDK
- Sub-3 second settlement verification
- Payment receipt with Hedera transaction hash
- Integration with existing X402 protocol flow

Hedera technical notes:
- USDC on Hedera is a native HTS (Hedera Token Service) token
- Token ID (testnet): 0.0.456858
- Amounts are in smallest unit (6 decimal places: 1 USDC = 1,000,000)
- TransferTransaction is used for all HTS token transfers

Built by AINative Dev Team
Refs #187
"""
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.errors import APIError
from app.services.hedera_client import HederaClient, get_hedera_client, USDC_TOKEN_ID_TESTNET
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table for Hedera payments
HEDERA_PAYMENTS_TABLE = "hedera_payments"

# Default USDC token ID for testnet operations
DEFAULT_USDC_TOKEN_ID = USDC_TOKEN_ID_TESTNET


class HederaPaymentError(APIError):
    """
    Raised when a Hedera payment operation fails.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: HEDERA_PAYMENT_ERROR
        - detail: Human-readable error message
    """

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(
            status_code=status_code,
            error_code="HEDERA_PAYMENT_ERROR",
            detail=detail or "Hedera payment error"
        )


class HederaSettlementTimeoutError(HederaPaymentError):
    """
    Raised when a Hedera transaction does not settle within the expected time.

    Hedera targets sub-3 second finality. This error is raised when polling
    exceeds the settlement timeout.

    Returns:
        - HTTP 504 (Gateway Timeout)
        - error_code: HEDERA_PAYMENT_ERROR (inherited)
        - detail: Message with transaction ID and timeout info
    """

    def __init__(self, transaction_id: str, timeout_seconds: int = 10):
        detail = (
            f"Transaction {transaction_id} did not settle within "
            f"{timeout_seconds} seconds. Hedera targets sub-3 second finality. "
            f"Check the mirror node for current status."
        )
        super().__init__(detail=detail, status_code=504)
        self.transaction_id = transaction_id
        self.timeout_seconds = timeout_seconds


class HederaPaymentNotFoundError(HederaPaymentError):
    """
    Raised when a Hedera payment record is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: HEDERA_PAYMENT_ERROR
        - detail: Message including payment ID
    """

    def __init__(self, payment_id: str):
        detail = (
            f"Hedera payment not found: {payment_id}"
            if payment_id
            else "Hedera payment not found"
        )
        super().__init__(detail=detail, status_code=404)
        self.payment_id = payment_id


class HederaPaymentService:
    """
    Service for executing USDC payments via Hedera Token Service (HTS).

    Implements the X402 payment protocol integration with Hedera Hashgraph,
    using native HTS token transfers rather than smart contract calls.

    Key differences from EVM/Circle payments:
    - Native HTS transfers (not ERC-20)
    - Token association required before first transfer
    - Sub-3 second settlement finality
    - Hedera transaction IDs follow {account}@{seconds}.{nanos} format
    """

    def __init__(
        self,
        hedera_client: Optional[HederaClient] = None,
        zerodb_client=None
    ):
        """
        Initialize the Hedera payment service.

        Args:
            hedera_client: Optional Hedera client instance (for testing)
            zerodb_client: Optional ZeroDB client instance (for testing)
        """
        self._hedera_client = hedera_client
        self._zerodb_client = zerodb_client

    @property
    def hedera_client(self) -> HederaClient:
        """Lazy initialization of Hedera client."""
        if self._hedera_client is None:
            self._hedera_client = get_hedera_client()
        return self._hedera_client

    @property
    def zerodb_client(self):
        """Lazy initialization of ZeroDB client."""
        if self._zerodb_client is None:
            self._zerodb_client = get_zerodb_client()
        return self._zerodb_client

    def _validate_account_id(self, account_id: str, field_name: str = "account_id") -> None:
        """
        Validate a Hedera account ID is not empty.

        Args:
            account_id: Account ID to validate
            field_name: Field name for error messaging

        Raises:
            HederaPaymentError: If account_id is empty
        """
        if not account_id or not account_id.strip():
            raise HederaPaymentError(
                f"{field_name} cannot be empty",
                status_code=400
            )

    def _validate_amount(self, amount: int) -> None:
        """
        Validate transfer amount is positive.

        Args:
            amount: Amount in token's smallest unit

        Raises:
            HederaPaymentError: If amount is not positive
        """
        if not isinstance(amount, int) or amount <= 0:
            raise HederaPaymentError(
                f"Transfer amount must be a positive integer (got {amount}). "
                f"USDC amounts use 6 decimal places: 1 USDC = 1,000,000",
                status_code=400
            )

    async def transfer_usdc(
        self,
        from_account: str,
        to_account: str,
        amount: int,
        memo: str = "",
        token_id: str = DEFAULT_USDC_TOKEN_ID
    ) -> Dict[str, Any]:
        """
        Execute a USDC transfer via Hedera Token Service (HTS).

        Uses the TransferTransaction pattern to move USDC tokens natively on
        the Hedera network. This is NOT a smart contract call — it uses HTS
        native token transfer which provides sub-3 second finality.

        Args:
            from_account: Source Hedera account ID (e.g., "0.0.11111")
            to_account: Destination Hedera account ID (e.g., "0.0.22222")
            amount: Transfer amount in USDC smallest unit (1 USDC = 1,000,000)
            memo: Optional transaction memo (max 100 bytes)
            token_id: HTS token ID (defaults to USDC testnet 0.0.456858)

        Returns:
            Dict containing:
            - transaction_id: Hedera transaction ID
            - status: "SUCCESS" on completion
            - hash: Transaction hash
            - from_account: Source account
            - to_account: Destination account
            - amount: Transfer amount
            - token_id: Token ID used

        Raises:
            HederaPaymentError: If from_account, to_account are empty, or amount is invalid
        """
        self._validate_account_id(from_account, "from_account")
        self._validate_account_id(to_account, "to_account")
        self._validate_amount(amount)

        logger.info(
            f"Initiating USDC HTS transfer: {from_account} -> {to_account}, "
            f"amount={amount} ({amount/1_000_000:.6f} USDC), memo={memo!r}"
        )

        try:
            result = await self.hedera_client.transfer_token(
                token_id=token_id,
                from_account=from_account,
                to_account=to_account,
                amount=amount,
                memo=memo
            )

            logger.info(
                f"USDC transfer successful: tx={result.get('transaction_id')}"
            )

            return result

        except HederaPaymentError:
            raise
        except Exception as e:
            logger.error(
                f"USDC transfer failed: {from_account} -> {to_account}: {e}"
            )
            raise HederaPaymentError(
                f"USDC transfer failed: {str(e)}"
            )

    async def verify_settlement(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Verify whether a Hedera transaction has settled.

        Queries the Hedera mirror node for the transaction receipt.
        Hedera targets sub-3 second settlement finality.

        Args:
            transaction_id: Hedera transaction ID to verify

        Returns:
            Dict containing:
            - transaction_id: The queried transaction ID
            - settled: True if transaction status is SUCCESS
            - status: Transaction status string
            - consensus_timestamp: When the transaction reached consensus (if settled)

        Raises:
            HederaPaymentError: If transaction_id is empty
        """
        if not transaction_id or not transaction_id.strip():
            raise HederaPaymentError(
                "transaction_id cannot be empty",
                status_code=400
            )

        logger.info(f"Verifying settlement for transaction: {transaction_id}")

        try:
            receipt = await self.hedera_client.get_transaction_receipt(
                transaction_id=transaction_id
            )

            status = receipt.get("status", "UNKNOWN")
            settled = status == "SUCCESS"

            return {
                "transaction_id": transaction_id,
                "settled": settled,
                "status": status,
                "consensus_timestamp": receipt.get("consensus_timestamp")
            }

        except HederaPaymentError:
            raise
        except Exception as e:
            logger.error(f"Settlement verification failed for tx {transaction_id}: {e}")
            raise HederaPaymentError(
                f"Settlement verification failed: {str(e)}"
            )

    async def get_payment_receipt(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Get the full receipt for a Hedera payment transaction.

        Returns complete receipt information including:
        - Transaction hash for on-chain verification
        - Consensus timestamp for finality proof
        - Status for payment confirmation

        Args:
            transaction_id: Hedera transaction ID

        Returns:
            Dict containing:
            - transaction_id: The transaction ID
            - hash: Transaction hash (for external verification)
            - status: Transaction status
            - consensus_timestamp: When consensus was reached
            - charged_tx_fee: Network fee charged

        Raises:
            HederaPaymentError: If transaction_id is empty or query fails
        """
        if not transaction_id or not transaction_id.strip():
            raise HederaPaymentError(
                "transaction_id cannot be empty",
                status_code=400
            )

        logger.info(f"Getting payment receipt for transaction: {transaction_id}")

        try:
            receipt = await self.hedera_client.get_transaction_receipt(
                transaction_id=transaction_id
            )

            return {
                "transaction_id": transaction_id,
                "hash": receipt.get("hash"),
                "status": receipt.get("status", "UNKNOWN"),
                "consensus_timestamp": receipt.get("consensus_timestamp"),
                "charged_tx_fee": receipt.get("charged_tx_fee", 0)
            }

        except HederaPaymentError:
            raise
        except Exception as e:
            logger.error(f"Failed to get receipt for tx {transaction_id}: {e}")
            raise HederaPaymentError(
                f"Failed to get payment receipt: {str(e)}"
            )

    async def create_x402_payment(
        self,
        agent_id: str,
        amount: int,
        recipient: str,
        task_id: str,
        from_account: Optional[str] = None,
        memo: Optional[str] = None,
        token_id: str = DEFAULT_USDC_TOKEN_ID
    ) -> Dict[str, Any]:
        """
        Create and execute an X402 protocol-integrated payment via Hedera HTS.

        This method integrates the X402 payment protocol with Hedera's native
        USDC token transfers. It:
        1. Validates inputs
        2. Executes the HTS USDC transfer
        3. Records the payment in ZeroDB for audit trail
        4. Returns a payment record with X402-compatible fields

        Args:
            agent_id: Agent identifier initiating the payment
            amount: Payment amount in USDC smallest unit (1 USDC = 1,000,000)
            recipient: Destination Hedera account ID
            task_id: Task identifier linking this payment to agent work
            from_account: Source Hedera account (defaults to operator account)
            memo: Optional transaction memo
            token_id: HTS token ID (defaults to USDC testnet)

        Returns:
            Dict containing:
            - payment_id: Unique payment identifier (format: hdr_pay_{uuid})
            - agent_id: Initiating agent
            - task_id: Associated task
            - amount: Transfer amount
            - recipient: Destination account
            - transaction_id: Hedera transaction ID
            - status: Payment status
            - created_at: ISO timestamp

        Raises:
            HederaPaymentError: If validation fails or transfer fails
        """
        self._validate_amount(amount)

        payment_id = f"hdr_pay_{uuid.uuid4().hex[:16]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Use operator account as from_account if not specified
        source_account = from_account or self.hedera_client.operator_id

        # Build default memo if not provided
        payment_memo = memo or f"X402 payment: agent={agent_id}, task={task_id}"

        logger.info(
            f"Creating X402 payment: payment_id={payment_id}, "
            f"agent={agent_id}, task={task_id}, amount={amount}, "
            f"recipient={recipient}"
        )

        try:
            # Execute the USDC HTS transfer
            transfer_result = await self.transfer_usdc(
                from_account=source_account,
                to_account=recipient,
                amount=amount,
                memo=payment_memo,
                token_id=token_id
            )

            payment_record = {
                "id": str(uuid.uuid4()),
                "payment_id": payment_id,
                "agent_id": agent_id,
                "task_id": task_id,
                "amount": amount,
                "recipient": recipient,
                "from_account": source_account,
                "token_id": token_id,
                "transaction_id": transfer_result["transaction_id"],
                "transaction_hash": transfer_result.get("hash"),
                "status": transfer_result["status"],
                "memo": payment_memo,
                "created_at": timestamp
            }

            # Persist to ZeroDB for audit trail
            await self.zerodb_client.insert_row(
                HEDERA_PAYMENTS_TABLE,
                payment_record
            )

            logger.info(
                f"X402 payment created: payment_id={payment_id}, "
                f"tx={transfer_result['transaction_id']}"
            )

            return payment_record

        except HederaPaymentError:
            raise
        except Exception as e:
            logger.error(
                f"X402 payment failed: agent={agent_id}, task={task_id}: {e}"
            )
            raise HederaPaymentError(
                f"X402 payment creation failed: {str(e)}"
            )


# Global service instance
hedera_payment_service = HederaPaymentService()


def get_hedera_payment_service() -> HederaPaymentService:
    """
    Get a HederaPaymentService instance.

    Returns:
        Configured HederaPaymentService instance
    """
    return hedera_payment_service
