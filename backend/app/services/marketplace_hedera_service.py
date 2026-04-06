"""
Marketplace Hedera Service.
On-chain agent identity verification via Hedera HTS NFTs.

Issue #217: On-Chain Agent Identity via Hedera.

Convention: agent_did encodes token_id and serial as
  did:hedera:<network>:<identifier>_<token_id>_<serial>
  e.g. did:hedera:testnet:abc_0.0.999_1

Uses hedera_hts_nft_client.py READ-ONLY (no modification to that file).

Built by AINative Dev Team
Refs #217
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.hedera_hts_nft_client import (
    HederaHTSNFTClient,
    HederaHTSNFTClientError,
    get_hedera_hts_nft_client,
)

logger = logging.getLogger(__name__)

# Pattern to extract token_id and serial from a DID string
# Matches: ..._0.0.<number>_<serial> at the end of the DID
_DID_TOKEN_PATTERN = re.compile(r"_(0\.0\.\d+)_(\d+)$")


class MarketplaceHederaService:
    """
    Provides on-chain identity verification for marketplace agents.

    Wraps HederaHTSNFTClient (READ-ONLY) to:
    - Verify that an agent DID maps to an existing Hedera NFT
    - Cross-reference marketplace IDs with on-chain NFT tokens
    """

    def __init__(self, nft_client: Optional[HederaHTSNFTClient] = None) -> None:
        self._nft_client = nft_client

    @property
    def nft_client(self) -> HederaHTSNFTClient:
        """Lazy-init NFT client."""
        if self._nft_client is None:
            self._nft_client = get_hedera_hts_nft_client()
        return self._nft_client

    async def verify_on_chain_identity(self, agent_did: str) -> Dict[str, Any]:
        """
        Verify that an agent DID corresponds to an existing Hedera NFT.

        The DID is expected to encode the token ID and serial number in its
        suffix, using the pattern: <prefix>_<token_id>_<serial>.

        Args:
            agent_did: Agent DID string

        Returns:
            Dict with keys: verified (bool), agent_did (str), and optionally
            token_id, serial, account_id, error
        """
        match = _DID_TOKEN_PATTERN.search(agent_did)
        if not match:
            logger.info(
                f"DID does not contain NFT token reference: {agent_did}"
            )
            return {
                "verified": False,
                "agent_did": agent_did,
                "error": "DID does not encode a Hedera token_id and serial",
            }

        token_id = match.group(1)
        serial = int(match.group(2))

        try:
            nft_info = await self.nft_client.get_nft_info(token_id, serial)
            logger.info(
                f"On-chain identity verified: {agent_did}, "
                f"token={token_id}, serial={serial}"
            )
            return {
                "verified": True,
                "agent_did": agent_did,
                "token_id": token_id,
                "serial": serial,
                "account_id": nft_info.get("account_id"),
                "created_timestamp": nft_info.get("created_timestamp"),
            }

        except HederaHTSNFTClientError as exc:
            logger.warning(
                f"On-chain identity NOT verified for {agent_did}: {exc}"
            )
            return {
                "verified": False,
                "agent_did": agent_did,
                "error": str(exc),
            }

    async def link_marketplace_to_nft(
        self,
        marketplace_id: str,
        nft_token_id: str,
        serial: int,
    ) -> Dict[str, Any]:
        """
        Create a cross-reference record linking a marketplace ID to an NFT.

        Args:
            marketplace_id: Marketplace listing identifier
            nft_token_id: Hedera HTS token ID (e.g. "0.0.9999")
            serial: NFT serial number (must be >= 1)

        Returns:
            Linkage dict with marketplace_id, nft_token_id, serial, linked_at

        Raises:
            ValueError: If marketplace_id is empty or serial < 1
        """
        if not marketplace_id:
            raise ValueError("marketplace_id must not be empty")
        if serial < 1:
            raise ValueError("serial must be a positive integer (>= 1)")

        now = datetime.now(timezone.utc).isoformat()
        linkage = {
            "marketplace_id": marketplace_id,
            "nft_token_id": nft_token_id,
            "serial": serial,
            "linked_at": now,
        }
        logger.info(
            f"Linked marketplace {marketplace_id} to NFT "
            f"{nft_token_id}#{serial}"
        )
        return linkage


def get_marketplace_hedera_service() -> MarketplaceHederaService:
    """Return a default MarketplaceHederaService instance."""
    return MarketplaceHederaService()
