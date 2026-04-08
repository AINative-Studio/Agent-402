"""
Webhook schemas for delivery system.

Built by AINative Dev Team
Refs #167
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class WebhookConfig(BaseModel):
    """Configuration for a registered webhook endpoint."""

    webhook_id: str
    project_id: str
    url: str
    event_types: List[str] = Field(default_factory=list)
    active: bool = True


class DeliveryAttempt(BaseModel):
    """Record of a single webhook delivery attempt."""

    attempt_id: str
    webhook_id: str
    status: str
    status_code: int
    created_at: str
    response_body: Optional[str] = None


class WebhookEvent(BaseModel):
    """An event to be delivered to webhook subscribers."""

    event_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
