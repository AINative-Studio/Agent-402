"""
Vendor Risk Service — Issue #166

Herfindahl-Hirschman Index (HHI) based vendor concentration risk analysis.

HHI = sum of squared market shares (scaled to 10000).
- HHI > 2500: high concentration
- HHI 1500-2500: moderate concentration
- HHI < 1500: low concentration

Built by AINative Dev Team
Refs #166
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

TRANSACTIONS_TABLE = "agent_transactions"

# Concentration thresholds (HHI scale 0-10000)
HHI_HIGH_THRESHOLD = 2500
HHI_MODERATE_THRESHOLD = 1500
# Vendors with market share above this are flagged for diversification
CONCENTRATION_FLAG_THRESHOLD = 0.5


class VendorRiskService:
    """
    Analyses vendor concentration risk for agent spending.

    Uses the Herfindahl-Hirschman Index (HHI) to quantify concentration.
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

    async def _get_vendor_spend(self, agent_id: str) -> Dict[str, float]:
        """Aggregate total spend by vendor for an agent."""
        result = await self.client.query_rows(
            TRANSACTIONS_TABLE,
            filter={"agent_id": agent_id},
            limit=100000,
        )
        rows = result.get("rows", [])

        vendor_totals: Dict[str, float] = defaultdict(float)
        for row in rows:
            vendor = row.get("vendor")
            if vendor:
                vendor_totals[vendor] += float(row.get("amount", 0.0))

        return dict(vendor_totals)

    def _compute_hhi(self, vendor_spend: Dict[str, float]) -> float:
        """Compute HHI from vendor spend dict. Returns 0 when no spend."""
        total = sum(vendor_spend.values())
        if total == 0:
            return 0.0

        hhi = sum((spend / total) ** 2 for spend in vendor_spend.values()) * 10000
        return round(hhi, 2)

    def _risk_level(self, hhi: float) -> str:
        """Classify HHI into risk level."""
        if hhi == 0:
            return "none"
        if hhi > HHI_HIGH_THRESHOLD:
            return "high"
        if hhi >= HHI_MODERATE_THRESHOLD:
            return "moderate"
        return "low"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def analyze_concentration(self, agent_id: str) -> Dict[str, Any]:
        """
        Return per-vendor spend distribution for an agent.

        Args:
            agent_id: Agent to analyse.

        Returns:
            Dict with vendors list (vendor, spend, market_share_pct) and total_spend.
        """
        vendor_spend = await self._get_vendor_spend(agent_id)
        total_spend = sum(vendor_spend.values())

        vendors: List[Dict[str, Any]] = []
        for vendor, spend in vendor_spend.items():
            share = (spend / total_spend * 100) if total_spend > 0 else 0.0
            vendors.append({
                "vendor": vendor,
                "spend": spend,
                "market_share_pct": round(share, 2),
            })

        vendors.sort(key=lambda v: v["spend"], reverse=True)

        return {
            "agent_id": agent_id,
            "vendors": vendors,
            "total_spend": total_spend,
        }

    async def get_risk_score(self, agent_id: str) -> Dict[str, Any]:
        """
        Calculate HHI risk score for an agent's vendor concentration.

        Args:
            agent_id: Agent to score.

        Returns:
            Dict with hhi, risk_level, agent_id.
        """
        vendor_spend = await self._get_vendor_spend(agent_id)
        hhi = self._compute_hhi(vendor_spend)
        risk = self._risk_level(hhi)

        return {
            "agent_id": agent_id,
            "hhi": hhi,
            "risk_level": risk,
        }

    async def get_diversification_recommendations(
        self, agent_id: str
    ) -> Dict[str, Any]:
        """
        Suggest diversification for over-concentrated vendors.

        Flags any vendor with > 50% market share.

        Args:
            agent_id: Agent to analyse.

        Returns:
            Dict with recommendations list.
        """
        concentration = await self.analyze_concentration(agent_id)
        total_spend = concentration["total_spend"]

        recommendations: List[Dict[str, Any]] = []
        for vendor_info in concentration["vendors"]:
            share_pct = vendor_info["market_share_pct"]
            share_fraction = share_pct / 100.0
            if share_fraction > CONCENTRATION_FLAG_THRESHOLD:
                recommendations.append({
                    "vendor": vendor_info["vendor"],
                    "market_share_pct": share_pct,
                    "recommendation": (
                        f"Vendor '{vendor_info['vendor']}' accounts for "
                        f"{share_pct:.1f}% of spend. Consider diversifying "
                        "across additional vendors to reduce concentration risk."
                    ),
                })

        return {
            "agent_id": agent_id,
            "total_spend": total_spend,
            "recommendations": recommendations,
        }


vendor_risk_service = VendorRiskService()
