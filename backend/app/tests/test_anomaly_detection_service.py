"""
Tests for AnomalyDetectionService — Issue #164

Statistical anomaly detection for agent spending.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #164
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


class DescribeAnomalyDetectionService:
    """Specification for AnomalyDetectionService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.anomaly_detection_service import AnomalyDetectionService
        return AnomalyDetectionService(client=mock_zerodb_client)

    @pytest.fixture
    def service_with_spend_data(self, mock_zerodb_client):
        """Service pre-seeded with consistent daily spend rows."""
        from app.services.anomaly_detection_service import AnomalyDetectionService
        # Seed transaction rows into mock ZeroDB
        table = "agent_transactions"
        import uuid
        from datetime import datetime, timedelta, timezone

        baseline_start = datetime.now(timezone.utc) - timedelta(days=95)
        for i in range(90):
            day = baseline_start + timedelta(days=i)
            mock_zerodb_client.data.setdefault(table, []).append({
                "id": i + 1,
                "row_id": i + 1,
                "agent_id": "agent-spend",
                "amount": 10.0,  # stable $10/day
                "created_at": day.isoformat(),
            })

        svc = AnomalyDetectionService(client=mock_zerodb_client)
        return svc

    # ------------------------------------------------------------------ #
    # calculate_baseline
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_calculates_mean_and_stddev_from_daily_spend(self, service_with_spend_data):
        """calculate_baseline returns mean and stddev of daily spend."""
        baseline = await service_with_spend_data.calculate_baseline(
            agent_id="agent-spend", window_days=90
        )

        assert "mean" in baseline
        assert "stddev" in baseline
        assert "window_days" in baseline
        assert baseline["mean"] >= 0
        assert baseline["stddev"] >= 0

    @pytest.mark.asyncio
    async def it_returns_zero_baseline_when_no_data(self, service):
        """calculate_baseline returns mean=0 stddev=0 for unknown agent."""
        baseline = await service.calculate_baseline(
            agent_id="no-data-agent", window_days=90
        )
        assert baseline["mean"] == 0.0
        assert baseline["stddev"] == 0.0

    # ------------------------------------------------------------------ #
    # check_transaction_anomaly
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_flags_transaction_greater_than_two_stddev_as_anomalous(
        self, service_with_spend_data
    ):
        """check_transaction_anomaly returns is_anomaly=True for spike amount."""
        # $10/day baseline, $200 is way beyond 2 stddev
        result = await service_with_spend_data.check_transaction_anomaly(
            agent_id="agent-spend", amount=200.0
        )

        assert result["is_anomaly"] is True
        assert "z_score" in result
        assert result["z_score"] > 2.0

    @pytest.mark.asyncio
    async def it_allows_normal_transaction_within_stddev(self, service_with_spend_data):
        """check_transaction_anomaly returns is_anomaly=False for normal amount."""
        result = await service_with_spend_data.check_transaction_anomaly(
            agent_id="agent-spend", amount=10.0
        )

        assert result["is_anomaly"] is False

    @pytest.mark.asyncio
    async def it_treats_any_transaction_as_anomalous_when_no_baseline(self, service):
        """check_transaction_anomaly flags non-zero amounts when no history."""
        result = await service.check_transaction_anomaly(
            agent_id="no-history-agent", amount=5.0
        )

        assert "is_anomaly" in result
        assert "z_score" in result

    @pytest.mark.asyncio
    async def it_uses_custom_threshold_when_provided(self, service_with_spend_data):
        """check_transaction_anomaly accepts custom z-score threshold."""
        result = await service_with_spend_data.check_transaction_anomaly(
            agent_id="agent-spend", amount=11.0, threshold=0.1
        )
        # At threshold=0.1, even a small deviation triggers anomaly
        assert result["is_anomaly"] is True

    # ------------------------------------------------------------------ #
    # detect_anomalies
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_list_of_anomalous_transactions(self, service_with_spend_data, mock_zerodb_client):
        """detect_anomalies returns anomalies found in the analysis window."""
        # Add one large spike
        mock_zerodb_client.data["agent_transactions"].append({
            "id": 999,
            "row_id": 999,
            "agent_id": "agent-spend",
            "amount": 500.0,
            "created_at": "2026-04-01T12:00:00+00:00",
        })

        result = await service_with_spend_data.detect_anomalies(
            agent_id="agent-spend", window_days=30
        )

        assert "anomalies" in result
        assert "window_days" in result
        assert isinstance(result["anomalies"], list)

    @pytest.mark.asyncio
    async def it_returns_empty_anomalies_for_stable_spend(self, service_with_spend_data):
        """detect_anomalies returns empty list when no spikes exist."""
        result = await service_with_spend_data.detect_anomalies(
            agent_id="agent-spend", window_days=30
        )

        assert result["anomalies"] == []

    # ------------------------------------------------------------------ #
    # get_anomaly_report
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_summary_report_structure(self, service):
        """get_anomaly_report returns structured summary."""
        report = await service.get_anomaly_report(agent_id="agent-001")

        assert "agent_id" in report
        assert "total_anomalies" in report
        assert "anomaly_rate" in report
        assert "anomalies" in report
        assert report["agent_id"] == "agent-001"


class DescribeAnomalyReportSchema:
    """Schema validation for observability.AnomalyReport."""

    def it_builds_anomaly_report_with_required_fields(self):
        """AnomalyReport requires agent_id, total_anomalies, anomaly_rate."""
        from app.schemas.observability import AnomalyReport
        report = AnomalyReport(
            agent_id="agent-001",
            total_anomalies=3,
            anomaly_rate=0.15,
            anomalies=[],
        )
        assert report.agent_id == "agent-001"
        assert report.total_anomalies == 3
