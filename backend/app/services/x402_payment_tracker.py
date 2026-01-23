"""
X402 Payment Tracker Service.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 8 (X402 Protocol):
- Track payment receipts in ZeroDB
- Link to USDC transaction hashes
- Update AgentTreasury contract on successful payment

Per PRD Section 6 (ZeroDB Integration):
- Payment receipts stored with agent and task linkage
- Supports audit trail for X402 protocol transactions
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.payment_tracking import PaymentStatus, PaymentReceiptCreate
from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# Table name for payment receipts in ZeroDB
PAYMENT_RECEIPTS_TABLE = "payment_receipts"


class PaymentReceiptNotFoundError(APIError):
    """
    Raised when a payment receipt is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: PAYMENT_RECEIPT_NOT_FOUND
        - detail: Message including receipt ID
    """

    def __init__(self, receipt_id: str):
        detail = f"Payment receipt not found: {receipt_id}" if receipt_id else "Payment receipt not found"
        super().__init__(
            status_code=404,
            error_code="PAYMENT_RECEIPT_NOT_FOUND",
            detail=detail
        )


class X402PaymentTracker:
    """
    Service for tracking X402 payment receipts.

    Handles creation, retrieval, and linking of payment receipts
    to X402 requests and Arc blockchain transactions.

    Uses ZeroDB for persistence via the payment_receipts table.
    """

    def __init__(self, client=None):
        """
        Initialize the X402 Payment Tracker service.

        Args:
            client: Optional ZeroDB client instance (for testing)
        """
        self._client = client

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    def generate_receipt_id(self) -> str:
        """
        Generate a unique payment receipt ID.

        Returns:
            str: Unique receipt identifier (format: pay_rcpt_{uuid})
        """
        return f"pay_rcpt_{uuid.uuid4().hex[:16]}"

    async def create_payment_receipt(
        self,
        project_id: str,
        receipt_data: PaymentReceiptCreate
    ) -> Dict[str, Any]:
        """
        Create a new payment receipt record.

        Args:
            project_id: Project identifier
            receipt_data: Payment receipt creation data

        Returns:
            Dict containing the created receipt record
        """
        receipt_id = self.generate_receipt_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build row data for ZeroDB table
        row_data = {
            "id": str(uuid.uuid4()),
            "receipt_id": receipt_id,
            "project_id": project_id,
            "x402_request_id": receipt_data.x402_request_id,
            "from_agent_id": receipt_data.from_agent_id,
            "to_agent_id": receipt_data.to_agent_id,
            "amount_usdc": receipt_data.amount_usdc,
            "purpose": receipt_data.purpose,
            "status": PaymentStatus.PENDING.value,
            "transaction_hash": None,
            "arc_payment_id": None,
            "treasury_from_id": None,
            "treasury_to_id": None,
            "created_at": timestamp,
            "confirmed_at": None,
            "metadata": receipt_data.metadata or {}
        }

        try:
            await self.client.insert_row(PAYMENT_RECEIPTS_TABLE, row_data)
            logger.info(f"Created payment receipt: {receipt_id}")

            return self._row_to_receipt(row_data)

        except Exception as e:
            logger.error(f"Failed to create payment receipt: {e}")
            raise

    async def get_payment_receipt(
        self,
        project_id: str,
        receipt_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a payment receipt by ID.

        Args:
            project_id: Project identifier
            receipt_id: Payment receipt identifier

        Returns:
            Dict containing the receipt record

        Raises:
            PaymentReceiptNotFoundError: If receipt not found
        """
        try:
            result = await self.client.query_rows(
                PAYMENT_RECEIPTS_TABLE,
                filter={"receipt_id": receipt_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise PaymentReceiptNotFoundError(receipt_id)

            return self._row_to_receipt(rows[0])

        except PaymentReceiptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment receipt {receipt_id}: {e}")
            raise PaymentReceiptNotFoundError(receipt_id)

    async def update_payment_status(
        self,
        project_id: str,
        receipt_id: str,
        status: PaymentStatus,
        transaction_hash: Optional[str] = None,
        arc_payment_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a payment receipt.

        Args:
            project_id: Project identifier
            receipt_id: Payment receipt identifier
            status: New payment status
            transaction_hash: Optional blockchain transaction hash
            arc_payment_id: Optional Arc contract payment ID
            error_message: Optional error message (for failed status)

        Returns:
            Updated receipt record

        Raises:
            PaymentReceiptNotFoundError: If receipt not found
        """
        try:
            # Find the row
            result = await self.client.query_rows(
                PAYMENT_RECEIPTS_TABLE,
                filter={"receipt_id": receipt_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise PaymentReceiptNotFoundError(receipt_id)

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            # Prepare updates
            status_value = status.value if isinstance(status, PaymentStatus) else status
            updated_row = {**row, "status": status_value}

            if transaction_hash:
                updated_row["transaction_hash"] = transaction_hash

            if arc_payment_id is not None:
                updated_row["arc_payment_id"] = arc_payment_id

            if status == PaymentStatus.CONFIRMED:
                updated_row["confirmed_at"] = datetime.utcnow().isoformat() + "Z"

            if error_message:
                metadata = updated_row.get("metadata", {}) or {}
                metadata["error_message"] = error_message
                updated_row["metadata"] = metadata

            await self.client.update_row(PAYMENT_RECEIPTS_TABLE, row_id, updated_row)
            logger.info(f"Updated payment receipt {receipt_id} status to {status_value}")

            return self._row_to_receipt(updated_row)

        except PaymentReceiptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update payment receipt {receipt_id}: {e}")
            raise PaymentReceiptNotFoundError(receipt_id)

    async def list_payment_receipts(
        self,
        project_id: str,
        from_agent_id: Optional[str] = None,
        to_agent_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        x402_request_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List payment receipts with optional filters.

        Args:
            project_id: Project identifier
            from_agent_id: Optional filter by sender agent ID
            to_agent_id: Optional filter by receiver agent ID
            status: Optional filter by payment status
            x402_request_id: Optional filter by X402 request ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (list of receipts, total count)
        """
        try:
            # Build filter
            query_filter: Dict[str, Any] = {"project_id": project_id}

            if from_agent_id:
                query_filter["from_agent_id"] = from_agent_id
            if to_agent_id:
                query_filter["to_agent_id"] = to_agent_id
            if status:
                status_value = status.value if isinstance(status, PaymentStatus) else status
                query_filter["status"] = status_value
            if x402_request_id:
                query_filter["x402_request_id"] = x402_request_id

            result = await self.client.query_rows(
                PAYMENT_RECEIPTS_TABLE,
                filter=query_filter,
                limit=limit,
                skip=offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            receipts = [self._row_to_receipt(row) for row in rows]

            # Sort by created_at descending
            receipts.sort(
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )

            return receipts, total

        except Exception as e:
            logger.error(f"Failed to list payment receipts: {e}")
            return [], 0

    async def link_to_arc_payment(
        self,
        project_id: str,
        receipt_id: str,
        arc_payment_id: int,
        treasury_from_id: int,
        treasury_to_id: int
    ) -> Dict[str, Any]:
        """
        Link a payment receipt to an Arc blockchain payment.

        Args:
            project_id: Project identifier
            receipt_id: Payment receipt identifier
            arc_payment_id: Payment ID from AgentTreasury contract
            treasury_from_id: Source treasury ID
            treasury_to_id: Destination treasury ID

        Returns:
            Updated receipt record

        Raises:
            PaymentReceiptNotFoundError: If receipt not found
        """
        try:
            # Find the row
            result = await self.client.query_rows(
                PAYMENT_RECEIPTS_TABLE,
                filter={"receipt_id": receipt_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise PaymentReceiptNotFoundError(receipt_id)

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            # Update with Arc payment info
            updated_row = {
                **row,
                "arc_payment_id": arc_payment_id,
                "treasury_from_id": treasury_from_id,
                "treasury_to_id": treasury_to_id
            }

            await self.client.update_row(PAYMENT_RECEIPTS_TABLE, row_id, updated_row)
            logger.info(f"Linked payment receipt {receipt_id} to Arc payment {arc_payment_id}")

            return self._row_to_receipt(updated_row)

        except PaymentReceiptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to link payment receipt to Arc: {e}")
            raise PaymentReceiptNotFoundError(receipt_id)

    async def get_receipts_by_x402_request(
        self,
        project_id: str,
        x402_request_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all payment receipts linked to an X402 request.

        Args:
            project_id: Project identifier
            x402_request_id: X402 request identifier
            limit: Maximum number of results

        Returns:
            List of receipt records
        """
        receipts, _ = await self.list_payment_receipts(
            project_id=project_id,
            x402_request_id=x402_request_id,
            limit=limit
        )
        return receipts

    def _row_to_receipt(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a ZeroDB row to the logical receipt format.

        Args:
            row: Raw row data from ZeroDB

        Returns:
            Receipt data in the expected format
        """
        return {
            "receipt_id": row.get("receipt_id"),
            "project_id": row.get("project_id"),
            "x402_request_id": row.get("x402_request_id"),
            "from_agent_id": row.get("from_agent_id"),
            "to_agent_id": row.get("to_agent_id"),
            "amount_usdc": row.get("amount_usdc"),
            "purpose": row.get("purpose"),
            "status": row.get("status"),
            "transaction_hash": row.get("transaction_hash"),
            "arc_payment_id": row.get("arc_payment_id"),
            "treasury_from_id": row.get("treasury_from_id"),
            "treasury_to_id": row.get("treasury_to_id"),
            "created_at": row.get("created_at"),
            "confirmed_at": row.get("confirmed_at"),
            "metadata": row.get("metadata", {})
        }


# Global service instance
x402_payment_tracker = X402PaymentTracker()
