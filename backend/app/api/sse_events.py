"""
SSE endpoint for task progress streaming — Issue #212.

Endpoint: GET /api/v1/events/tasks/{task_id}/stream

Built by AINative Dev Team
Refs #212
"""
from __future__ import annotations

import logging
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.errors import InvalidAPIKeyError
from app.services.sse_service import get_sse_service, SSEService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/events",
    tags=["SSE Events"],
)


@router.get(
    "/tasks/{task_id}/stream",
    summary="Stream task progress via Server-Sent Events",
    response_class=StreamingResponse,
)
async def stream_task_progress(
    task_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> StreamingResponse:
    """
    Subscribe to task progress events via Server-Sent Events.

    Streams ``data: <json>\\n\\n`` events until the queue is drained.

    Each event JSON contains:
      task_id, step, total_steps, message, timestamp

    For completion events the JSON additionally contains:
      status, result

    **Authentication:** Required via X-API-Key header.
    """
    if not x_api_key or not x_api_key.strip():
        raise InvalidAPIKeyError()

    sse_service = get_sse_service()

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in sse_service.subscribe_task(task_id):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
