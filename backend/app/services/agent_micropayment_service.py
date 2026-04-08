"""
Agent Micropayment Service — agent-to-agent HBAR micropayments (Issue #268 Phase 3).

Provides a payment channel abstraction for agent-to-agent transfers:
- create_payment_channel: set up a channel between two agent DIDs
- submit_micropayment: transfer HBAR within a channel
- close_channel: settle final balance and close the channel
- get_channel_balance: query remaining balance and payment history

Uses existing hedera_client.py (READ-ONLY) for HBAR transfers.

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class AgentMicropaymentError(Exception):
    """Raised when a micropayment operation fails."""

    def __init__(self, message: str, original: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.message = message
        self.original = original


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

class _Channel:
    """In-process channel state (not persisted between restarts)."""

    def __init__(
        self,
        channel_id: str,
        sender_did: str,
        receiver_did: str,
        max_amount: float,
    ) -> None:
        self.channel_id = channel_id
        self.sender_did = sender_did
        self.receiver_did = receiver_did
        self.max_amount = max_amount
        self.status = "open"
        self.spent: float = 0.0
        self.history: List[Dict[str, Any]] = []

    @property
    def remaining(self) -> float:
        return self.max_amount - self.spent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "sender_did": self.sender_did,
            "receiver_did": self.receiver_did,
            "max_amount": self.max_amount,
            "status": self.status,
            "remaining": self.remaining,
            "spent": self.spent,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AgentMicropaymentService:
    """
    Agent-to-agent HBAR micropayment channels.

    Channels are held in memory (dict). A production version would persist
    channel state in ZeroDB or another durable store.
    """

    def __init__(self, hedera_client: Any) -> None:
        """
        Args:
            hedera_client: An async Hedera client with transfer_hbar method.
        """
        self._client = hedera_client
        self._channels: Dict[str, _Channel] = {}

    # -------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------

    async def create_payment_channel(
        self,
        sender_did: str,
        receiver_did: str,
        max_amount: float,
    ) -> Dict[str, Any]:
        """
        Set up a micropayment channel between two agent DIDs.

        Args:
            sender_did: DID of the sending agent.
            receiver_did: DID of the receiving agent.
            max_amount: Maximum total HBAR this channel can transfer.

        Returns:
            Channel dict with channel_id, status, max_amount, etc.

        Raises:
            AgentMicropaymentError: if max_amount is <= 0.
        """
        if max_amount <= 0:
            raise AgentMicropaymentError(
                f"max_amount must be positive, got {max_amount}"
            )

        channel_id = f"ch_{uuid.uuid4().hex[:16]}"
        channel = _Channel(
            channel_id=channel_id,
            sender_did=sender_did,
            receiver_did=receiver_did,
            max_amount=max_amount,
        )
        self._channels[channel_id] = channel
        return channel.to_dict()

    async def submit_micropayment(
        self,
        channel_id: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transfer HBAR within a channel.

        Args:
            channel_id: Channel to use for the transfer.
            amount: HBAR amount to transfer.
            memo: Optional memo for the transaction.

        Returns:
            dict with payment_id, status, amount, transaction_id.

        Raises:
            AgentMicropaymentError: if channel not found, closed, or amount
                exceeds remaining balance.
        """
        channel = self._channels.get(channel_id)
        if channel is None:
            raise AgentMicropaymentError(
                f"Payment channel not found: {channel_id}"
            )

        if channel.status == "closed":
            raise AgentMicropaymentError(
                f"Cannot submit payment to closed channel: {channel_id}"
            )

        if amount > channel.remaining:
            raise AgentMicropaymentError(
                f"Amount {amount} exceeds remaining channel balance {channel.remaining}"
            )

        # Perform the HBAR transfer via the Hedera client
        transfer_result = await self._client.transfer_hbar(
            sender_did=channel.sender_did,
            receiver_did=channel.receiver_did,
            amount=amount,
            memo=memo or "",
        )

        payment_id = f"pay_{uuid.uuid4().hex[:16]}"
        transaction_id = transfer_result.get("transaction_id", "")
        status = transfer_result.get("status", "SUCCESS")

        # Update channel state
        channel.spent += amount
        record: Dict[str, Any] = {
            "payment_id": payment_id,
            "channel_id": channel_id,
            "amount": amount,
            "memo": memo,
            "transaction_id": transaction_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        channel.history.append(record)

        return {
            "payment_id": payment_id,
            "channel_id": channel_id,
            "amount": amount,
            "memo": memo,
            "transaction_id": transaction_id,
            "status": status,
        }

    async def close_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Settle and close a payment channel.

        Args:
            channel_id: Channel to close.

        Returns:
            dict with status='closed' and final_balance.

        Raises:
            AgentMicropaymentError: if channel not found or already closed.
        """
        channel = self._channels.get(channel_id)
        if channel is None:
            raise AgentMicropaymentError(
                f"Payment channel not found: {channel_id}"
            )

        if channel.status == "closed":
            raise AgentMicropaymentError(
                f"Channel is already closed: {channel_id}"
            )

        channel.status = "closed"
        return {
            "channel_id": channel_id,
            "status": "closed",
            "final_balance": channel.remaining,
            "total_spent": channel.spent,
        }

    async def get_channel_balance(self, channel_id: str) -> Dict[str, Any]:
        """
        Return the current balance and payment history for a channel.

        Args:
            channel_id: Channel to query.

        Returns:
            dict with remaining, spent, history.

        Raises:
            AgentMicropaymentError: if channel not found.
        """
        channel = self._channels.get(channel_id)
        if channel is None:
            raise AgentMicropaymentError(
                f"Payment channel not found: {channel_id}"
            )

        return {
            "channel_id": channel_id,
            "status": channel.status,
            "max_amount": channel.max_amount,
            "remaining": channel.remaining,
            "spent": channel.spent,
            "history": list(channel.history),
        }


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def get_agent_micropayment_service() -> AgentMicropaymentService:
    """
    Return an AgentMicropaymentService wired to the shared Hedera client.
    """
    from app.services.hedera_client import get_hedera_client

    hedera = get_hedera_client()
    return AgentMicropaymentService(hedera_client=hedera)
