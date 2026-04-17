"""
POST /v1/public/{project_id}/memory/recall — cognitive recall endpoint.

Refs #292, #310 (S2).

Semantic retrieval over agent memories with recency + importance
weighting. Composite score = similarity*w_sim + recency*w_rec +
importance*w_imp. Results are sorted by composite score descending and
truncated to `limit`.

Falls back gracefully when legacy memory records have no `importance`
field — those default to 0.5 (neutral).
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Path, status

from app.schemas.cognitive_memory import (
    CognitiveMemoryType,
    MemoryCategory,
    RecallItem,
    RecallRequest,
    RecallResponse,
    RecallWeights,
)
from app.services.agent_memory_service import agent_memory_service
from app.services.cognitive_memory_service import get_cognitive_memory_service

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


def _parse_category(raw: Any) -> MemoryCategory:
    """Safely map a string to MemoryCategory, defaulting to OTHER."""
    if isinstance(raw, MemoryCategory):
        return raw
    try:
        return MemoryCategory(raw)
    except (ValueError, TypeError):
        return MemoryCategory.OTHER


def _parse_memory_type(raw: Any) -> CognitiveMemoryType:
    """Safely map a string to CognitiveMemoryType, defaulting to WORKING."""
    if isinstance(raw, CognitiveMemoryType):
        return raw
    try:
        return CognitiveMemoryType(raw)
    except (ValueError, TypeError):
        return CognitiveMemoryType.WORKING


@router.post(
    "/{project_id}/memory/recall",
    response_model=RecallResponse,
    status_code=status.HTTP_200_OK,
    summary="Recall (semantic retrieval with relevance + recency)",
)
async def recall(
    request: RecallRequest,
    project_id: str = Path(..., min_length=1),
) -> RecallResponse:
    """Return memories ranked by composite relevance score."""
    weights = request.weights or RecallWeights()
    cognitive = get_cognitive_memory_service()

    matches: List[Dict[str, Any]] = await agent_memory_service.search_memories(
        project_id=project_id,
        query=request.query,
        namespace=request.namespace,
        top_k=request.limit,
    )

    items: List[RecallItem] = []
    for match in matches:
        if request.agent_id and match.get("agent_id") != request.agent_id:
            continue

        metadata = match.get("metadata", {}) or {}
        importance = metadata.get("importance", 0.5)
        try:
            importance = float(importance)
        except (TypeError, ValueError):
            importance = 0.5

        recency_weight = cognitive.compute_recency_weight(
            match.get("timestamp"),
            half_life_days=weights.half_life_days,
        )
        similarity = float(match.get("similarity_score", 0.0) or 0.0)
        composite = cognitive.compose_relevance(
            similarity=similarity,
            recency=recency_weight,
            importance=importance,
            weights=weights,
        )

        items.append(
            RecallItem(
                memory_id=match.get("memory_id", ""),
                agent_id=match.get("agent_id"),
                content=match.get("content", ""),
                category=_parse_category(metadata.get("category")),
                memory_type=_parse_memory_type(
                    metadata.get("cognitive_memory_type")
                    or match.get("memory_type")
                ),
                importance=max(0.0, min(1.0, importance)),
                similarity_score=similarity,
                recency_weight=recency_weight,
                composite_score=composite,
                timestamp=match.get("timestamp"),
            )
        )

    items.sort(key=lambda m: m.composite_score, reverse=True)
    if len(items) > request.limit:
        items = items[: request.limit]

    return RecallResponse(memories=items, query=request.query, weights=weights)
