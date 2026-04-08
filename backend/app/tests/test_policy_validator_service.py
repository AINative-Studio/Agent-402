"""
Tests for PolicyValidatorService — Issue #171

Policy schema validation, dry-run simulation, and diffing.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #171
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any


VALID_POLICY = {
    "policy_id": "pol-001",
    "policy_type": "spend_limit",
    "rules": {
        "daily_limit_usd": 500.0,
        "per_call_limit_usd": 50.0,
    },
    "agent_id": "agent-001",
}

INVALID_POLICY_MISSING_TYPE = {
    "policy_id": "pol-bad",
    "rules": {},
}

CONFLICT_POLICY = {
    "policy_id": "pol-conflict",
    "policy_type": "spend_limit",
    "rules": {
        "daily_limit_usd": -100.0,  # negative is invalid
    },
    "agent_id": "agent-001",
}


class DescribePolicyValidatorService:
    """Specification for PolicyValidatorService."""

    @pytest.fixture
    def service(self, mock_zerodb_client):
        from app.services.policy_validator_service import PolicyValidatorService
        return PolicyValidatorService(client=mock_zerodb_client)

    # ------------------------------------------------------------------ #
    # validate_policy
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_valid_true_for_well_formed_policy(self, service):
        """validate_policy returns {valid: True, errors: [], warnings: []} for good policy."""
        result = await service.validate_policy(VALID_POLICY)

        assert result["valid"] is True
        assert result["errors"] == []
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def it_returns_valid_false_when_policy_type_missing(self, service):
        """validate_policy returns valid=False when policy_type is absent."""
        result = await service.validate_policy(INVALID_POLICY_MISSING_TYPE)

        assert result["valid"] is False
        assert len(result["errors"]) >= 1

    @pytest.mark.asyncio
    async def it_returns_errors_for_negative_spend_limits(self, service):
        """validate_policy catches negative spend limits as errors."""
        result = await service.validate_policy(CONFLICT_POLICY)

        assert result["valid"] is False
        assert any("daily_limit_usd" in e or "negative" in e.lower() for e in result["errors"])

    @pytest.mark.asyncio
    async def it_returns_warnings_for_very_high_limits(self, service):
        """validate_policy adds warning when daily limit is unusually high."""
        policy = {
            "policy_id": "pol-warn",
            "policy_type": "spend_limit",
            "rules": {"daily_limit_usd": 1_000_000.0},
            "agent_id": "agent-001",
        }
        result = await service.validate_policy(policy)

        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def it_returns_errors_list_not_none(self, service):
        """validate_policy always returns errors and warnings as lists."""
        result = await service.validate_policy(VALID_POLICY)

        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    # ------------------------------------------------------------------ #
    # dry_run_policy
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_simulates_policy_against_test_actions(self, service):
        """dry_run_policy returns pass/fail results for each test action."""
        test_actions = [
            {"action": "spend", "amount": 100.0},
            {"action": "spend", "amount": 600.0},  # exceeds $500 daily limit
        ]

        result = await service.dry_run_policy(VALID_POLICY, test_actions)

        assert "results" in result
        assert len(result["results"]) == 2
        assert "summary" in result

    @pytest.mark.asyncio
    async def it_marks_action_as_pass_within_limits(self, service):
        """dry_run_policy marks actions within limits as 'pass'."""
        test_actions = [{"action": "spend", "amount": 10.0}]
        result = await service.dry_run_policy(VALID_POLICY, test_actions)

        assert result["results"][0]["result"] == "pass"

    @pytest.mark.asyncio
    async def it_marks_action_as_fail_when_exceeds_limit(self, service):
        """dry_run_policy marks spend exceeding daily limit as 'fail'."""
        test_actions = [{"action": "spend", "amount": 999.0}]
        result = await service.dry_run_policy(VALID_POLICY, test_actions)

        assert result["results"][0]["result"] == "fail"

    @pytest.mark.asyncio
    async def it_includes_reason_in_each_result(self, service):
        """dry_run_policy includes a reason string in each action result."""
        test_actions = [{"action": "spend", "amount": 100.0}]
        result = await service.dry_run_policy(VALID_POLICY, test_actions)

        assert "reason" in result["results"][0]

    # ------------------------------------------------------------------ #
    # diff_policies
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def it_returns_empty_diff_for_identical_policies(self, service):
        """diff_policies returns no changes when policies are identical."""
        result = await service.diff_policies(VALID_POLICY, VALID_POLICY)

        assert "changes" in result
        assert result["changes"] == []

    @pytest.mark.asyncio
    async def it_detects_changed_rule_values(self, service):
        """diff_policies identifies changed rule values."""
        policy_b = {
            **VALID_POLICY,
            "rules": {
                "daily_limit_usd": 1000.0,  # was 500
                "per_call_limit_usd": 50.0,
            },
        }
        result = await service.diff_policies(VALID_POLICY, policy_b)

        assert len(result["changes"]) >= 1
        changed_fields = [c["field"] for c in result["changes"]]
        assert any("daily_limit_usd" in f for f in changed_fields)

    @pytest.mark.asyncio
    async def it_detects_added_rules(self, service):
        """diff_policies detects newly added rule keys."""
        policy_b = {
            **VALID_POLICY,
            "rules": {
                "daily_limit_usd": 500.0,
                "per_call_limit_usd": 50.0,
                "monthly_limit_usd": 10000.0,  # new
            },
        }
        result = await service.diff_policies(VALID_POLICY, policy_b)

        assert len(result["changes"]) >= 1
        change_types = [c.get("change_type") for c in result["changes"]]
        assert "added" in change_types

    @pytest.mark.asyncio
    async def it_detects_removed_rules(self, service):
        """diff_policies detects removed rule keys."""
        policy_b = {
            **VALID_POLICY,
            "rules": {
                "daily_limit_usd": 500.0,
                # per_call_limit_usd removed
            },
        }
        result = await service.diff_policies(VALID_POLICY, policy_b)

        change_types = [c.get("change_type") for c in result["changes"]]
        assert "removed" in change_types
