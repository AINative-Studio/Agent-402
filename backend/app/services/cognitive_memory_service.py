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

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

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
    # Insight synthesis (Refs #311 S3)
    # ------------------------------------------------------------------

    # Categories we expect to see in any long-running agent's corpus;
    # missing ones become `gaps`.
    _EXPECTED_GAP_CATEGORIES = [
        MemoryCategory.DECISION,
        MemoryCategory.PLAN,
        MemoryCategory.OBSERVATION,
    ]

    _APPROVE_TOKENS = ("approve", "approved", "accept", "ok'd", "yes")
    _REJECT_TOKENS = ("reject", "rejected", "deny", "denied", "blocked")

    # Tokens too generic to count as "shared topic" signal.
    _STOPWORDS = frozenset({
        "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
        "for", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "this", "that", "these", "those", "it", "its", "as", "if",
        "then", "than", "so", "such", "not", "no", "yes", "do", "does", "did",
        "have", "has", "had", "will", "would", "should", "could", "can", "may",
        "might", "must", "up", "down", "out", "over", "under", "again", "also",
    })

    def _significant_tokens(self, text: str) -> set:
        """Lowercased, non-stopword word set for naive topic comparison."""
        tokens = set()
        for raw in text.lower().split():
            cleaned = "".join(ch for ch in raw if ch.isalnum())
            if len(cleaned) < 3:
                continue
            if cleaned in self._STOPWORDS:
                continue
            tokens.add(cleaned)
        return tokens

    def _extract_category(self, memory: Dict[str, Any]) -> MemoryCategory:
        """Pull the stored category from metadata; fall back to OTHER."""
        metadata = memory.get("metadata", {}) or {}
        raw = metadata.get("category")
        if isinstance(raw, MemoryCategory):
            return raw
        try:
            return MemoryCategory(raw)
        except (ValueError, TypeError):
            return MemoryCategory.OTHER

    def synthesize_insights(
        self,
        memories: List[Dict[str, Any]],
    ) -> Dict[str, List[Any]]:
        """
        Deterministic heuristic synthesis.

        - `patterns`: top-3 most common categories across `memories`, sorted
          by count desc. Label is the category's enum value.
        - `contradictions`: pairs of memories where one contains an
          approve-token and the other a reject-token AND they share at
          least 2 significant (non-stopword) tokens — taken as a naive
          "same topic" proxy.
        - `gaps`: expected categories (`decision`, `plan`, `observation`)
          absent from the corpus.
        """
        # --- Patterns -------------------------------------------------
        counts: Dict[MemoryCategory, int] = {}
        for m in memories:
            cat = self._extract_category(m)
            counts[cat] = counts.get(cat, 0) + 1

        patterns: List[InsightPattern] = [
            InsightPattern(label=cat.value, count=n, category=cat)
            for cat, n in sorted(
                counts.items(), key=lambda kv: (-kv[1], kv[0].value)
            )
        ][:3]

        # --- Contradictions ------------------------------------------
        approves = []
        rejects = []
        for m in memories:
            content_lower = (m.get("content") or "").lower()
            if any(tok in content_lower for tok in self._APPROVE_TOKENS):
                approves.append(m)
            if any(tok in content_lower for tok in self._REJECT_TOKENS):
                rejects.append(m)

        contradictions: List[InsightContradiction] = []
        seen_pairs = set()
        for a in approves:
            a_tokens = self._significant_tokens(a.get("content") or "")
            for r in rejects:
                if a.get("memory_id") == r.get("memory_id"):
                    continue
                r_tokens = self._significant_tokens(r.get("content") or "")
                overlap = a_tokens & r_tokens
                if len(overlap) < 2:
                    continue
                pair_key = frozenset({a.get("memory_id"), r.get("memory_id")})
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                topic = " ".join(sorted(overlap)[:3])
                contradictions.append(
                    InsightContradiction(
                        topic=topic,
                        memory_ids=[a.get("memory_id", ""), r.get("memory_id", "")],
                    )
                )

        # --- Gaps -----------------------------------------------------
        present = {c for c, n in counts.items() if n > 0}
        gaps: List[InsightGap] = []
        for cat in self._EXPECTED_GAP_CATEGORIES:
            if cat not in present:
                gaps.append(
                    InsightGap(
                        category=cat,
                        description=(
                            f"No memories of category '{cat.value}' in the corpus"
                        ),
                    )
                )

        return {
            "patterns": patterns,
            "contradictions": contradictions,
            "gaps": gaps,
        }

    # ------------------------------------------------------------------
    # Profile building (Refs #312 S4)
    # ------------------------------------------------------------------

    _PROFILE_TOPIC_LIMIT = 10
    _EXPERTISE_AREA_LIMIT = 5

    def build_profile(
        self,
        agent_id: str,
        memories: List[Dict[str, Any]],
    ) -> ProfileResponse:
        """
        Compute a cognitive profile from the agent's memory corpus.

        - `categories`: ProfileCategoryStats per MemoryCategory that appears
          in the corpus, sorted by count desc.
        - `topics`: top N ProfileTopicCount entries by count, each with an
          average-importance value. Topics are extracted via
          `_significant_tokens` (non-stopword, length>=3).
        - `expertise_areas`: top topics sorted by `count × avg_importance`,
          capped at 5.
        - `first_memory_at` / `last_memory_at`: min / max ISO timestamps.
        """
        if not memories:
            return ProfileResponse(agent_id=agent_id, memory_count=0)

        # Categories
        cat_counts: Dict[MemoryCategory, int] = {}
        # Topic aggregation: {token: (count, sum_importance)}
        topic_agg: Dict[str, List[float]] = {}
        timestamps: List[str] = []

        for m in memories:
            cat = self._extract_category(m)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

            metadata = m.get("metadata", {}) or {}
            try:
                importance = float(metadata.get("importance", 0.5))
            except (TypeError, ValueError):
                importance = 0.5

            for token in self._significant_tokens(m.get("content") or ""):
                bucket = topic_agg.setdefault(token, [0, 0.0])
                bucket[0] += 1
                bucket[1] += importance

            ts = m.get("timestamp")
            if isinstance(ts, str) and ts:
                timestamps.append(ts)

        categories = [
            ProfileCategoryStats(category=cat, count=count)
            for cat, count in sorted(
                cat_counts.items(), key=lambda kv: (-kv[1], kv[0].value)
            )
        ]

        topics = [
            ProfileTopicCount(
                topic=token,
                count=count,
                average_importance=max(0.0, min(1.0, total_imp / count)),
            )
            for token, (count, total_imp) in sorted(
                topic_agg.items(), key=lambda kv: (-kv[1][0], kv[0])
            )
        ][: self._PROFILE_TOPIC_LIMIT]

        # Expertise: rank by count × avg_importance
        expertise_areas = [
            token
            for token, _score in sorted(
                (
                    (token, count * (total_imp / count))
                    for token, (count, total_imp) in topic_agg.items()
                ),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ][: self._EXPERTISE_AREA_LIMIT]

        first_ts = min(timestamps) if timestamps else None
        last_ts = max(timestamps) if timestamps else None

        return ProfileResponse(
            agent_id=agent_id,
            memory_count=len(memories),
            categories=categories,
            topics=topics,
            expertise_areas=expertise_areas,
            first_memory_at=first_ts,
            last_memory_at=last_ts,
        )

    # ------------------------------------------------------------------
    # HCS anchoring hook (Refs #313 S5)
    # ------------------------------------------------------------------

    @staticmethod
    def content_hash(content: str) -> str:
        """Deterministic SHA-256 hex digest of UTF-8 memory content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def anchor_to_hcs(
        self,
        memory_id: str,
        content: str,
        agent_id: str,
        namespace: str,
        anchoring_service: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Best-effort anchor of a memory's content hash to HCS.

        Returns the anchoring-service result on success, or None on any
        failure. Failures are logged but never raise — the caller may
        still return success to the client because the memory is stored
        durably in ZeroDB regardless of HCS availability.
        """
        if anchoring_service is None:
            # Lazy import to avoid a circular service-layer dependency.
            from app.services.hcs_anchoring_service import get_hcs_anchoring_service

            try:
                anchoring_service = get_hcs_anchoring_service()
            except Exception as exc:  # pragma: no cover — defensive
                logger.warning(
                    "HCS anchoring service unavailable for memory %s: %s",
                    memory_id,
                    exc,
                )
                return None

        try:
            return await anchoring_service.anchor_memory(
                memory_id=memory_id,
                content_hash=self.content_hash(content),
                agent_id=agent_id,
                namespace=namespace,
            )
        except Exception as exc:  # best-effort: log, don't raise
            logger.warning(
                "HCS anchor failed for memory %s (agent %s): %s",
                memory_id,
                agent_id,
                exc,
            )
            return None


# Singleton pattern — matches the existing service modules in app/services.
_cognitive_memory_service: Optional[CognitiveMemoryService] = None


def get_cognitive_memory_service() -> CognitiveMemoryService:
    """Return the singleton, creating it on first call."""
    global _cognitive_memory_service
    if _cognitive_memory_service is None:
        _cognitive_memory_service = CognitiveMemoryService()
    return _cognitive_memory_service
