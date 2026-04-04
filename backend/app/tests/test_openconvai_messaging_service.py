"""
Tests for OpenConvAI HCS-10 Messaging Service.

Issue #204: Agent-to-Agent Messaging via HCS-10 (OpenConvAI protocol).

TDD Red phase: these tests define the expected contract for
OpenConvAIMessagingService before implementation exists.

Built by AINative Dev Team
Refs #204
"""
from __future__ import annotations

import pytest
import uuid
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SENDER_DID = "did:hedera:testnet:z6Mksender123"
RECIPIENT_DID = "did:hedera:testnet:z6Mkrecipient456"
AGENT_DID = "did:hedera:testnet:z6Mkagent789"


@pytest.fixture
def mock_hedera_client():
    """Mock HederaClient for isolation."""
    client = AsyncMock()
    client.submit_topic_message = AsyncMock(return_value={
        "transaction_id": "0.0.12345@1234567890.000000000",
        "status": "SUCCESS",
        "sequence_number": 1,
        "consensus_timestamp": "2026-04-03T12:00:00Z",
    })
    client.get_topic_messages = AsyncMock(return_value={
        "messages": [
            {
                "sequence_number": 1,
                "consensus_timestamp": "2026-04-03T12:00:00Z",
                "message": (
                    '{"protocol":"hcs-10","version":"1.0",'
                    f'"sender_did":"{SENDER_DID}",'
                    f'"recipient_did":"{AGENT_DID}",'
                    '"message_type":"text","payload":{"text":"hello"},'
                    '"conversation_id":"conv-abc","timestamp":"2026-04-03T12:00:00Z"}'
                ),
            }
        ]
    })
    return client


@pytest.fixture
def messaging_service(mock_hedera_client):
    """OpenConvAIMessagingService with mocked Hedera client."""
    from app.services.openconvai_messaging_service import OpenConvAIMessagingService
    return OpenConvAIMessagingService(hedera_client=mock_hedera_client)


# ---------------------------------------------------------------------------
# DescribeSendMessage
# ---------------------------------------------------------------------------

class DescribeSendMessage:
    """Tests for OpenConvAIMessagingService.send_message."""

    @pytest.mark.asyncio
    async def it_sends_a_text_message_and_returns_transaction_id(
        self, messaging_service
    ):
        """send_message returns a dict with transaction_id on success."""
        result = await messaging_service.send_message(
            sender_did=SENDER_DID,
            recipient_did=RECIPIENT_DID,
            message_type="text",
            payload={"text": "hello agent"},
            conversation_id="conv-001",
        )
        assert "transaction_id" in result

    @pytest.mark.asyncio
    async def it_includes_hcs10_protocol_fields_in_submitted_message(
        self, messaging_service, mock_hedera_client
    ):
        """send_message submits a message with correct HCS-10 protocol fields."""
        await messaging_service.send_message(
            sender_did=SENDER_DID,
            recipient_did=RECIPIENT_DID,
            message_type="task_request",
            payload={"task": "analyze"},
            conversation_id="conv-002",
        )
        mock_hedera_client.submit_topic_message.assert_awaited_once()
        submitted_args = mock_hedera_client.submit_topic_message.call_args
        message_body = submitted_args[1].get("message") or submitted_args[0][1]
        import json
        parsed = json.loads(message_body)
        assert parsed["protocol"] == "hcs-10"
        assert parsed["version"] == "1.0"
        assert parsed["sender_did"] == SENDER_DID
        assert parsed["recipient_did"] == RECIPIENT_DID
        assert parsed["message_type"] == "task_request"
        assert "timestamp" in parsed
        assert "conversation_id" in parsed

    @pytest.mark.asyncio
    async def it_accepts_all_valid_message_types(self, messaging_service):
        """send_message succeeds for every defined message_type."""
        valid_types = ["text", "task_request", "task_result", "coordination", "discovery"]
        for msg_type in valid_types:
            result = await messaging_service.send_message(
                sender_did=SENDER_DID,
                recipient_did=RECIPIENT_DID,
                message_type=msg_type,
                payload={},
                conversation_id=f"conv-{msg_type}",
            )
            assert "transaction_id" in result

    @pytest.mark.asyncio
    async def it_generates_conversation_id_when_not_provided(
        self, messaging_service
    ):
        """send_message generates a conversation_id when None is passed."""
        result = await messaging_service.send_message(
            sender_did=SENDER_DID,
            recipient_did=RECIPIENT_DID,
            message_type="text",
            payload={"text": "auto-id test"},
            conversation_id=None,
        )
        assert "conversation_id" in result
        assert result["conversation_id"] is not None


