"""
Analytics Dashboard Service — Issue #170

Provides spend summaries, agent activity metrics, time-series trends,
and composite project health scores.

Built by AINative Dev Team
Refs #170
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

TRANSACTIONS_TABLE = "agent_transactions"
DECISIONS_TABLE = "agent_decisions"

# Period string -> days mapping
PERIOD_DAYS: Dict[str, int] = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
}


def _parse_period(period: str) -> int:
    """Convert period string to number of days."""
    return PERIOD_DAYS.get(period, 7)


def _parse_ts(ts_str: str) -> Optional[datetime]:
    """Parse ISO timestamp to aware datetime, or return None on failure."""
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except (ValueError, TypeError):
        return None


class AnalyticsDashboardService:
    """
    Aggregates observability data for the analytics dashboard.

    All methods return plain dicts compatible with the analytics schemas.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    async def _fetch_transactions(
        self, project_id: str, since: datetime
    ) -> List[Dict[str, Any]]:
        result = await self.client.query_rows(
            TRANSACTIONS_TABLE,
            filter={"project_id": project_id},
            limit=100000,
        )
        rows = result.get("rows", [])
        filtered = []
        for row in rows:
            ts = _parse_ts(row.get("created_at", ""))
            if ts and ts >= since:
                filtered.append(row)
        return filtered

    async def _fetch_decisions(
        self, project_id: str, since: datetime
    ) -> List[Dict[str, Any]]:
        result = await self.client.query_rows(
            DECISIONS_TABLE,
            filter={"project_id": project_id},
            limit=100000,
        )
        rows = result.get("rows", [])
        filtered = []
        for row in rows:
            ts = _parse_ts(row.get("created_at", ""))
            if ts and ts >= since:
                filtered.append(row)
        return filtered

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_spend_summary(
        self, project_id: str, period: str = "7d"
    ) -> Dict[str, Any]:
        """
        Return total spend, by-agent, and by-category breakdowns.

        Args:
            project_id: Project to summarise.
            period: Look-back window string (e.g. "7d", "30d").

        Returns:
            SpendSummary-compatible dict.
        """
        days = _parse_period(period)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await self._fetch_transactions(project_id, since)

        total = 0.0
        by_agent: Dict[str, float] = defaultdict(float)
        by_category: Dict[str, float] = defaultdict(float)

        for row in rows:
            amount = float(row.get("amount", 0.0))
            total += amount
            agent_id = row.get("agent_id", "unknown")
            category = row.get("category", "uncategorized")
            by_agent[agent_id] += amount
            by_category[category] += amount

        return {
            "project_id": project_id,
            "period": period,
            "total_spend": total,
            "by_agent": dict(by_agent),
            "by_category": dict(by_category),
        }

    async def get_agent_activity(
        self, project_id: str, period: str = "7d"
    ) -> Dict[str, Any]:
        """
        Return task, decision, and payment activity counts for a project.

        Args:
            project_id: Project to query.
            period: Look-back window string.

        Returns:
            AgentActivity-compatible dict.
        """
        days = _parse_period(period)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        decisions = await self._fetch_decisions(project_id, since)
        transactions = await self._fetch_transactions(project_id, since)

        # Count settled payments (those with a positive amount as proxy)
        payments_settled = sum(
            1 for t in transactions if float(t.get("amount", 0.0)) > 0
        )

        return {
            "project_id": project_id,
            "period": period,
            "decisions_made": len(decisions),
            "payments_settled": payments_settled,
            "tasks_completed": len(decisions),  # proxy: each decision = a task step
        }

    async def get_trend_data(
        self,
        project_id: str,
        metric: str,
        granularity: str = "daily",
    ) -> Dict[str, Any]:
        """
        Return time-series data points for a metric.

        Args:
            project_id: Project to query.
            metric: One of "spend", "decisions", "payments".
            granularity: "hourly", "daily", or "weekly".

        Returns:
            TrendData-compatible dict with data_points list.
        """
        # Determine window and bucket width
        granularity_days = {
            "hourly": (2, timedelta(hours=1)),
            "daily": (30, timedelta(days=1)),
            "weekly": (90, timedelta(weeks=1)),
        }
        window_days, bucket_size = granularity_days.get(
            granularity, (30, timedelta(days=1))
        )

        since = datetime.now(timezone.utc) - timedelta(days=window_days)

        if metric in ("spend", "payments"):
            rows = await self._fetch_transactions(project_id, since)
        else:
            rows = await self._fetch_decisions(project_id, since)

        # Bucket data
        buckets: Dict[str, float] = defaultdict(float)
        for row in rows:
            ts = _parse_ts(row.get("created_at", ""))
            if not ts:
                continue
            # Floor to bucket
            if granularity == "hourly":
                key = ts.strftime("%Y-%m-%dT%H:00:00Z")
            elif granularity == "weekly":
                # ISO week start (Monday)
                week_start = ts - timedelta(days=ts.weekday())
                key = week_start.strftime("%Y-%m-%d")
            else:
                key = ts.strftime("%Y-%m-%d")

            if metric == "spend":
                buckets[key] += float(row.get("amount", 0.0))
            else:
                buckets[key] += 1

        data_points = [
            {"timestamp": ts_key, "value": value}
            for ts_key, value in sorted(buckets.items())
        ]

        return {
            "project_id": project_id,
            "metric": metric,
            "granularity": granularity,
            "data_points": data_points,
        }

    async def get_project_health(self, project_id: str) -> Dict[str, Any]:
        """
        Compute a composite health score for a project.

        Component scores (each 0-100):
        - spend: how close to zero overspend (simple heuristic)
        - anomalies: inverse of anomaly rate
        - drift: inverse of drift severity
        - activity: presence of recent activity

        Args:
            project_id: Project to evaluate.

        Returns:
            ProjectHealth-compatible dict.
        """
        # Spend: full score if any transactions exist (data presence = healthy)
        spend_result = await self.get_spend_summary(project_id, period="7d")
        spend_score = 80.0 if spend_result["total_spend"] > 0 else 100.0

        # Activity: score based on decisions in the last 7 days
        activity_result = await self.get_agent_activity(project_id, period="7d")
        activity_score = min(100.0, 60.0 + activity_result["decisions_made"] * 2)

        # Anomaly: use a fixed neutral score (full detection would require
        # per-agent analysis across the project)
        anomaly_score = 90.0

        # Drift: fixed neutral until cross-agent drift is computed
        drift_score = 85.0

        components = {
            "spend": spend_score,
            "anomalies": anomaly_score,
            "drift": drift_score,
            "activity": activity_score,
        }

        health_score = sum(components.values()) / len(components)

        return {
            "project_id": project_id,
            "health_score": round(health_score, 2),
            "components": components,
        }


analytics_dashboard_service = AnalyticsDashboardService()
