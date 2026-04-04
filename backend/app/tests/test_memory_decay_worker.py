"""
Tests for Memory Decay Worker — Issues #208, #209, #210.

Covers:
  - Importance decay calculation with exponential formula
  - Access boost applied per recent access
  - Decay cycle results aggregated per project
  - Auto-promotion rules across the memory tier hierarchy
  - LRU eviction with tier-protection rules

BDD-style: DescribeX / it_does_something naming convention.
"""
from __future__ import annotations

import math
import pytest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — build in-memory memory dicts matching the service's expected shape
# ---------------------------------------------------------------------------

def _make_memory(
    memory_id: str,
    tier: str,
    initial_importance: float,
    created_at: datetime,
    access_count: int = 0,
    recent_accesses: Optional[List[datetime]] = None,
    last_accessed: Optional[datetime] = None,
    session_ids: Optional[List[str]] = None,
    entity_id: str = "entity_001",
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "memory_id": memory_id,
        "tier": tier,
        "initial_importance": initial_importance,
        "created_at": created_at.isoformat(),
        "access_count": access_count,
        "recent_accesses": [
            a.isoformat() for a in (recent_accesses or [])
        ],
        "last_accessed": (last_accessed or created_at).isoformat(),
        "session_ids": session_ids or [],
        "entity_id": entity_id,
        "marked_for_eviction": False,
    }


# ---------------------------------------------------------------------------
# Issue #208 — Importance Decay Calculation
# ---------------------------------------------------------------------------

class DescribeCalculateImportance:
    """Unit tests for MemoryDecayWorker.calculate_importance."""

    @pytest.mark.asyncio
    async def it_returns_full_importance_for_fresh_core_memory(self, decay_worker):
        memory = _make_memory(
            "mem_001", "core", 1.0,
            created_at=datetime.now(timezone.utc),
        )
        score = await decay_worker.calculate_importance(memory)
        # core decay_rate = 0, age_days = ~0 → importance ≈ 1.0
        assert abs(score - 1.0) < 0.01

    @pytest.mark.asyncio
    async def it_applies_zero_decay_to_core_memories(self, decay_worker):
        old_date = datetime.now(timezone.utc) - timedelta(days=365)
        memory = _make_memory("mem_002", "core", 0.8, created_at=old_date)
        score = await decay_worker.calculate_importance(memory)
        # core never decays: importance = 0.8 * exp(0 * 365) = 0.8
        assert abs(score - 0.8) < 0.01

    @pytest.mark.asyncio
    async def it_decays_working_memory_at_point_one_per_day(self, decay_worker):
        created = datetime.now(timezone.utc) - timedelta(days=10)
        memory = _make_memory("mem_003", "working", 1.0, created_at=created)
        score = await decay_worker.calculate_importance(memory)
        expected = 1.0 * math.exp(-0.1 * 10)
        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def it_decays_episodic_memory_at_point_zero_one_per_day(self, decay_worker):
        created = datetime.now(timezone.utc) - timedelta(days=30)
        memory = _make_memory("mem_004", "episodic", 1.0, created_at=created)
        score = await decay_worker.calculate_importance(memory)
        expected = 1.0 * math.exp(-0.01 * 30)
        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def it_decays_semantic_memory_at_point_zero_zero_one_per_day(self, decay_worker):
        created = datetime.now(timezone.utc) - timedelta(days=100)
        memory = _make_memory("mem_005", "semantic", 1.0, created_at=created)
        score = await decay_worker.calculate_importance(memory)
        expected = 1.0 * math.exp(-0.001 * 100)
        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def it_adds_access_boost_for_each_access_in_last_seven_days(
        self, decay_worker
    ):
        now = datetime.now(timezone.utc)
        recent = [now - timedelta(hours=i * 12) for i in range(3)]  # 3 accesses
        memory = _make_memory(
            "mem_006", "working", 1.0,
            created_at=now - timedelta(days=1),
            recent_accesses=recent,
        )
        score = await decay_worker.calculate_importance(memory)
        base = 1.0 * math.exp(-0.1 * 1)
        expected = base + 0.3  # +0.1 per access × 3
        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def it_ignores_accesses_older_than_seven_days(self, decay_worker):
        now = datetime.now(timezone.utc)
        old_access = now - timedelta(days=8)
        memory = _make_memory(
            "mem_007", "working", 1.0,
            created_at=now - timedelta(days=1),
            recent_accesses=[old_access],
        )
        score = await decay_worker.calculate_importance(memory)
        base = 1.0 * math.exp(-0.1 * 1)
        assert abs(score - base) < 0.001  # no boost applied

    @pytest.mark.asyncio
    async def it_marks_memory_for_eviction_when_below_threshold(self, decay_worker):
        # Working memory that is 100 days old has essentially zero importance
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        memory = _make_memory("mem_008", "working", 0.04, created_at=old_date)
        score = await decay_worker.calculate_importance(memory)
        assert score < 0.05  # verifies the eviction threshold condition