# ---------------------------------------------------------------------------
# DescribeReceiveMessages
# ---------------------------------------------------------------------------

class DescribeReceiveMessages:
    """Tests for OpenConvAIMessagingService.receive_messages."""

    @pytest.mark.asyncio
    async def it_returns_messages_addressed_to_agent(
        self, messaging_service
    ):
        """receive_messages returns a list of decoded HCS-10 messages for the agent."""
        messages = await messaging_service.receive_messages(agent_did=AGENT_DID)
        assert isinstance(messages, list)
        assert len(messages) > 0

    @pytest.mark.asyncio
    async def it_filters_to_only_messages_for_the_requested_agent(
        self, messaging_service
    ):
        """receive_messages excludes messages not addressed to agent_did."""
        messages = await messaging_service.receive_messages(agent_did=AGENT_DID)
        for msg in messages:
            assert msg["recipient_did"] == AGENT_DID

    @pytest.mark.asyncio
    async def it_respects_the_since_sequence_parameter(
        self, messaging_service, mock_hedera_client
    ):
        """receive_messages passes since_sequence to the mirror node query."""
        await messaging_service.receive_messages(
            agent_did=AGENT_DID, since_sequence=10
        )
        mock_hedera_client.get_topic_messages.assert_awaited_once()
        call_kwargs = mock_hedera_client.get_topic_messages.call_args[1]
        assert call_kwargs.get("since_sequence") == 10

    @pytest.mark.asyncio
    async def it_respects_the_limit_parameter(
        self, messaging_service, mock_hedera_client
    ):
        """receive_messages passes limit to the mirror node query."""
        await messaging_service.receive_messages(
            agent_did=AGENT_DID, limit=25
        )
        call_kwargs = mock_hedera_client.get_topic_messages.call_args[1]
        assert call_kwargs.get("limit") == 25

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_messages_exist(
        self, messaging_service, mock_hedera_client
    ):
        """receive_messages returns [] when mirror node returns no messages."""
        mock_hedera_client.get_topic_messages.return_value = {"messages": []}
        messages = await messaging_service.receive_messages(agent_did=AGENT_DID)
        assert messages == []


# ---------------------------------------------------------------------------
# DescribeCreateConversation
# ---------------------------------------------------------------------------

class DescribeCreateConversation:
    """Tests for OpenConvAIMessagingService.create_conversation."""

    @pytest.mark.asyncio
    async def it_returns_a_conversation_with_an_id(
        self, messaging_service
    ):
        """create_conversation returns a dict with a conversation_id."""
        result = await messaging_service.create_conversation(
            initiator_did=SENDER_DID,
            participant_dids=[RECIPIENT_DID],
            topic="Market Analysis",
        )
        assert "conversation_id" in result
        assert result["conversation_id"] is not None

    @pytest.mark.asyncio
    async def it_includes_all_participants_in_the_conversation(
        self, messaging_service
    ):
        """create_conversation stores all participants including the initiator."""
        result = await messaging_service.create_conversation(
            initiator_did=SENDER_DID,
            participant_dids=[RECIPIENT_DID, AGENT_DID],
            topic="Multi-party workflow",
        )
        participants = result["participants"]
        assert SENDER_DID in participants
        assert RECIPIENT_DID in participants
        assert AGENT_DID in participants

    @pytest.mark.asyncio
    async def it_broadcasts_a_coordination_message_on_creation(
        self, messaging_service, mock_hedera_client
    ):
        """create_conversation sends an HCS-10 coordination message."""
        await messaging_service.create_conversation(
            initiator_did=SENDER_DID,
            participant_dids=[RECIPIENT_DID],
            topic="New conversation",
        )
        mock_hedera_client.submit_topic_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def it_sets_status_to_active(self, messaging_service):
        """create_conversation returns a conversation with status 'active'."""
        result = await messaging_service.create_conversation(
            initiator_did=SENDER_DID,
            participant_dids=[RECIPIENT_DID],
            topic="Active check",
        )
        assert result["status"] == "active"
