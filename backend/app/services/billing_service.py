"""
Billing Service — Issues #226, #227, #228.

Provides:
  - Per-agent cost breakdown by category (Issue #226)
  - Per-project cost aggregation (Issue #226)
  - Usage event recording and paginated history (Issue #226)
  - Per-agent daily/monthly budget limits (Issue #227)
  - Per-project daily/monthly budget limits (Issue #228)

Cost categories:
  llm_inference | memory_storage | vector_search | file_storage | payment_fee

Storage: ZeroDB tables
  - billing_usage_events  : individual cost events
  - billing_agent_budgets : per-agent budget configuration
  - billing_project_budgets : per-project budget configuration

Built by AINative Dev Team.
Refs #226, #227, #228.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.billing import VALID_CATEGORIES
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table names
_USAGE_TABLE = "billing_usage_events"
_AGENT_BUDGET_TABLE = "billing_agent_budgets"
_PROJECT_BUDGET_TABLE = "billing_project_budgets"


def _today_period() -> str:
    """Return current UTC period in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _today_date() -> str:
    """Return current UTC date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class BillingService:
    """
    Service for recording and querying agent usage costs and budget limits.

    All monetary amounts use Decimal for precision.
    Persistence is backed by ZeroDB.
    """

    def __init__(self, client: Any = None) -> None:
        """
        Initialise the service.

        Args:
            client: Optional ZeroDB client (injected for testing; lazy-loaded otherwise).
        """
        self._client = client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def client(self) -> Any:
        """Lazy-initialise the ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    async def _get_events_for_agent(
        self,
        agent_id: str,
        period: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return all usage events for an agent/period, optionally filtered by category."""
        filter_query: Dict[str, Any] = {"agent_id": agent_id, "period": period}
        if category is not None:
            filter_query["category"] = category
        result = await self.client.query_rows(_USAGE_TABLE, filter=filter_query, limit=10_000)
        return result.get("rows", [])

    async def _get_events_for_project(
        self,
        project_id: str,
        period: str,
    ) -> List[Dict[str, Any]]:
        """Return all usage events tagged with a given project_id and period."""
        result = await self.client.query_rows(
            _USAGE_TABLE,
            filter={"project_id": project_id, "period": period},
            limit=100_000,
        )
        return result.get("rows", [])

    # ------------------------------------------------------------------
    # Issue #226 — Per-Agent Cost Breakdown API
    # ------------------------------------------------------------------

    async def get_agent_cost_breakdown(
        self,
        agent_id: str,
        period: str,
    ) -> Dict[str, Any]:
        """
        Return costs broken down by category for an agent in a billing period.

        Args:
            agent_id: Agent identifier.
            period:   Billing period in YYYY-MM format.

        Returns:
            Dict with keys: agent_id, period, llm_inference, memory_storage,
            vector_search, file_storage, payment_fee, total.
        """
        events = await self._get_events_for_agent(agent_id, period)

        totals: Dict[str, Decimal] = {cat: Decimal("0") for cat in VALID_CATEGORIES}
        for event in events:
            cat = event.get("category")
            if cat in totals:
                try:
                    totals[cat] += Decimal(str(event.get("amount", "0")))
                except Exception:
                    logger.warning("Skipping event with unparseable amount: %s", event)

        grand_total = sum(totals.values(), Decimal("0"))

        return {
            "agent_id": agent_id,
            "period": period,
            **totals,
            "total": grand_total,
        }

    async def get_project_cost_summary(
        self,
        project_id: str,
        period: str,
    ) -> Dict[str, Any]:
        """
        Aggregate costs for all agents in a project during a billing period.

        Args:
            project_id: Project identifier.
            period:     Billing period in YYYY-MM format.

        Returns:
            Dict with keys: project_id, period, agents (list), total.
        """
        events = await self._get_events_for_project(project_id, period)

        per_agent: Dict[str, Decimal] = {}
        for event in events:
            aid = event.get("agent_id", "")
            try:
                amount = Decimal(str(event.get("amount", "0")))
            except Exception:
                amount = Decimal("0")
            per_agent[aid] = per_agent.get(aid, Decimal("0")) + amount

        agents_list = [{"agent_id": k, "total": v} for k, v in per_agent.items()]
        grand_total = sum(per_agent.values(), Decimal("0"))

        return {
            "project_id": project_id,
            "period": period,
            "agents": agents_list,
            "total": grand_total,
        }

    async def record_usage_event(
        self,
        agent_id: str,
        category: str,
        amount: Decimal,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Record a single cost event for an agent.

        Args:
            agent_id:  Agent identifier.
            category:  Cost category (one of VALID_CATEGORIES).
            amount:    Cost amount in USD.
            metadata:  Arbitrary key/value metadata (e.g. project_id, model).

        Returns:
            Dict containing event_id, agent_id, category, amount, metadata.
        """
        event_id = str(uuid.uuid4())
        period = metadata.get("period") or _today_period()
        project_id = metadata.get("project_id", "")
        recorded_at = datetime.now(timezone.utc).isoformat()

        row_data: Dict[str, Any] = {
            "event_id": event_id,
            "agent_id": agent_id,
            "category": category,
            "amount": str(amount),
            "period": period,
            "project_id": project_id,
            "metadata": str(metadata),
            "recorded_at": recorded_at,
        }

        await self.client.insert_row(_USAGE_TABLE, row_data)

        logger.info(
            "Recorded usage event %s for agent %s: %s %.4f",
            event_id,
            agent_id,
            category,
            amount,
        )

        return {
            "event_id": event_id,
            "agent_id": agent_id,
            "category": category,
            "amount": amount,
            "metadata": metadata,
            "recorded_at": recorded_at,
        }

    async def get_usage_history(
        self,
        agent_id: str,
        category: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve paginated usage history for an agent and category.

        Args:
            agent_id:  Agent identifier.
            category:  Cost category to filter on.
            limit:     Maximum number of events to return.

        Returns:
            List of event dicts, most-recent first (up to limit).
        """
        result = await self.client.query_rows(
            _USAGE_TABLE,
            filter={"agent_id": agent_id, "category": category},
            limit=limit,
        )
        rows = result.get("rows", [])
        events = []
        for row in rows:
            events.append(
                {
                    "event_id": row.get("event_id"),
                    "agent_id": row.get("agent_id"),
                    "category": row.get("category"),
                    "amount": Decimal(str(row.get("amount", "0"))),
                    "period": row.get("period"),
                    "recorded_at": row.get("recorded_at"),
                }
            )
        return events

    # ------------------------------------------------------------------
    # Issue #227 — Per-Agent Budget Limits
    # ------------------------------------------------------------------

    async def set_agent_budget(
        self,
        agent_id: str,
        max_daily: Optional[Decimal],
        max_monthly: Optional[Decimal],
    ) -> Dict[str, Any]:
        """
        Configure daily and monthly spending limits for an agent.

        Existing budget config for the agent is replaced.

        Args:
            agent_id:    Agent identifier.
            max_daily:   Maximum daily spend in USD (None = unlimited).
            max_monthly: Maximum monthly spend in USD (None = unlimited).

        Returns:
            Dict with agent_id, max_daily, max_monthly.
        """
        row_data: Dict[str, Any] = {
            "agent_id": agent_id,
            "max_daily": str(max_daily) if max_daily is not None else "",
            "max_monthly": str(max_monthly) if max_monthly is not None else "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Upsert: replace existing row if present
        existing = await self.client.query_rows(
            _AGENT_BUDGET_TABLE, filter={"agent_id": agent_id}, limit=1
        )
        rows = existing.get("rows", [])
        if rows:
            row_id = rows[0].get("row_id") or rows[0].get("id")
            await self.client.update_row(_AGENT_BUDGET_TABLE, row_id, row_data)
        else:
            await self.client.insert_row(_AGENT_BUDGET_TABLE, row_data)

        return {
            "agent_id": agent_id,
            "max_daily": max_daily,
            "max_monthly": max_monthly,
        }

    async def _get_agent_budget_config(
        self, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return the stored budget config row for an agent, or None."""
        result = await self.client.query_rows(
            _AGENT_BUDGET_TABLE, filter={"agent_id": agent_id}, limit=1
        )
        rows = result.get("rows", [])
        return rows[0] if rows else None

    async def check_agent_budget(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Check whether a proposed spend is within the agent's configured budgets.

        Checks both daily and monthly limits; the spend must pass both to be
        allowed.

        Args:
            agent_id: Agent identifier.
            amount:   Proposed spend amount in USD.

        Returns:
            Dict with keys: allowed, remaining_daily, remaining_monthly.
        """
        config = await self._get_agent_budget_config(agent_id)

        if config is None:
            return {
                "allowed": True,
                "remaining_daily": None,
                "remaining_monthly": None,
            }

        raw_daily = config.get("max_daily", "")
        raw_monthly = config.get("max_monthly", "")
        max_daily: Optional[Decimal] = Decimal(raw_daily) if raw_daily else None
        max_monthly: Optional[Decimal] = Decimal(raw_monthly) if raw_monthly else None

        today_period = _today_period()
        events = await self._get_events_for_agent(agent_id, today_period)

        spent_today = sum(
            (Decimal(str(e.get("amount", "0"))) for e in events), Decimal("0")
        )
        # For monthly: sum all events regardless of period filtering (same month)
        all_month_events = await self.client.query_rows(
            _USAGE_TABLE,
            filter={"agent_id": agent_id},
            limit=100_000,
        )
        current_ym = _today_period()
        spent_month = sum(
            (
                Decimal(str(e.get("amount", "0")))
                for e in all_month_events.get("rows", [])
                if e.get("period", "") == current_ym
            ),
            Decimal("0"),
        )

        allowed = True
        remaining_daily: Optional[Decimal] = None
        remaining_monthly: Optional[Decimal] = None

        if max_daily is not None:
            remaining_daily = max(Decimal("0"), max_daily - spent_today)
            if spent_today + amount > max_daily:
                allowed = False

        if max_monthly is not None:
            remaining_monthly = max(Decimal("0"), max_monthly - spent_month)
            if spent_month + amount > max_monthly:
                allowed = False

        return {
            "allowed": allowed,
            "remaining_daily": remaining_daily,
            "remaining_monthly": remaining_monthly,
        }

    async def get_agent_budget_status(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Return current spend vs configured limits for an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            Dict with agent_id, max_daily, max_monthly, spent_daily, spent_monthly,
            remaining_daily, remaining_monthly.
        """
        config = await self._get_agent_budget_config(agent_id)

        max_daily: Optional[Decimal] = None
        max_monthly: Optional[Decimal] = None

        if config is not None:
            raw_daily = config.get("max_daily", "")
            raw_monthly = config.get("max_monthly", "")
            max_daily = Decimal(raw_daily) if raw_daily else None
            max_monthly = Decimal(raw_monthly) if raw_monthly else None

        today_period = _today_period()
        events = await self._get_events_for_agent(agent_id, today_period)
        spent_today = sum(
            (Decimal(str(e.get("amount", "0"))) for e in events), Decimal("0")
        )

        all_month_events = await self.client.query_rows(
            _USAGE_TABLE,
            filter={"agent_id": agent_id},
            limit=100_000,
        )
        current_ym = _today_period()
        spent_month = sum(
            (
                Decimal(str(e.get("amount", "0")))
                for e in all_month_events.get("rows", [])
                if e.get("period", "") == current_ym
            ),
            Decimal("0"),
        )

        return {
            "agent_id": agent_id,
            "max_daily": max_daily,
            "max_monthly": max_monthly,
            "spent_daily": spent_today,
            "spent_monthly": spent_month,
            "remaining_daily": (
                max(Decimal("0"), max_daily - spent_today) if max_daily is not None else None
            ),
            "remaining_monthly": (
                max(Decimal("0"), max_monthly - spent_month) if max_monthly is not None else None
            ),
        }

    # ------------------------------------------------------------------
    # Issue #228 — Per-Project Budget Limits
    # ------------------------------------------------------------------

    async def set_project_budget(
        self,
        project_id: str,
        max_daily: Optional[Decimal],
        max_monthly: Optional[Decimal],
    ) -> Dict[str, Any]:
        """
        Configure daily and monthly spending limits for a project.

        Args:
            project_id:  Project identifier.
            max_daily:   Maximum daily project spend in USD (None = unlimited).
            max_monthly: Maximum monthly project spend in USD (None = unlimited).

        Returns:
            Dict with project_id, max_daily, max_monthly.
        """
        row_data: Dict[str, Any] = {
            "project_id": project_id,
            "max_daily": str(max_daily) if max_daily is not None else "",
            "max_monthly": str(max_monthly) if max_monthly is not None else "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        existing = await self.client.query_rows(
            _PROJECT_BUDGET_TABLE, filter={"project_id": project_id}, limit=1
        )
        rows = existing.get("rows", [])
        if rows:
            row_id = rows[0].get("row_id") or rows[0].get("id")
            await self.client.update_row(_PROJECT_BUDGET_TABLE, row_id, row_data)
        else:
            await self.client.insert_row(_PROJECT_BUDGET_TABLE, row_data)

        return {
            "project_id": project_id,
            "max_daily": max_daily,
            "max_monthly": max_monthly,
        }

    async def _get_project_budget_config(
        self, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return the stored budget config row for a project, or None."""
        result = await self.client.query_rows(
            _PROJECT_BUDGET_TABLE, filter={"project_id": project_id}, limit=1
        )
        rows = result.get("rows", [])
        return rows[0] if rows else None

    async def _get_project_daily_spend(self, project_id: str) -> Decimal:
        """Return total today's spend across all agents tagged with project_id."""
        today_period = _today_period()
        events = await self._get_events_for_project(project_id, today_period)
        return sum(
            (Decimal(str(e.get("amount", "0"))) for e in events), Decimal("0")
        )

    async def _get_project_monthly_spend(self, project_id: str) -> Decimal:
        """Return total this-month's spend for the project."""
        current_ym = _today_period()
        events = await self._get_events_for_project(project_id, current_ym)
        return sum(
            (Decimal(str(e.get("amount", "0"))) for e in events), Decimal("0")
        )

    async def check_project_budget(
        self,
        project_id: str,
        amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Check whether a proposed spend is within the project's configured budgets.

        Args:
            project_id: Project identifier.
            amount:     Proposed spend amount in USD.

        Returns:
            Dict with keys: allowed, remaining.
        """
        config = await self._get_project_budget_config(project_id)

        if config is None:
            return {"allowed": True, "remaining": None}

        raw_daily = config.get("max_daily", "")
        raw_monthly = config.get("max_monthly", "")
        max_daily: Optional[Decimal] = Decimal(raw_daily) if raw_daily else None
        max_monthly: Optional[Decimal] = Decimal(raw_monthly) if raw_monthly else None

        spent_today = await self._get_project_daily_spend(project_id)
        spent_month = await self._get_project_monthly_spend(project_id)

        allowed = True
        remaining: Optional[Decimal] = None

        if max_daily is not None:
            remaining = max(Decimal("0"), max_daily - spent_today)
            if spent_today + amount > max_daily:
                allowed = False

        if max_monthly is not None:
            monthly_remaining = max(Decimal("0"), max_monthly - spent_month)
            if remaining is None or monthly_remaining < remaining:
                remaining = monthly_remaining
            if spent_month + amount > max_monthly:
                allowed = False

        return {"allowed": allowed, "remaining": remaining}

    async def get_project_budget_status(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Return aggregate spend vs limits for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Dict with project_id, max_daily, max_monthly, spent_daily, spent_monthly.
        """
        config = await self._get_project_budget_config(project_id)

        max_daily: Optional[Decimal] = None
        max_monthly: Optional[Decimal] = None

        if config is not None:
            raw_daily = config.get("max_daily", "")
            raw_monthly = config.get("max_monthly", "")
            max_daily = Decimal(raw_daily) if raw_daily else None
            max_monthly = Decimal(raw_monthly) if raw_monthly else None

        spent_today = await self._get_project_daily_spend(project_id)
        spent_month = await self._get_project_monthly_spend(project_id)

        return {
            "project_id": project_id,
            "max_daily": max_daily,
            "max_monthly": max_monthly,
            "spent_daily": spent_today,
            "spent_monthly": spent_month,
        }


# Global singleton
billing_service = BillingService()
