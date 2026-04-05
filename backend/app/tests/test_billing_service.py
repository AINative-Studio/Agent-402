"""
Tests for BillingService — Issues #226, #227, #228.

Covers:
  - Per-agent cost breakdown (Issue #226)
  - Per-agent budget limits (Issue #227)
  - Per-project budget limits (Issue #228)

BDD-style: DescribeX / it_does_something naming convention.
Refs #226, #227, #228.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """In-memory ZeroDB mock client for billing tests."""
    from app.tests.fixtures.zerodb_mock import MockZeroDBClient
    client = MockZeroDBClient()
    client.reset()
    return client


@pytest.fixture
def billing(mock_db):
    """Fresh BillingService instance backed by the mock DB."""
    from app.services.billing_service import BillingService
    return BillingService(client=mock_db)


# ---------------------------------------------------------------------------
# Issue #226 — Per-Agent Cost Breakdown
# ---------------------------------------------------------------------------

class DescribeGetAgentCostBreakdown:
    """Tests for BillingService.get_agent_cost_breakdown."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_all_cost_categories(self, billing):
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert isinstance(result, dict)
        expected_keys = {
            "agent_id", "period", "llm_inference",
            "memory_storage", "vector_search", "file_storage", "payment_fee", "total",
        }
        assert expected_keys == set(result.keys())

    @pytest.mark.asyncio
    async def it_returns_zero_costs_when_no_events_exist(self, billing):
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["total"] == Decimal("0")
        assert result["llm_inference"] == Decimal("0")
        assert result["memory_storage"] == Decimal("0")
        assert result["vector_search"] == Decimal("0")
        assert result["file_storage"] == Decimal("0")
        assert result["payment_fee"] == Decimal("0")

    @pytest.mark.asyncio
    async def it_includes_agent_id_in_response(self, billing):
        result = await billing.get_agent_cost_breakdown("agent-abc", "2026-04")
        assert result["agent_id"] == "agent-abc"

    @pytest.mark.asyncio
    async def it_includes_period_in_response(self, billing):
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["period"] == "2026-04"

    @pytest.mark.asyncio
    async def it_sums_llm_inference_events(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("1.50"), {})
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("0.50"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["llm_inference"] == Decimal("2.00")

    @pytest.mark.asyncio
    async def it_sums_memory_storage_events(self, billing):
        await billing.record_usage_event("agent-1", "memory_storage", Decimal("0.10"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["memory_storage"] == Decimal("0.10")

    @pytest.mark.asyncio
    async def it_sums_vector_search_events(self, billing):
        await billing.record_usage_event("agent-1", "vector_search", Decimal("0.25"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["vector_search"] == Decimal("0.25")

    @pytest.mark.asyncio
    async def it_sums_file_storage_events(self, billing):
        await billing.record_usage_event("agent-1", "file_storage", Decimal("0.05"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["file_storage"] == Decimal("0.05")

    @pytest.mark.asyncio
    async def it_sums_payment_fee_events(self, billing):
        await billing.record_usage_event("agent-1", "payment_fee", Decimal("0.30"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["payment_fee"] == Decimal("0.30")

    @pytest.mark.asyncio
    async def it_calculates_total_across_all_categories(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("1.00"), {})
        await billing.record_usage_event("agent-1", "memory_storage", Decimal("0.10"), {})
        await billing.record_usage_event("agent-1", "vector_search", Decimal("0.05"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["total"] == Decimal("1.15")

    @pytest.mark.asyncio
    async def it_isolates_costs_per_agent(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("5.00"), {})
        await billing.record_usage_event("agent-2", "llm_inference", Decimal("3.00"), {})
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["llm_inference"] == Decimal("5.00")

    @pytest.mark.asyncio
    async def it_isolates_costs_per_period(self, billing):
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("5.00"), {"period": "2026-04"}
        )
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("3.00"), {"period": "2026-03"}
        )
        result = await billing.get_agent_cost_breakdown("agent-1", "2026-04")
        assert result["llm_inference"] == Decimal("5.00")


# ---------------------------------------------------------------------------
# Issue #226 — get_project_cost_summary
# ---------------------------------------------------------------------------

class DescribeGetProjectCostSummary:
    """Tests for BillingService.get_project_cost_summary."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_required_keys(self, billing):
        result = await billing.get_project_cost_summary("proj-1", "2026-04")
        assert "project_id" in result
        assert "period" in result
        assert "agents" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def it_returns_zero_total_when_no_events_exist(self, billing):
        result = await billing.get_project_cost_summary("proj-1", "2026-04")
        assert result["total"] == Decimal("0")

    @pytest.mark.asyncio
    async def it_includes_project_id_in_response(self, billing):
        result = await billing.get_project_cost_summary("proj-xyz", "2026-04")
        assert result["project_id"] == "proj-xyz"

    @pytest.mark.asyncio
    async def it_aggregates_costs_across_project_agents(self, billing):
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("2.00"), {"project_id": "proj-1"}
        )
        await billing.record_usage_event(
            "agent-2", "llm_inference", Decimal("3.00"), {"project_id": "proj-1"}
        )
        result = await billing.get_project_cost_summary("proj-1", "2026-04")
        assert result["total"] == Decimal("5.00")

    @pytest.mark.asyncio
    async def it_lists_per_agent_breakdown_in_agents_field(self, billing):
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("2.00"), {"project_id": "proj-1"}
        )
        result = await billing.get_project_cost_summary("proj-1", "2026-04")
        assert isinstance(result["agents"], list)

    @pytest.mark.asyncio
    async def it_returns_empty_agents_list_when_no_events(self, billing):
        result = await billing.get_project_cost_summary("proj-empty", "2026-04")
        assert result["agents"] == []


# ---------------------------------------------------------------------------
# Issue #226 — record_usage_event
# ---------------------------------------------------------------------------

class DescribeRecordUsageEvent:
    """Tests for BillingService.record_usage_event."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_event_id(self, billing):
        result = await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("1.00"), {}
        )
        assert "event_id" in result

    @pytest.mark.asyncio
    async def it_returns_agent_id_in_result(self, billing):
        result = await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("1.00"), {}
        )
        assert result["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def it_returns_category_in_result(self, billing):
        result = await billing.record_usage_event(
            "agent-1", "vector_search", Decimal("0.25"), {}
        )
        assert result["category"] == "vector_search"

    @pytest.mark.asyncio
    async def it_returns_amount_in_result(self, billing):
        result = await billing.record_usage_event(
            "agent-1", "memory_storage", Decimal("0.10"), {}
        )
        assert result["amount"] == Decimal("0.10")

    @pytest.mark.asyncio
    async def it_persists_event_retrievable_by_history(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("1.00"), {})
        history = await billing.get_usage_history("agent-1", "llm_inference", 10)
        assert len(history) == 1

    @pytest.mark.asyncio
    async def it_stores_metadata_with_event(self, billing):
        meta = {"model": "gpt-4", "tokens": 1024}
        result = await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("1.00"), meta
        )
        assert result.get("metadata") is not None


# ---------------------------------------------------------------------------
# Issue #226 — get_usage_history
# ---------------------------------------------------------------------------

class DescribeGetUsageHistory:
    """Tests for BillingService.get_usage_history."""

    @pytest.mark.asyncio
    async def it_returns_a_list(self, billing):
        result = await billing.get_usage_history("agent-1", "llm_inference", 10)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_events(self, billing):
        result = await billing.get_usage_history("agent-99", "llm_inference", 10)
        assert result == []

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(self, billing):
        for i in range(5):
            await billing.record_usage_event(
                "agent-1", "llm_inference", Decimal("0.10"), {}
            )
        result = await billing.get_usage_history("agent-1", "llm_inference", 3)
        assert len(result) <= 3

    @pytest.mark.asyncio
    async def it_filters_by_category(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("1.00"), {})
        await billing.record_usage_event("agent-1", "vector_search", Decimal("0.25"), {})
        result = await billing.get_usage_history("agent-1", "llm_inference", 10)
        for event in result:
            assert event["category"] == "llm_inference"

    @pytest.mark.asyncio
    async def it_filters_by_agent_id(self, billing):
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("1.00"), {})
        await billing.record_usage_event("agent-2", "llm_inference", Decimal("2.00"), {})
        result = await billing.get_usage_history("agent-1", "llm_inference", 10)
        for event in result:
            assert event["agent_id"] == "agent-1"


# ---------------------------------------------------------------------------
# Issue #227 — Per-Agent Budget Limits
# ---------------------------------------------------------------------------

class DescribeSetAgentBudget:
    """Tests for BillingService.set_agent_budget."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_agent_id(self, billing):
        result = await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        assert result["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def it_stores_max_daily_limit(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        status = await billing.get_agent_budget_status("agent-1")
        assert status["max_daily"] == Decimal("10.00")

    @pytest.mark.asyncio
    async def it_stores_max_monthly_limit(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        status = await billing.get_agent_budget_status("agent-1")
        assert status["max_monthly"] == Decimal("100.00")

    @pytest.mark.asyncio
    async def it_accepts_none_for_unlimited_daily(self, billing):
        result = await billing.set_agent_budget("agent-1", None, Decimal("100.00"))
        assert result is not None

    @pytest.mark.asyncio
    async def it_accepts_none_for_unlimited_monthly(self, billing):
        result = await billing.set_agent_budget("agent-1", Decimal("10.00"), None)
        assert result is not None


class DescribeCheckAgentBudget:
    """Tests for BillingService.check_agent_budget."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_allowed_key(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.check_agent_budget("agent-1", Decimal("1.00"))
        assert "allowed" in result

    @pytest.mark.asyncio
    async def it_returns_remaining_daily_in_result(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.check_agent_budget("agent-1", Decimal("1.00"))
        assert "remaining_daily" in result

    @pytest.mark.asyncio
    async def it_returns_remaining_monthly_in_result(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.check_agent_budget("agent-1", Decimal("1.00"))
        assert "remaining_monthly" in result

    @pytest.mark.asyncio
    async def it_allows_spend_within_daily_limit(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.check_agent_budget("agent-1", Decimal("5.00"))
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def it_blocks_spend_exceeding_daily_limit(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        # Record spend near the limit
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("9.50"), {})
        result = await billing.check_agent_budget("agent-1", Decimal("5.00"))
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def it_allows_when_no_budget_configured(self, billing):
        result = await billing.check_agent_budget("agent-no-budget", Decimal("9999.00"))
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def it_shows_correct_remaining_daily(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        await billing.record_usage_event("agent-1", "llm_inference", Decimal("3.00"), {})
        result = await billing.check_agent_budget("agent-1", Decimal("1.00"))
        assert result["remaining_daily"] == Decimal("7.00")


class DescribeGetAgentBudgetStatus:
    """Tests for BillingService.get_agent_budget_status."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_required_keys(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.get_agent_budget_status("agent-1")
        required = {"agent_id", "max_daily", "max_monthly", "spent_daily", "spent_monthly"}
        assert required.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def it_shows_zero_spend_when_no_events_recorded(self, billing):
        await billing.set_agent_budget("agent-1", Decimal("10.00"), Decimal("100.00"))
        result = await billing.get_agent_budget_status("agent-1")
        assert result["spent_daily"] == Decimal("0")
        assert result["spent_monthly"] == Decimal("0")

    @pytest.mark.asyncio
    async def it_returns_none_limits_when_no_budget_configured(self, billing):
        result = await billing.get_agent_budget_status("agent-no-budget")
        assert result["max_daily"] is None
        assert result["max_monthly"] is None


# ---------------------------------------------------------------------------
# Issue #228 — Per-Project Budget Limits
# ---------------------------------------------------------------------------

class DescribeSetProjectBudget:
    """Tests for BillingService.set_project_budget."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_project_id(self, billing):
        result = await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        assert result["project_id"] == "proj-1"

    @pytest.mark.asyncio
    async def it_stores_max_daily_limit(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        status = await billing.get_project_budget_status("proj-1")
        assert status["max_daily"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def it_stores_max_monthly_limit(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        status = await billing.get_project_budget_status("proj-1")
        assert status["max_monthly"] == Decimal("500.00")


class DescribeCheckProjectBudget:
    """Tests for BillingService.check_project_budget."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_allowed_key(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        result = await billing.check_project_budget("proj-1", Decimal("10.00"))
        assert "allowed" in result

    @pytest.mark.asyncio
    async def it_returns_remaining_in_result(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        result = await billing.check_project_budget("proj-1", Decimal("10.00"))
        assert "remaining" in result

    @pytest.mark.asyncio
    async def it_allows_spend_within_daily_limit(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        result = await billing.check_project_budget("proj-1", Decimal("20.00"))
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def it_blocks_spend_exceeding_project_daily_limit(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("48.00"), {"project_id": "proj-1"}
        )
        result = await billing.check_project_budget("proj-1", Decimal("10.00"))
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def it_allows_when_no_project_budget_configured(self, billing):
        result = await billing.check_project_budget("proj-no-budget", Decimal("9999.00"))
        assert result["allowed"] is True


class DescribeGetProjectBudgetStatus:
    """Tests for BillingService.get_project_budget_status."""

    @pytest.mark.asyncio
    async def it_returns_a_dict_with_required_keys(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        result = await billing.get_project_budget_status("proj-1")
        required = {"project_id", "max_daily", "max_monthly", "spent_daily", "spent_monthly"}
        assert required.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def it_shows_aggregate_spend_across_agents(self, billing):
        await billing.set_project_budget("proj-1", Decimal("50.00"), Decimal("500.00"))
        await billing.record_usage_event(
            "agent-1", "llm_inference", Decimal("5.00"), {"project_id": "proj-1"}
        )
        await billing.record_usage_event(
            "agent-2", "llm_inference", Decimal("3.00"), {"project_id": "proj-1"}
        )
        result = await billing.get_project_budget_status("proj-1")
        assert result["spent_daily"] == Decimal("8.00")

    @pytest.mark.asyncio
    async def it_returns_none_limits_when_no_budget_configured(self, billing):
        result = await billing.get_project_budget_status("proj-no-budget")
        assert result["max_daily"] is None
        assert result["max_monthly"] is None
