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

from datetime import datetime, timezone
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
    # Importance scoring (Refs #309 S1)
    # ------------------------------------------------------------------

    # Base importance by memory_type: procedural and semantic "stick" longer
    # than working/episodic, so they earn a higher baseline. Working memory
    # is short-term and therefore gets the lowest base score.
    _BASE_BY_TYPE: Dict[CognitiveMemoryType, float] = {
        CognitiveMemoryType.WORKING: 0.3,
        CognitiveMemoryType.EPISODIC: 0.5,
        CognitiveMemoryType.SEMANTIC: 0.55,
        CognitiveMemoryType.PROCEDURAL: 0.7,
    }

    _CRITICAL_FLAGS = {
        "critical", "urgent", "high", "p0", "p1", "important", "priority",
    }

    def score_importance(
        self,
        memory_type: CognitiveMemoryType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance_hint: Optional[float] = None,
    ) -> float:
        """
        Deterministic 0.0–1.0 importance score.

        importance = base(type) + length_bonus + metadata_boost, clipped.

        - base: 0.3 (working) / 0.5 (episodic) / 0.55 (semantic) / 0.7 (procedural)
        - length_bonus: min(len(content) / 2500, 0.2)
        - metadata_boost: +0.2 when a metadata key or value matches a
          critical flag (case-insensitive) — e.g. `{"urgent": True}` or
          `{"priority": "critical"}`.

        A caller-supplied `importance_hint` (any float) overrides the
        heuristic and is clipped to [0.0, 1.0].
        """
        if importance_hint is not None:
            return max(0.0, min(1.0, float(importance_hint)))

        base = self._BASE_BY_TYPE.get(memory_type, self.DEFAULT_IMPORTANCE)
        length_bonus = min(len(content) / 2500.0, 0.2)

        metadata_boost = 0.0
        for key, value in (metadata or {}).items():
            if isinstance(value, bool) and value and key.lower() in self._CRITICAL_FLAGS:
                metadata_boost = 0.2
                break
            if isinstance(value, str) and value.strip().lower() in self._CRITICAL_FLAGS:
                metadata_boost = 0.2
                break

        return max(0.0, min(1.0, base + length_bonus + metadata_boost))

    # ------------------------------------------------------------------
    # Auto-categorization (Refs #309 S1)
    # ------------------------------------------------------------------

    # Ordered keyword lists; first match wins. ERROR comes before DECISION
    # so "error while approving" classifies as ERROR. Trailing spaces on
    # short keywords avoid substring false-positives (e.g. "will " in "willing").
    _CATEGORY_KEYWORDS: List[Any] = [
        (MemoryCategory.ERROR, [
            "error", "exception", "fail", "failed", "failure", "broken", "crash",
        ]),
        (MemoryCategory.DECISION, [
            "decid", "approve", "approved", "reject", "rejected", "chose",
        ]),
        (MemoryCategory.PLAN, [
            "plan", "schedule", "roadmap", "will ", "going to", "upcoming",
        ]),
        (MemoryCategory.OBSERVATION, [
            "observ", "notic", "saw ", "metric", "spike", "dropped", "measured",
        ]),
        (MemoryCategory.INTERACTION, [
            "asked", "replied", "said", "chat", "told", "responded",
        ]),
    ]

    def categorize(
        self,
        content: str,
        memory_type: CognitiveMemoryType,
    ) -> MemoryCategory:
        """
        Keyword-based deterministic classification.

        Ordering: ERROR > DECISION > PLAN > OBSERVATION > INTERACTION.
        Semantic memories without keyword matches are tagged KNOWLEDGE; all
        other non-matching memories fall through to OTHER.
        """
        text = content.lower()
        for category, keywords in self._CATEGORY_KEYWORDS:
            if any(kw in text for kw in keywords):
                return category
        if memory_type == CognitiveMemoryType.SEMANTIC:
            return MemoryCategory.KNOWLEDGE
        return MemoryCategory.OTHER

    # ------------------------------------------------------------------
    # Recency weighting (Refs #310 S2)
    # ------------------------------------------------------------------

    def compute_recency_weight(
        self,
        timestamp: Optional[str],
        half_life_days: float = 7.0,
        now: Optional[datetime] = None,
    ) -> float:
        """
        Exponential decay: `weight = 0.5 ** (age_days / half_life_days)`.

        - `timestamp` is an ISO-8601 string (with or without trailing 'Z').
        - Missing or malformed timestamps default to 1.0 so downstream
          ranking still sees them.
        - `now` is injectable for deterministic tests; defaults to UTC now.
        """
        if not timestamp:
            return 1.0

        ts_str = (
            timestamp.replace("Z", "+00:00")
            if timestamp.endswith("Z")
            else timestamp
        )
        try:
            parsed = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return 1.0

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        now_dt = now or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        age_seconds = max((now_dt - parsed).total_seconds(), 0.0)
        age_days = age_seconds / 86400.0
        return 0.5 ** (age_days / max(half_life_days, 1e-6))

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
