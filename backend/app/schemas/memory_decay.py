"""
Schemas for Memory Decay Worker — Issues #208, #209, #210.

Provides Pydantic models for:
  - MemoryTier enum
  - MemoryImportance score record
  - DecayCycleResult summary
  - PromotionResult per-memory promotion record
  - EvictionResult per-entity eviction report

Built by AINative Dev Team.
Refs #208, #209, #210.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    """Memory tier hierarchy — lower tiers decay faster."""

    WORKING = "working"      # Short-term, high decay (0.1/day)
    EPISODIC = "episodic"    # Session-scoped, medium decay (0.01/day)
    SEMANTIC = "semantic"    # Long-term, slow decay (0.001/day)
    CORE = "core"            # Permanent, never decays


class MemoryImportance(BaseModel):
    """Computed importance score for a single memory entry."""

    memory_id: str = Field(..., description="Unique memory identifier")
    tier: MemoryTier = Field(..., description="Current memory tier")
    initial_importance: float = Field(
        ..., ge=0.0, le=1.0, description="Importance at creation time"
    )
    current_importance: float = Field(
        ..., ge=0.0, description="Decayed importance at calculation time"
    )
    age_days: float = Field(..., ge=0.0, description="Age of the memory in days")
    access_boost: float = Field(
        default=0.0, ge=0.0,
        description="Boost applied from recent accesses (+0.1 per access in 7 days)"
    )
    marked_for_eviction: bool = Field(
        default=False,
        description="True when current_importance < eviction threshold (0.05)"
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of this calculation"
    )


class DecayCycleResult(BaseModel):
    """Summary of a completed decay cycle for a project."""

    project_id: str = Field(..., description="Project the decay cycle ran against")
    total_processed: int = Field(
        default=0, ge=0, description="Total number of memories processed"
    )
    flagged_for_eviction: int = Field(
        default=0, ge=0, description="Memories flagged below eviction threshold"
    )
    updated_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of memory_id → updated importance score"
    )
    ran_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the cycle completed"
    )


class PromotionResult(BaseModel):
    """Result of a single memory promotion operation."""

    memory_id: str = Field(..., description="Memory that was evaluated/promoted")
    from_tier: MemoryTier = Field(..., description="Source tier before promotion")
    to_tier: MemoryTier = Field(..., description="Target tier after promotion")
    promoted: bool = Field(
        default=False, description="True if the promotion was executed"
    )
    reason: Optional[str] = Field(
        default=None, description="Human-readable reason for promotion decision"
    )
    promoted_at: Optional[datetime] = Field(
        default=None, description="Timestamp of successful promotion"
    )


class EvictionResult(BaseModel):
    """Result of an LRU eviction pass for one entity."""

    project_id: str = Field(..., description="Project scoping the eviction")
    entity_id: str = Field(..., description="Entity whose memories were evaluated")
    evicted_ids: List[str] = Field(
        default_factory=list, description="IDs of memories that were evicted"
    )
    eviction_count: int = Field(
        default=0, ge=0, description="Number of memories evicted"
    )
    ran_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the eviction run"
    )

    def model_post_init(self, __context: Any) -> None:
        """Keep eviction_count in sync with evicted_ids length."""
        self.eviction_count = len(self.evicted_ids)
