"""
Auto-Settlement Service for USDC payments.
Issue #240: Auto-Settlement Cron for USDC

Periodically finds pending x402 payments and settles them via Hedera or Circle.
Runs as an asyncio periodic task (no Celery dependency).

Settlement logic:
- Query ZeroDB x402_payments table for pending payments
- For each pending payment older than 5 minutes, attempt settlement
- Update payment status in ZeroDB after each attempt

Built by AINative Dev Team
Refs #240
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ZeroDB table for x402 payments
X402_PAYMENTS_TABLE = "x402_payments"

# Minimum age before a pending payment is eligible for auto-settlement
MIN_PENDING_AGE_MINUTES = 5


class AutoSettlementService:
    """
    Service that runs periodic USDC settlement cycles.

    Queries ZeroDB for pending x402 payments and settles each one
    via the appropriate network service (Hedera or Circle).

    Designed for use as an asyncio background task without Celery.
    """

    def __init__(
        self,
        zerodb_client: Optional[Any] = None,
        hedera_service: Optional[Any] = None,
        circle_service: Optional[Any] = None,
    ) -> None:
        """
        Initialise the settlement service.

        Args:
            zerodb_client: Injected ZeroDB client (for testing / DI).
            hedera_service: Injected Hedera payment service instance.
            circle_service: Injected Circle service instance.
        """
        self._zerodb_client = zerodb_client
        self._hedera_service = hedera_service
        self._circle_service = circle_service

    # ------------------------------------------------------------------
    # Lazy dependency accessors
    # ------------------------------------------------------------------

    @property
    def zerodb_client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._zerodb_client is None:
            from app.services.zerodb_client import get_zerodb_client
            self._zerodb_client = get_zerodb_client()
        return self._zerodb_client

    @property
    def hedera_service(self) -> Any:
        """Lazy-init Hedera payment service."""
        if self._hedera_service is None:
            from app.services.hedera_payment_service import get_hedera_payment_service
            self._hedera_service = get_hedera_payment_service()
        return self._hedera_service

    @property
    def circle_service(self) -> Any:
        """Lazy-init Circle service."""
        if self._circle_service is None:
            from app.services.circle_service import get_circle_service
            self._circle_service = get_circle_service()
        return self._circle_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_pending_settlements(
        self,
        max_age_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Query ZeroDB for unsettled x402 payments within the age window.

        Args:
            max_age_hours: Maximum payment age to include (payments older
                than this are ignored). Defaults to 24 hours.

        Returns:
            List of payment record dicts with status == "pending".
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cutoff_iso = cutoff.isoformat()

        logger.info(
            f"Querying pending settlements: max_age_hours={max_age_hours}, "
            f"cutoff={cutoff_iso}"
        )

        records = await self.zerodb_client.query_rows(
            X402_PAYMENTS_TABLE,
            {
                "status": "pending",
                "created_at_after": cutoff_iso,
            },
        )

        logger.info(f"Found {len(records)} pending payment(s) to settle.")
        return records

    async def settle_payment(
        self,
        payment_id: str,
    ) -> Dict[str, Any]:
        """
        Execute settlement for a single payment.

        Looks up the payment in ZeroDB, validates it is still pending and
        old enough to auto-settle, then delegates to the appropriate
        network service (Hedera or Circle).

        Args:
            payment_id: Identifier of the payment to settle.

        Returns:
            Dict with keys:
            - status: "settled" | "skipped" | "failed"
            - payment_id: The payment identifier.
            - transaction_id: Network transaction ID (on success).
            - error: Error message string (on failure).

        Raises:
            ValueError: When the payment_id is not found in ZeroDB.
        """
        records = await self.zerodb_client.query_rows(
            X402_PAYMENTS_TABLE,
            {"payment_id": payment_id},
        )

        if not records:
            raise ValueError(f"Payment not found: {payment_id}")

        payment = records[0]
        current_status = payment.get("status", "")

        # Skip payments that are not in a settleable state
        if current_status != "pending":
            logger.info(
                f"Skipping payment {payment_id}: status={current_status}"
            )
            return {"status": "skipped", "payment_id": payment_id}

        network = payment.get("network", "hedera")

        try:
            if network == "circle":
                result = await self._settle_via_circle(payment)
            else:
                result = await self._settle_via_hedera(payment)

            # Update ZeroDB record to reflect the settled state
            await self.zerodb_client.update_row(
                X402_PAYMENTS_TABLE,
                {"payment_id": payment_id},
                {
                    "status": "settled",
                    "transaction_id": result.get("transaction_id"),
                    "settled_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(
                f"Payment {payment_id} settled: "
                f"transaction_id={result.get('transaction_id')}"
            )

            return {
                "status": "settled",
                "payment_id": payment_id,
                "transaction_id": result.get("transaction_id"),
            }

        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                f"Settlement failed for payment {payment_id}: {error_msg}"
            )

            # Best-effort status update to "failed"
            try:
                await self.zerodb_client.update_row(
                    X402_PAYMENTS_TABLE,
                    {"payment_id": payment_id},
                    {
                        "status": "failed",
                        "error": error_msg,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as update_exc:
                logger.warning(
                    f"Could not update failed status for {payment_id}: {update_exc}"
                )

            return {
                "status": "failed",
                "payment_id": payment_id,
                "error": error_msg,
            }

    async def run_settlement_cycle(self) -> Dict[str, Any]:
        """
        Process all pending payments in a single settlement cycle.

        Retrieves pending payments from ZeroDB and attempts to settle
        each one, tracking counts for monitoring/alerting.

        Returns:
            Summary dict:
            - total: Number of payments processed.
            - settled: Successfully settled count.
            - failed: Failed settlement count.
            - skipped: Skipped (non-pending) count.
        """
        logger.info("Starting settlement cycle.")

        pending = await self.get_pending_settlements()
        total = len(pending)
        settled = 0
        failed = 0
        skipped = 0

        for payment in pending:
            payment_id = payment.get("payment_id", "")
            if not payment_id:
                logger.warning("Skipping payment record with no payment_id.")
                skipped += 1
                continue

            result = await self.settle_payment(payment_id)
            status = result.get("status")

            if status == "settled":
                settled += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1

        summary = {
            "total": total,
            "settled": settled,
            "failed": failed,
            "skipped": skipped,
        }
        logger.info(f"Settlement cycle complete: {summary}")
        return summary

    async def schedule_settlement(
        self,
        interval_minutes: float = 15,
    ) -> "asyncio.Task[None]":
        """
        Start a periodic background task that runs settlement cycles.

        Uses asyncio.create_task() — no Celery or external scheduler needed.

        Args:
            interval_minutes: How often to run the settlement cycle.
                              Defaults to 15 minutes.

        Returns:
            asyncio.Task that can be cancelled to stop the scheduler.
        """
        interval_seconds = interval_minutes * 60

        async def _loop() -> None:
            while True:
                try:
                    await self.run_settlement_cycle()
                except Exception as exc:
                    logger.error(f"Settlement cycle error: {exc}")
                await asyncio.sleep(interval_seconds)

        task = asyncio.create_task(_loop())
        logger.info(
            f"Auto-settlement scheduler started: "
            f"interval={interval_minutes} minutes."
        )
        return task

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _settle_via_hedera(
        self,
        payment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Settle a payment via Hedera HTS."""
        result = await self.hedera_service.transfer_usdc(
            from_account=payment.get("from_account", ""),
            to_account=payment.get("to_account", ""),
            amount=int(payment.get("amount", 0)),
            memo=f"auto-settlement:{payment.get('payment_id', '')}",
        )
        return {"transaction_id": result.get("transaction_id"), "status": "SUCCESS"}

    async def _settle_via_circle(
        self,
        payment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Settle a payment via Circle."""
        idempotency_key = str(uuid.uuid4())
        result = await self.circle_service.create_transfer(
            source_wallet_id=payment.get("from_account", ""),
            destination_address=payment.get("to_account", ""),
            amount=str(payment.get("amount", "0")),
            idempotency_key=idempotency_key,
        )
        transfer_id = result.get("data", {}).get("id", "")
        return {"transaction_id": transfer_id, "status": "COMPLETE"}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

auto_settlement_service = AutoSettlementService()


def get_auto_settlement_service() -> AutoSettlementService:
    """Return the module-level AutoSettlementService singleton."""
    return auto_settlement_service
