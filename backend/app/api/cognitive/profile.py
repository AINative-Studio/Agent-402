"""
GET /v1/public/{project_id}/memory/profile/{agent_id} — cognitive profile.

Refs #292. S0 (#308) lands a 501 stub; S4 (#312) replaces with real
profile building (topic distribution, expertise areas, etc.).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.cognitive_memory import ProfileResponse

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.get(
    "/{project_id}/memory/profile/{agent_id}",
    response_model=ProfileResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Cognitive profile (stats, topics, expertise)",
)
async def profile(project_id: str, agent_id: str) -> ProfileResponse:
    """Placeholder until #312 lands the real handler."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": "NOT_IMPLEMENTED",
            "detail": "GET /memory/profile/{agent_id} not yet implemented (#312)",
        },
    )
