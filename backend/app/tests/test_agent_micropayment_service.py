"""
Tests for AgentMicropaymentService (Issue #268 Phase 3).

Covers:
- create_payment_channel: set up micropayment channel between two agents
- submit_micropayment: agent-to-agent HBAR transfer
- close_channel: settle final balance
- get_channel_balance: current balance and history

TDD Cycle: RED -> GREEN -> REFACTOR
BDD-style: class DescribeX / def it_does_something

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent_micropayment_service import (
    AgentMicropaymentService,
    AgentMicropaymentError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_hedera_client: Optional[AsyncMock] = None) -> tuple[AgentMicropaymentService, AsyncMock]:
    """Return a (service, mock_client) pair."""
    if mock_hedera_client is None:
        mock_hedera_client = AsyncMock()
    service = AgentMicropaymentService(hedera_client=mock_hedera_client)
    return service, mock_hedera_client


# ===========================================================================
# create_payment_channel
# ===========================================================================

class DescribeCreatePaymentChannel:
    """Tests for AgentMicropaymentService.create_payment_channel."""

    @pytest.mark.asyncio
    async def it_creates_a_channel_and_returns_a_channel_id(self):
        """
        Arrange: service with mock hedera client.
        Act: create_payment_channel with two agent DIDs and max_amount.
        Assert: result contains channel_id.
        """
        service, _ = _make_service()

        result = await service.create_payment_channel(
            sender_did="did:hedera:testnet:agent-sender",
            receiver_did="did:hedera:testnet:agent-receiver",
            max_amount=100.0,
        )

        assert "channel_id" in result
        assert result["channel_id"].startswith("ch_")

    @pytest.mark.asyncio
    async def it_stores_sender_and_receiver_in_the_channel(self):
        """
        Arrange: service.
        Act: create_payment_channel.
        Assert: returned channel includes sender_did and receiver_did.
        """
        service, _ = _make_service()

        result = await service.create_payment_channel(
            sender_did="did:hedera:testnet:sender-1",
            receiver_did="did:hedera:testnet:receiver-1",
            max_amount=50.0,
        )

        assert result["sender_did"] == "did:hedera:testnet:sender-1"
        assert result["receiver_did"] == "did:hedera:testnet:receiver-1"

    @pytest.mark.asyncio
    async def it_stores_max_amount_in_the_channel(self):
        """
        Arrange: service.
        Act: create_payment_channel with max_amount=200.0.
        Assert: returned channel includes max_amount=200.0.
        """
        service, _ = _make_service()

        result = await service.create_payment_channel(
            sender_did="did:hedera:testnet:a",
            receiver_did="did:hedera:testnet:b",
            max_amount=200.0,
        )

        assert result["max_amount"] == 200.0

    @pytest.mark.asyncio
    async def it_initializes_channel_with_open_status(self):
        """
        Arrange: service.
        Act: create_payment_channel.
        Assert: channel status is 'open'.
        """
        service, _ = _make_service()

        result = await service.create_payment_channel(
            sender_did="did:hedera:testnet:a",
            receiver_did="did:hedera:testnet:b",
            max_amount=100.0,
        )

        assert result["status"] == "open"

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_when_max_amount_is_zero(self):
        """
        Arrange: service.
        Act: create_payment_channel with max_amount=0.
        Assert: AgentMicropaymentError raised.
        """
        service, _ = _make_service()

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.create_payment_channel(
                sender_did="did:hedera:testnet:a",
                receiver_did="did:hedera:testnet:b",
                max_amount=0,
            )

        assert "max_amount" in str(exc_info.value).lower()


# ===========================================================================
# submit_micropayment
# ===========================================================================

class DescribeSubmitMicropayment:
    """Tests for AgentMicropaymentService.submit_micropayment."""

    @pytest.mark.asyncio
    async def it_transfers_hbar_and_returns_a_payment_id(self):
        """
        Arrange: open channel and mock hedera client transfer.
        Act: submit_micropayment.
        Assert: result contains payment_id and status SUCCESS.
        """
        service, mock_client = _make_service()
        mock_client.transfer_hbar = AsyncMock(return_value={
            "transaction_id": "txn-micro-001",
            "status": "SUCCESS",
        })

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:sender",
            receiver_did="did:hedera:testnet:receiver",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]

        result = await service.submit_micropayment(
            channel_id=channel_id,
            amount=5.0,
            memo="task fee",
        )

        assert "payment_id" in result
        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_deducts_amount_from_remaining_channel_balance(self):
        """
        Arrange: channel with max_amount=100.
        Act: submit_micropayment of 30.
        Assert: channel remaining balance is 70.
        """
        service, mock_client = _make_service()
        mock_client.transfer_hbar = AsyncMock(return_value={
            "transaction_id": "txn-micro-002",
            "status": "SUCCESS",
        })

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]

        await service.submit_micropayment(channel_id=channel_id, amount=30.0, memo="fee")

        balance = await service.get_channel_balance(channel_id)
        assert balance["remaining"] == 70.0

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_when_amount_exceeds_remaining(self):
        """
        Arrange: channel with max_amount=50.
        Act: submit_micropayment of 60.
        Assert: AgentMicropaymentError raised.
        """
        service, mock_client = _make_service()

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=50.0,
        )
        channel_id = channel["channel_id"]

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.submit_micropayment(channel_id=channel_id, amount=60.0, memo="too much")

        assert "exceeds" in str(exc_info.value).lower() or "insufficient" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_for_closed_channel(self):
        """
        Arrange: closed channel.
        Act: submit_micropayment.
        Assert: AgentMicropaymentError raised.
        """
        service, mock_client = _make_service()
        mock_client.transfer_hbar = AsyncMock(return_value={"transaction_id": "t1", "status": "SUCCESS"})

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]
        await service.close_channel(channel_id)

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.submit_micropayment(channel_id=channel_id, amount=1.0, memo="after close")

        assert "closed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_for_unknown_channel(self):
        """
        Arrange: service with no channels.
        Act: submit_micropayment with non-existent channel_id.
        Assert: AgentMicropaymentError raised.
        """
        service, _ = _make_service()

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.submit_micropayment(channel_id="ch_nonexistent", amount=1.0, memo="test")

        assert "not found" in str(exc_info.value).lower()


# ===========================================================================
# close_channel
# ===========================================================================

class DescribeCloseChannel:
    """Tests for AgentMicropaymentService.close_channel."""

    @pytest.mark.asyncio
    async def it_closes_the_channel_and_returns_final_balance(self):
        """
        Arrange: open channel with some payments.
        Act: close_channel.
        Assert: result contains final_balance and status='closed'.
        """
        service, mock_client = _make_service()
        mock_client.transfer_hbar = AsyncMock(return_value={"transaction_id": "t1", "status": "SUCCESS"})

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]
        await service.submit_micropayment(channel_id=channel_id, amount=25.0, memo="payment 1")

        result = await service.close_channel(channel_id)

        assert result["status"] == "closed"
        assert "final_balance" in result
        assert result["final_balance"] == 75.0

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_for_already_closed_channel(self):
        """
        Arrange: already closed channel.
        Act: close_channel again.
        Assert: AgentMicropaymentError raised.
        """
        service, _ = _make_service()

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]
        await service.close_channel(channel_id)

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.close_channel(channel_id)

        assert "closed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_for_unknown_channel(self):
        """
        Arrange: service with no channels.
        Act: close_channel with unknown id.
        Assert: AgentMicropaymentError raised.
        """
        service, _ = _make_service()

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.close_channel("ch_ghost")

        assert "not found" in str(exc_info.value).lower()


# ===========================================================================
# get_channel_balance
# ===========================================================================

class DescribeGetChannelBalance:
    """Tests for AgentMicropaymentService.get_channel_balance."""

    @pytest.mark.asyncio
    async def it_returns_full_balance_for_channel_with_no_payments(self):
        """
        Arrange: open channel with max_amount=100, no payments.
        Act: get_channel_balance.
        Assert: remaining=100 and spent=0.
        """
        service, _ = _make_service()

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]

        result = await service.get_channel_balance(channel_id)

        assert result["remaining"] == 100.0
        assert result["spent"] == 0.0
        assert result["history"] == []

    @pytest.mark.asyncio
    async def it_returns_correct_history_after_multiple_payments(self):
        """
        Arrange: channel with two micropayments.
        Act: get_channel_balance.
        Assert: history has 2 entries, remaining is correct.
        """
        service, mock_client = _make_service()
        mock_client.transfer_hbar = AsyncMock(return_value={"transaction_id": "t1", "status": "SUCCESS"})

        channel = await service.create_payment_channel(
            sender_did="did:hedera:testnet:s",
            receiver_did="did:hedera:testnet:r",
            max_amount=100.0,
        )
        channel_id = channel["channel_id"]

        await service.submit_micropayment(channel_id=channel_id, amount=10.0, memo="first")
        await service.submit_micropayment(channel_id=channel_id, amount=20.0, memo="second")

        result = await service.get_channel_balance(channel_id)

        assert result["remaining"] == 70.0
        assert result["spent"] == 30.0
        assert len(result["history"]) == 2

    @pytest.mark.asyncio
    async def it_raises_agent_micropayment_error_for_unknown_channel(self):
        """
        Arrange: service with no channels.
        Act: get_channel_balance.
        Assert: AgentMicropaymentError raised.
        """
        service, _ = _make_service()

        with pytest.raises(AgentMicropaymentError) as exc_info:
            await service.get_channel_balance("ch_unknown")

        assert "not found" in str(exc_info.value).lower()