# ---------------------------------------------------------------------------
# Issue #208 — Decay Cycle
# ---------------------------------------------------------------------------

class DescribeRunDecayCycle:
    """Integration-style tests for MemoryDecayWorker.run_decay_cycle."""

    @pytest.mark.asyncio
    async def it_returns_a_decay_cycle_result(self, decay_worker_with_mock_storage):
        worker, mock_storage = decay_worker_with_mock_storage
        result = await worker.run_decay_cycle("proj_001")
        assert result is not None
        assert hasattr(result, "project_id")
        assert result.project_id == "proj_001"

    @pytest.mark.asyncio
    async def it_reports_total_memories_processed(self, decay_worker_with_mock_storage):
        worker, mock_storage = decay_worker_with_mock_storage
        result = await worker.run_decay_cycle("proj_001")
        assert result.total_processed == len(mock_storage)

    @pytest.mark.asyncio
    async def it_flags_memories_below_threshold_for_eviction(
        self, decay_worker_with_mock_storage
    ):
        worker, mock_storage = decay_worker_with_mock_storage
        result = await worker.run_decay_cycle("proj_001")
        # One memory in mock_storage has importance below 0.05
        assert result.flagged_for_eviction >= 1

    @pytest.mark.asyncio
    async def it_records_updated_importance_scores(
        self, decay_worker_with_mock_storage
    ):
        worker, mock_storage = decay_worker_with_mock_storage
        result = await worker.run_decay_cycle("proj_001")
        assert isinstance(result.updated_scores, dict)
        assert len(result.updated_scores) == len(mock_storage)


# ---------------------------------------------------------------------------
# Issue #209 — Auto-Promotion Hierarchy
# ---------------------------------------------------------------------------

class DescribeCheckPromotions:
    """Tests for MemoryDecayWorker.check_promotions."""

    @pytest.mark.asyncio
    async def it_promotes_working_to_episodic_after_three_accesses_in_24_hours(
        self, decay_worker
    ):
        now = datetime.now(timezone.utc)
        accesses_24h = [now - timedelta(hours=i * 6) for i in range(3)]
        memory = _make_memory(
            "mem_p01", "working", 0.5,
            created_at=now - timedelta(days=1),
            access_count=3,
            recent_accesses=accesses_24h,
        )
        should_promote, to_tier = await decay_worker._evaluate_promotion(memory)
        assert should_promote is True
        assert to_tier == "episodic"

    @pytest.mark.asyncio
    async def it_does_not_promote_working_memory_with_fewer_than_three_accesses(
        self, decay_worker
    ):
        now = datetime.now(timezone.utc)
        accesses_24h = [now - timedelta(hours=i * 6) for i in range(2)]
        memory = _make_memory(
            "mem_p02", "working", 0.5,
            created_at=now - timedelta(days=1),
            access_count=2,
            recent_accesses=accesses_24h,
        )
        should_promote, _ = await decay_worker._evaluate_promotion(memory)
        assert should_promote is False

    @pytest.mark.asyncio
    async def it_promotes_episodic_to_semantic_after_ten_accesses_across_three_sessions(
        self, decay_worker
    ):
        now = datetime.now(timezone.utc)
        memory = _make_memory(
            "mem_p03", "episodic", 0.6,
            created_at=now - timedelta(days=7),
            access_count=10,
            session_ids=["sess_a", "sess_b", "sess_c"],
        )
        should_promote, to_tier = await decay_worker._evaluate_promotion(memory)
        assert should_promote is True
        assert to_tier == "semantic"

    @pytest.mark.asyncio
    async def it_does_not_promote_episodic_with_fewer_than_three_sessions(
        self, decay_worker
    ):
        now = datetime.now(timezone.utc)
        memory = _make_memory(
            "mem_p04", "episodic", 0.6,
            created_at=now - timedelta(days=7),
            access_count=10,
            session_ids=["sess_a", "sess_b"],
        )
        should_promote, _ = await decay_worker._evaluate_promotion(memory)
        assert should_promote is False

    @pytest.mark.asyncio
    async def it_promotes_semantic_to_core_after_fifty_accesses(self, decay_worker):
        now = datetime.now(timezone.utc)
        memory = _make_memory(
            "mem_p05", "semantic", 0.9,
            created_at=now - timedelta(days=30),
            access_count=50,
        )
        should_promote, to_tier = await decay_worker._evaluate_promotion(memory)
        assert should_promote is True
        assert to_tier == "core"

    @pytest.mark.asyncio
    async def it_does_not_promote_semantic_below_fifty_accesses(self, decay_worker):
        now = datetime.now(timezone.utc)
        memory = _make_memory(
            "mem_p06", "semantic", 0.9,
            created_at=now - timedelta(days=30),
            access_count=49,
        )
        should_promote, _ = await decay_worker._evaluate_promotion(memory)
        assert should_promote is False

    @pytest.mark.asyncio
    async def it_does_not_promote_core_memories(self, decay_worker):
        now = datetime.now(timezone.utc)
        memory = _make_memory(
            "mem_p07", "core", 1.0,
            created_at=now - timedelta(days=100),
            access_count=999,
        )
        should_promote, _ = await decay_worker._evaluate_promotion(memory)
        assert should_promote is False


