"""
Analytics schemas for the dashboard service.

Built by AINative Dev Team
Refs #170
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class SpendSummary(BaseModel):
    """Spend summary for a project over a given period."""

    project_id: str
    period: str
    total_spend: float
    by_agent: Dict[str, float] = Field(default_factory=dict)
    by_category: Dict[str, float] = Field(default_factory=dict)


class AgentActivity(BaseModel):
    """Agent activity counts for a project over a given period."""

    project_id: str
    period: str
    decisions_made: int = 0
    payments_settled: int = 0
    tasks_completed: int = 0


class TrendData(BaseModel):
    """Time-series trend data for a metric."""

    project_id: str
    metric: str
    granularity: str
    data_points: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectHealth(BaseModel):
    """Composite health score for a project."""

    project_id: str
    health_score: float
    components: Dict[str, float] = Field(default_factory=dict)
