"""
POST /v1/public/{project_id}/memory/reflect — cognitive reflect endpoint.

Refs #292, #311 (S3).

Fetches an agent's memories within `window_days`, runs the deterministic
insight heuristic (patterns, contradictions, gaps), and returns the
report. Intended to be pluggable to LLM synthesis in a follow-up.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Path, status

from app.schemas.cognitive_memory import ReflectRequest, ReflectResponse
from app.services.agent_memory_service import agent_memory_service
from app.services.cognitive_memory_service import get_cognitive_memory_service

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


def _within_window(
    timestamp: Optional[str],
    window_days: int,
    now: Optional[datetime] = None,
) -> bool:
    """True if `timestamp` is within `window_days` of `now`.

    Missing/unparseable timestamps are treated as in-window so legacy
    records aren't silently dropped from reflection.
    """
    if not timestamp:
        return True
    ts_str = (
        timestamp.replace("Z", "+00:00")
        if timestamp.endswith("Z")
        else timestamp
    )
    try:
        parsed = datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now_dt = now or datetime.now(timezone.utc)
    cutoff = now_dt - timedelta(days=window_days)
    return parsed >= cutoff


@router.post(
    "/{project_id}/memory/reflect",
    response_model=ReflectResponse,
    status_code=status.HTTP_200_OK,
    summary="Reflect (synthesize patterns, contradictions, gaps)",
)
async def reflect(
    request: ReflectRequest,
    project_id: str = Path(..., min_length=1),
) -> ReflectResponse:
    """Synthesize an insight report over the agent's recent memories."""
    memories, total, _filters = await agent_memory_service.list_memories(
        project_id=project_id,
        agent_id=request.agent_id,
        namespace=request.namespace,
        limit=500,
    )

    in_window: List[Dict[str, Any]] = [
        m for m in memories if _within_window(m.get("timestamp"), request.window_days)
    ]

    cognitive = get_cognitive_memory_service()
    insights = cognitive.synthesize_insights(in_window)

    return ReflectResponse(
        agent_id=request.agent_id,
        window_days=request.window_days,
        memory_count=total,
        patterns=insights["patterns"],
        contradictions=insights["contradictions"],
        gaps=insights["gaps"],
    )
