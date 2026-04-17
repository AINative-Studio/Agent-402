"""
POST /v1/public/{project_id}/memory/recall — cognitive recall endpoint.

Refs #292. S0 (#308) lands a 501 stub; S2 (#310) replaces with real
semantic retrieval + recency/importance weighting.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.cognitive_memory import RecallRequest, RecallResponse

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.post(
    "/{project_id}/memory/recall",
    response_model=RecallResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Recall (semantic retrieval with relevance + recency)",
)
async def recall(project_id: str, request: RecallRequest) -> RecallResponse:
    """Placeholder until #310 lands the real handler."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": "NOT_IMPLEMENTED",
            "detail": "POST /memory/recall not yet implemented (#310)",
        },
    )
