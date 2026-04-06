"""
RED tests for WebSocket Service — Issue #211.

Covers WebSocketService: connect, disconnect, broadcast_event,
get_connected_clients, and event type validation.
Built by AINative Dev Team
Refs #211
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from typing import Optional, Dict, List, Any


# ===========================================================================
# Issue #211 — WebSocket Service
# ===========================================================================

class DescribeWebSocketServiceConnect:
    """Tests for WebSocketService.connect (Issue #211)."""

    @pytest.mark.asyncio
    async def it_registers_a_websocket_for_an_agent(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-1", ["task_started"])
        clients = await service.get_connected_clients("agent-1")
        assert len(clients) == 1

    @pytest.mark.asyncio
    async def it_accepts_all_valid_event_types(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        valid_types = [
            "task_started", "task_completed", "task_failed",
            "memory_stored", "payment_settled",
        ]
        await service.connect(websocket, "agent-2", valid_types)
        clients = await service.get_connected_clients("agent-2")
        assert len(clients) == 1

    @pytest.mark.asyncio
    async def it_allows_multiple_clients_per_agent(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await service.connect(ws1, "agent-3", ["task_started"])
        await service.connect(ws2, "agent-3", ["task_completed"])
        clients = await service.get_connected_clients("agent-3")
        assert len(clients) == 2

    @pytest.mark.asyncio
    async def it_stores_subscribed_event_types_per_client(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-4", ["task_started", "task_failed"])
        clients = await service.get_connected_clients("agent-4")
        assert len(clients) == 1
        assert set(clients[0]["event_types"]) == {"task_started", "task_failed"}


class DescribeWebSocketServiceDisconnect:
    """Tests for WebSocketService.disconnect (Issue #211)."""

    @pytest.mark.asyncio
    async def it_removes_a_registered_websocket(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-5", ["task_started"])
        await service.disconnect(websocket)
        clients = await service.get_connected_clients("agent-5")
        assert len(clients) == 0

    @pytest.mark.asyncio
    async def it_does_not_raise_when_disconnecting_unknown_socket(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        # Should not raise even if websocket was never connected
        await service.disconnect(websocket)

    @pytest.mark.asyncio
    async def it_only_removes_the_specific_websocket(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await service.connect(ws1, "agent-6", ["task_started"])
        await service.connect(ws2, "agent-6", ["task_completed"])
        await service.disconnect(ws1)
        clients = await service.get_connected_clients("agent-6")
        assert len(clients) == 1


class DescribeWebSocketServiceBroadcast:
    """Tests for WebSocketService.broadcast_event (Issue #211)."""

    @pytest.mark.asyncio
    async def it_sends_event_to_subscribed_client(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-7", ["task_started"])
        await service.broadcast_event("agent-7", "task_started", {"task_id": "t1"})
        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "task_started"
        assert call_args["payload"]["task_id"] == "t1"

    @pytest.mark.asyncio
    async def it_does_not_send_to_unsubscribed_event_types(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-8", ["task_completed"])
        await service.broadcast_event("agent-8", "task_started", {"task_id": "t2"})
        websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def it_broadcasts_to_all_subscribed_clients_for_agent(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await service.connect(ws1, "agent-9", ["task_started"])
        await service.connect(ws2, "agent-9", ["task_started"])
        await service.broadcast_event("agent-9", "task_started", {"x": 1})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def it_does_not_broadcast_to_other_agents(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        ws_other = AsyncMock()
        await service.connect(ws_other, "agent-other", ["task_started"])
        await service.broadcast_event("agent-10", "task_started", {"x": 1})
        ws_other.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def it_includes_agent_id_and_timestamp_in_broadcast_payload(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-11", ["payment_settled"])
        await service.broadcast_event("agent-11", "payment_settled", {"amount": 100})
        call_args = websocket.send_json.call_args[0][0]
        assert "agent_id" in call_args
        assert call_args["agent_id"] == "agent-11"
        assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def it_removes_stale_connection_on_send_error(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        websocket.send_json.side_effect = Exception("connection closed")
        await service.connect(websocket, "agent-12", ["task_started"])
        # Should not raise
        await service.broadcast_event("agent-12", "task_started", {})
        clients = await service.get_connected_clients("agent-12")
        assert len(clients) == 0


class DescribeWebSocketServiceGetClients:
    """Tests for WebSocketService.get_connected_clients (Issue #211)."""

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_unknown_agent(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        clients = await service.get_connected_clients("unknown-agent")
        assert clients == []

    @pytest.mark.asyncio
    async def it_returns_list_of_connection_dicts(self):
        from app.services.websocket_service import WebSocketService
        service = WebSocketService()
        websocket = AsyncMock()
        await service.connect(websocket, "agent-13", ["memory_stored"])
        clients = await service.get_connected_clients("agent-13")
        assert isinstance(clients, list)
        assert isinstance(clients[0], dict)
        assert "event_types" in clients[0]
