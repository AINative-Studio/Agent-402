"""
Hedera DID Service.
Implements did:hedera DID Integration via Hedera Consensus Service (HCS).

Issue #192: did:hedera DID Integration
- Create DID Documents on HCS topics
- DID format: did:hedera:testnet:{account_id}_{topic_id}
- Resolve DID to agent metadata (W3C DID Document format)
- Update DID Documents via HCS topic messages
- Revoke DIDs by submitting deactivation messages

DID Documents follow the W3C DID Core specification:
https://www.w3.org/TR/did-core/

Built by AINative Dev Team
Refs #192
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
    get_hedera_hts_nft_client,
)

logger = logging.getLogger(__name__)

# Valid DID prefix
DID_PREFIX = "did:hedera:"


class HederaDIDError(APIError):
    """
    Raised when a Hedera DID operation fails.

    Returns:
        - HTTP 400 for validation errors
        - HTTP 502 for network/service errors
        - error_code: HEDERA_DID_ERROR
    """

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            error_code="HEDERA_DID_ERROR",
            detail=detail or "Hedera DID error",
        )


class HederaDIDNotFoundError(HederaDIDError):
    """
    Raised when a DID cannot be resolved (no HCS messages found).

    Returns:
        - HTTP 404 (Not Found)
        - error_code: HEDERA_DID_ERROR
    """

    def __init__(self, did_string: str):
        super().__init__(
            detail=f"DID not found: {did_string}",
            status_code=404,
        )
        self.did_string = did_string


def _parse_did(did_string: str) -> tuple:
    """
    Parse a did:hedera DID string into (network, account_id, topic_id).

    Format: did:hedera:{network}:{account_id}_{topic_id}

    Args:
        did_string: DID string to parse

    Returns:
        Tuple of (network, account_id, topic_id)

    Raises:
        HederaDIDError: If the DID format is invalid
    """
    if not did_string or not did_string.startswith(DID_PREFIX):
        raise HederaDIDError(
            f"Invalid DID format: '{did_string}'. "
            f"Expected format: did:hedera:{{network}}:{{account_id}}_{{topic_id}}"
        )

    rest = did_string[len(DID_PREFIX):]
    parts = rest.split(":", 1)
    if len(parts) != 2:
        raise HederaDIDError(
            f"Invalid DID format: missing network or identifier in '{did_string}'"
        )

    network = parts[0]
    identifier = parts[1]

    if "_" not in identifier:
        raise HederaDIDError(
            f"Invalid DID identifier: '{identifier}'. "
            f"Expected format: {{account_id}}_{{topic_id}}"
        )

    account_id, topic_id = identifier.split("_", 1)

    if not account_id or not topic_id:
        raise HederaDIDError(
            f"Invalid DID: account_id or topic_id is empty in '{did_string}'"
        )

    return network, account_id, topic_id


def _build_did_document(
    did_string: str,
    account_id: str,
    updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a minimal W3C-compliant DID Document.

    Args:
        did_string: The DID string
        account_id: Hedera account ID (controller)
        updates: Optional fields to merge into the base document

    Returns:
        W3C DID Document dict
    """
    doc: Dict[str, Any] = {
        "id": did_string,
        "controller": did_string,
        "verificationMethod": [
            {
                "id": f"{did_string}#key-1",
                "type": "Ed25519VerificationKey2018",
                "controller": did_string,
                "publicKeyBase58": "",  # populated in production
            }
        ],
        "authentication": [f"{did_string}#key-1"],
        "service": [],
    }

    if updates:
        for key, value in updates.items():
            doc[key] = value

    return doc


