"""
Tests for GovernancePolicyService.
Issue #236: Agent Self-Governance Policies.

TDD: RED phase — tests written before implementation.
BDD-style: class Describe* / def it_*
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest


class DescribeGovernancePolicyServiceInit:
    """GovernancePolicyService initializes correctly."""

    def it_initializes_with_lazy_client(self):
        """Service defers client creation."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService()
        assert svc._client is None

    def it_accepts_injected_client(self):
        """Service accepts a pre-built client."""
        from app.services.governance_policy_service import GovernancePolicyService

        mock = MagicMock()
        svc = GovernancePolicyService(client=mock)
        assert svc.client is mock


class DescribeCreatePolicy:
    """Tests for create_policy — Issue #236."""

    @pytest.mark.asyncio
    async def it_creates_spend_limit_policy(self, mock_zerodb_client):
        """create_policy stores a spend_limit policy and returns policy_id."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 10.0, "per_call_limit_usd": 1.0},
        )

        assert "policy_id" in result
        assert result["agent_did"] == "did:hedera:testnet:agent1"
        assert result["policy_type"] == "spend_limit"
        assert result["rules"]["daily_limit_usd"] == 10.0

    @pytest.mark.asyncio
    async def it_creates_interaction_whitelist_policy(self, mock_zerodb_client):
        """create_policy stores an interaction_whitelist policy."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="interaction_whitelist",
            rules={"allowed_dids": ["did:hedera:testnet:trusted1"]},
        )

        assert result["policy_type"] == "interaction_whitelist"

    @pytest.mark.asyncio
    async def it_creates_task_scope_policy(self, mock_zerodb_client):
        """create_policy stores a task_scope policy."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="task_scope",
            rules={"allowed_tasks": ["summarize", "translate"]},
        )

        assert result["policy_type"] == "task_scope"

    @pytest.mark.asyncio
    async def it_creates_data_access_policy(self, mock_zerodb_client):
        """create_policy stores a data_access policy."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="data_access",
            rules={"allowed_tables": ["public_data"], "read_only": True},
        )

        assert result["policy_type"] == "data_access"

    @pytest.mark.asyncio
    async def it_raises_for_unsupported_policy_type(self, mock_zerodb_client):
        """create_policy raises ValueError for unrecognised policy type."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)

        with pytest.raises(ValueError):
            await svc.create_policy(
                agent_did="did:hedera:testnet:agent1",
                policy_type="unknown_policy",
                rules={},
            )

    @pytest.mark.asyncio
    async def it_persists_policy_to_governance_policies_table(self, mock_zerodb_client):
        """create_policy inserts one row into governance_policies table."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 5.0},
        )

        rows = mock_zerodb_client.get_table_data("governance_policies")
        assert len(rows) == 1


class DescribeEvaluatePolicy:
    """Tests for evaluate_policy — Issue #236."""

    @pytest.mark.asyncio
    async def it_allows_action_within_spend_limit(self, mock_zerodb_client):
        """evaluate_policy returns allowed=True when spend is under limit."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 10.0, "per_call_limit_usd": 1.0},
        )

        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:agent1",
            action="spend",
            context={"amount_usd": 0.5},
        )

        assert result["allowed"] is True
        assert result["violated_policies"] == []

    @pytest.mark.asyncio
    async def it_blocks_action_exceeding_spend_limit(self, mock_zerodb_client):
        """evaluate_policy returns allowed=False when spend exceeds per_call_limit."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 10.0, "per_call_limit_usd": 0.10},
        )

        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:agent1",
            action="spend",
            context={"amount_usd": 5.0},
        )

        assert result["allowed"] is False
        assert len(result["violated_policies"]) > 0

    @pytest.mark.asyncio
    async def it_allows_interaction_with_whitelisted_did(self, mock_zerodb_client):
        """evaluate_policy returns allowed=True when target_did is whitelisted."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        trusted = "did:hedera:testnet:trusted1"
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="interaction_whitelist",
            rules={"allowed_dids": [trusted]},
        )

        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:agent1",
            action="call_agent",
            context={"target_did": trusted},
        )

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def it_blocks_interaction_with_non_whitelisted_did(self, mock_zerodb_client):
        """evaluate_policy returns allowed=False for non-whitelisted DID."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent1",
            policy_type="interaction_whitelist",
            rules={"allowed_dids": ["did:hedera:testnet:trusted1"]},
        )

        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:agent1",
            action="call_agent",
            context={"target_did": "did:hedera:testnet:stranger"},
        )

        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def it_allows_all_actions_when_no_policies_exist(self, mock_zerodb_client):
        """evaluate_policy returns allowed=True when agent has no policies."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:no_policies",
            action="spend",
            context={"amount_usd": 999.0},
        )

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def it_blocks_out_of_scope_task(self, mock_zerodb_client):
        """evaluate_policy returns allowed=False for tasks outside task_scope."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:scoped",
            policy_type="task_scope",
            rules={"allowed_tasks": ["summarize"]},
        )

        result = await svc.evaluate_policy(
            agent_did="did:hedera:testnet:scoped",
            action="execute_task",
            context={"task": "delete_database"},
        )

        assert result["allowed"] is False


class DescribeGetPolicies:
    """Tests for get_policies — Issue #236."""

    @pytest.mark.asyncio
    async def it_returns_all_policies_for_agent(self, mock_zerodb_client):
        """get_policies returns every policy registered for an agent_did."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:multi",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 5.0},
        )
        await svc.create_policy(
            agent_did="did:hedera:testnet:multi",
            policy_type="task_scope",
            rules={"allowed_tasks": ["read"]},
        )

        policies = await svc.get_policies("did:hedera:testnet:multi")

        assert len(policies) == 2
        types = {p["policy_type"] for p in policies}
        assert "spend_limit" in types
        assert "task_scope" in types

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_agent_without_policies(
        self, mock_zerodb_client
    ):
        """get_policies returns [] when no policies exist for agent."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        result = await svc.get_policies("did:hedera:testnet:nobody")

        assert result == []

    @pytest.mark.asyncio
    async def it_does_not_return_policies_for_other_agents(self, mock_zerodb_client):
        """get_policies scopes results to the requested agent_did only."""
        from app.services.governance_policy_service import GovernancePolicyService

        svc = GovernancePolicyService(client=mock_zerodb_client)
        await svc.create_policy(
            agent_did="did:hedera:testnet:agent_A",
            policy_type="spend_limit",
            rules={"daily_limit_usd": 5.0},
        )

        result = await svc.get_policies("did:hedera:testnet:agent_B")

        assert result == []
