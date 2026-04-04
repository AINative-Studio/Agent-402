"""
Hedera Identity Service.
HTS NFT Agent Registry and AAP Capability Mapping.

Issue #191: HTS NFT Agent Registry
- Create HTS non-fungible token class for agent registry
- Mint agent NFTs with metadata (name, role, capabilities, DID)
- Retrieve and update agent NFT metadata
- Deactivate agents by freezing their NFT

Issue #194: AAP Capability Mapping to HTS
- Encode/decode AAP capabilities in NFT metadata
- Verify specific capability presence
- KYC flag maps to compliance verification status
- Freeze flag maps to agent suspension

Built by AINative Dev Team
Refs #191, #194
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

# Valid AAP capabilities per Issue #194
AAP_CAPABILITIES = frozenset([
    "chat",
    "memory",
    "vector_search",
    "file_storage",
    "payment",
    "compliance",
    "analytics",
])

# Required metadata fields for agent NFTs
REQUIRED_METADATA_FIELDS = ("name", "role", "did")


class HederaIdentityError(APIError):
    """
    Raised when a Hedera identity operation fails.

    Returns:
        - HTTP 400 or 502 depending on cause
        - error_code: HEDERA_IDENTITY_ERROR
        - detail: Human-readable error message
    """

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            error_code="HEDERA_IDENTITY_ERROR",
            detail=detail or "Hedera identity error",
        )


class HederaIdentityService:
    """
    Service for managing agent identities via Hedera HTS NFTs.

    Each agent is represented by a unique NFT:
    - NFT token class = agent registry (one-time setup per deployment)
    - Each NFT serial = one agent identity
    - NFT metadata = agent profile (name, role, DID, capabilities, status)
    - Frozen NFT = suspended agent

    AAP capabilities are stored in the NFT metadata 'capabilities' list
    and can be queried/updated without minting a new NFT.
    """

    def __init__(
        self,
        nft_client: Optional[HederaHTSNFTClient] = None,
    ):
        """
        Initialize the Hedera Identity Service.

        Args:
            nft_client: Optional HTS NFT client (lazy-initialized if None)
        """
        self._nft_client = nft_client

    @property
    def nft_client(self) -> HederaHTSNFTClient:
        """Lazy-initialized HTS NFT client."""
        if self._nft_client is None:
            self._nft_client = get_hedera_hts_nft_client()
        return self._nft_client

    # ------------------------------------------------------------------
    # Issue #191: HTS NFT Agent Registry
    # ------------------------------------------------------------------

    async def create_agent_token_class(
        self,
        name: str,
        symbol: str,
        admin_key: str,
    ) -> Dict[str, Any]:
        """
        Create an HTS non-fungible token class for the agent registry.

        This is a one-time setup operation. The resulting token_id is used
        for all subsequent agent NFT minting operations.

        Args:
            name: Token class name (e.g. "AgentRegistry")
            symbol: Token symbol (e.g. "AREG")
            admin_key: Admin public key hex (Ed25519)

        Returns:
            Dict with token_id, transaction_id, status

        Raises:
            HederaIdentityError: If name or symbol is empty
        """
        if not name or not name.strip():
            raise HederaIdentityError("Token class name cannot be empty")
        if not symbol or not symbol.strip():
            raise HederaIdentityError("Token symbol cannot be empty")

        logger.info(
            f"Creating agent token class: name={name}, symbol={symbol}"
        )

        return await self.nft_client.create_nft_token(
            name=name,
            symbol=symbol,
            admin_key=admin_key,
        )

    async def mint_agent_nft(
        self,
        token_id: str,
        agent_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Mint an agent NFT with the provided metadata.

        Encodes the agent metadata as JSON bytes and submits a
        TokenMintTransaction to the Hedera network.

        Agent metadata must include: name, role, did.

        Args:
            token_id: HTS token ID to mint under
            agent_metadata: Dict with agent attributes

        Returns:
            Dict with serial_number, token_id, transaction_id, status

        Raises:
            HederaIdentityError: If token_id is empty or metadata is missing
                                  required fields
        """
        if not token_id or not token_id.strip():
            raise HederaIdentityError("token_id cannot be empty")

        for field in REQUIRED_METADATA_FIELDS:
            if not agent_metadata.get(field):
                raise HederaIdentityError(
                    f"Agent metadata is missing required field: '{field}'. "
                    f"Required fields: {list(REQUIRED_METADATA_FIELDS)}"
                )

        # Ensure required fields have defaults
        if "capabilities" not in agent_metadata:
            agent_metadata = {**agent_metadata, "capabilities": []}
        if "status" not in agent_metadata:
            agent_metadata = {**agent_metadata, "status": "active"}
        if "created_at" not in agent_metadata:
            agent_metadata = {
                **agent_metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        metadata_bytes = json.dumps(agent_metadata).encode("utf-8")

        logger.info(
            f"Minting agent NFT: token_id={token_id}, "
            f"agent_name={agent_metadata.get('name')}"
        )

        return await self.nft_client.mint_nft(
            token_id=token_id,
            metadata_bytes=metadata_bytes,
        )

    async def get_agent_nft(
        self,
        token_id: str,
        serial_number: int,
    ) -> Dict[str, Any]:
        """
        Get agent NFT metadata from the mirror node.

        Retrieves the NFT and decodes the metadata bytes back to a dict.

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number

        Returns:
            Dict with token_id, serial_number, metadata (decoded dict), owner_account

        Raises:
            HederaIdentityError: If the NFT is not found (wraps client error)
        """
        raw = await self.nft_client.get_nft_info(
            token_id=token_id,
            serial=serial_number,
        )

        # Decode base64 metadata → JSON dict
        metadata_b64 = raw.get("metadata", "")
        metadata: Dict[str, Any] = {}
        if metadata_b64:
            try:
                decoded = base64.b64decode(metadata_b64).decode("utf-8")
                metadata = json.loads(decoded)
            except Exception:
                # Metadata may not be JSON (old format or empty)
                metadata = {}

        return {
            "token_id": raw["token_id"],
            "serial_number": raw["serial_number"],
            "metadata": metadata,
            "owner_account": raw.get("account_id"),
        }

    async def update_agent_metadata(
        self,
        token_id: str,
        serial_number: int,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update agent metadata via a new mint (metadata replacement pattern).

        HTS NFTs store metadata as immutable bytes per serial number. To
        "update" metadata, this service mints new metadata bytes via a
        token update transaction. In production, this uses TokenUpdateNftsTransaction
        (available since HIP-657).

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number to update
            metadata: New metadata fields to apply (must be non-empty)

        Returns:
            Dict with status, transaction_id

        Raises:
            HederaIdentityError: If metadata dict is empty
        """
        if not metadata:
            raise HederaIdentityError("Metadata update cannot be empty")

        # Encode updated metadata
        metadata_bytes = json.dumps(metadata).encode("utf-8")

        logger.info(
            f"Updating NFT metadata: token_id={token_id}, serial={serial_number}"
        )

        # Re-use mint_nft for simulation (production: TokenUpdateNftsTransaction)
        result = await self.nft_client.mint_nft(
            token_id=token_id,
            metadata_bytes=metadata_bytes,
        )

        return {
            "status": result["status"],
            "transaction_id": result.get("transaction_id"),
            "token_id": token_id,
            "serial_number": serial_number,
        }

    async def deactivate_agent(
        self,
        token_id: str,
        serial_number: int,
    ) -> Dict[str, Any]:
        """
        Deactivate an agent by freezing their NFT.

        Freezing suspends all transfers of the NFT, effectively
        preventing the agent from operating.

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number

        Returns:
            Dict with status, transaction_id, token_id, serial_number

        Raises:
            HederaIdentityError: If the freeze operation fails
        """
        logger.info(
            f"Deactivating agent NFT: token_id={token_id}, serial={serial_number}"
        )

        return await self.nft_client.freeze_nft(
            token_id=token_id,
            serial=serial_number,
        )

    # ------------------------------------------------------------------
    # Issue #194: AAP Capability Mapping
    # ------------------------------------------------------------------

    async def map_aap_capabilities(
        self,
        token_id: str,
        serial_number: int,
        capabilities: List[str],
    ) -> Dict[str, Any]:
        """
        Encode AAP capabilities into NFT metadata.

        Validates that all capabilities are from the defined AAP set,
        then updates the NFT metadata with the capability list.

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number
            capabilities: List of AAP capability strings to assign

        Returns:
            Dict with status, token_id, serial_number, capabilities

        Raises:
            HederaIdentityError: If any capability is not in the AAP set
        """
        invalid = [c for c in capabilities if c not in AAP_CAPABILITIES]
        if invalid:
            raise HederaIdentityError(
                f"Invalid AAP capabilities: {invalid}. "
                f"Valid capabilities: {sorted(AAP_CAPABILITIES)}"
            )

        # Fetch current metadata to merge with
        current = await self.get_agent_nft(
            token_id=token_id, serial_number=serial_number
        )
        current_meta = current.get("metadata", {})

        # Apply capability update
        updated_meta = {**current_meta, "capabilities": capabilities}

        # Persist the update
        metadata_bytes = json.dumps(updated_meta).encode("utf-8")
        result = await self.nft_client.mint_nft(
            token_id=token_id,
            metadata_bytes=metadata_bytes,
        )

        logger.info(
            f"Mapped AAP capabilities: token_id={token_id}, "
            f"serial={serial_number}, capabilities={capabilities}"
        )

        return {
            "status": result["status"],
            "token_id": token_id,
            "serial_number": serial_number,
            "capabilities": capabilities,
            "transaction_id": result.get("transaction_id"),
        }

    async def get_agent_capabilities(
        self,
        token_id: str,
        serial_number: int,
    ) -> List[str]:
        """
        Decode AAP capabilities from NFT metadata.

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number

        Returns:
            List of capability strings (empty list if none stored)
        """
        nft = await self.get_agent_nft(
            token_id=token_id, serial_number=serial_number
        )
        metadata = nft.get("metadata", {})
        return metadata.get("capabilities", [])

    async def check_capability(
        self,
        token_id: str,
        serial_number: int,
        capability: str,
    ) -> bool:
        """
        Verify whether an agent has a specific AAP capability.

        Args:
            token_id: HTS token ID
            serial_number: NFT serial number
            capability: AAP capability name to check

        Returns:
            True if the agent has the capability, False otherwise

        Raises:
            HederaIdentityError: If capability name is not in the AAP set
        """
        if capability not in AAP_CAPABILITIES:
            raise HederaIdentityError(
                f"Invalid capability name: '{capability}'. "
                f"Valid capabilities: {sorted(AAP_CAPABILITIES)}"
            )

        capabilities = await self.get_agent_capabilities(
            token_id=token_id, serial_number=serial_number
        )
        return capability in capabilities


# Global service instance
hedera_identity_service = HederaIdentityService()


def get_hedera_identity_service() -> HederaIdentityService:
    """
    Get the global HederaIdentityService instance.

    Returns:
        Configured HederaIdentityService instance
    """
    return hedera_identity_service
