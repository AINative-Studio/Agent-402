"""
Tests for DecisionLoggerService — Issue #163

Contextual logging for agent decisions.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #163
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, List, Any


class DescribeDecisionLoggerService:
    """Specification for DecisionLoggerService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.decision_logger_service import DecisionLoggerService
        svc = DecisionLoggerService(client=mock_zerodb_client)
        return svc

    # ------------------------------------------------------------------ #
    # log_decision
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_logs_a_decision_and_returns_structured_record(self, service, mock_zerodb_client):
        """log_decision stores a structured decision log to ZeroDB and returns it."""
        result = await service.log_decision(
            agent_id="agent-001",
            decision_type="task_selection",
            context={"available_tasks": ["a", "b"]},
            outcome="selected_task_a",
            confidence=0.92,
            reasoning="Task A had higher priority",
        )

        assert result["agent_id"] == "agent-001"
        assert result["decision_type"] == "task_selection"
        assert result["outcome"] == "selected_task_a"
        assert result["confidence"] == 0.92
        assert result["reasoning"] == "Task A had higher priority"
        assert "log_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def it_persists_the_decision_in_zerodb(self, service, mock_zerodb_client):
        """log_decision inserts a row into the decisions table."""
        await service.log_decision(
            agent_id="agent-001",
            decision_type="payment_approval",
            context={"amount": 100.0},
            outcome="approved",
            confidence=0.99,
            reasoning="Within daily limit",
        )

        calls = [c for c in mock_zerodb_client.call_history if c["method"] == "insert_row"]
        assert len(calls) >= 1
        assert calls[-1]["table_name"] == "agent_decisions"

    @pytest.mark.asyncio
    async def it_accepts_all_valid_decision_types(self, service):
        """log_decision works for all defined decision types."""
        valid_types = [
            "task_selection",
            "payment_approval",
            "compliance_check",
            "memory_recall",
            "agent_selection",
        ]
        for dtype in valid_types:
            result = await service.log_decision(
                agent_id="agent-x",
                decision_type=dtype,
                context={},
                outcome="done",
                confidence=0.8,
                reasoning="test",
            )
            assert result["decision_type"] == dtype

    @pytest.mark.asyncio
    async def it_attaches_run_id_when_provided(self, service):
        """log_decision stores run_id when passed as part of context."""
        result = await service.log_decision(
            agent_id="agent-001",
            decision_type="task_selection",
            context={"run_id": "run-abc", "task": "pay"},
            outcome="selected",
            confidence=0.85,
            reasoning="context has run_id",
        )
        assert result["context"]["run_id"] == "run-abc"

    # ------------------------------------------------------------------ #
    # get_decision_history
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_paginated_history_for_an_agent(self, service, mock_zerodb_client):
        """get_decision_history returns decisions for the given agent_id."""
        for i in range(5):
            await service.log_decision(
                agent_id="agent-hist",
                decision_type="task_selection",
                context={},
                outcome=f"outcome_{i}",
                confidence=0.5,
                reasoning=f"reason_{i}",
            )

        history = await service.get_decision_history(agent_id="agent-hist", limit=3)

        assert isinstance(history, list)
        assert len(history) <= 3

    @pytest.mark.asyncio
    async def it_filters_history_by_decision_type(self, service):
        """get_decision_history filters by decision_type when provided."""
        for dtype in ["task_selection", "payment_approval", "task_selection"]:
            await service.log_decision(
                agent_id="agent-filter",
                decision_type=dtype,
                context={},
                outcome="x",
                confidence=0.5,
                reasoning="r",
            )

        results = await service.get_decision_history(
            agent_id="agent-filter",
            decision_type="task_selection",
            limit=10,
        )

        for r in results:
            assert r["decision_type"] == "task_selection"

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_history_exists(self, service):
        """get_decision_history returns [] for unknown agent_id."""
        history = await service.get_decision_history(agent_id="no-such-agent", limit=10)
        assert history == []

    # ------------------------------------------------------------------ #
    # get_decision_chain
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_all_decisions_in_a_run_ordered(self, service):
        """get_decision_chain returns all decisions for a run_id in order."""
        run_id = "run-chain-test"
        for i in range(3):
            await service.log_decision(
                agent_id="agent-chain",
                decision_type="task_selection",
                context={"run_id": run_id, "seq": i},
                outcome=f"step_{i}",
                confidence=0.7,
                reasoning=f"step {i}",
            )
        # One unrelated decision
        await service.log_decision(
            agent_id="agent-chain",
            decision_type="task_selection",
            context={"run_id": "other-run"},
            outcome="other",
            confidence=0.5,
            reasoning="other run",
        )

        chain = await service.get_decision_chain(run_id=run_id)

        assert isinstance(chain, list)
        assert len(chain) == 3
        for item in chain:
            assert item["context"].get("run_id") == run_id

    @pytest.mark.asyncio
    async def it_returns_empty_chain_for_unknown_run(self, service):
        """get_decision_chain returns [] for unknown run_id."""
        chain = await service.get_decision_chain(run_id="no-such-run")
        assert chain == []


class DescribeDecisionLoggerServiceSchemas:
    """Schema validation for observability.DecisionLog."""

    def it_builds_decision_log_with_required_fields(self):
        """DecisionLog schema requires log_id, agent_id, decision_type, outcome."""
        from app.schemas.observability import DecisionLog
        log = DecisionLog(
            log_id="log-001",
            agent_id="agent-001",
            decision_type="task_selection",
            context={},
            outcome="done",
            confidence=0.9,
            reasoning="ok",
            timestamp="2026-04-03T00:00:00Z",
        )
        assert log.log_id == "log-001"
        assert log.decision_type == "task_selection"

    def it_allows_optional_run_id(self):
        """DecisionLog.run_id is optional."""
        from app.schemas.observability import DecisionLog
        log = DecisionLog(
            log_id="log-002",
            agent_id="agent-001",
            decision_type="compliance_check",
            context={},
            outcome="passed",
            confidence=1.0,
            reasoning="all clear",
            timestamp="2026-04-03T00:00:00Z",
        )
        assert log.run_id is None
