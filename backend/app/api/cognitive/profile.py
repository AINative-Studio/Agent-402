"""
GET /v1/public/{project_id}/memory/profile/{agent_id} — cognitive profile.

Refs #292, #312 (S4).

Fetches all memories for the agent (up to 500), delegates to
CognitiveMemoryService.build_profile to compute stats, topics, expertise
areas, and timeline boundaries.
"""
from __future__ import annotations

from fastapi import APIRouter, Path, Query, status

from app.schemas.cognitive_memory import ProfileResponse
from app.services.agent_memory_service import agent_memory_service
from app.services.cognitive_memory_service import get_cognitive_memory_service

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.get(
    "/{project_id}/memory/profile/{agent_id}",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Cognitive profile (stats, topics, expertise)",
)
async def profile(
    project_id: str = Path(..., min_length=1),
    agent_id: str = Path(..., min_length=1),
    namespace: str = Query(default="default", min_length=1),
) -> ProfileResponse:
    """Return the agent's cognitive profile."""
    memories, _total, _filters = await agent_memory_service.list_memories(
        project_id=project_id,
        agent_id=agent_id,
        namespace=namespace,
        limit=500,
    )

    cognitive = get_cognitive_memory_service()
    return cognitive.build_profile(agent_id=agent_id, memories=memories)
