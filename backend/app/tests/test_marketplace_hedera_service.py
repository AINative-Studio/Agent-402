"""
Tests for MarketplaceHederaService.
Issue #217: On-Chain Agent Identity via Hedera.

TDD: RED phase — tests written before implementation.
BDD-style: class Describe* / def it_*
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class DescribeMarketplaceHederaServiceInit:
    """MarketplaceHederaService initializes correctly."""

    def it_initializes_with_lazy_nft_client(self):
        """Service defers HederaHTSNFTClient construction."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        svc = MarketplaceHederaService()
        assert svc._nft_client is None

    def it_accepts_injected_nft_client(self):
        """Service accepts injected client for tests."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        mock = MagicMock()
        svc = MarketplaceHederaService(nft_client=mock)
        assert svc.nft_client is mock


class DescribeVerifyOnChainIdentity:
    """Tests for verify_on_chain_identity — Issue #217."""

    @pytest.mark.asyncio
    async def it_returns_verified_true_when_nft_exists(self):
        """verify_on_chain_identity returns verified=True if NFT is found."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        mock_nft = AsyncMock()
        mock_nft.get_nft_info = AsyncMock(
            return_value={
                "token_id": "0.0.999",
                "serial_number": 1,
                "metadata": "eyJhZ2VudF9kaWQiOiAiZGlkOmhlZGVyYTp0ZXN0bmV0OmFiYyJ9",
                "account_id": "0.0.111",
            }
        )

        svc = MarketplaceHederaService(nft_client=mock_nft)
        result = await svc.verify_on_chain_identity("did:hedera:testnet:abc_0.0.999_1")

        assert result["verified"] is True
        assert result["agent_did"] == "did:hedera:testnet:abc_0.0.999_1"

    @pytest.mark.asyncio
    async def it_returns_verified_false_when_nft_not_found(self):
        """verify_on_chain_identity returns verified=False if NFT raises 404."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService
        from app.services.hedera_hts_nft_client import HederaHTSNFTClientError

        mock_nft = AsyncMock()
        mock_nft.get_nft_info = AsyncMock(
            side_effect=HederaHTSNFTClientError("NFT not found", 404)
        )

        svc = MarketplaceHederaService(nft_client=mock_nft)
        result = await svc.verify_on_chain_identity("did:hedera:testnet:xyz_0.0.111_99")

        assert result["verified"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def it_handles_did_without_token_reference(self):
        """verify_on_chain_identity returns unverifiable for DIDs without NFT token."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        svc = MarketplaceHederaService(nft_client=AsyncMock())
        result = await svc.verify_on_chain_identity("did:hedera:testnet:no_token_here")

        # DID does not contain token_id+serial — cannot verify on-chain
        assert result["verified"] is False
        assert result["agent_did"] == "did:hedera:testnet:no_token_here"


class DescribeLinkMarketplaceToNFT:
    """Tests for link_marketplace_to_nft — Issue #217."""

    @pytest.mark.asyncio
    async def it_returns_linkage_record_with_all_ids(self):
        """link_marketplace_to_nft creates a cross-reference record."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        svc = MarketplaceHederaService(nft_client=AsyncMock())
        result = await svc.link_marketplace_to_nft(
            marketplace_id="mkt_001",
            nft_token_id="0.0.9999",
            serial=42,
        )

        assert result["marketplace_id"] == "mkt_001"
        assert result["nft_token_id"] == "0.0.9999"
        assert result["serial"] == 42
        assert "linked_at" in result

    @pytest.mark.asyncio
    async def it_raises_for_empty_marketplace_id(self):
        """link_marketplace_to_nft raises ValueError for empty marketplace_id."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        svc = MarketplaceHederaService(nft_client=AsyncMock())

        with pytest.raises(ValueError):
            await svc.link_marketplace_to_nft(
                marketplace_id="",
                nft_token_id="0.0.9999",
                serial=1,
            )

    @pytest.mark.asyncio
    async def it_raises_for_invalid_serial(self):
        """link_marketplace_to_nft raises ValueError for non-positive serial."""
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        svc = MarketplaceHederaService(nft_client=AsyncMock())

        with pytest.raises(ValueError):
            await svc.link_marketplace_to_nft(
                marketplace_id="mkt_001",
                nft_token_id="0.0.9999",
                serial=0,
            )
