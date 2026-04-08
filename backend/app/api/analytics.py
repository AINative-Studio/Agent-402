"""
Analytics Dashboard API Router — Issue #170

Endpoints:
  GET /analytics/spend    — spend summary for a project
  GET /analytics/activity — agent activity counts
  GET /analytics/trends   — time-series trend data
  GET /analytics/health   — composite project health score

Built by AINative Dev Team
Refs #170
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Depends, Query

from app.services.analytics_dashboard_service import (
    AnalyticsDashboardService,
    analytics_dashboard_service,
)

router = APIRouter(tags=["analytics"])


def get_analytics_dashboard_service() -> AnalyticsDashboardService:
    """Dependency provider for AnalyticsDashboardService."""
    return analytics_dashboard_service


@router.get("/spend")
async def get_spend(
    project_id: str = Query(..., description="Project identifier"),
    period: str = Query("7d", description="Look-back period (e.g. 7d, 30d)"),
    service: AnalyticsDashboardService = Depends(get_analytics_dashboard_service),
) -> Dict[str, Any]:
    """Return spend summary for a project over a given period."""
    return await service.get_spend_summary(project_id=project_id, period=period)


@router.get("/activity")
async def get_activity(
    project_id: str = Query(..., description="Project identifier"),
    period: str = Query("7d", description="Look-back period"),
    service: AnalyticsDashboardService = Depends(get_analytics_dashboard_service),
) -> Dict[str, Any]:
    """Return agent activity counts for a project."""
    return await service.get_agent_activity(project_id=project_id, period=period)


@router.get("/trends")
async def get_trends(
    project_id: str = Query(..., description="Project identifier"),
    metric: str = Query(..., description="Metric name (spend, decisions, payments)"),
    granularity: str = Query("daily", description="Granularity: hourly, daily, weekly"),
    service: AnalyticsDashboardService = Depends(get_analytics_dashboard_service),
) -> Dict[str, Any]:
    """Return time-series trend data for a project metric."""
    return await service.get_trend_data(
        project_id=project_id,
        metric=metric,
        granularity=granularity,
    )


@router.get("/health")
async def get_health(
    project_id: str = Query(..., description="Project identifier"),
    service: AnalyticsDashboardService = Depends(get_analytics_dashboard_service),
) -> Dict[str, Any]:
    """Return composite health score for a project."""
    return await service.get_project_health(project_id=project_id)
