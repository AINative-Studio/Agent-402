"""
Anomaly Detection Service — Issue #164

Statistical z-score anomaly detection for agent spend patterns.

Uses z-score method: anomaly when |amount - mean| / stddev > threshold.
Default threshold = 2.0 (two standard deviations).

Built by AINative Dev Team
Refs #164
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

TRANSACTIONS_TABLE = "agent_transactions"
DEFAULT_THRESHOLD = 2.0


class AnomalyDetectionService:
    """
    Detects spending anomalies using z-score statistical analysis.

    Compares each transaction amount against a rolling baseline of
    daily spend to identify outliers.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _compute_stats(self, amounts: List[float]) -> Dict[str, float]:
        """Compute mean and standard deviation from a list of amounts."""
        if not amounts:
            return {"mean": 0.0, "stddev": 0.0, "count": 0}

        n = len(amounts)
        mean = sum(amounts) / n

        if n < 2:
            return {"mean": mean, "stddev": 0.0, "count": n}

        variance = sum((x - mean) ** 2 for x in amounts) / (n - 1)
        stddev = math.sqrt(variance)
        return {"mean": mean, "stddev": stddev, "count": n}

    def _z_score(self, amount: float, mean: float, stddev: float) -> float:
        """Calculate z-score. Returns 0 when stddev is 0."""
        if stddev == 0:
            return 0.0 if amount == mean else float("inf")
        return abs(amount - mean) / stddev

    async def _fetch_transactions(
        self, agent_id: str, since: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch transactions for an agent since a given datetime."""
        result = await self.client.query_rows(
            TRANSACTIONS_TABLE,
            filter={"agent_id": agent_id},
            limit=10000,
        )
        rows = result.get("rows", [])

        # Filter by date
        filtered = []
        for row in rows:
            ts_str = row.get("created_at", "")
            try:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= since:
                    filtered.append(row)
            except (ValueError, TypeError):
                continue

        return filtered

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def calculate_baseline(
        self, agent_id: str, window_days: int = 90
    ) -> Dict[str, Any]:
        """
        Calculate mean and standard deviation of daily spend over a window.

        Args:
            agent_id: Agent to analyse.
            window_days: Number of past days to include.

        Returns:
            Dict with mean, stddev, window_days.
        """
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        rows = await self._fetch_transactions(agent_id, since)

        amounts = [float(r.get("amount", 0.0)) for r in rows]
        stats = self._compute_stats(amounts)

        return {
            "agent_id": agent_id,
            "mean": stats["mean"],
            "stddev": stats["stddev"],
            "window_days": window_days,
            "sample_count": stats["count"],
        }

    async def check_transaction_anomaly(
        self,
        agent_id: str,
        amount: float,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Determine whether a transaction amount is anomalous.

        Args:
            agent_id: Agent performing the transaction.
            amount: Transaction amount in USD.
            threshold: Z-score threshold (default 2.0).

        Returns:
            Dict with is_anomaly, z_score, mean, stddev.
        """
        baseline = await self.calculate_baseline(agent_id, window_days=90)
        mean = baseline["mean"]
        stddev = baseline["stddev"]

        z = self._z_score(amount, mean, stddev)
        is_anomaly = z > threshold

        return {
            "agent_id": agent_id,
            "amount": amount,
            "is_anomaly": is_anomaly,
            "z_score": z,
            "mean": mean,
            "stddev": stddev,
            "threshold": threshold,
        }

    async def detect_anomalies(
        self, agent_id: str, window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect anomalous transactions within the analysis window.

        Uses the 90-day baseline to evaluate each transaction in
        the shorter window.

        Args:
            agent_id: Agent to analyse.
            window_days: Window to scan for anomalies.

        Returns:
            Dict with anomalies list and window_days.
        """
        # Build baseline from 90-day history
        baseline = await self.calculate_baseline(agent_id, window_days=90)
        mean = baseline["mean"]
        stddev = baseline["stddev"]

        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        rows = await self._fetch_transactions(agent_id, since)

        anomalies: List[Dict[str, Any]] = []
        for row in rows:
            amount = float(row.get("amount", 0.0))
            z = self._z_score(amount, mean, stddev)
            if z > DEFAULT_THRESHOLD:
                anomalies.append({
                    "transaction": row,
                    "amount": amount,
                    "z_score": z,
                    "mean": mean,
                    "stddev": stddev,
                })

        return {
            "agent_id": agent_id,
            "window_days": window_days,
            "anomalies": anomalies,
            "total_scanned": len(rows),
        }

    async def get_anomaly_report(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate a summary anomaly report for an agent.

        Args:
            agent_id: Agent to report on.

        Returns:
            Dict with agent_id, total_anomalies, anomaly_rate, anomalies.
        """
        detection = await self.detect_anomalies(agent_id, window_days=30)
        total_scanned = detection["total_scanned"]
        anomalies = detection["anomalies"]
        total_anomalies = len(anomalies)
        anomaly_rate = total_anomalies / total_scanned if total_scanned > 0 else 0.0

        return {
            "agent_id": agent_id,
            "total_anomalies": total_anomalies,
            "anomaly_rate": anomaly_rate,
            "anomalies": anomalies,
        }


anomaly_detection_service = AnomalyDetectionService()
