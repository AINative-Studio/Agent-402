"""
POST /v1/public/{project_id}/memory/remember — cognitive remember endpoint.

Refs #292, #309 (S1), #313 (S5 HCS anchor hook).

Wraps `AgentMemoryService.store_memory` with:
- Importance scoring (CognitiveMemoryService.score_importance)
- Auto-categorization (CognitiveMemoryService.categorize)
- Best-effort HCS anchoring of the memory's content hash (S5)
- A stable envelope (`RememberResponse`) matching the TS SDK shape.

HCS anchoring is best-effort: if the HCS pipeline fails, the memory is
still persisted and the handler returns 201 with `hcs_anchor_pending=True`
so the client knows anchoring can be retried.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Path, status

from app.schemas.cognitive_memory import RememberRequest, RememberResponse
from app.services.agent_memory_service import agent_memory_service
from app.services.cognitive_memory_service import get_cognitive_memory_service

router = APIRouter(prefix="/v1/public", tags=["cognitive-memory"])


@router.post(
    "/{project_id}/memory/remember",
    response_model=RememberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Remember (store with importance + category)",
)
async def remember(
    request: RememberRequest,
    project_id: str = Path(..., min_length=1),
) -> RememberResponse:
    """
    Store a memory with auto-computed importance and category, then anchor
    the content hash to HCS (best-effort).

    The memory goes through the existing `AgentMemoryService` for embedding
    + row persistence. Cognitive enrichment (importance, category) is
    merged into the metadata so downstream `/recall` and `/reflect` can
    operate on it. An HCS anchor is submitted as a best-effort operation;
    failure is logged but does not fail the request.
    """
    cognitive = get_cognitive_memory_service()
    importance = cognitive.score_importance(
        memory_type=request.memory_type,
        content=request.content,
        metadata=request.metadata,
        importance_hint=request.importance_hint,
    )
    category = cognitive.categorize(
        content=request.content,
        memory_type=request.memory_type,
    )

    enriched_metadata: Dict[str, Any] = dict(request.metadata)
    enriched_metadata["importance"] = importance
    enriched_metadata["category"] = category.value
    enriched_metadata["cognitive_memory_type"] = request.memory_type.value

    run_id = request.run_id or f"run_{uuid.uuid4().hex[:12]}"

    stored = await agent_memory_service.store_memory(
        project_id=project_id,
        agent_id=request.agent_id,
        run_id=run_id,
        memory_type=request.memory_type.value,
        content=request.content,
        namespace=request.namespace,
        metadata=enriched_metadata,
    )

    anchor_result = await cognitive.anchor_to_hcs(
        memory_id=stored["memory_id"],
        content=request.content,
        agent_id=request.agent_id,
        namespace=request.namespace,
    )

    return RememberResponse(
        memory_id=stored["memory_id"],
        agent_id=stored["agent_id"],
        content=request.content,
        memory_type=request.memory_type,
        category=category,
        importance=importance,
        namespace=stored.get("namespace", request.namespace),
        timestamp=stored.get("timestamp", ""),
        hcs_anchor_pending=anchor_result is None,
    )
