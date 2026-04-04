"""
Spend Tracking Service for per-agent daily budget enforcement.
Issue #153: Implement per-agent daily spending limits.
Issue #239: Per-transaction spend limit enforcement.

This service handles:
- Tracking daily spend per agent
- Checking if a payment would exceed daily budget
- Enforcing per-transaction spend limits
- Calculating remaining budget
- Resetting daily spend at midnight UTC

Uses ZeroDB for persistence via the agent_spend_tracking table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table name
SPEND_TRACKING_TABLE = "agent_spend_tracking"


class SpendTrackingService:
    """
    Service for tracking and enforcing agent spending budgets.

    Tracks daily spend per agent and enforces max_daily_spend limits
    configured in agent transaction wallets.
    """

    def __init__(self, client=None):
        """
        Initialize the spend tracking service.

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

    def _get_current_date_key(self) -> str:
        """
        Get the current date key for spend tracking (YYYY-MM-DD).

        Returns:
            Date key string in UTC timezone
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def get_daily_spend(
        self,
        agent_id: str,
        project_id: str,
        date_key: Optional[str] = None
    ) -> Decimal:
        """
        Get the total spend for an agent on a specific date.

        Args:
            agent_id: Agent DID
            project_id: Project identifier
            date_key: Date key (YYYY-MM-DD), defaults to today

        Returns:
            Total spend as Decimal
        """
        if date_key is None:
            date_key = self._get_current_date_key()

        try:
            result = await self.client.query_rows(
                "payment_receipts",
                filter={
                    "from_agent_id": agent_id,
                    "status": "confirmed",
                    "created_at": {
                        "$gte": f"{date_key}T00:00:00+00:00",
                        "$lt": f"{date_key}T23:59:59+00:00"
                    }
                },
                limit=1000
            )

            rows = result.get("rows", [])
            total_spend = Decimal("0")
            for row in rows:
                row_data = row.get("row_data", {})
                amount_str = row_data.get("amount_usdc", "0")
                try:
                    total_spend += Decimal(amount_str)
                except (ValueError, TypeError, Exception) as e:
                    # Skip invalid amounts and log warning
                    logger.warning(
                        f"Skipping invalid amount_usdc value: {amount_str}",
                        extra={"agent_id": agent_id, "error": str(e)}
                    )
                    continue

            return total_spend

        except Exception as e:
            logger.error(f"Failed to get daily spend for agent {agent_id}: {e}")
            raise

    async def check_daily_budget(
        self,
        agent_id: str,
        project_id: str,
        amount: Decimal,
        daily_limit: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Check if a payment would exceed the agent's daily budget.

        Args:
            agent_id: Agent DID
            project_id: Project identifier
            amount: Payment amount to check
            daily_limit: Daily spending limit (None = unlimited)

        Returns:
            Dict containing:
                - allowed: bool - Whether payment is allowed
                - current_spend: Decimal - Current daily spend
                - limit: Decimal | None - Daily limit
                - remaining: Decimal | None - Remaining budget
                - proposed_total: Decimal - Current + proposed amount
                - exceeded_by: Decimal - Amount over limit (only if blocked)
        """
        # Get current daily spend
        current_spend = await self.get_daily_spend(agent_id, project_id)

        # Calculate what total would be after this payment
        proposed_total = current_spend + amount

        # If no limit set, always allow
        if daily_limit is None:
            logger.info(
                f"Budget check passed for agent {agent_id}: no limit configured",
                extra={"agent_id": agent_id, "amount": str(amount)}
            )
            return {
                "allowed": True,
                "current_spend": current_spend,
                "limit": None,
                "remaining": None,
                "proposed_total": proposed_total
            }

        # Check if within limit
        allowed = proposed_total <= daily_limit

        # Calculate remaining budget
        remaining = daily_limit - current_spend

        logger.info(
            f"Budget check for {agent_id}: "
            f"current={current_spend}, amount={amount}, "
            f"limit={daily_limit}, allowed={allowed}"
        )

        result = {
            "allowed": allowed,
            "current_spend": current_spend,
            "limit": daily_limit,
            "remaining": remaining,
            "proposed_total": proposed_total
        }

        # Add exceeded_by if transaction would be blocked
        if not allowed:
            exceeded_by = proposed_total - daily_limit
            result["exceeded_by"] = exceeded_by
            logger.warning(
                f"Budget check BLOCKED for agent {agent_id}: would exceed by ${exceeded_by}",
                extra={"agent_id": agent_id, "exceeded_by": str(exceeded_by)}
            )

        return result



    async def check_per_transaction_limit(
        self,
        agent_id: str,
        amount: Decimal,
        max_per_tx: Optional[Decimal],
    ) -> bool:
        """
        Check that a single transaction amount does not exceed the per-tx limit.

        Issue #239: Per-transaction spend limit enforcement.

        Args:
            agent_id: Agent DID or identifier
            amount: Transaction amount to validate
            max_per_tx: Maximum allowed per-transaction spend (None = unlimited)

        Returns:
            True if the amount is within the limit

        Raises:
            PerTransactionLimitExceededError: When amount exceeds max_per_tx
        """
        from app.core.errors import PerTransactionLimitExceededError

        if max_per_tx is None:
            logger.info(
                f"Per-tx check passed for agent {agent_id}: no limit configured",
                extra={"agent_id": agent_id, "amount": str(amount)},
            )
            return True

        if amount <= max_per_tx:
            logger.info(
                f"Per-tx check passed for agent {agent_id}: "
                f"amount={amount} <= limit={max_per_tx}",
                extra={"agent_id": agent_id, "amount": str(amount), "max_per_tx": str(max_per_tx)},
            )
            return True

        logger.warning(
            f"Per-tx check BLOCKED for agent {agent_id}: "
            f"amount={amount} exceeds limit={max_per_tx}",
            extra={"agent_id": agent_id, "amount": str(amount), "max_per_tx": str(max_per_tx)},
        )
        raise PerTransactionLimitExceededError(
            agent_id=agent_id,
            amount=amount,
            max_per_tx=max_per_tx,
        )

    async def get_monthly_spend(
        self,
        agent_id: str,
        project_id: str
    ) -> Decimal:
        """
        Calculate total spend for agent this month (UTC).
        Month boundaries: 1st 00:00:00 UTC to last day 23:59:59 UTC

        Args:
            agent_id: Agent identifier
            project_id: Project identifier

        Returns:
            Total spend for this month in USDC
        """
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

        try:
            result = await self.client.query_rows(
                "payment_receipts",
                filter={
                    "from_agent_id": agent_id,
                    "status": "confirmed",
                    "created_at": {"$gte": month_start.isoformat()}
                },
                limit=10000  # Reasonable monthly transaction limit
            )

            rows = result.get("rows", [])
            total_spend = Decimal("0")
            for row in rows:
                row_data = row.get("row_data", {})
                amount_str = row_data.get("amount_usdc", "0")
                try:
                    total_spend += Decimal(amount_str)
                except (ValueError, TypeError, Exception):
                    continue

            logger.info(
                f"Monthly spend for agent {agent_id}: ${total_spend}",
                extra={"agent_id": agent_id, "month": now.strftime("%Y-%m")}
            )

            return total_spend

        except Exception as e:
            logger.error(f"Failed to get monthly spend for agent {agent_id}: {e}")
            raise

    async def check_monthly_budget(
        self,
        agent_id: str,
        project_id: str,
        amount: Decimal,
        monthly_limit: Decimal
    ) -> Dict[str, Any]:
        """
        Check if transaction would exceed monthly budget.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier
            amount: Transaction amount to check
            monthly_limit: Monthly spending limit in USDC

        Returns:
            Dict with allowed, current_spend, limit, remaining, period
        """
        current_spend = await self.get_monthly_spend(agent_id, project_id)
        remaining = monthly_limit - current_spend
        allowed = (current_spend + amount) <= monthly_limit

        now = datetime.now(timezone.utc)

        return {
            "allowed": allowed,
            "current_spend": current_spend,
            "limit": monthly_limit,
            "remaining": max(Decimal("0"), remaining),
            "period": now.strftime("%Y-%m")
        }

    async def check_combined_budget(
        self,
        agent_id: str,
        project_id: str,
        amount: Decimal,
        daily_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None,
        max_per_tx: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Check daily, monthly, and per-transaction budgets.
        Transaction must pass ALL configured checks.

        Issue #153: Daily and monthly limit enforcement.
        Issue #239: Per-transaction limit enforcement added.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier
            amount: Transaction amount to check
            daily_limit: Optional daily spending limit in USDC
            monthly_limit: Optional monthly spending limit in USDC
            max_per_tx: Optional per-transaction spending limit in USDC

        Returns:
            Dict with:
                - allowed: bool (True only if all configured limits pass)
                - violations: List of limit violations with details
        """
        results: Dict[str, Any] = {
            "allowed": True,
            "violations": [],
        }

        # Check per-transaction limit first (cheapest check — no DB query)
        if max_per_tx is not None and amount > max_per_tx:
            results["allowed"] = False
            results["violations"].append({
                "type": "per_tx_limit_exceeded",
                "details": {
                    "amount": amount,
                    "max_per_tx": max_per_tx,
                    "exceeded_by": amount - max_per_tx,
                },
            })

        # Check daily limit if provided
        if daily_limit is not None:
            daily_check = await self.check_daily_budget(
                agent_id, project_id, amount, daily_limit
            )
            if not daily_check["allowed"]:
                results["allowed"] = False
                results["violations"].append({
                    "type": "daily_limit_exceeded",
                    "details": daily_check,
                })

        # Check monthly limit if provided
        if monthly_limit is not None:
            monthly_check = await self.check_monthly_budget(
                agent_id, project_id, amount, monthly_limit
            )
            if not monthly_check["allowed"]:
                results["allowed"] = False
                results["violations"].append({
                    "type": "monthly_limit_exceeded",
                    "details": monthly_check,
                })

        return results

# Global service instance
spend_tracking_service = SpendTrackingService()
