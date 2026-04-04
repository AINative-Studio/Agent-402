"""
OpenConvAI HCS-10 Messaging Service.

Issue #204: Agent-to-Agent Messaging via HCS-10 (OpenConvAI protocol).

Provides:
- send_message    — submit HCS-10 message to the shared topic
- receive_messages — poll mirror node for messages addressed to an agent
- create_conversation — create a new conversation thread

HCS-10 message format:
    {protocol, version, sender_did, recipient_did, message_type,
     payload, conversation_id, timestamp}

Valid message_types: text | task_request | task_result | coordination | discovery

Built by AINative Dev Team
Refs #204
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Shared HCS topic for OpenConvAI messages (configurable via env)
import os
HCS10_SHARED_TOPIC_ID = os.getenv("HCS10_TOPIC_ID", "0.0.5000000")

VALID_MESSAGE_TYPES = frozenset(
    ["text", "task_request", "task_result", "coordination", "discovery"]
)
HEARTBEAT_WINDOW_SECONDS = 300  # 5 minutes


class OpenConvAIMessagingService:
    """
    Handles HCS-10 agent-to-agent messaging over Hedera Consensus Service.

    All messages follow the OpenConvAI HCS-10 protocol format and are
    submitted to / read from a shared HCS topic.
    """

    def __init__(self, hedera_client: Any = None):
        """
        Initialise the messaging service.

        Args:
            hedera_client: HederaClient instance (injected for testability).
                           If None, a default client is created from env vars.
        """
        if hedera_client is not None:
            self._hedera = hedera_client
        else:
            from app.services.hedera_client import get_hedera_client
            self._hedera = get_hedera_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_message(
        self,
        sender_did: str,
        recipient_did: str,
        message_type: str,
        payload: Dict[str, Any],
        conversation_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Submit an HCS-10 message to the shared topic.

        Args:
            sender_did:       DID of the sending agent.
            recipient_did:    DID of the recipient agent.
            message_type:     One of text | task_request | task_result |
                              coordination | discovery.
            payload:          Arbitrary message payload dict.
            conversation_id:  Conversation thread ID; auto-generated when None.

        Returns:
            Dict with transaction_id, status, conversation_id, and sequence_number.
        """
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:16]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        envelope: Dict[str, Any] = {
            "protocol": "hcs-10",
            "version": "1.0",
            "sender_did": sender_did,
            "recipient_did": recipient_did,
            "message_type": message_type,
            "payload": payload,
            "conversation_id": conv_id,
            "timestamp": timestamp,
        }

        message_json = json.dumps(envelope)

        logger.info(
            "Sending HCS-10 message",
            extra={
                "sender_did": sender_did,
                "recipient_did": recipient_did,
                "message_type": message_type,
                "conversation_id": conv_id,
            },
        )

        receipt = await self._hedera.submit_topic_message(
            topic_id=HCS10_SHARED_TOPIC_ID,
            message=message_json,
        )

        return {
            "transaction_id": receipt.get("transaction_id"),
            "status": receipt.get("status", "SUCCESS"),
            "conversation_id": conv_id,
            "sequence_number": receipt.get("sequence_number"),
            "consensus_timestamp": receipt.get("consensus_timestamp"),
        }

    async def receive_messages(
        self,
        agent_did: str,
        since_sequence: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Poll the mirror node for HCS-10 messages addressed to agent_did.

        Args:
            agent_did:       DID of the receiving agent.
            since_sequence:  Only return messages after this sequence number.
            limit:           Maximum messages to return.

        Returns:
            List of decoded HCS-10 message dicts where recipient_did == agent_did.
        """
        logger.info(
            "Polling HCS-10 messages",
            extra={
                "agent_did": agent_did,
                "since_sequence": since_sequence,
                "limit": limit,
            },
        )

        raw = await self._hedera.get_topic_messages(
            topic_id=HCS10_SHARED_TOPIC_ID,
            since_sequence=since_sequence,
            limit=limit,
        )

        messages: List[Dict[str, Any]] = []
        for item in raw.get("messages", []):
            try:
                envelope = json.loads(item["message"])
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to decode HCS-10 message: %s", item)
                continue

            # Filter to only messages addressed to this agent
            if envelope.get("recipient_did") != agent_did:
                continue

            # Enrich with HCS metadata
            envelope["sequence_number"] = item.get("sequence_number")
            envelope["consensus_timestamp"] = item.get("consensus_timestamp")
            messages.append(envelope)

        return messages

    async def create_conversation(
        self,
        initiator_did: str,
        participant_dids: List[str],
        topic: str,
    ) -> Dict[str, Any]:
        """
        Create a new HCS-10 conversation thread.

        Broadcasts a coordination message to initialise the thread and
        returns the conversation record.

        Args:
            initiator_did:    DID of the conversation initiator.
            participant_dids: List of participant DIDs (excluding initiator).
            topic:            Human-readable conversation topic.

        Returns:
            Conversation dict with conversation_id, participants, status.
        """
        conversation_id = f"conv-{uuid.uuid4().hex[:16]}"
        all_participants = [initiator_did] + [
            did for did in participant_dids if did != initiator_did
        ]
        timestamp = datetime.now(timezone.utc).isoformat()

        # Broadcast a coordination message to kick off the thread
        await self.send_message(
            sender_did=initiator_did,
            recipient_did=initiator_did,  # self-addressed broadcast
            message_type="coordination",
            payload={
                "action": "conversation_created",
                "topic": topic,
                "participants": all_participants,
            },
            conversation_id=conversation_id,
        )

        logger.info(
            "Created HCS-10 conversation",
            extra={
                "conversation_id": conversation_id,
                "initiator_did": initiator_did,
                "participants": all_participants,
                "topic": topic,
            },
        )

        return {
            "conversation_id": conversation_id,
            "initiator_did": initiator_did,
            "participants": all_participants,
            "topic": topic,
            "status": "active",
            "created_at": timestamp,
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_messaging_service: Optional[OpenConvAIMessagingService] = None


def get_openconvai_messaging_service() -> OpenConvAIMessagingService:
    """Return the shared OpenConvAIMessagingService singleton."""
    global _messaging_service
    if _messaging_service is None:
        _messaging_service = OpenConvAIMessagingService()
    return _messaging_service
