"""
Tests for OpenConvAI HCS-10 Audit Service.

Issue #206: Message Audit Trail stored in ZeroDB hcs10_audit_trail table.

TDD Red phase: tests define the contract for OpenConvAIAuditService
before the implementation is written.

Built by AINative Dev Team
Refs #206
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CONVERSATION_ID = "conv-audit-001"
AGENT_DID = "did:hedera:testnet:z6MkAuditAgent"
SENDER_DID = "did:hedera:testnet:z6MkSender"

SAMPLE_MESSAGE = {
    "protocol": "hcs-10",
    "version": "1.0",
    "sender_did": SENDER_DID,
    "recipient_did": AGENT_DID,
    "message_type": "text",
    "payload": {"text": "audit this"},
    "conversation_id": CONVERSATION_ID,
    "timestamp": "2026-04-03T10:00:00Z",
}


@pytest.fixture
def mock_zerodb(mock_zerodb_client):
    """Use the shared mock ZeroDB client from conftest."""
    return mock_zerodb_client


@pytest.fixture
def audit_service(mock_zerodb):
    """OpenConvAIAuditService with mock ZeroDB."""
    from app.services.openconvai_audit_service import OpenConvAIAuditService
    return OpenConvAIAuditService(zerodb_client=mock_zerodb)


# ---------------------------------------------------------------------------
# DescribeLogMessage
# ---------------------------------------------------------------------------

class DescribeLogMessage:
    """Tests for OpenConvAIAuditService.log_message."""

    @pytest.mark.asyncio
    async def it_stores_a_message_in_the_audit_table(
        self, audit_service, mock_zerodb
    ):
        """log_message inserts a row into hcs10_audit_trail."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        rows = mock_zerodb.get_table_data("hcs10_audit_trail")
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def it_returns_an_audit_entry_with_an_id(
        self, audit_service
    ):
        """log_message returns a dict with audit_id."""
        result = await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        assert "audit_id" in result
        assert result["audit_id"] is not None

    @pytest.mark.asyncio
    async def it_persists_sender_did_in_audit_row(
        self, audit_service, mock_zerodb
    ):
        """log_message records the sender_did in the stored row."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        rows = mock_zerodb.get_table_data("hcs10_audit_trail")
        assert rows[0]["sender_did"] == SENDER_DID

    @pytest.mark.asyncio
    async def it_persists_conversation_id_in_audit_row(
        self, audit_service, mock_zerodb
    ):
        """log_message records the conversation_id in the stored row."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        rows = mock_zerodb.get_table_data("hcs10_audit_trail")
        assert rows[0]["conversation_id"] == CONVERSATION_ID

    @pytest.mark.asyncio
    async def it_persists_sequence_number_in_audit_row(
        self, audit_service, mock_zerodb
    ):
        """log_message records the HCS sequence_number."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=42,
        )
        rows = mock_zerodb.get_table_data("hcs10_audit_trail")
        assert rows[0]["sequence_number"] == 42


# ---------------------------------------------------------------------------
# DescribeGetAuditTrail
# ---------------------------------------------------------------------------

class DescribeGetAuditTrail:
    """Tests for OpenConvAIAuditService.get_audit_trail."""

    @pytest.mark.asyncio
    async def it_returns_all_messages_for_a_conversation(
        self, audit_service
    ):
        """get_audit_trail returns entries matching conversation_id."""
        for i in range(3):
            msg = {**SAMPLE_MESSAGE, "timestamp": f"2026-04-03T10:0{i}:00Z"}
            await audit_service.log_message(
                message=msg,
                consensus_timestamp=f"2026-04-03T10:0{i}:00Z",
                sequence_number=i + 1,
            )
        trail = await audit_service.get_audit_trail(
            conversation_id=CONVERSATION_ID
        )
        assert len(trail) == 3

    @pytest.mark.asyncio
    async def it_excludes_messages_from_other_conversations(
        self, audit_service
    ):
        """get_audit_trail filters out messages from different conversation_ids."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        other_msg = {
            **SAMPLE_MESSAGE,
            "conversation_id": "conv-other-999",
        }
        await audit_service.log_message(
            message=other_msg,
            consensus_timestamp="2026-04-03T10:01:00Z",
            sequence_number=2,
        )
        trail = await audit_service.get_audit_trail(
            conversation_id=CONVERSATION_ID
        )
        assert len(trail) == 1
        assert trail[0]["conversation_id"] == CONVERSATION_ID

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_unknown_conversation(
        self, audit_service
    ):
        """get_audit_trail returns [] when no messages match."""
        trail = await audit_service.get_audit_trail(
            conversation_id="conv-nonexistent"
        )
        assert trail == []

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(
        self, audit_service
    ):
        """get_audit_trail returns at most `limit` entries."""
        for i in range(5):
            msg = {**SAMPLE_MESSAGE, "timestamp": f"2026-04-03T10:0{i}:00Z"}
            await audit_service.log_message(
                message=msg,
                consensus_timestamp=f"2026-04-03T10:0{i}:00Z",
                sequence_number=i + 1,
            )
        trail = await audit_service.get_audit_trail(
            conversation_id=CONVERSATION_ID, limit=3
        )
        assert len(trail) <= 3


