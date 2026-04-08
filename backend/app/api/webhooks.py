"""
Webhooks API Router — Issue #167

Endpoints:
  POST /webhooks/register          — register a new webhook endpoint
  POST /webhooks/test              — trigger a test delivery
  GET  /webhooks/{id}/history      — delivery attempt history

Built by AINative Dev Team
Refs #167
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel

from app.services.webhook_delivery_service import (
    WebhookDeliveryService,
    webhook_delivery_service,
)

router = APIRouter(tags=["webhooks"])


def get_webhook_delivery_service() -> WebhookDeliveryService:
    """Dependency provider for WebhookDeliveryService."""
    return webhook_delivery_service


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class RegisterWebhookRequest(BaseModel):
    project_id: str
    url: str
    event_types: List[str]
    secret: str


class TestWebhookRequest(BaseModel):
    project_id: str
    event_type: str
    payload: Dict[str, Any] = {}


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #

@router.post("/register", status_code=201)
async def register_webhook(
    body: RegisterWebhookRequest,
    service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
) -> Dict[str, Any]:
    """Register a new webhook endpoint for a project."""
    return await service.register_webhook(
        project_id=body.project_id,
        url=body.url,
        event_types=body.event_types,
        secret=body.secret,
    )


@router.post("/test")
async def test_webhook(
    body: TestWebhookRequest,
    service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
) -> Dict[str, Any]:
    """Trigger a test delivery to all webhooks registered for the project/event."""
    return await service.deliver_event(
        event_type=body.event_type,
        payload=body.payload,
        project_id=body.project_id,
    )


@router.get("/{webhook_id}/history")
async def get_history(
    webhook_id: str = Path(..., description="Webhook identifier"),
    limit: int = Query(20, description="Maximum records to return"),
    service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
) -> List[Dict[str, Any]]:
    """Return delivery attempt history for a webhook."""
    return await service.get_delivery_history(
        webhook_id=webhook_id,
        limit=limit,
    )
