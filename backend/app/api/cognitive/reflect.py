"""
POST /v1/public/{project_id}/memory/reflect — cognitive reflect endpoint.

Refs #292. S0 (#308) lands a 501 stub; S3 (#311) replaces with heuristic
synthesis of patterns / contradictions / gaps.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.cognitive_memory import ReflectRequest, ReflectResponse

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.post(
    "/{project_id}/memory/reflect",
    response_model=ReflectResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Reflect (synthesize patterns, contradictions, gaps)",
)
async def reflect(project_id: str, request: ReflectRequest) -> ReflectResponse:
    """Placeholder until #311 lands the real handler."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": "NOT_IMPLEMENTED",
            "detail": "POST /memory/reflect not yet implemented (#311)",
        },
    )
