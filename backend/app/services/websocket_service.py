"""
WebSocket service for real-time agent event broadcasting — Issue #211.

Implements:
- connect: register a WebSocket client for an agent's event types
- disconnect: unregister a client
- broadcast_event: fan-out to all subscribed clients
- get_connected_clients: list active connections for an agent

Built by AINative Dev Team
Refs #211
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES: List[str] = [
    "task_started",
    "task_completed",
    "task_failed",
    "memory_stored",
    "payment_settled",
]


class WebSocketService:
    """
    Manages WebSocket connections for real-time agent event streaming.

    Maintains an in-memory registry of (websocket -> {agent_id, event_types}).
    Supports multi-client fan-out per agent and per-event-type filtering.
    """

    def __init__(self) -> None:
        # Maps: websocket object -> {"agent_id": str, "event_types": list[str]}
        self._connections: Dict[Any, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: Any,
        agent_id: str,
        event_types: List[str],
    ) -> None:
        """
        Register a WebSocket client for a specific agent and set of event types.

        Args:
            websocket: The WebSocket connection object (must support send_json).
            agent_id: The agent whose events this client wants to receive.
            event_types: List of event type strings to subscribe to.
        """
        self._connections[websocket] = {
            "agent_id": agent_id,
            "event_types": list(event_types),
        }
        logger.info(
            "WebSocket connected for agent %s, types=%s",
            agent_id,
            event_types,
        )

    async def disconnect(self, websocket: Any) -> None:
        """
        Unregister a WebSocket client.

        Safe to call even if the websocket was never registered.

        Args:
            websocket: The WebSocket connection to remove.
        """
        self._connections.pop(websocket, None)
        logger.info("WebSocket disconnected")

    async def broadcast_event(
        self,
        agent_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Send an event to all WebSocket clients subscribed to the given
        agent_id and event_type.

        Stale connections (those that raise on send_json) are silently pruned.

        Args:
            agent_id: The agent that emitted the event.
            event_type: One of the VALID_EVENT_TYPES.
            payload: Arbitrary event data dict.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        message: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": timestamp,
        }

        stale: List[Any] = []

        for ws, meta in list(self._connections.items()):
            if meta["agent_id"] != agent_id:
                continue
            if event_type not in meta["event_types"]:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning(
                    "Stale WebSocket for agent %s, pruning", agent_id
                )
                stale.append(ws)

        for ws in stale:
            self._connections.pop(ws, None)

    async def get_connected_clients(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Return metadata for all active WebSocket clients for a given agent.

        Args:
            agent_id: The agent ID to query.

        Returns:
            List of dicts with at least {"event_types": [...]} per connection.
        """
        return [
            {"event_types": meta["event_types"]}
            for meta in self._connections.values()
            if meta["agent_id"] == agent_id
        ]


# Singleton
_websocket_service: Optional[WebSocketService] = None


def get_websocket_service() -> WebSocketService:
    """Return the singleton WebSocketService instance."""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service
