"""
Pydantic schemas for the Billing Service — Issues #226, #227, #228.

Provides models for:
  - UsageEvent          — a single recorded cost event
  - AgentCostBreakdown  — per-category cost breakdown for an agent
  - ProjectCostSummary  — aggregate cost summary across a project's agents
  - AgentBudgetConfig   — daily/monthly budget limits for an agent
  - AgentBudgetStatus   — current spend vs configured limits for an agent
  - BudgetCheckResult   — result of a budget-allowance check
  - ProjectBudgetConfig — daily/monthly budget limits for a project
  - ProjectBudgetStatus — aggregate spend vs limits for a project

Built by AINative Dev Team.
Refs #226, #227, #228.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Usage Events
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset(
    {"llm_inference", "memory_storage", "vector_search", "file_storage", "payment_fee"}
)


class UsageEvent(BaseModel):
    """A single recorded cost event for an agent."""

    event_id: str = Field(..., description="Unique identifier for this event")
    agent_id: str = Field(..., description="Agent that incurred the cost")
    category: str = Field(
        ...,
        description=(
            "Cost category: llm_inference | memory_storage | "
            "vector_search | file_storage | payment_fee"
        ),
    )
    amount: Decimal = Field(..., description="Cost amount in USD", ge=0)
    period: str = Field(
        ...,
        description="Billing period in YYYY-MM format",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key/value metadata for this event",
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event was recorded",
    )


# ---------------------------------------------------------------------------
# Agent Cost Breakdown (Issue #226)
# ---------------------------------------------------------------------------

class AgentCostBreakdown(BaseModel):
    """Per-category cost breakdown for a single agent over a billing period."""

    agent_id: str = Field(..., description="Agent identifier")
    period: str = Field(..., description="Billing period YYYY-MM")
    llm_inference: Decimal = Field(Decimal("0"), description="LLM inference costs")
    memory_storage: Decimal = Field(Decimal("0"), description="Memory storage costs")
    vector_search: Decimal = Field(Decimal("0"), description="Vector search costs")
    file_storage: Decimal = Field(Decimal("0"), description="File storage costs")
    payment_fee: Decimal = Field(Decimal("0"), description="Payment processing fees")
    total: Decimal = Field(Decimal("0"), description="Sum of all category costs")


# ---------------------------------------------------------------------------
# Project Cost Summary (Issue #226)
# ---------------------------------------------------------------------------

class AgentCostEntry(BaseModel):
    """Single agent entry within a project cost summary."""

    agent_id: str
    total: Decimal


class ProjectCostSummary(BaseModel):
    """Aggregate cost summary for a project across all its agents."""

    project_id: str = Field(..., description="Project identifier")
    period: str = Field(..., description="Billing period YYYY-MM")
    agents: List[AgentCostEntry] = Field(
        default_factory=list,
        description="Per-agent cost breakdowns",
    )
    total: Decimal = Field(Decimal("0"), description="Grand total across all agents")


# ---------------------------------------------------------------------------
# Agent Budget Config & Status (Issue #227)
# ---------------------------------------------------------------------------

class AgentBudgetConfig(BaseModel):
    """Daily/monthly spending limits for a single agent."""

    agent_id: str = Field(..., description="Agent identifier")
    max_daily: Optional[Decimal] = Field(
        None,
        description="Maximum daily spend in USD. None = unlimited.",
        ge=0,
    )
    max_monthly: Optional[Decimal] = Field(
        None,
        description="Maximum monthly spend in USD. None = unlimited.",
        ge=0,
    )


class AgentBudgetStatus(BaseModel):
    """Current spend vs configured limits for an agent."""

    agent_id: str
    max_daily: Optional[Decimal]
    max_monthly: Optional[Decimal]
    spent_daily: Decimal = Decimal("0")
    spent_monthly: Decimal = Decimal("0")
    remaining_daily: Optional[Decimal] = None
    remaining_monthly: Optional[Decimal] = None


class BudgetCheckResult(BaseModel):
    """Result of a budget-allowance check."""

    allowed: bool
    remaining_daily: Optional[Decimal] = None
    remaining_monthly: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# Project Budget Config & Status (Issue #228)
# ---------------------------------------------------------------------------

class ProjectBudgetConfig(BaseModel):
    """Daily/monthly spending limits for a project (aggregate across agents)."""

    project_id: str = Field(..., description="Project identifier")
    max_daily: Optional[Decimal] = Field(
        None,
        description="Maximum daily project spend in USD. None = unlimited.",
        ge=0,
    )
    max_monthly: Optional[Decimal] = Field(
        None,
        description="Maximum monthly project spend in USD. None = unlimited.",
        ge=0,
    )


class ProjectBudgetStatus(BaseModel):
    """Aggregate spend vs limits for a project."""

    project_id: str
    max_daily: Optional[Decimal]
    max_monthly: Optional[Decimal]
    spent_daily: Decimal = Decimal("0")
    spent_monthly: Decimal = Decimal("0")
    remaining: Optional[Decimal] = None
