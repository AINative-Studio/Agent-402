"""
Billing API router — Issues #226, #227, #228.

Endpoints (all under /v1/public/billing):
  GET  /agents/{agent_id}/costs              — per-agent cost breakdown
  GET  /projects/{project_id}/costs          — project cost summary
  POST /agents/{agent_id}/events             — record usage event
  GET  /agents/{agent_id}/events             — usage history
  PUT  /agents/{agent_id}/budget             — set agent budget
  GET  /agents/{agent_id}/budget             — get agent budget status
  POST /agents/{agent_id}/budget/check       — check agent budget
  PUT  /projects/{project_id}/budget         — set project budget
  GET  /projects/{project_id}/budget         — get project budget status
  POST /projects/{project_id}/budget/check   — check project budget

NOTE: This router is NOT registered in main.py (per task spec).

Built by AINative Dev Team.
Refs #226, #227, #228.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import get_current_user
from app.schemas.billing import (
    AgentBudgetConfig,
    AgentBudgetStatus,
    AgentCostBreakdown,
    BudgetCheckResult,
    ProjectBudgetConfig,
    ProjectBudgetStatus,
    ProjectCostSummary,
    UsageEvent,
)
from app.services.billing_service import billing_service

router = APIRouter(prefix="/v1/public/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Issue #226 — Per-Agent Cost Breakdown
# ---------------------------------------------------------------------------


@router.get(
    "/agents/{agent_id}/costs",
    status_code=status.HTTP_200_OK,
    summary="Get per-agent cost breakdown",
    description="""
    Returns costs broken down by category (llm_inference, memory_storage,
    vector_search, file_storage, payment_fee) for the specified agent
    during the given billing period.

    **Authentication:** Requires X-API-Key header.

    Refs #226.
    """,
)
async def get_agent_cost_breakdown(
    agent_id: str,
    period: str = Query(..., description="Billing period in YYYY-MM format"),
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    return await billing_service.get_agent_cost_breakdown(agent_id, period)


@router.get(
    "/projects/{project_id}/costs",
    status_code=status.HTTP_200_OK,
    summary="Get project cost summary",
    description="""
    Returns aggregate costs across all agents associated with a project
    for the given billing period.

    Refs #226.
    """,
)
async def get_project_cost_summary(
    project_id: str,
    period: str = Query(..., description="Billing period in YYYY-MM format"),
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    return await billing_service.get_project_cost_summary(project_id, period)


@router.post(
    "/agents/{agent_id}/events",
    status_code=status.HTTP_201_CREATED,
    summary="Record usage event",
    description="""
    Log a cost event for an agent. The event is attributed to a billing period
    and category and contributes to cost breakdowns and budget checks.

    Refs #226.
    """,
)
async def record_usage_event(
    agent_id: str,
    body: Dict[str, Any],
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    category = body.get("category", "")
    amount = Decimal(str(body.get("amount", "0")))
    metadata = body.get("metadata", {})
    return await billing_service.record_usage_event(agent_id, category, amount, metadata)


@router.get(
    "/agents/{agent_id}/events",
    status_code=status.HTTP_200_OK,
    summary="Get usage history",
    description="""
    Retrieve paginated usage event history for an agent filtered by category.

    Refs #226.
    """,
)
async def get_usage_history(
    agent_id: str,
    category: str = Query(..., description="Cost category to filter on"),
    limit: int = Query(20, ge=1, le=1000, description="Max events to return"),
    _user: str = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return await billing_service.get_usage_history(agent_id, category, limit)


# ---------------------------------------------------------------------------
# Issue #227 — Per-Agent Budget Limits
# ---------------------------------------------------------------------------


@router.put(
    "/agents/{agent_id}/budget",
    status_code=status.HTTP_200_OK,
    summary="Set agent budget limits",
    description="""
    Configure daily and monthly spending limits for an agent.
    Replaces any existing budget configuration.

    Refs #227.
    """,
)
async def set_agent_budget(
    agent_id: str,
    body: Dict[str, Any],
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    raw_daily = body.get("max_daily")
    raw_monthly = body.get("max_monthly")
    max_daily: Optional[Decimal] = Decimal(str(raw_daily)) if raw_daily is not None else None
    max_monthly: Optional[Decimal] = Decimal(str(raw_monthly)) if raw_monthly is not None else None
    return await billing_service.set_agent_budget(agent_id, max_daily, max_monthly)


@router.get(
    "/agents/{agent_id}/budget",
    status_code=status.HTTP_200_OK,
    summary="Get agent budget status",
    description="""
    Return current daily/monthly spend against configured limits for an agent.

    Refs #227.
    """,
)
async def get_agent_budget_status(
    agent_id: str,
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    return await billing_service.get_agent_budget_status(agent_id)


@router.post(
    "/agents/{agent_id}/budget/check",
    status_code=status.HTTP_200_OK,
    summary="Check agent budget",
    description="""
    Check whether a proposed spend amount falls within the agent's configured
    daily and monthly budget limits.

    Returns: allowed (bool), remaining_daily, remaining_monthly.

    Refs #227.
    """,
)
async def check_agent_budget(
    agent_id: str,
    body: Dict[str, Any],
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    amount = Decimal(str(body.get("amount", "0")))
    return await billing_service.check_agent_budget(agent_id, amount)


# ---------------------------------------------------------------------------
# Issue #228 — Per-Project Budget Limits
# ---------------------------------------------------------------------------


@router.put(
    "/projects/{project_id}/budget",
    status_code=status.HTTP_200_OK,
    summary="Set project budget limits",
    description="""
    Configure daily and monthly spending limits for a project (aggregate across
    all agents associated with the project).

    Refs #228.
    """,
)
async def set_project_budget(
    project_id: str,
    body: Dict[str, Any],
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    raw_daily = body.get("max_daily")
    raw_monthly = body.get("max_monthly")
    max_daily: Optional[Decimal] = Decimal(str(raw_daily)) if raw_daily is not None else None
    max_monthly: Optional[Decimal] = Decimal(str(raw_monthly)) if raw_monthly is not None else None
    return await billing_service.set_project_budget(project_id, max_daily, max_monthly)


@router.get(
    "/projects/{project_id}/budget",
    status_code=status.HTTP_200_OK,
    summary="Get project budget status",
    description="""
    Return aggregate daily/monthly spend across all agents vs configured project
    limits.

    Refs #228.
    """,
)
async def get_project_budget_status(
    project_id: str,
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    return await billing_service.get_project_budget_status(project_id)


@router.post(
    "/projects/{project_id}/budget/check",
    status_code=status.HTTP_200_OK,
    summary="Check project budget",
    description="""
    Check whether a proposed spend amount falls within the project's configured
    daily and monthly budget limits.

    Returns: allowed (bool), remaining.

    Refs #228.
    """,
)
async def check_project_budget(
    project_id: str,
    body: Dict[str, Any],
    _user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    amount = Decimal(str(body.get("amount", "0")))
    return await billing_service.check_project_budget(project_id, amount)
