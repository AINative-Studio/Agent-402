"""
Tests for Analytics API Router — Issue #170

GET /analytics/spend, /analytics/activity, /analytics/trends, /analytics/health
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #170
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch
from typing import Optional, Dict, List, Any


@pytest.fixture
def analytics_app():
    """Isolated FastAPI app with only the analytics router mounted."""
    from app.api.analytics import router
    app = FastAPI()
    app.include_router(router, prefix="/analytics")
    return app


@pytest.fixture
def analytics_client(analytics_app):
    return TestClient(analytics_app)


@pytest.fixture
def mock_dashboard_service():
    svc = AsyncMock()
    svc.get_spend_summary.return_value = {
        "project_id": "proj-001",
        "period": "7d",
        "total_spend": 1500.0,
        "by_agent": {"agent-001": 1000.0},
        "by_category": {"compute": 1500.0},
    }
    svc.get_agent_activity.return_value = {
        "project_id": "proj-001",
        "period": "7d",
        "decisions_made": 42,
        "payments_settled": 10,
        "tasks_completed": 30,
    }
    svc.get_trend_data.return_value = {
        "project_id": "proj-001",
        "metric": "spend",
        "granularity": "daily",
        "data_points": [{"timestamp": "2026-04-01", "value": 100.0}],
    }
    svc.get_project_health.return_value = {
        "project_id": "proj-001",
        "health_score": 85.0,
        "components": {"spend": 90.0, "anomalies": 80.0, "drift": 85.0, "activity": 85.0},
    }
    return svc


class DescribeAnalyticsSpendEndpoint:
    """GET /analytics/spend"""

    def it_returns_200_with_spend_summary(self, analytics_client, mock_dashboard_service):
        """GET /analytics/spend returns 200 with spend data."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/spend?project_id=proj-001&period=7d")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_spend" in data
        assert data["project_id"] == "proj-001"

    def it_requires_project_id_query_param(self, analytics_client, mock_dashboard_service):
        """GET /analytics/spend returns 422 when project_id is missing."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/spend?period=7d")

        assert resp.status_code == 422


class DescribeAnalyticsActivityEndpoint:
    """GET /analytics/activity"""

    def it_returns_200_with_activity_data(self, analytics_client, mock_dashboard_service):
        """GET /analytics/activity returns 200 with agent activity counts."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/activity?project_id=proj-001&period=7d")

        assert resp.status_code == 200
        data = resp.json()
        assert "decisions_made" in data
        assert "payments_settled" in data

    def it_requires_project_id_query_param(self, analytics_client, mock_dashboard_service):
        """GET /analytics/activity returns 422 without project_id."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/activity")

        assert resp.status_code == 422


class DescribeAnalyticsTrendsEndpoint:
    """GET /analytics/trends"""

    def it_returns_200_with_trend_data(self, analytics_client, mock_dashboard_service):
        """GET /analytics/trends returns 200 with time-series data."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get(
                "/analytics/trends?project_id=proj-001&metric=spend&granularity=daily"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "data_points" in data
        assert "granularity" in data

    def it_requires_metric_query_param(self, analytics_client, mock_dashboard_service):
        """GET /analytics/trends returns 422 without metric."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/trends?project_id=proj-001")

        assert resp.status_code == 422


class DescribeAnalyticsHealthEndpoint:
    """GET /analytics/health"""

    def it_returns_200_with_health_score(self, analytics_client, mock_dashboard_service):
        """GET /analytics/health returns 200 with composite health score."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/health?project_id=proj-001")

        assert resp.status_code == 200
        data = resp.json()
        assert "health_score" in data
        assert 0 <= data["health_score"] <= 100

    def it_requires_project_id_query_param(self, analytics_client, mock_dashboard_service):
        """GET /analytics/health returns 422 without project_id."""
        with patch(
            "app.api.analytics.get_analytics_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            resp = analytics_client.get("/analytics/health")

        assert resp.status_code == 422
