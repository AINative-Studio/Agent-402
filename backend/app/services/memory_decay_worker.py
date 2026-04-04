"""
Memory Decay Worker — Issues #208, #209, #210.

Implements:
  - Exponential importance decay per memory tier
  - Access boost for recently accessed memories
  - Auto-promotion hierarchy across tiers
  - LRU eviction with tier-protection rules

Decay rates per tier:
  working  → 0.1  / day
  episodic → 0.01 / day
  semantic → 0.001 / day
  core     → 0    (never decays)

Formula: importance = initial_importance * exp(-decay_rate * age_days) + access_boost

Built by AINative Dev Team.
Refs #208, #209, #210.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.memory_decay import (
    DecayCycleResult,
    EvictionResult,
    MemoryTier,
    PromotionResult,
)

logger = logging.getLogger(__name__)

# Decay rate constants (per day)
DECAY_RATES: Dict[str, float] = {
    MemoryTier.WORKING: 0.1,
    MemoryTier.EPISODIC: 0.01,
    MemoryTier.SEMANTIC: 0.001,
    MemoryTier.CORE: 0.0,
}

# Importance below this value → flagged for eviction
EVICTION_THRESHOLD: float = 0.05

# Access boost per recent access
ACCESS_BOOST_PER_ACCESS: float = 0.1

# Window for "recent" accesses
RECENT_ACCESS_WINDOW_DAYS: int = 7

# Tier ordering for eviction priority (evict lower-priority tiers first)
_TIER_EVICTION_PRIORITY: Dict[str, int] = {
    MemoryTier.WORKING: 0,
    MemoryTier.EPISODIC: 1,
    MemoryTier.SEMANTIC: 2,
    MemoryTier.CORE: 3,   # Never evicted
}


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse an ISO-format datetime string or return a datetime unchanged."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


class MemoryDecayWorker:
    """
    Worker that applies importance decay, manages promotions, and enforces
    memory limits via LRU eviction.

    Designed to be dependency-free for unit testing; storage interactions are
    delegated to the overridable _fetch_memories / _update_* hooks.
    """

    # ------------------------------------------------------------------
    # Issue #208 — Importance Decay
    # ------------------------------------------------------------------

    async def calculate_importance(self, memory: Dict[str, Any]) -> float:
        """
        Compute the current importance score for a memory entry.

        Args:
            memory: Memory dict containing at minimum:
                      tier, initial_importance, created_at,
                      recent_accesses (list of ISO strings)

        Returns:
            Current floating-point importance score (may exceed 1.0 with boost).
        """
        tier = memory.get("tier", MemoryTier.WORKING)
        initial = float(memory.get("initial_importance", 1.0))
        created_at = _parse_dt(memory.get("created_at"))

        now = datetime.now(timezone.utc)
        age_days = 0.0
        if created_at:
            delta = now - created_at
            age_days = max(0.0, delta.total_seconds() / 86400.0)

        decay_rate = DECAY_RATES.get(tier, DECAY_RATES[MemoryTier.WORKING])
        base_importance = initial * math.exp(-decay_rate * age_days)

        # Access boost — +0.1 per access that occurred within last 7 days
        cutoff = now - timedelta(days=RECENT_ACCESS_WINDOW_DAYS)
        recent_accesses = memory.get("recent_accesses") or []
        access_boost = 0.0
        for raw_ts in recent_accesses:
            ts = _parse_dt(raw_ts)
            if ts and ts >= cutoff:
                access_boost += ACCESS_BOOST_PER_ACCESS

        return base_importance + access_boost

    async def run_decay_cycle(self, project_id: str) -> DecayCycleResult:
        """
        Scan all memories for a project and apply decay scores.

        Args:
            project_id: Project to process.

        Returns:
            DecayCycleResult summarising the run.
        """
        memories = await self._fetch_memories(project_id)

        updated_scores: Dict[str, float] = {}
        flagged = 0

        for memory in memories:
            memory_id = memory.get("memory_id", "")
            score = await self.calculate_importance(memory)
            updated_scores[memory_id] = score

            if score < EVICTION_THRESHOLD:
                flagged += 1
                await self._mark_for_eviction(memory_id)
            else:
                await self._update_memory_importance(memory_id, score)

        return DecayCycleResult(
            project_id=project_id,
            total_processed=len(memories),
            flagged_for_eviction=flagged,
            updated_scores=updated_scores,
        )

    # ------------------------------------------------------------------
    # Issue #209 — Auto-Promotion Hierarchy
    # ------------------------------------------------------------------

    async def _evaluate_promotion(
        self, memory: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine whether a memory should be promoted to the next tier.

        Returns:
            (should_promote, target_tier) — target_tier is None when no promotion.
        """
        tier = memory.get("tier", MemoryTier.WORKING)
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)

        if tier == MemoryTier.WORKING:
            # Promote → episodic: 3+ accesses within last 24 hours
            recent = memory.get("recent_accesses") or []
            count_24h = sum(
                1 for raw in recent
                if (ts := _parse_dt(raw)) and ts >= cutoff_24h
            )
            if count_24h >= 3:
                return True, MemoryTier.EPISODIC
            return False, None

        if tier == MemoryTier.EPISODIC:
            # Promote → semantic: 10+ total accesses across 3+ distinct sessions
            access_count = int(memory.get("access_count", 0))
            session_ids = memory.get("session_ids") or []
            distinct_sessions = len(set(session_ids))
            if access_count >= 10 and distinct_sessions >= 3:
                return True, MemoryTier.SEMANTIC
            return False, None

        if tier == MemoryTier.SEMANTIC:
            # Promote → core: 50+ total accesses (or manual promotion handled externally)
            access_count = int(memory.get("access_count", 0))
            if access_count >= 50:
                return True, MemoryTier.CORE
            return False, None

        # core tier — never promoted further
        return False, None

    async def promote_memory(
        self, memory_id: str, from_tier: str, to_tier: str
    ) -> PromotionResult:
        """
        Execute a promotion of a memory from one tier to another.

        Args:
            memory_id: Memory to promote.
            from_tier: Current tier.
            to_tier: Target tier.

        Returns:
            PromotionResult recording the outcome.
        """
        promoted_at = datetime.now(timezone.utc)
        await self._update_memory_tier(memory_id, to_tier)

        return PromotionResult(
            memory_id=memory_id,
            from_tier=MemoryTier(from_tier),
            to_tier=MemoryTier(to_tier),
            promoted=True,
            reason=f"Tier upgraded from {from_tier} to {to_tier}",
            promoted_at=promoted_at,
        )

    async def check_promotions(self, project_id: str) -> List[PromotionResult]:
        """
        Evaluate all memories for a project and promote eligible ones.

        Args:
            project_id: Project to process.

        Returns:
            List of PromotionResult — one per evaluated-and-eligible memory.
        """
        memories = await self._fetch_memories(project_id)
        results: List[PromotionResult] = []

        for memory in memories:
            should_promote, to_tier = await self._evaluate_promotion(memory)
            if should_promote and to_tier:
                memory_id = memory.get("memory_id", "")
                from_tier = memory.get("tier", MemoryTier.WORKING)
                result = await self.promote_memory(memory_id, from_tier, to_tier)
                results.append(result)

        return results

    # ------------------------------------------------------------------
    # Issue #210 — LRU Eviction
    # ------------------------------------------------------------------

    async def enforce_memory_limits(
        self,
        project_id: str,
        entity_id: str,
        memories: Optional[List[Dict[str, Any]]] = None,
        max_memories: int = 1000,
    ) -> List[str]:
        """
        Enforce a per-entity memory cap using LRU eviction.

        Protection rules:
          - core tier memories are NEVER evicted
          - semantic memories are evicted after working and episodic

        Args:
            project_id:   Project scope.
            entity_id:    Entity whose memories are being capped.
            memories:     Pre-fetched list of memory dicts (used in tests).
                          When None the worker fetches from storage.
            max_memories: Maximum number of memories to retain.

        Returns:
            List of evicted memory IDs (strings).
        """
        if memories is None:
            memories = await self._fetch_memories(project_id, entity_id=entity_id)

        # Separate out core memories — these are never touched
        evictable = [m for m in memories if m.get("tier") != MemoryTier.CORE]
        protected = [m for m in memories if m.get("tier") == MemoryTier.CORE]

        over_by = len(memories) - max_memories
        if over_by <= 0:
            return []

        # Sort evictable by: tier priority (lowest first), then last_accessed (oldest first)
        def _sort_key(m: Dict[str, Any]) -> Tuple[int, float]:
            tier = m.get("tier", MemoryTier.WORKING)
            priority = _TIER_EVICTION_PRIORITY.get(tier, 0)
            ts = _parse_dt(m.get("last_accessed"))
            # Lower timestamp = older = evicted sooner → use seconds since epoch ascending
            ts_score = ts.timestamp() if ts else 0.0
            return (priority, ts_score)

        evictable.sort(key=_sort_key)

        to_evict = evictable[:over_by]
        evicted_ids = [m["memory_id"] for m in to_evict]

        for mid in evicted_ids:
            await self._evict_memory(mid)

        return evicted_ids

    # ------------------------------------------------------------------
    # Storage hooks — override in subclasses or patch in tests
    # ------------------------------------------------------------------

    async def _fetch_memories(
        self,
        project_id: str,
        entity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch memories from storage.

        Override or monkeypatch this in tests to inject fixture data.
        Production implementations would call the ZeroDB client here.
        """
        logger.warning(
            "_fetch_memories called without a storage backend — returning []"
        )
        return []

    async def _update_memory_importance(
        self, memory_id: str, importance: float
    ) -> None:
        """Persist the updated importance score for a memory."""
        logger.debug("_update_memory_importance: %s → %.4f", memory_id, importance)

    async def _mark_for_eviction(self, memory_id: str) -> None:
        """Flag a memory as below the eviction threshold."""
        logger.debug("_mark_for_eviction: %s", memory_id)

    async def _update_memory_tier(self, memory_id: str, new_tier: str) -> None:
        """Persist a tier change for a memory."""
        logger.debug("_update_memory_tier: %s → %s", memory_id, new_tier)

    async def _evict_memory(self, memory_id: str) -> None:
        """Delete or archive a memory from storage."""
        logger.debug("_evict_memory: %s", memory_id)
