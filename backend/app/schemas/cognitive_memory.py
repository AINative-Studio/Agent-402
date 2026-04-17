"""
Pydantic schemas for the ZeroMemory Cognitive API (#292).

Shared across the four cognitive endpoints:
- POST /memory/remember
- POST /memory/recall
- POST /memory/reflect
- GET  /memory/profile/{agent_id}

Design notes:
- Importance is a float in [0.0, 1.0] auto-computed on write by
  `CognitiveMemoryService.score_importance`. Clients may pass
  `importance_hint` to influence scoring.
- Category is determined by a keyword heuristic in S0; S1 replaces the stub
  with real logic. See `CognitiveMemoryService.categorize`.
- Recall composite score = `similarity*w_sim + recency*w_rec + importance*w_imp`.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CognitiveMemoryType(str, Enum):
    """ZeroMemory memory types per issue #292."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryCategory(str, Enum):
    """Categories produced by the auto-categorization heuristic."""

    DECISION = "decision"
    OBSERVATION = "observation"
    KNOWLEDGE = "knowledge"
    PLAN = "plan"
    INTERACTION = "interaction"
    ERROR = "error"
    OTHER = "other"


# ---------------------------------------------------------------------------
# /remember
# ---------------------------------------------------------------------------


class RememberRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    run_id: Optional[str] = None
    content: str = Field(..., min_length=1)
    memory_type: CognitiveMemoryType = CognitiveMemoryType.WORKING
    namespace: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance_hint: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RememberResponse(BaseModel):
    memory_id: str
    agent_id: str
    content: str
    memory_type: CognitiveMemoryType
    category: MemoryCategory
    importance: float = Field(..., ge=0.0, le=1.0)
    namespace: str
    timestamp: str
    hcs_anchor_pending: bool = True


# ---------------------------------------------------------------------------
# /recall
# ---------------------------------------------------------------------------


class RecallWeights(BaseModel):
    similarity: float = Field(default=0.6, ge=0.0, le=1.0)
    recency: float = Field(default=0.3, ge=0.0, le=1.0)
    importance: float = Field(default=0.1, ge=0.0, le=1.0)
    half_life_days: float = Field(default=7.0, gt=0.0)


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1)
    agent_id: Optional[str] = None
    namespace: str = "default"
    limit: int = Field(default=10, ge=1, le=100)
    weights: Optional[RecallWeights] = None


class RecallItem(BaseModel):
    memory_id: str
    agent_id: Optional[str] = None
    content: str
    category: MemoryCategory = MemoryCategory.OTHER
    memory_type: CognitiveMemoryType = CognitiveMemoryType.WORKING
    importance: float = 0.5
    similarity_score: float
    recency_weight: float
    composite_score: float
    timestamp: Optional[str] = None


class RecallResponse(BaseModel):
    memories: List[RecallItem] = Field(default_factory=list)
    query: str
    weights: RecallWeights


# ---------------------------------------------------------------------------
# /reflect
# ---------------------------------------------------------------------------


class ReflectRequest(BaseModel):
    agent_id: Optional[str] = None
    namespace: str = "default"
    window_days: int = Field(default=30, ge=1, le=365)


class InsightPattern(BaseModel):
    label: str
    count: int
    category: MemoryCategory


class InsightContradiction(BaseModel):
    topic: str
    memory_ids: List[str]


class InsightGap(BaseModel):
    category: MemoryCategory
    description: str


class ReflectResponse(BaseModel):
    agent_id: Optional[str] = None
    window_days: int
    memory_count: int
    patterns: List[InsightPattern] = Field(default_factory=list)
    contradictions: List[InsightContradiction] = Field(default_factory=list)
    gaps: List[InsightGap] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /profile
# ---------------------------------------------------------------------------


class ProfileCategoryStats(BaseModel):
    category: MemoryCategory
    count: int


class ProfileTopicCount(BaseModel):
    topic: str
    count: int
    average_importance: float = Field(..., ge=0.0, le=1.0)


class ProfileResponse(BaseModel):
    agent_id: str
    memory_count: int
    categories: List[ProfileCategoryStats] = Field(default_factory=list)
    topics: List[ProfileTopicCount] = Field(default_factory=list)
    expertise_areas: List[str] = Field(default_factory=list)
    first_memory_at: Optional[str] = None
    last_memory_at: Optional[str] = None
