"""
Tests for ReputationAgentSelector.
Issue #198: Integration with Swarm Agent Selection.

TDD Approach: Tests written FIRST, then implementation.
BDD-style: class Describe* / def it_* naming.

Test Coverage:
- Filter agents by minimum trust tier
- Filter agents by minimum score
- Sort agents by score descending
- Select single best agent for task type
- Fallback when no candidates meet threshold
- Edge cases: empty candidates, tie scores
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, List, Any


def _make_candidate(
    agent_did: str,
    score: float,
    trust_tier: int,
    capabilities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Helper to create a candidate agent dict."""
    return {
        "agent_did": agent_did,
        "score": score,
        "trust_tier": trust_tier,
        "capabilities": capabilities or []
    }


class DescribeReputationAgentSelectorInit:
    """Tests for ReputationAgentSelector initialization."""

    def it_initializes_with_reputation_service(self):
        """Selector holds a reference to the reputation service."""
        from app.services.reputation_agent_selector import ReputationAgentSelector
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = MagicMock(spec=HederaReputationService)
        selector = ReputationAgentSelector(reputation_service=mock_service)
        assert selector.reputation_service is mock_service

    def it_creates_default_reputation_service_when_none_provided(self):
        """Creates a default HederaReputationService if none injected."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        selector = ReputationAgentSelector()
        assert selector.reputation_service is not None


class DescribeSelectAgentsByReputation:
    """Tests for select_agents_by_reputation method — Issue #198."""

    @pytest.mark.asyncio
    async def it_returns_all_candidates_when_no_filters(self):
        """Returns all candidates when min_trust_tier=0 and min_score=0.0."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=4.5, trust_tier=3),
            _make_candidate("did:hedera:testnet:agent2", score=2.0, trust_tier=1),
            _make_candidate("did:hedera:testnet:agent3", score=1.0, trust_tier=0),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=0,
            min_score=0.0
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def it_filters_candidates_below_min_trust_tier(self):
        """Excludes candidates below the minimum trust tier."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=4.5, trust_tier=3),
            _make_candidate("did:hedera:testnet:agent2", score=3.0, trust_tier=1),
            _make_candidate("did:hedera:testnet:agent3", score=2.5, trust_tier=0),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=2,
            min_score=0.0
        )

        assert len(result) == 1
        assert result[0]["agent_did"] == "did:hedera:testnet:agent1"

    @pytest.mark.asyncio
    async def it_filters_candidates_below_min_score(self):
        """Excludes candidates below the minimum score."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=4.5, trust_tier=3),
            _make_candidate("did:hedera:testnet:agent2", score=3.0, trust_tier=2),
            _make_candidate("did:hedera:testnet:agent3", score=1.5, trust_tier=2),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=0,
            min_score=3.0
        )

        assert len(result) == 2
        assert all(a["score"] >= 3.0 for a in result)

    @pytest.mark.asyncio
    async def it_sorts_results_by_score_descending(self):
        """Results are sorted highest score first."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=2.0, trust_tier=1),
            _make_candidate("did:hedera:testnet:agent2", score=4.5, trust_tier=3),
            _make_candidate("did:hedera:testnet:agent3", score=3.5, trust_tier=2),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=0,
            min_score=0.0
        )

        assert result[0]["score"] == 4.5
        assert result[1]["score"] == 3.5
        assert result[2]["score"] == 2.0

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_candidates_meet_criteria(self):
        """Returns empty list when no candidates pass the filters."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=1.0, trust_tier=0),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=3,
            min_score=4.0
        )

        assert result == []

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_candidates_is_empty(self):
        """Returns empty list when no candidates provided."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=[],
            min_trust_tier=0,
            min_score=0.0
        )

        assert result == []

    @pytest.mark.asyncio
    async def it_applies_both_tier_and_score_filters_together(self):
        """Both tier and score filters are applied (AND logic)."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=4.5, trust_tier=3),  # passes both
            _make_candidate("did:hedera:testnet:agent2", score=4.5, trust_tier=1),  # fails tier
            _make_candidate("did:hedera:testnet:agent3", score=2.0, trust_tier=3),  # fails score
            _make_candidate("did:hedera:testnet:agent4", score=2.0, trust_tier=1),  # fails both
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=2,
            min_score=3.0
        )

        assert len(result) == 1
        assert result[0]["agent_did"] == "did:hedera:testnet:agent1"


class DescribeSelectBestAgent:
    """Tests for select_best_agent method — Issue #198."""

    @pytest.mark.asyncio
    async def it_returns_highest_score_agent_meeting_threshold(self):
        """Returns the single agent with the highest score above threshold."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=3.0, trust_tier=2),
            _make_candidate("did:hedera:testnet:agent2", score=4.5, trust_tier=3),
            _make_candidate("did:hedera:testnet:agent3", score=2.0, trust_tier=1),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_best_agent(
            candidates=candidates,
            task_type="analysis",
            min_trust_tier=1
        )

        assert result["agent_did"] == "did:hedera:testnet:agent2"

    @pytest.mark.asyncio
    async def it_falls_back_to_any_agent_when_none_meet_threshold(self):
        """Falls back to highest-score agent when no one meets min_trust_tier."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=3.0, trust_tier=0),
            _make_candidate("did:hedera:testnet:agent2", score=4.5, trust_tier=0),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_best_agent(
            candidates=candidates,
            task_type="analysis",
            min_trust_tier=3  # Neither candidate meets this
        )

        # Should fall back to best available
        assert result is not None
        assert result["agent_did"] == "did:hedera:testnet:agent2"

    @pytest.mark.asyncio
    async def it_returns_none_when_candidates_is_empty(self):
        """Returns None when no candidates are provided."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        selector = ReputationAgentSelector()
        result = await selector.select_best_agent(
            candidates=[],
            task_type="analysis",
            min_trust_tier=1
        )

        assert result is None

    @pytest.mark.asyncio
    async def it_uses_default_min_trust_tier_1(self):
        """Default minimum trust tier for select_best_agent is 1."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=4.0, trust_tier=1),
            _make_candidate("did:hedera:testnet:agent2", score=3.0, trust_tier=0),  # excluded by default
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_best_agent(
            candidates=candidates,
            task_type="reporting"
            # min_trust_tier defaults to 1
        )

        # Should prefer tier>=1 agent
        assert result["agent_did"] == "did:hedera:testnet:agent1"

    @pytest.mark.asyncio
    async def it_handles_single_candidate_above_threshold(self):
        """Returns the single candidate if it meets the threshold."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate("did:hedera:testnet:agent1", score=3.5, trust_tier=2),
        ]

        selector = ReputationAgentSelector()
        result = await selector.select_best_agent(
            candidates=candidates,
            task_type="verification",
            min_trust_tier=1
        )

        assert result["agent_did"] == "did:hedera:testnet:agent1"

    @pytest.mark.asyncio
    async def it_considers_task_type_in_selection(self):
        """Task type is captured in selection (for future capability filtering)."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        candidates = [
            _make_candidate(
                "did:hedera:testnet:agent1",
                score=4.0,
                trust_tier=2,
                capabilities=["analysis", "reporting"]
            ),
        ]

        selector = ReputationAgentSelector()
        # Should not raise even with specific task_type
        result = await selector.select_best_agent(
            candidates=candidates,
            task_type="analysis",
            min_trust_tier=1
        )

        assert result is not None
