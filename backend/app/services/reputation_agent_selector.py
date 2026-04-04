"""
Reputation-Based Agent Selector.
Filters and ranks agents for swarm task assignment by reputation.

Issue #198: Integration with Swarm Agent Selection

Provides:
- Filter candidates by minimum trust tier and score
- Sort by reputation score descending
- Select single best agent for a given task type
- Fallback to any available agent if no candidates meet threshold

This is a standalone service — it does NOT modify crew.py or
crew_orchestrator.py. It can be called by the orchestration layer
or injected wherever agent selection decisions are needed.

Built by AINative Dev Team
Refs #198
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any

from app.services.hedera_reputation_service import HederaReputationService, get_reputation_service

logger = logging.getLogger(__name__)

# Default minimum trust tier for select_best_agent
DEFAULT_MIN_TRUST_TIER = 1


class ReputationAgentSelector:
    """
    Selects and ranks agents based on their HCS-anchored reputation scores.

    Designed to be injected into swarm orchestration logic. It does not
    call CrewAI directly — it returns ranked candidate lists for the
    caller to use.

    Candidates are dicts with at least:
    - agent_did: str
    - score: float (0.0-5.0)
    - trust_tier: int (0-4)
    - capabilities: List[str] (optional)
    """

    def __init__(
        self,
        reputation_service: Optional[HederaReputationService] = None
    ):
        """
        Initialize the agent selector.

        Args:
            reputation_service: Optional reputation service for injection.
                                 Creates a default if not provided.
        """
        self._reputation_service = reputation_service

    @property
    def reputation_service(self) -> HederaReputationService:
        """Lazily initialize the reputation service."""
        if self._reputation_service is None:
            self._reputation_service = get_reputation_service()
        return self._reputation_service

    async def select_agents_by_reputation(
        self,
        candidates: List[Dict[str, Any]],
        min_trust_tier: int = 0,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Filter and rank candidates by reputation criteria.

        Applies both tier and score filters (AND logic), then sorts
        the passing candidates by score descending.

        Args:
            candidates: List of agent dicts (must have score and trust_tier)
            min_trust_tier: Minimum trust tier to include (default 0 = all)
            min_score: Minimum score to include (default 0.0 = all)

        Returns:
            Filtered and sorted list of candidates (highest score first)
        """
        if not candidates:
            return []

        filtered = [
            agent for agent in candidates
            if agent.get("trust_tier", 0) >= min_trust_tier
            and agent.get("score", 0.0) >= min_score
        ]

        # Sort by score descending (highest reputation first)
        filtered.sort(key=lambda a: a.get("score", 0.0), reverse=True)

        logger.info(
            f"select_agents_by_reputation: {len(candidates)} candidates -> "
            f"{len(filtered)} passing (min_tier={min_trust_tier}, min_score={min_score})"
        )

        return filtered

    async def select_best_agent(
        self,
        candidates: List[Dict[str, Any]],
        task_type: str,
        min_trust_tier: int = DEFAULT_MIN_TRUST_TIER
    ) -> Optional[Dict[str, Any]]:
        """
        Select the single best agent for a given task type.

        Attempts to find the highest-scored candidate meeting the trust
        tier threshold. If no candidate meets the threshold, falls back
        to the highest-scored agent available (any tier).

        Args:
            candidates: List of agent dicts
            task_type: Task type string (for logging/future capability filtering)
            min_trust_tier: Minimum required trust tier (default 1 = BASIC+)

        Returns:
            Best matching agent dict, or None if candidates is empty
        """
        if not candidates:
            logger.info(f"select_best_agent: no candidates for task_type={task_type!r}")
            return None

        # First: try to find an agent meeting the minimum tier
        qualified = await self.select_agents_by_reputation(
            candidates=candidates,
            min_trust_tier=min_trust_tier,
            min_score=0.0
        )

        if qualified:
            best = qualified[0]
            logger.info(
                f"select_best_agent: selected {best.get('agent_did')} "
                f"(score={best.get('score')}, tier={best.get('trust_tier')}) "
                f"for task_type={task_type!r}"
            )
            return best

        # Fallback: no candidate meets the tier threshold; pick best available
        logger.warning(
            f"select_best_agent: no candidates meet min_trust_tier={min_trust_tier} "
            f"for task_type={task_type!r}; falling back to best available agent"
        )

        all_sorted = sorted(
            candidates,
            key=lambda a: a.get("score", 0.0),
            reverse=True
        )
        return all_sorted[0] if all_sorted else None


def get_agent_selector() -> ReputationAgentSelector:
    """
    Get a configured ReputationAgentSelector instance.

    Returns:
        ReputationAgentSelector with default reputation service
    """
    return ReputationAgentSelector()