# ---------------------------------------------------------------------------
# DescribeGetAgentAudit
# ---------------------------------------------------------------------------

class DescribeGetAgentAudit:
    """Tests for OpenConvAIAuditService.get_agent_audit."""

    @pytest.mark.asyncio
    async def it_returns_all_messages_sent_to_the_agent(
        self, audit_service
    ):
        """get_agent_audit returns entries where agent_did is sender or recipient."""
        await audit_service.log_message(
            message=SAMPLE_MESSAGE,
            consensus_timestamp="2026-04-03T10:00:00Z",
            sequence_number=1,
        )
        entries = await audit_service.get_agent_audit(agent_did=AGENT_DID)
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_unknown_agent(
        self, audit_service
    ):
        """get_agent_audit returns [] when no messages match the agent."""
        entries = await audit_service.get_agent_audit(
            agent_did="did:hedera:testnet:z6MkUnknown"
        )
        assert entries == []

    @pytest.mark.asyncio
    async def it_filters_by_since_timestamp(
        self, audit_service
    ):
        """get_agent_audit only returns entries at or after `since`."""
        await audit_service.log_message(
            message={**SAMPLE_MESSAGE, "timestamp": "2026-04-03T09:00:00Z"},
            consensus_timestamp="2026-04-03T09:00:00Z",
            sequence_number=1,
        )
        await audit_service.log_message(
            message={**SAMPLE_MESSAGE, "timestamp": "2026-04-03T11:00:00Z"},
            consensus_timestamp="2026-04-03T11:00:00Z",
            sequence_number=2,
        )
        entries = await audit_service.get_agent_audit(
            agent_did=AGENT_DID, since="2026-04-03T10:00:00Z"
        )
        for entry in entries:
            assert entry["consensus_timestamp"] >= "2026-04-03T10:00:00Z"

    @pytest.mark.asyncio
    async def it_filters_by_until_timestamp(
        self, audit_service
    ):
        """get_agent_audit only returns entries at or before `until`."""
        await audit_service.log_message(
            message={**SAMPLE_MESSAGE, "timestamp": "2026-04-03T08:00:00Z"},
            consensus_timestamp="2026-04-03T08:00:00Z",
            sequence_number=1,
        )
        await audit_service.log_message(
            message={**SAMPLE_MESSAGE, "timestamp": "2026-04-03T12:00:00Z"},
            consensus_timestamp="2026-04-03T12:00:00Z",
            sequence_number=2,
        )
        entries = await audit_service.get_agent_audit(
            agent_did=AGENT_DID, until="2026-04-03T10:00:00Z"
        )
        for entry in entries:
            assert entry["consensus_timestamp"] <= "2026-04-03T10:00:00Z"
