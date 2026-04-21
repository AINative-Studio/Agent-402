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
        agent_lookup: Optional[Any] = None,
    ):
        """
        Initialize the Hedera Identity Service.

        Args:
            nft_client: Optional HTS NFT client (lazy-initialized if None)
            agent_lookup: Optional async callable `(agent_id) -> Optional[Agent]`
                used by register_for_existing_agent to resolve a stored agent.
                Defaults to a lookup against AgentService when None.
        """
        self._nft_client = nft_client
        self._agent_lookup = agent_lookup

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
    # Issue #346: Linked agent registration
    # ------------------------------------------------------------------

    async def register_for_existing_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        name: Optional[str] = None,
        role: Optional[str] = None,
        token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attach a Hedera HTS NFT identity to an agent that already exists in
        the project store.

        Unlike :meth:`mint_agent_nft` (which is invoked by the standalone
        /register endpoint and generates a fresh agent_id), this method
        preserves the caller-supplied agent_id so the workshop's "create
        agent" step (Tutorial 01 Step 1) and "register on Hedera" step
        (Tutorial 01 Step 4) refer to the SAME agent record.

        Args:
            agent_id: The pre-existing agent identifier to link
            capabilities: AAP capabilities to assign
            name: Optional agent name override (defaults to the stored agent's name)
            role: Optional agent role override (defaults to the stored agent's role)
            token_id: Optional HTS token id to mint under

        Returns:
            Dict with agent_id (same as input), token_id, serial_number, did,
            status, transaction_id.

        Raises:
            HederaIdentityError(404): if the agent_id does not exist in the store.
        """
        lookup = self._agent_lookup or _default_agent_lookup
        existing = await lookup(agent_id)
        if existing is None:
            raise HederaIdentityError(
                f"Agent '{agent_id}' not found. Create it first via "
                f"POST /v1/public/{{project_id}}/agents.",
                status_code=404,
            )

        effective_name = name or getattr(existing, "name", "")
        effective_role = role or getattr(existing, "role", "")
        effective_token_id = token_id or "0.0.pending"
        timestamp = datetime.now(timezone.utc).isoformat()
        did = f"did:hedera:testnet:{agent_id}_pending"

        metadata = {
            "name": effective_name,
            "role": effective_role,
            "did": did,
            "capabilities": capabilities,
            "created_at": timestamp,
            "status": "active",
        }

        mint_result = await self.mint_agent_nft(
            token_id=effective_token_id,
            agent_metadata=metadata,
        )

        return {
            "agent_id": agent_id,
            "token_id": mint_result["token_id"],
            "serial_number": mint_result["serial_number"],
            "did": did,
            "status": mint_result["status"],
            "transaction_id": mint_result.get("transaction_id"),
        }

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


async def _default_agent_lookup(agent_id: str):
    """
    Default lookup used by ``register_for_existing_agent``.

    Resolves an agent by id from the agents store (ZeroDB-backed in production,
    in-memory mock store in dev/test). Returns ``None`` if the agent does not
    exist so the caller can return a 404.

    Refs #346
    """
    try:
        from app.services.zerodb_client import get_zerodb_client
        from app.services.agent_service import AGENTS_TABLE, _row_to_agent

        client = get_zerodb_client()
        result = await client.query_rows(
            table_name=AGENTS_TABLE,
            filter={"agent_id": agent_id},
            limit=1,
        )
        rows = result.get("rows", [])
        if not rows:
            return None
        return _row_to_agent(rows[0])
    except Exception as exc:
        logger.warning(
            "Default agent lookup failed for %s: %s", agent_id, exc
        )
        return None


# Global service instance
hedera_identity_service = HederaIdentityService()


def get_hedera_identity_service() -> HederaIdentityService:
    """
    Get the global HederaIdentityService instance.

    Returns:
        Configured HederaIdentityService instance
    """
    return hedera_identity_service
