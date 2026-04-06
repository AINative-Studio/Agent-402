"""
WebSocket endpoint for real-time agent event streaming — Issue #211.

Endpoint: /ws/events/{agent_id}

Query params:
  event_types: comma-separated list of event types to subscribe to.
               Defaults to all valid types if omitted.

Built by AINative Dev Team
Refs #211
"""
from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.websocket_service import get_websocket_service, VALID_EVENT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Events"])


@router.websocket("/ws/events/{agent_id}")
async def agent_event_stream(
    websocket: WebSocket,
    agent_id: str,
    event_types: Optional[str] = Query(
        default=None,
        description="Comma-separated list of event types to subscribe to",
    ),
) -> None:
    """
    WebSocket endpoint for real-time agent event streaming.

    Connect to receive events for a specific agent. Clients may optionally
    pass ?event_types=task_started,task_failed to filter the event stream.

    Valid event types:
      task_started, task_completed, task_failed, memory_stored, payment_settled

    Messages are JSON objects:
      {
        "agent_id": "...",
        "event_type": "...",
        "payload": {...},
        "timestamp": "2026-..."
      }
    """
    service = get_websocket_service()

    if event_types:
        subscribed = [t.strip() for t in event_types.split(",") if t.strip()]
    else:
        subscribed = list(VALID_EVENT_TYPES)

    await websocket.accept()
    await service.connect(websocket, agent_id, subscribed)
    logger.info("WS client connected agent=%s types=%s", agent_id, subscribed)

    try:
        while True:
            # Keep connection alive; server-side events come from broadcast_event
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS client disconnected agent=%s", agent_id)
    finally:
        await service.disconnect(websocket)
