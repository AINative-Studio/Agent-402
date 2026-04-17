"""
CognitiveMemoryService — cognition helpers layered on top of
AgentMemoryService.

Refs #292 (#308 S0 scaffold).

This module provides the importance scoring, categorization, recency
weighting, insight synthesis, and profile-building helpers used by the
four cognitive endpoints. S0 lands deterministic stubs; S1–S4 replace
them with real logic in a worktree-safe pattern (each sub-story owns one
method).

Design:
- Pure functions where possible — no ZeroDB dependency in the helpers
  themselves. The endpoint layer composes helpers with the existing
  `AgentMemoryService` to persist and fetch.
- Deterministic outputs for easy testing.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.cognitive_memory import (
    CognitiveMemoryType,
    InsightContradiction,
    InsightGap,
    InsightPattern,
    MemoryCategory,
    ProfileCategoryStats,
    ProfileResponse,
    ProfileTopicCount,
    RecallWeights,
)


class CognitiveMemoryService:
    """Cognition helpers. Thin, dependency-free class for easy testing."""

    DEFAULT_IMPORTANCE = 0.5
    DEFAULT_RECENCY_WEIGHT = 1.0

    # ------------------------------------------------------------------
    # Importance scoring (real logic lands in S1)
    # ------------------------------------------------------------------

    def score_importance(
        self,
        memory_type: CognitiveMemoryType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance_hint: Optional[float] = None,
    ) -> float:
        """Return a deterministic 0.5 placeholder. Replaced in S1 (#309)."""
        if importance_hint is not None:
            return max(0.0, min(1.0, importance_hint))
        return self.DEFAULT_IMPORTANCE

    # ------------------------------------------------------------------
    # Auto-categorization (real logic lands in S1)
    # ------------------------------------------------------------------

    def categorize(
        self,
        content: str,
        memory_type: CognitiveMemoryType,
    ) -> MemoryCategory:
        """Return MemoryCategory.OTHER placeholder. Replaced in S1 (#309)."""
        return MemoryCategory.OTHER

    # ------------------------------------------------------------------
    # Recency weighting (real logic lands in S2)
    # ------------------------------------------------------------------

    def compute_recency_weight(
        self,
        timestamp: Optional[str],
        half_life_days: float = 7.0,
        now: Optional[datetime] = None,
    ) -> float:
        """Return 1.0 placeholder (no decay). Replaced in S2 (#310)."""
        return self.DEFAULT_RECENCY_WEIGHT

    def compose_relevance(
        self,
        similarity: float,
        recency: float,
        importance: float,
        weights: Optional[RecallWeights] = None,
    ) -> float:
        """Weighted sum of the three signals; sane default weights."""
        w = weights or RecallWeights()
        return (
            similarity * w.similarity
            + recency * w.recency
            + importance * w.importance
        )

    # ------------------------------------------------------------------
    # Insight synthesis (real logic lands in S3)
    # ------------------------------------------------------------------

    def synthesize_insights(
        self,
        memories: List[Dict[str, Any]],
    ) -> Dict[str, List[Any]]:
        """
        Return empty insights. Replaced in S3 (#311).

        Returns a dict with `patterns`, `contradictions`, `gaps` keys so the
        endpoint layer has a consistent interface from S0 onward.
        """
        return {
            "patterns": [],  # type: List[InsightPattern]
            "contradictions": [],  # type: List[InsightContradiction]
            "gaps": [],  # type: List[InsightGap]
        }

    # ------------------------------------------------------------------
    # Profile building (real logic lands in S4)
    # ------------------------------------------------------------------

    def build_profile(
        self,
        agent_id: str,
        memories: List[Dict[str, Any]],
    ) -> ProfileResponse:
        """Return a minimal profile. Replaced in S4 (#312)."""
        return ProfileResponse(
            agent_id=agent_id,
            memory_count=len(memories),
            categories=[],
            topics=[],
            expertise_areas=[],
            first_memory_at=None,
            last_memory_at=None,
        )


# Singleton pattern — matches the existing service modules in app/services.
_cognitive_memory_service: Optional[CognitiveMemoryService] = None


def get_cognitive_memory_service() -> CognitiveMemoryService:
    """Return the singleton, creating it on first call."""
    global _cognitive_memory_service
    if _cognitive_memory_service is None:
        _cognitive_memory_service = CognitiveMemoryService()
    return _cognitive_memory_service
