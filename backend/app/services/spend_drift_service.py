"""
Spend Drift Service — Issue #165

Monitors spend drift: compares current spend rate against a baseline.

Drift formula: (current_rate - baseline_rate) / baseline_rate * 100

Built by AINative Dev Team
Refs #165
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

TRANSACTIONS_TABLE = "agent_transactions"
BASELINES_TABLE = "spend_drift_baselines"


class SpendDriftService:
    """
    Calculates spend drift for agents relative to a baseline period.

    Alerts are raised when an agent's current spend rate diverges
    beyond a configurable percentage threshold.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _daily_rate(
        self, agent_id: str, since: datetime, until: datetime
    ) -> float:
        """Calculate average daily spend for an agent within a time window."""
        result = await self.client.query_rows(
            TRANSACTIONS_TABLE,
            filter={"agent_id": agent_id},
            limit=100000,
        )
        rows = result.get("rows", [])

        total = 0.0
        for row in rows:
            ts_str = row.get("created_at", "")
            try:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if since <= ts <= until:
                    total += float(row.get("amount", 0.0))
            except (ValueError, TypeError):
                continue

        days = max((until - since).days, 1)
        return total / days

    async def _get_agents_for_project(self, project_id: str) -> List[str]:
        """List distinct agent IDs with transactions in a project."""
        result = await self.client.query_rows(
            TRANSACTIONS_TABLE,
            filter={"project_id": project_id},
            limit=100000,
        )
        rows = result.get("rows", [])
        return list({r["agent_id"] for r in rows if "agent_id" in r})

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def calculate_drift(
        self,
        agent_id: str,
        baseline_period_days: int = 30,
        current_period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Compare current spend rate to the baseline period rate.

        Args:
            agent_id: Agent to analyse.
            baseline_period_days: Length of baseline window in days.
            current_period_days: Length of current window in days.

        Returns:
            Dict with agent_id, drift_pct, baseline_rate, current_rate.
        """
        now = datetime.now(timezone.utc)

        current_since = now - timedelta(days=current_period_days)
        # Baseline window is the period immediately preceding the current window,
        # extending back baseline_period_days further.
        baseline_until = current_since
        baseline_since = now - timedelta(days=baseline_period_days + current_period_days + 10)

        baseline_rate = await self._daily_rate(agent_id, baseline_since, baseline_until)
        current_rate = await self._daily_rate(agent_id, current_since, now)

        if baseline_rate == 0.0:
            drift_pct = 0.0
        else:
            drift_pct = (current_rate - baseline_rate) / baseline_rate * 100

        return {
            "agent_id": agent_id,
            "drift_pct": drift_pct,
            "baseline_rate": baseline_rate,
            "current_rate": current_rate,
            "baseline_period_days": baseline_period_days,
            "current_period_days": current_period_days,
        }

    async def get_drift_alerts(
        self,
        project_id: str,
        threshold_pct: float = 20.0,
    ) -> List[Dict[str, Any]]:
        """
        Return agents whose spend drifted beyond the threshold.

        Args:
            project_id: Project to scan.
            threshold_pct: Minimum drift percentage to trigger alert.

        Returns:
            List of drift alert dicts for agents exceeding the threshold.
        """
        agent_ids = await self._get_agents_for_project(project_id)
        alerts: List[Dict[str, Any]] = []

        for agent_id in agent_ids:
            drift = await self.calculate_drift(agent_id)
            if abs(drift["drift_pct"]) > threshold_pct:
                alerts.append({
                    "agent_id": agent_id,
                    "project_id": project_id,
                    "drift_pct": drift["drift_pct"],
                    "baseline_rate": drift["baseline_rate"],
                    "current_rate": drift["current_rate"],
                })

        return alerts

    async def set_drift_baseline(self, agent_id: str) -> Dict[str, Any]:
        """
        Snapshot the agent's current spend as a new baseline.

        Args:
            agent_id: Agent whose baseline to reset.

        Returns:
            Dict with agent_id, status, baseline_rate.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=7)
        baseline_rate = await self._daily_rate(agent_id, since, now)

        row_data = {
            "agent_id": agent_id,
            "baseline_rate": baseline_rate,
            "set_at": now.isoformat(),
        }
        await self.client.insert_row(BASELINES_TABLE, row_data)

        return {
            "agent_id": agent_id,
            "status": "baseline_set",
            "baseline_rate": baseline_rate,
            "set_at": now.isoformat(),
        }


spend_drift_service = SpendDriftService()
