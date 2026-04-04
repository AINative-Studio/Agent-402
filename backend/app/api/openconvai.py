"""
OpenConvAI HCS-10 API Router.

Issues #204–#207: REST endpoints for OpenConvAI protocol operations.

Endpoints:
    POST  /hcs10/send                      — Send agent-to-agent message
    GET   /hcs10/messages/{agent_did}      — Receive messages for an agent
    POST  /hcs10/workflow                  — Initiate a multi-agent workflow
    GET   /hcs10/audit/{conversation_id}  — Retrieve message audit trail
    POST  /hcs10/discover                  — Discover agents by capability

NOTE: This router is NOT registered in main.py per FILE ISOLATION rules.
      Mount it explicitly in tests or via a separate include.

Built by AINative Dev Team
Refs #204, #205, #206, #207
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, Query

from app.schemas.openconvai import (
    SendMessageRequest,
    WorkflowRequest,
    DiscoverRequest,
)

router = APIRouter(prefix="/hcs10", tags=["openconvai"])


# ---------------------------------------------------------------------------
# Dependency injectors (overridable in tests)
# ---------------------------------------------------------------------------

def get_messaging_service():
    """Provide the OpenConvAIMessagingService singleton."""
    from app.services.openconvai_messaging_service import (
        get_openconvai_messaging_service,
    )
    return get_openconvai_messaging_service()


def get_coordination_service():
    """Provide the OpenConvAICoordinationService singleton."""
    from app.services.openconvai_coordination_service import (
        get_openconvai_coordination_service,
    )
    return get_openconvai_coordination_service()


def get_audit_service():
    """Provide the OpenConvAIAuditService singleton."""
    from app.services.openconvai_audit_service import (
        get_openconvai_audit_service,
    )
    return get_openconvai_audit_service()


def get_discovery_service():
    """Provide the OpenConvAIDiscoveryService singleton."""
    from app.services.openconvai_discovery_service import (
        get_openconvai_discovery_service,
    )
    return get_openconvai_discovery_service()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    messaging: Any = Depends(get_messaging_service),
) -> Dict[str, Any]:
    """
    Send an HCS-10 agent-to-agent message.

    Submits the message to the shared HCS topic and returns the
    Hedera transaction ID and conversation ID.
    """
    result = await messaging.send_message(
        sender_did=body.sender_did,
        recipient_did=body.recipient_did,
        message_type=body.message_type,
        payload=body.payload,
        conversation_id=body.conversation_id,
    )
    return result


@router.get("/messages/{agent_did}")
async def receive_messages(
    agent_did: str,
    since_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    messaging: Any = Depends(get_messaging_service),
) -> List[Dict[str, Any]]:
    """
    Retrieve HCS-10 messages addressed to an agent.

    Queries the mirror node for messages where recipient_did == agent_did.
    """
    messages = await messaging.receive_messages(
        agent_did=agent_did,
        since_sequence=since_sequence,
        limit=limit,
    )
    return messages


@router.post("/workflow")
async def coordinate_workflow(
    body: WorkflowRequest,
    coordination: Any = Depends(get_coordination_service),
) -> Dict[str, Any]:
    """
    Initiate a multi-agent workflow via HCS-10 coordination messages.

    Creates a workflow record and broadcasts stage assignments to each
    agent's DID.
    """
    stages = [s.model_dump() for s in body.stages]
    result = await coordination.coordinate_workflow(
        workflow_id=body.workflow_id,
        stages=stages,
    )
    return result


@router.get("/audit/{conversation_id}")
async def get_audit_trail(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    audit: Any = Depends(get_audit_service),
) -> List[Dict[str, Any]]:
    """
    Retrieve the audit trail for a conversation.

    Returns messages from hcs10_audit_trail ordered by sequence number.
    """
    trail = await audit.get_audit_trail(
        conversation_id=conversation_id,
        limit=limit,
    )
    return trail


@router.post("/discover")
async def discover_agents(
    body: DiscoverRequest,
    discovery: Any = Depends(get_discovery_service),
) -> List[Dict[str, Any]]:
    """
    Discover agents by capability via HCS-10 discovery messages.

    Queries the mirror node for agent discovery broadcasts and optionally
    filters by capability.
    """
    agents = await discovery.discover_agents(
        capability=body.capability,
        message_type=body.message_type,
    )
    return agents
