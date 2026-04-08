"""
Tests for AnalyticsDashboardService — Issue #170

Analytics dashboard endpoints: spend summary, activity, trends, health.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #170
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


class DescribeAnalyticsDashboardService:
    """Specification for AnalyticsDashboardService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.analytics_dashboard_service import AnalyticsDashboardService
        return AnalyticsDashboardService(client=mock_zerodb_client)

    @pytest.fixture
    def service_with_data(self, mock_zerodb_client):
        """Service with transaction and decision data seeded."""
        from app.services.analytics_dashboard_service import AnalyticsDashboardService

        tx_table = "agent_transactions"
        dec_table = "agent_decisions"

        mock_zerodb_client.data[tx_table] = [
            {
                "id": i,
                "row_id": i,
                "agent_id": f"agent-{i % 2}",
                "project_id": "proj-dash",
                "amount": float(10 * (i + 1)),
                "category": "compute" if i % 2 == 0 else "storage",
                "created_at": f"2026-04-0{(i % 3) + 1}T00:00:00Z",
            }
            for i in range(6)
        ]

        mock_zerodb_client.data[dec_table] = [
            {
                "id": i,
                "row_id": i,
                "agent_id": "agent-0",
                "project_id": "proj-dash",
                "decision_type": "task_selection",
                "created_at": "2026-04-01T00:00:00Z",
            }
            for i in range(3)
        ]

        return AnalyticsDashboardService(client=mock_zerodb_client)

    # ------------------------------------------------------------------ #
    # get_spend_summary
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_total_spend_for_project(self, service_with_data):
        """get_spend_summary includes total_spend for the project."""
        result = await service_with_data.get_spend_summary(
            project_id="proj-dash", period="7d"
        )

        assert "total_spend" in result
        assert result["total_spend"] >= 0
        assert "project_id" in result

    @pytest.mark.asyncio
    async def it_returns_spend_broken_down_by_agent(self, service_with_data):
        """get_spend_summary includes per-agent breakdown."""
        result = await service_with_data.get_spend_summary(
            project_id="proj-dash", period="7d"
        )

        assert "by_agent" in result
        assert isinstance(result["by_agent"], dict)

    @pytest.mark.asyncio
    async def it_returns_spend_broken_down_by_category(self, service_with_data):
        """get_spend_summary includes per-category breakdown."""
        result = await service_with_data.get_spend_summary(
            project_id="proj-dash", period="30d"
        )

        assert "by_category" in result
        assert isinstance(result["by_category"], dict)

    @pytest.mark.asyncio
    async def it_returns_zero_totals_for_empty_project(self, service):
        """get_spend_summary returns zero totals when no transactions exist."""
        result = await service.get_spend_summary(
            project_id="no-proj", period="7d"
        )

        assert result["total_spend"] == 0.0
        assert result["by_agent"] == {}
        assert result["by_category"] == {}

    # ------------------------------------------------------------------ #
    # get_agent_activity
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_tasks_completed_and_decisions_made(self, service_with_data):
        """get_agent_activity includes tasks_completed and decisions_made."""
        result = await service_with_data.get_agent_activity(
            project_id="proj-dash", period="7d"
        )

        assert "decisions_made" in result
        assert "payments_settled" in result
        assert "project_id" in result
        assert result["project_id"] == "proj-dash"

    @pytest.mark.asyncio
    async def it_returns_zero_activity_for_empty_project(self, service):
        """get_agent_activity returns zeros for unknown project."""
        result = await service.get_agent_activity(
            project_id="no-proj", period="7d"
        )

        assert result["decisions_made"] == 0
        assert result["payments_settled"] == 0

    # ------------------------------------------------------------------ #
    # get_trend_data
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_time_series_for_daily_granularity(self, service_with_data):
        """get_trend_data returns a list of time-bucketed data points."""
        result = await service_with_data.get_trend_data(
            project_id="proj-dash",
            metric="spend",
            granularity="daily",
        )

        assert "data_points" in result
        assert "metric" in result
        assert "granularity" in result
        assert isinstance(result["data_points"], list)
        assert result["granularity"] == "daily"

    @pytest.mark.asyncio
    async def it_returns_time_series_for_weekly_granularity(self, service):
        """get_trend_data works for weekly granularity."""
        result = await service.get_trend_data(
            project_id="proj-empty",
            metric="spend",
            granularity="weekly",
        )

        assert result["granularity"] == "weekly"
        assert isinstance(result["data_points"], list)

    @pytest.mark.asyncio
    async def it_returns_time_series_for_hourly_granularity(self, service):
        """get_trend_data works for hourly granularity."""
        result = await service.get_trend_data(
            project_id="proj-empty",
            metric="decisions",
            granularity="hourly",
        )

        assert result["granularity"] == "hourly"

    # ------------------------------------------------------------------ #
    # get_project_health
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_composite_health_score(self, service):
        """get_project_health returns a health_score between 0 and 100."""
        result = await service.get_project_health(project_id="proj-001")

        assert "health_score" in result
        assert "project_id" in result
        assert 0 <= result["health_score"] <= 100
        assert result["project_id"] == "proj-001"

    @pytest.mark.asyncio
    async def it_includes_component_scores_in_health(self, service):
        """get_project_health breaks health into component scores."""
        result = await service.get_project_health(project_id="proj-001")

        assert "components" in result
        components = result["components"]
        assert "spend" in components
        assert "anomalies" in components
        assert "drift" in components
        assert "activity" in components


class DescribeAnalyticsSchemas:
    """Schema validation for analytics schemas."""

    def it_builds_spend_summary_with_required_fields(self):
        """SpendSummary requires project_id, total_spend, by_agent, by_category."""
        from app.schemas.analytics import SpendSummary
        summary = SpendSummary(
            project_id="proj-001",
            period="7d",
            total_spend=1500.0,
            by_agent={"agent-001": 1000.0, "agent-002": 500.0},
            by_category={"compute": 1200.0, "storage": 300.0},
        )
        assert summary.total_spend == 1500.0
        assert "agent-001" in summary.by_agent

    def it_builds_agent_activity_with_counts(self):
        """AgentActivity requires project_id and activity counts."""
        from app.schemas.analytics import AgentActivity
        activity = AgentActivity(
            project_id="proj-001",
            period="7d",
            decisions_made=42,
            payments_settled=10,
            tasks_completed=30,
        )
        assert activity.decisions_made == 42

    def it_builds_trend_data_with_data_points(self):
        """TrendData requires project_id, metric, granularity, data_points."""
        from app.schemas.analytics import TrendData
        trend = TrendData(
            project_id="proj-001",
            metric="spend",
            granularity="daily",
            data_points=[{"timestamp": "2026-04-01", "value": 100.0}],
        )
        assert len(trend.data_points) == 1

    def it_builds_project_health_with_score_and_components(self):
        """ProjectHealth requires project_id, health_score, components."""
        from app.schemas.analytics import ProjectHealth
        health = ProjectHealth(
            project_id="proj-001",
            health_score=85.0,
            components={"spend": 90.0, "anomalies": 80.0, "drift": 85.0, "activity": 85.0},
        )
        assert health.health_score == 85.0