class HederaDIDService:
    """
    Service for managing agent DIDs via Hedera Consensus Service.

    Each agent DID is anchored to an HCS topic. DID Documents and updates
    are stored as HCS messages, providing a tamper-evident audit trail.

    DID format: did:hedera:testnet:{account_id}_{topic_id}
    """

    def __init__(
        self,
        nft_client: Optional[HederaHTSNFTClient] = None,
    ):
        """
        Initialize the Hedera DID Service.

        Args:
            nft_client: Optional HTS/HCS client (lazy-initialized if None)
        """
        self._nft_client = nft_client

    @property
    def nft_client(self) -> HederaHTSNFTClient:
        """Lazy-initialized HTS/HCS client."""
        if self._nft_client is None:
            self._nft_client = get_hedera_hts_nft_client()
        return self._nft_client

    async def create_did(
        self,
        account_id: str,
        topic_id: str,
    ) -> Dict[str, Any]:
        """
        Create a DID Document on an HCS topic.

        Submits the initial DID Document as an HCS message to the
        specified topic. The DID string is derived from the account
        and topic IDs.

        Format: did:hedera:testnet:{account_id}_{topic_id}

        Args:
            account_id: Hedera account ID for this DID
            topic_id: HCS topic ID where the DID Document is stored

        Returns:
            Dict with did, did_document, transaction_id, status

        Raises:
            HederaDIDError: If account_id or topic_id is empty
        """
        if not account_id or not account_id.strip():
            raise HederaDIDError("account_id cannot be empty")
        if not topic_id or not topic_id.strip():
            raise HederaDIDError("topic_id cannot be empty")

        # Construct DID string — use client network if available, else testnet
        try:
            network = self.nft_client.hedera_client.network
            if not isinstance(network, str) or not network:
                network = "testnet"
        except Exception:
            network = "testnet"
        did_string = f"did:hedera:{network}:{account_id}_{topic_id}"

        # Build W3C DID Document
        did_document = _build_did_document(did_string, account_id)

        # Publish to HCS
        timestamp = datetime.now(timezone.utc).isoformat()
        hcs_message = {
            "type": "create",
            "did": did_string,
            "document": did_document,
            "timestamp": timestamp,
        }

        logger.info(f"Creating DID: {did_string}")

        result = await self.nft_client.submit_hcs_message(
            topic_id=topic_id,
            message=hcs_message,
        )

        return {
            "did": did_string,
            "did_document": did_document,
            "transaction_id": result.get("transaction_id"),
            "status": result.get("status", "SUCCESS"),
        }

    async def resolve_did(
        self,
        did_string: str,
    ) -> Dict[str, Any]:
        """
        Resolve a DID string to its current DID Document.

        Queries the HCS topic for messages and reconstructs the
        DID Document from the message history (last create/update wins).

        Args:
            did_string: DID to resolve (did:hedera:testnet:...)

        Returns:
            Dict with did_document and metadata

        Raises:
            HederaDIDError: If the DID format is invalid
            HederaDIDNotFoundError: If no messages are found for this DID
        """
        network, account_id, topic_id = _parse_did(did_string)

        logger.info(f"Resolving DID: {did_string}")

        result = await self.nft_client.get_hcs_messages(
            topic_id=topic_id,
            limit=100,
            order="asc",
        )

        messages = result.get("messages", [])
        if not messages:
            raise HederaDIDNotFoundError(did_string)

        # Reconstruct current DID Document from message history
        did_document = _build_did_document(did_string, account_id)
        created_at: Optional[str] = None
        updated_at: Optional[str] = None
        deactivated = False

        for msg_entry in messages:
            raw_message = msg_entry.get("message", "")
            consensus_ts = msg_entry.get("consensus_timestamp")

            # Messages are base64-encoded by the mirror node
            try:
                decoded = base64.b64decode(raw_message).decode("utf-8")
                msg_data = json.loads(decoded)
            except Exception:
                continue

            msg_type = msg_data.get("type", "")

            if msg_type == "create":
                did_document = msg_data.get("document", did_document)
                created_at = msg_data.get("timestamp") or consensus_ts

            elif msg_type == "update":
                updates = msg_data.get("updates", {})
                for key, value in updates.items():
                    did_document[key] = value
                updated_at = msg_data.get("timestamp") or consensus_ts

            elif msg_type in ("deactivate", "revoke"):
                deactivated = True
                updated_at = msg_data.get("timestamp") or consensus_ts

        return {
            "did_document": did_document,
            "metadata": {
                "created": created_at,
                "updated": updated_at,
                "deactivated": deactivated,
            },
        }

    async def update_did_document(
        self,
        did_string: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Submit a DID Document update to the HCS topic.

        The update is appended as a new message; resolution replays
        all messages and applies updates in order.

        Args:
            did_string: DID to update
            updates: Dict of fields to update in the DID Document

        Returns:
            Dict with status, transaction_id

        Raises:
            HederaDIDError: If updates dict is empty or DID format is invalid
        """
        if not updates:
            raise HederaDIDError("DID Document updates cannot be empty")

        network, account_id, topic_id = _parse_did(did_string)

        timestamp = datetime.now(timezone.utc).isoformat()
        hcs_message = {
            "type": "update",
            "did": did_string,
            "updates": updates,
            "timestamp": timestamp,
        }

        logger.info(f"Updating DID Document: {did_string}")

        result = await self.nft_client.submit_hcs_message(
            topic_id=topic_id,
            message=hcs_message,
        )

        return {
            "status": result.get("status", "SUCCESS"),
            "transaction_id": result.get("transaction_id"),
            "did": did_string,
        }

    async def revoke_did(
        self,
        did_string: str,
    ) -> Dict[str, Any]:
        """
        Revoke a DID by submitting a deactivation message.

        After revocation, the DID resolves with deactivated=True.
        This is irreversible per the W3C DID spec.

        Args:
            did_string: DID to revoke

        Returns:
            Dict with deactivated=True, status, transaction_id

        Raises:
            HederaDIDError: If the DID format is invalid
        """
        network, account_id, topic_id = _parse_did(did_string)

        timestamp = datetime.now(timezone.utc).isoformat()
        hcs_message = {
            "type": "deactivate",
            "did": did_string,
            "timestamp": timestamp,
        }

        logger.info(f"Revoking DID: {did_string}")

        result = await self.nft_client.submit_hcs_message(
            topic_id=topic_id,
            message=hcs_message,
        )

        return {
            "deactivated": True,
            "status": result.get("status", "SUCCESS"),
            "transaction_id": result.get("transaction_id"),
            "did": did_string,
        }


# Global service instance
hedera_did_service = HederaDIDService()


def get_hedera_did_service() -> HederaDIDService:
    """
    Get the global HederaDIDService instance.

    Returns:
        Configured HederaDIDService instance
    """
    return hedera_did_service
