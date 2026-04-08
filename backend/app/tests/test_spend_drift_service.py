"""
Tests for SpendDriftService — Issue #165

Spend drift monitoring compares current vs baseline spend rates.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #165
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


class DescribeSpendDriftService:
    """Specification for SpendDriftService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.spend_drift_service import SpendDriftService
        return SpendDriftService(client=mock_zerodb_client)

    @pytest.fixture
    def service_with_drift_data(self, mock_zerodb_client):
        """Service with baseline and current spend seeded."""
        from app.services.spend_drift_service import SpendDriftService
        from datetime import datetime, timedelta, timezone

        table = "agent_transactions"
        now = datetime.now(timezone.utc)

        # Baseline: 30 days at $10/day
        for i in range(30):
            day = now - timedelta(days=40 + i)
            mock_zerodb_client.data.setdefault(table, []).append({
                "id": i + 100,
                "row_id": i + 100,
                "agent_id": "agent-drift",
                "project_id": "proj-001",
                "amount": 10.0,
                "created_at": day.isoformat(),
            })

        # Current: 7 days at $20/day (100% drift up)
        for i in range(7):
            day = now - timedelta(days=i)
            mock_zerodb_client.data[table].append({
                "id": i + 200,
                "row_id": i + 200,
                "agent_id": "agent-drift",
                "project_id": "proj-001",
                "amount": 20.0,
                "created_at": day.isoformat(),
            })

        return SpendDriftService(client=mock_zerodb_client)

    # ------------------------------------------------------------------ #
    # calculate_drift
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_calculates_positive_drift_when_current_spend_is_higher(
        self, service_with_drift_data
    ):
        """calculate_drift returns positive pct when current rate exceeds baseline."""
        result = await service_with_drift_data.calculate_drift(
            agent_id="agent-drift",
            baseline_period_days=30,
            current_period_days=7,
        )

        assert "drift_pct" in result
        assert result["drift_pct"] > 0
        assert "baseline_rate" in result
        assert "current_rate" in result
        assert result["current_rate"] > result["baseline_rate"]

    @pytest.mark.asyncio
    async def it_returns_zero_drift_when_no_spend_data(self, service):
        """calculate_drift returns drift_pct=0 when no transactions exist."""
        result = await service.calculate_drift(
            agent_id="no-data-agent",
            baseline_period_days=30,
            current_period_days=7,
        )

        assert result["drift_pct"] == 0.0
        assert result["baseline_rate"] == 0.0
        assert result["current_rate"] == 0.0

    @pytest.mark.asyncio
    async def it_includes_agent_id_in_drift_result(self, service):
        """calculate_drift result includes the queried agent_id."""
        result = await service.calculate_drift(
            agent_id="agent-xyz",
            baseline_period_days=30,
            current_period_days=7,
        )
        assert result["agent_id"] == "agent-xyz"

    # ------------------------------------------------------------------ #
    # get_drift_alerts
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_agents_whose_drift_exceeds_threshold(
        self, service_with_drift_data
    ):
        """get_drift_alerts returns agents with drift > threshold_pct."""
        alerts = await service_with_drift_data.get_drift_alerts(
            project_id="proj-001", threshold_pct=20
        )

        assert isinstance(alerts, list)
        # agent-drift should be in alerts (100% drift > 20% threshold)
        agent_ids = [a["agent_id"] for a in alerts]
        assert "agent-drift" in agent_ids

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_agents_breach_threshold(self, service):
        """get_drift_alerts returns [] when drift is within threshold."""
        alerts = await service.get_drift_alerts(
            project_id="no-proj", threshold_pct=20
        )
        assert alerts == []

    @pytest.mark.asyncio
    async def it_includes_drift_pct_in_each_alert(self, service_with_drift_data):
        """Each drift alert contains drift_pct and agent_id."""
        alerts = await service_with_drift_data.get_drift_alerts(
            project_id="proj-001", threshold_pct=20
        )
        for alert in alerts:
            assert "agent_id" in alert
            assert "drift_pct" in alert

    # ------------------------------------------------------------------ #
    # set_drift_baseline
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_snapshots_current_spend_as_new_baseline(self, service, mock_zerodb_client):
        """set_drift_baseline persists a baseline snapshot row."""
        result = await service.set_drift_baseline(agent_id="agent-snap")

        assert result["agent_id"] == "agent-snap"
        assert result["status"] == "baseline_set"
        assert "baseline_rate" in result

        calls = [c for c in mock_zerodb_client.call_history if c["method"] == "insert_row"]
        assert any(c["table_name"] == "spend_drift_baselines" for c in calls)


class DescribeDriftAlertSchema:
    """Schema validation for observability.DriftAlert."""

    def it_builds_drift_alert_with_required_fields(self):
        """DriftAlert requires agent_id and drift_pct."""
        from app.schemas.observability import DriftAlert
        alert = DriftAlert(
            agent_id="agent-001",
            drift_pct=55.5,
            baseline_rate=10.0,
            current_rate=15.55,
        )
        assert alert.agent_id == "agent-001"
        assert alert.drift_pct == 55.5