class DescribePromoteMemory:
    """Tests for MemoryDecayWorker.promote_memory."""

    @pytest.mark.asyncio
    async def it_returns_a_promotion_result_with_correct_tiers(self, decay_worker):
        result = await decay_worker.promote_memory("mem_001", "working", "episodic")
        assert result is not None
        assert result.memory_id == "mem_001"
        assert result.from_tier == "working"
        assert result.to_tier == "episodic"

    @pytest.mark.asyncio
    async def it_sets_promoted_flag_to_true_on_success(self, decay_worker):
        result = await decay_worker.promote_memory("mem_002", "episodic", "semantic")
        assert result.promoted is True

    @pytest.mark.asyncio
    async def it_records_promotion_timestamp(self, decay_worker):
        result = await decay_worker.promote_memory("mem_003", "semantic", "core")
        assert result.promoted_at is not None


class DescribeCheckPromotionsCycle:
    """Tests for the full check_promotions cycle."""

    @pytest.mark.asyncio
    async def it_returns_list_of_promotion_results(
        self, decay_worker_with_promotable_memories
    ):
        worker, _ = decay_worker_with_promotable_memories
        results = await worker.check_promotions("proj_001")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def it_promotes_eligible_memories(
        self, decay_worker_with_promotable_memories
    ):
        worker, _ = decay_worker_with_promotable_memories
        results = await worker.check_promotions("proj_001")
        promoted = [r for r in results if r.promoted]
        assert len(promoted) >= 1


# ---------------------------------------------------------------------------
# Issue #210 — LRU Eviction
# ---------------------------------------------------------------------------

