"""
Schemas for real-time events (WebSocket and SSE) — Issues #211, #212.

Defines request/response models for:
- WebSocket agent event subscriptions
- SSE task progress streaming

Built by AINative Dev Team
Refs #211 #212
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


VALID_EVENT_TYPES: List[str] = [
    "task_started",
    "task_completed",
    "task_failed",
    "memory_stored",
    "payment_settled",
]


class WebSocketConnectRequest(BaseModel):
    """Request payload for WebSocket event subscription."""

    agent_id: str = Field(..., description="Agent ID to subscribe to")
    event_types: List[str] = Field(
        default_factory=lambda: VALID_EVENT_TYPES[:],
        description="Event types to subscribe to",
    )


class WebSocketEventMessage(BaseModel):
    """Envelope for outbound WebSocket event messages."""

    agent_id: str = Field(..., description="Agent ID that emitted the event")
    event_type: str = Field(..., description="Event type identifier")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


class SSEProgressEvent(BaseModel):
    """SSE event data for task progress updates."""

    task_id: str = Field(..., description="Task identifier")
    step: int = Field(..., description="Current step number")
    total_steps: int = Field(..., description="Total number of steps")
    message: str = Field(..., description="Human-readable progress message")
    timestamp: str = Field(..., description="ISO8601 timestamp")


class SSECompletionEvent(BaseModel):
    """SSE event data for task completion."""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(default="completed", description="Task status")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result payload"
    )
    timestamp: str = Field(..., description="ISO8601 timestamp")
