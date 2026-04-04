"""
HCS-14 Agent Directory Service.
Implements agent directory registration and discovery via HCS topics.

Issue #193: HCS-14 Directory Registration
- Register agents in the HCS-14 directory
- Query agents by capability, role, and reputation
- Update and remove directory entries
- HCS-14 message format: {type, did, capabilities, role, reputation, timestamp}

HCS-14 uses a Hedera Consensus Service topic as a shared directory ledger.
All operations submit messages to the topic; resolution replays the message
history to reconstruct current state.

Built by AINative Dev Team
Refs #193
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.errors import APIError
from app.services.hedera_hts_nft_client import (
    HederaHTSNFTClient,
    DEFAULT_DIRECTORY_TOPIC_ID,
    get_hedera_hts_nft_client,
)

logger = logging.getLogger(__name__)


class HCS14DirectoryError(APIError):
    """
    Raised when an HCS-14 directory operation fails.

    Returns:
        - HTTP 400 for validation errors
        - HTTP 502 for network errors
        - error_code: HCS14_DIRECTORY_ERROR
    """

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            error_code="HCS14_DIRECTORY_ERROR",
            detail=detail or "HCS-14 directory error",
        )


class HCS14DirectoryService:
    """
    Service for agent discovery via HCS-14 directory protocol.

    Uses a Hedera Consensus Service topic as the shared agent directory.
    All registration, update, and deregistration operations submit messages
    to the directory topic. Queries replay the message history to build
    the current directory state.

    Message format (HCS-14 spec):
    {
        "type": "register" | "update" | "deregister",
        "did": "did:hedera:testnet:...",
        "capabilities": ["chat", "memory", ...],
        "role": "analyst",
        "reputation": 100,
        "timestamp": "2026-04-03T00:00:00+00:00"
    }
    """

    def __init__(
        self,
        nft_client: Optional[HederaHTSNFTClient] = None,
        directory_topic_id: Optional[str] = None,
    ):
        """
        Initialize the HCS-14 Directory Service.

        Args:
            nft_client: Optional HTS/HCS client (lazy-initialized if None)
            directory_topic_id: Override directory topic ID
        """
        self._nft_client = nft_client
        self._directory_topic_id = directory_topic_id or DEFAULT_DIRECTORY_TOPIC_ID

    @property
    def nft_client(self) -> HederaHTSNFTClient:
        """Lazy-initialized HTS/HCS client."""
        if self._nft_client is None:
            self._nft_client = get_hedera_hts_nft_client()
        return self._nft_client

    @property
    def directory_topic_id(self) -> str:
        """HCS-14 directory topic ID."""
        return self._directory_topic_id

    async def register_agent(
        self,
        agent_did: str,
        capabilities: List[str],
        role: str,
        reputation_score: int,
    ) -> Dict[str, Any]:
        """
        Register an agent in the HCS-14 directory.

        Submits a registration message to the directory HCS topic.
        The message follows the HCS-14 format with type="register".

        Args:
            agent_did: Agent DID string (did:hedera:testnet:...)
            capabilities: List of AAP capability strings
            role: Agent role (analyst, compliance, transaction, etc.)
            reputation_score: Initial reputation score (must be >= 0)

        Returns:
            Dict with status, transaction_id, did

        Raises:
            HCS14DirectoryError: If agent_did is empty or reputation is negative
        """
        if not agent_did or not agent_did.strip():
            raise HCS14DirectoryError("agent_did cannot be empty")
        if reputation_score < 0:
            raise HCS14DirectoryError(
                f"reputation_score must be >= 0, got {reputation_score}"
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        message: Dict[str, Any] = {
            "type": "register",
            "did": agent_did,
            "capabilities": capabilities,
            "role": role,
            "reputation": reputation_score,
            "timestamp": timestamp,
        }

        logger.info(
            f"Registering agent in HCS-14 directory: did={agent_did}, role={role}"
        )

        result = await self.nft_client.submit_hcs_message(
            topic_id=self.directory_topic_id,
            message=message,
        )

        return {
            "status": result.get("status", "SUCCESS"),
            "transaction_id": result.get("transaction_id"),
            "did": agent_did,
        }

    async def query_directory(
        self,
        capability: Optional[str] = None,
        role: Optional[str] = None,
        min_reputation: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Query the HCS-14 agent directory.

        Retrieves all messages from the directory topic and reconstructs
        the current agent list. Applies optional filters for capability,
        role, and minimum reputation score.

        Only the latest registration state for each DID is returned
        (deregistered agents are excluded).

        Args:
            capability: Filter to agents with this capability
            role: Filter to agents with this role
            min_reputation: Filter to agents with reputation >= this value

        Returns:
            Dict with agents list (each entry has did, capabilities, role, reputation)
        """
        logger.info(
            f"Querying HCS-14 directory: capability={capability}, "
            f"role={role}, min_reputation={min_reputation}"
        )

        result = await self.nft_client.get_hcs_messages(
            topic_id=self.directory_topic_id,
            limit=500,
            order="asc",
        )

        messages = result.get("messages", [])

        # Replay messages to build current directory state
        # key = agent DID, value = latest registration entry
        directory: Dict[str, Dict[str, Any]] = {}

        for msg_entry in messages:
            raw_message = msg_entry.get("message", "")
            consensus_ts = msg_entry.get("consensus_timestamp")

            # Messages stored as base64 in the mirror node
            try:
                decoded = base64.b64decode(raw_message).decode("utf-8")
                msg_data = json.loads(decoded)
            except Exception:
                # Skip malformed messages
                continue

            msg_type = msg_data.get("type", "")
            did = msg_data.get("did", "")

            if not did:
                continue

            if msg_type == "register":
                directory[did] = {
                    "did": did,
                    "capabilities": msg_data.get("capabilities", []),
                    "role": msg_data.get("role", ""),
                    "reputation": msg_data.get("reputation", 0),
                    "registered_at": msg_data.get("timestamp"),
                    "consensus_timestamp": consensus_ts,
                }

            elif msg_type == "update":
                if did in directory:
                    updates = {
                        k: v
                        for k, v in msg_data.items()
                        if k not in ("type", "did", "timestamp")
                    }
                    directory[did].update(updates)

            elif msg_type in ("deregister", "remove"):
                directory.pop(did, None)

        agents = list(directory.values())

        # Apply filters
        if capability is not None:
            agents = [a for a in agents if capability in a.get("capabilities", [])]
        if role is not None:
            agents = [a for a in agents if a.get("role") == role]
        if min_reputation is not None:
            agents = [a for a in agents if a.get("reputation", 0) >= min_reputation]

        return {"agents": agents}

    async def update_registration(
        self,
        agent_did: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an agent's directory entry.

        Submits an update message to the HCS topic. The next query
        will incorporate these updates into the agent's entry.

        Args:
            agent_did: Agent DID string to update
            updates: Dict of fields to update (must be non-empty)

        Returns:
            Dict with status, transaction_id

        Raises:
            HCS14DirectoryError: If updates dict is empty
        """
        if not updates:
            raise HCS14DirectoryError("Registration updates cannot be empty")

        timestamp = datetime.now(timezone.utc).isoformat()
        message: Dict[str, Any] = {
            "type": "update",
            "did": agent_did,
            "timestamp": timestamp,
            **updates,
        }

        logger.info(f"Updating directory registration: did={agent_did}")

        result = await self.nft_client.submit_hcs_message(
            topic_id=self.directory_topic_id,
            message=message,
        )

        return {
            "status": result.get("status", "SUCCESS"),
            "transaction_id": result.get("transaction_id"),
            "did": agent_did,
        }

    async def deregister_agent(
        self,
        agent_did: str,
    ) -> Dict[str, Any]:
        """
        Remove an agent from the directory.

        Submits a deregister message to the HCS topic. After this,
        queries will no longer return this agent.

        Args:
            agent_did: Agent DID string to remove

        Returns:
            Dict with status, transaction_id

        Raises:
            HCS14DirectoryError: If agent_did is empty
        """
        if not agent_did or not agent_did.strip():
            raise HCS14DirectoryError("agent_did cannot be empty")

        timestamp = datetime.now(timezone.utc).isoformat()
        message: Dict[str, Any] = {
            "type": "deregister",
            "did": agent_did,
            "timestamp": timestamp,
        }

        logger.info(f"Deregistering agent from directory: did={agent_did}")

        result = await self.nft_client.submit_hcs_message(
            topic_id=self.directory_topic_id,
            message=message,
        )

        return {
            "status": result.get("status", "SUCCESS"),
            "transaction_id": result.get("transaction_id"),
            "did": agent_did,
        }


# Global service instance
hcs14_directory_service = HCS14DirectoryService()


def get_hcs14_directory_service() -> HCS14DirectoryService:
    """
    Get the global HCS14DirectoryService instance.

    Returns:
        Configured HCS14DirectoryService instance
    """
    return hcs14_directory_service