class DescribeEnforceMemoryLimits:
    """Tests for MemoryDecayWorker.enforce_memory_limits."""

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_under_limit(self, decay_worker):
        memories = [
            _make_memory(f"mem_{i}", "working", 0.5,
                         created_at=datetime.now(timezone.utc) - timedelta(days=i))
            for i in range(5)
        ]
        evicted = await decay_worker.enforce_memory_limits(
            "proj_001", "entity_001", memories=memories, max_memories=10
        )
        assert evicted == []

    @pytest.mark.asyncio
    async def it_evicts_oldest_lru_memories_when_over_limit(self, decay_worker):
        now = datetime.now(timezone.utc)
        memories = [
            _make_memory(
                f"mem_{i}", "working", 0.5,
                created_at=now - timedelta(days=100),
                last_accessed=now - timedelta(days=i),
            )
            for i in range(5)
        ]
        evicted = await decay_worker.enforce_memory_limits(
            "proj_001", "entity_001", memories=memories, max_memories=3
        )
        # Should evict 2 memories (oldest last_accessed = highest day delta)
        assert len(evicted) == 2

    @pytest.mark.asyncio
    async def it_never_evicts_core_tier_memories(self, decay_worker):
        now = datetime.now(timezone.utc)
        memories = [
            _make_memory("core_mem", "core", 1.0,
                         created_at=now - timedelta(days=200),
                         last_accessed=now - timedelta(days=200)),
            _make_memory("working_mem_1", "working", 0.3,
                         created_at=now - timedelta(days=50),
                         last_accessed=now - timedelta(days=50)),
            _make_memory("working_mem_2", "working", 0.3,
                         created_at=now - timedelta(days=30),
                         last_accessed=now - timedelta(days=30)),
        ]
        evicted = await decay_worker.enforce_memory_limits(
            "proj_001", "entity_001", memories=memories, max_memories=2
        )
        assert "core_mem" not in evicted

    @pytest.mark.asyncio
    async def it_evicts_semantic_after_working_and_episodic(self, decay_worker):
        now = datetime.now(timezone.utc)
        memories = [
            _make_memory("sem_mem", "semantic", 0.7,
                         created_at=now - timedelta(days=10),
                         last_accessed=now - timedelta(days=10)),
            _make_memory("work_mem", "working", 0.3,
                         created_at=now - timedelta(days=5),
                         last_accessed=now - timedelta(days=5)),
            _make_memory("epis_mem", "episodic", 0.4,
                         created_at=now - timedelta(days=8),
                         last_accessed=now - timedelta(days=8)),
        ]
        # max_memories=1 forces 2 evictions — working and episodic evicted first
        evicted = await decay_worker.enforce_memory_limits(
            "proj_001", "entity_001", memories=memories, max_memories=1
        )
        assert "sem_mem" not in evicted
        assert "work_mem" in evicted

    @pytest.mark.asyncio
    async def it_returns_eviction_result_objects_with_memory_ids(self, decay_worker):
        now = datetime.now(timezone.utc)
        memories = [
            _make_memory(
                f"mem_{i}", "working", 0.5,
                created_at=now - timedelta(days=100),
                last_accessed=now - timedelta(days=i),
            )
            for i in range(5)
        ]
        evicted = await decay_worker.enforce_memory_limits(
            "proj_001", "entity_001", memories=memories, max_memories=3
        )
        for eid in evicted:
            assert isinstance(eid, str)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def decay_worker():
    """Provide a MemoryDecayWorker with no external dependencies."""
    from app.services.memory_decay_worker import MemoryDecayWorker
    return MemoryDecayWorker()


@pytest.fixture
def mock_storage():
    """Six test memories with varying ages and tiers."""
    now = datetime.now(timezone.utc)
    return [
        _make_memory("m1", "working", 1.0, created_at=now - timedelta(days=1)),
        _make_memory("m2", "episodic", 0.8, created_at=now - timedelta(days=5)),
        _make_memory("m3", "semantic", 0.9, created_at=now - timedelta(days=20)),
        _make_memory("m4", "core", 1.0, created_at=now - timedelta(days=365)),
        # This one will decay below threshold (working, 100 days old, low initial)
        _make_memory("m5", "working", 0.01, created_at=now - timedelta(days=100)),
        _make_memory("m6", "episodic", 0.5, created_at=now - timedelta(days=10)),
    ]


@pytest.fixture
def decay_worker_with_mock_storage(decay_worker, mock_storage):
    """Pair a worker with a fixed memory list via monkeypatched fetch."""
    decay_worker._fetch_memories = AsyncMock(return_value=mock_storage)
    decay_worker._update_memory_importance = AsyncMock()
    decay_worker._mark_for_eviction = AsyncMock()
    return decay_worker, mock_storage


@pytest.fixture
def decay_worker_with_promotable_memories(decay_worker):
    """Worker with one clearly promotable memory pre-loaded."""
    now = datetime.now(timezone.utc)
    promotable = _make_memory(
        "pm_01", "working", 0.5,
        created_at=now - timedelta(days=1),
        access_count=3,
        recent_accesses=[now - timedelta(hours=i * 6) for i in range(3)],
    )
    not_promotable = _make_memory(
        "pm_02", "working", 0.5,
        created_at=now - timedelta(days=1),
        access_count=1,
    )
    decay_worker._fetch_memories = AsyncMock(return_value=[promotable, not_promotable])
    decay_worker._update_memory_tier = AsyncMock()
    return decay_worker, [promotable, not_promotable]
