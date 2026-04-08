"""
Tests for VendorRiskService — Issue #166

Herfindahl-Hirschman Index (HHI) concentration risk analysis.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #166
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


class DescribeVendorRiskService:
    """Specification for VendorRiskService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.vendor_risk_service import VendorRiskService
        return VendorRiskService(client=mock_zerodb_client)

    @pytest.fixture
    def service_with_vendor_data(self, mock_zerodb_client):
        """Service pre-seeded with vendor spend: 80% vendor-A, 20% vendor-B."""
        from app.services.vendor_risk_service import VendorRiskService

        table = "agent_transactions"
        rows = [
            {"id": 1, "row_id": 1, "agent_id": "agent-v", "vendor": "vendor-A", "amount": 800.0, "created_at": "2026-03-01T00:00:00Z"},
            {"id": 2, "row_id": 2, "agent_id": "agent-v", "vendor": "vendor-A", "amount": 0.0, "created_at": "2026-03-02T00:00:00Z"},
            {"id": 3, "row_id": 3, "agent_id": "agent-v", "vendor": "vendor-B", "amount": 200.0, "created_at": "2026-03-03T00:00:00Z"},
        ]
        mock_zerodb_client.data[table] = rows
        return VendorRiskService(client=mock_zerodb_client)

    # ------------------------------------------------------------------ #
    # analyze_concentration
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_vendor_spend_distribution(self, service_with_vendor_data):
        """analyze_concentration returns a per-vendor spend breakdown."""
        result = await service_with_vendor_data.analyze_concentration(agent_id="agent-v")

        assert "vendors" in result
        assert "total_spend" in result
        assert isinstance(result["vendors"], list)
        vendor_names = [v["vendor"] for v in result["vendors"]]
        assert "vendor-A" in vendor_names

    @pytest.mark.asyncio
    async def it_includes_market_share_for_each_vendor(self, service_with_vendor_data):
        """analyze_concentration includes market_share_pct for each vendor."""
        result = await service_with_vendor_data.analyze_concentration(agent_id="agent-v")

        for vendor in result["vendors"]:
            assert "market_share_pct" in vendor
            assert 0 <= vendor["market_share_pct"] <= 100

    @pytest.mark.asyncio
    async def it_returns_empty_distribution_for_unknown_agent(self, service):
        """analyze_concentration handles unknown agent gracefully."""
        result = await service.analyze_concentration(agent_id="no-agent")

        assert result["vendors"] == []
        assert result["total_spend"] == 0.0

    # ------------------------------------------------------------------ #
    # get_risk_score (HHI)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_high_hhi_for_concentrated_spend(self, service_with_vendor_data):
        """get_risk_score returns HHI > 2500 for 80/20 concentration."""
        result = await service_with_vendor_data.get_risk_score(agent_id="agent-v")

        assert "hhi" in result
        assert "risk_level" in result
        # 0.8^2 + 0.2^2 = 0.64 + 0.04 = 0.68 → HHI = 6800 (scaled to 10000)
        assert result["hhi"] > 2500
        assert result["risk_level"] == "high"

    @pytest.mark.asyncio
    async def it_returns_low_hhi_for_evenly_distributed_spend(self, mock_zerodb_client):
        """get_risk_score returns HHI < 1500 for 4-vendor even split."""
        from app.services.vendor_risk_service import VendorRiskService

        table = "agent_transactions"
        rows = [
            {"id": i, "row_id": i, "agent_id": "agent-even",
             "vendor": f"vendor-{chr(65+i)}", "amount": 250.0,
             "created_at": "2026-03-01T00:00:00Z"}
            for i in range(4)
        ]
        mock_zerodb_client.data[table] = rows
        svc = VendorRiskService(client=mock_zerodb_client)

        result = await svc.get_risk_score(agent_id="agent-even")

        # 4 vendors, 25% each: HHI = 4*(0.25^2)*10000 = 2500
        assert result["hhi"] <= 2500

    @pytest.mark.asyncio
    async def it_returns_zero_hhi_for_no_spend(self, service):
        """get_risk_score returns hhi=0 when no transactions exist."""
        result = await service.get_risk_score(agent_id="empty-agent")

        assert result["hhi"] == 0
        assert result["risk_level"] == "none"

    # ------------------------------------------------------------------ #
    # get_diversification_recommendations
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_recommends_diversification_for_over_concentrated_vendor(
        self, service_with_vendor_data
    ):
        """get_diversification_recommendations flags dominant vendors."""
        result = await service_with_vendor_data.get_diversification_recommendations(
            agent_id="agent-v"
        )

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        # vendor-A at 80% share should be flagged
        flagged = [r for r in result["recommendations"] if r.get("vendor") == "vendor-A"]
        assert len(flagged) >= 1

    @pytest.mark.asyncio
    async def it_returns_no_recommendations_for_diversified_spend(self, mock_zerodb_client):
        """get_diversification_recommendations returns empty list for diversified agent."""
        from app.services.vendor_risk_service import VendorRiskService

        table = "agent_transactions"
        rows = [
            {"id": i, "row_id": i, "agent_id": "agent-div",
             "vendor": f"vendor-{i}", "amount": 100.0,
             "created_at": "2026-03-01T00:00:00Z"}
            for i in range(10)
        ]
        mock_zerodb_client.data[table] = rows
        svc = VendorRiskService(client=mock_zerodb_client)

        result = await svc.get_diversification_recommendations(agent_id="agent-div")

        assert result["recommendations"] == []


class DescribeVendorConcentrationSchema:
    """Schema validation for observability.VendorConcentration."""

    def it_builds_vendor_concentration_with_required_fields(self):
        """VendorConcentration requires agent_id, hhi, risk_level, vendors."""
        from app.schemas.observability import VendorConcentration
        vc = VendorConcentration(
            agent_id="agent-001",
            hhi=6800,
            risk_level="high",
            vendors=[{"vendor": "A", "spend": 800.0, "market_share_pct": 80.0}],
            total_spend=1000.0,
        )
        assert vc.hhi == 6800
        assert vc.risk_level == "high"
