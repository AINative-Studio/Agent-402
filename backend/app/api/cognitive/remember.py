"""
POST /v1/public/{project_id}/memory/remember — cognitive remember endpoint.

Refs #292. S0 (#308) lands a 501 stub; S1 (#309) replaces with real logic
for importance scoring, auto-categorization, and persistence via
AgentMemoryService.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.cognitive_memory import RememberRequest, RememberResponse

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.post(
    "/{project_id}/memory/remember",
    response_model=RememberResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Remember (store with importance + category)",
)
async def remember(project_id: str, request: RememberRequest) -> RememberResponse:
    """Placeholder until #309 lands the real handler."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": "NOT_IMPLEMENTED",
            "detail": "POST /memory/remember not yet implemented (#309)",
        },
    )
