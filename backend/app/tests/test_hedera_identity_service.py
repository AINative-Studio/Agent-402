"""
Tests for HederaIdentityService — Issue #191 (HTS NFT Agent Registry)
and Issue #194 (AAP Capability Mapping to HTS).

TDD: Tests written FIRST, RED phase.

Refs #191, #194
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# Issue #191: HTS NFT Agent Registry
# ---------------------------------------------------------------------------


class DescribeHederaIdentityServiceInit:
    """HederaIdentityService initializes correctly."""

    def it_initializes_with_default_nft_client(self):
        """Service creates an NFT client lazily when none is provided."""
        from app.services.hedera_identity_service import HederaIdentityService

        service = HederaIdentityService()
        assert service._nft_client is None  # lazy init

    def it_accepts_an_injected_nft_client(self):
        """Service accepts an injected NFT client for testing."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = MagicMock()
        service = HederaIdentityService(nft_client=mock_client)
        assert service._nft_client is mock_client

    def it_exposes_nft_client_property(self):
        """Accessing .nft_client on a freshly created service returns a client."""
        from app.services.hedera_identity_service import HederaIdentityService
        from app.services.hedera_hts_nft_client import HederaHTSNFTClient

        service = HederaIdentityService()
        client = service.nft_client
        assert isinstance(client, HederaHTSNFTClient)


class DescribeCreateAgentTokenClass:
    """HederaIdentityService.create_agent_token_class creates an HTS NFT token class."""

    @pytest.mark.asyncio
    async def it_returns_token_id_on_success(self):
        """create_agent_token_class returns a dict containing token_id."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.create_nft_token.return_value = {
            "token_id": "0.0.9999",
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.create_agent_token_class(
            name="AgentRegistry",
            symbol="AREG",
            admin_key="ed25519_public_key_hex",
        )

        assert result["token_id"] == "0.0.9999"

    @pytest.mark.asyncio
    async def it_passes_name_symbol_admin_key_to_client(self):
        """create_agent_token_class forwards name/symbol/admin_key to NFT client."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.create_nft_token.return_value = {
            "token_id": "0.0.8888",
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        await service.create_agent_token_class(
            name="TestToken",
            symbol="TST",
            admin_key="key_hex_value",
        )

        mock_client.create_nft_token.assert_called_once_with(
            name="TestToken",
            symbol="TST",
            admin_key="key_hex_value",
        )

    @pytest.mark.asyncio
    async def it_raises_identity_error_when_name_is_empty(self):
        """create_agent_token_class raises HederaIdentityError for empty name."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.create_agent_token_class(
                name="", symbol="TST", admin_key="key"
            )

    @pytest.mark.asyncio
    async def it_raises_identity_error_when_symbol_is_empty(self):
        """create_agent_token_class raises HederaIdentityError for empty symbol."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.create_agent_token_class(
                name="Name", symbol="", admin_key="key"
            )


class DescribeMintAgentNFT:
    """HederaIdentityService.mint_agent_nft mints an agent NFT with metadata."""

    @pytest.mark.asyncio
    async def it_returns_serial_number_on_success(self):
        """mint_agent_nft returns a result containing serial_number."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.mint_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        metadata = {
            "name": "Agent Alpha",
            "role": "analyst",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["chat", "memory"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        result = await service.mint_agent_nft(
            token_id="0.0.9999", agent_metadata=metadata
        )

        assert result["serial_number"] == 1

    @pytest.mark.asyncio
    async def it_encodes_metadata_as_bytes_for_mint(self):
        """mint_agent_nft passes encoded metadata bytes to the NFT client."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.mint_nft.return_value = {
            "serial_number": 2,
            "token_id": "0.0.9999",
            "transaction_id": "tx_id",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        metadata = {
            "name": "Agent Beta",
            "role": "compliance",
            "did": "did:hedera:testnet:0.0.333_0.0.444",
            "capabilities": ["compliance"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        await service.mint_agent_nft(token_id="0.0.9999", agent_metadata=metadata)

        mock_client.mint_nft.assert_called_once()
        call_kwargs = mock_client.mint_nft.call_args
        assert call_kwargs[1]["token_id"] == "0.0.9999" or call_kwargs[0][0] == "0.0.9999"
        # metadata_bytes should be bytes
        passed_bytes = (
            call_kwargs[1].get("metadata_bytes") or call_kwargs[0][1]
        )
        assert isinstance(passed_bytes, bytes)

    @pytest.mark.asyncio
    async def it_raises_identity_error_when_token_id_is_empty(self):
        """mint_agent_nft raises HederaIdentityError for empty token_id."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.mint_agent_nft(token_id="", agent_metadata={})

    @pytest.mark.asyncio
    async def it_raises_identity_error_when_metadata_lacks_required_fields(self):
        """mint_agent_nft raises HederaIdentityError when required fields are missing."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            # Missing 'name', 'role', 'did'
            await service.mint_agent_nft(
                token_id="0.0.9999", agent_metadata={"capabilities": []}
            )


class DescribeGetAgentNFT:
    """HederaIdentityService.get_agent_nft retrieves agent NFT metadata."""

    @pytest.mark.asyncio
    async def it_returns_nft_metadata_on_success(self):
        """get_agent_nft returns a dict with token_id, serial_number, and metadata."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "metadata": "eyJuYW1lIjogIkFnZW50IEFscGhhIn0=",  # base64
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.get_agent_nft(
            token_id="0.0.9999", serial_number=1
        )

        assert result["token_id"] == "0.0.9999"
        assert result["serial_number"] == 1
        assert "metadata" in result

    @pytest.mark.asyncio
    async def it_calls_nft_client_with_correct_params(self):
        """get_agent_nft calls nft_client.get_nft_info with token_id and serial."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 5,
            "metadata": "e30=",
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        await service.get_agent_nft(token_id="0.0.9999", serial_number=5)

        mock_client.get_nft_info.assert_called_once_with(
            token_id="0.0.9999", serial=5
        )


class DescribeUpdateAgentMetadata:
    """HederaIdentityService.update_agent_metadata updates NFT metadata."""

    @pytest.mark.asyncio
    async def it_returns_success_status(self):
        """update_agent_metadata returns a result with SUCCESS status."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.mint_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "tx_update",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.update_agent_metadata(
            token_id="0.0.9999",
            serial_number=1,
            metadata={"status": "updated", "name": "Agent Alpha v2"},
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_raises_identity_error_for_empty_metadata(self):
        """update_agent_metadata raises HederaIdentityError for empty metadata dict."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.update_agent_metadata(
                token_id="0.0.9999", serial_number=1, metadata={}
            )


class DescribeDeactivateAgent:
    """HederaIdentityService.deactivate_agent freezes the NFT (suspends agent)."""

    @pytest.mark.asyncio
    async def it_returns_deactivated_status(self):
        """deactivate_agent returns a result indicating the agent is frozen/suspended."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.freeze_nft.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "transaction_id": "tx_freeze",
            "status": "FROZEN",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.deactivate_agent(
            token_id="0.0.9999", serial_number=1
        )

        assert result["status"] in ("FROZEN", "DEACTIVATED", "SUCCESS")

    @pytest.mark.asyncio
    async def it_calls_freeze_nft_on_the_client(self):
        """deactivate_agent calls the freeze operation on the NFT client."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.freeze_nft.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "transaction_id": "tx_freeze",
            "status": "FROZEN",
        }

        service = HederaIdentityService(nft_client=mock_client)
        await service.deactivate_agent(token_id="0.0.9999", serial_number=1)

        mock_client.freeze_nft.assert_called_once_with(
            token_id="0.0.9999", serial=1
        )


# ---------------------------------------------------------------------------
# Issue #194: AAP Capability Mapping to HTS
# ---------------------------------------------------------------------------


class DescribeMapAAPCapabilities:
    """HederaIdentityService.map_aap_capabilities encodes AAP capabilities in NFT metadata."""

    @pytest.mark.asyncio
    async def it_returns_success_on_valid_capabilities(self):
        """map_aap_capabilities returns SUCCESS when valid capabilities are provided."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "metadata": "e30=",  # empty JSON base64
            "account_id": "0.0.5555",
        }
        mock_client.mint_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "tx_cap",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.map_aap_capabilities(
            token_id="0.0.9999",
            serial_number=1,
            capabilities=["chat", "memory", "vector_search"],
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_raises_identity_error_for_invalid_capability_names(self):
        """map_aap_capabilities raises HederaIdentityError for unknown capability."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.map_aap_capabilities(
                token_id="0.0.9999",
                serial_number=1,
                capabilities=["invalid_capability_xyz"],
            )

    @pytest.mark.asyncio
    async def it_accepts_all_defined_aap_capabilities(self):
        """map_aap_capabilities accepts all seven defined AAP capabilities."""
        from app.services.hedera_identity_service import HederaIdentityService

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "metadata": "e30=",
            "account_id": "0.0.5555",
        }
        mock_client.mint_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "tx_all_caps",
            "status": "SUCCESS",
        }

        service = HederaIdentityService(nft_client=mock_client)
        all_caps = [
            "chat",
            "memory",
            "vector_search",
            "file_storage",
            "payment",
            "compliance",
            "analytics",
        ]
        result = await service.map_aap_capabilities(
            token_id="0.0.9999",
            serial_number=1,
            capabilities=all_caps,
        )

        assert result["status"] == "SUCCESS"


class DescribeGetAgentCapabilities:
    """HederaIdentityService.get_agent_capabilities decodes capabilities from NFT."""

    @pytest.mark.asyncio
    async def it_returns_list_of_capabilities(self):
        """get_agent_capabilities returns a list of capability strings."""
        from app.services.hedera_identity_service import HederaIdentityService
        import json
        import base64

        stored_meta = json.dumps({
            "name": "Agent Alpha",
            "role": "analyst",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["chat", "memory"],
            "created_at": "2026-04-03T00:00:00+00:00",
            "status": "active",
        })
        encoded = base64.b64encode(stored_meta.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 1,
            "metadata": encoded,
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        capabilities = await service.get_agent_capabilities(
            token_id="0.0.9999", serial_number=1
        )

        assert isinstance(capabilities, list)
        assert "chat" in capabilities
        assert "memory" in capabilities

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_capabilities_stored(self):
        """get_agent_capabilities returns empty list when NFT has no capabilities."""
        from app.services.hedera_identity_service import HederaIdentityService
        import json
        import base64

        stored_meta = json.dumps({"name": "Agent Gamma", "role": "worker"})
        encoded = base64.b64encode(stored_meta.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 3,
            "metadata": encoded,
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        capabilities = await service.get_agent_capabilities(
            token_id="0.0.9999", serial_number=3
        )

        assert capabilities == []


class DescribeCheckCapability:
    """HederaIdentityService.check_capability verifies agent has specific capability."""

    @pytest.mark.asyncio
    async def it_returns_true_when_agent_has_capability(self):
        """check_capability returns True when the specified capability is present."""
        from app.services.hedera_identity_service import HederaIdentityService
        import json
        import base64

        stored_meta = json.dumps({
            "name": "Agent Delta",
            "role": "analyst",
            "did": "did:hedera:testnet:0.0.111_0.0.333",
            "capabilities": ["chat", "payment", "analytics"],
            "created_at": "2026-04-03T00:00:00+00:00",
            "status": "active",
        })
        encoded = base64.b64encode(stored_meta.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 4,
            "metadata": encoded,
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.check_capability(
            token_id="0.0.9999", serial_number=4, capability="payment"
        )

        assert result is True

    @pytest.mark.asyncio
    async def it_returns_false_when_agent_lacks_capability(self):
        """check_capability returns False when the specified capability is absent."""
        from app.services.hedera_identity_service import HederaIdentityService
        import json
        import base64

        stored_meta = json.dumps({
            "name": "Agent Delta",
            "role": "analyst",
            "did": "did:hedera:testnet:0.0.111_0.0.333",
            "capabilities": ["chat"],
            "created_at": "2026-04-03T00:00:00+00:00",
            "status": "active",
        })
        encoded = base64.b64encode(stored_meta.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_nft_info.return_value = {
            "token_id": "0.0.9999",
            "serial_number": 4,
            "metadata": encoded,
            "account_id": "0.0.5555",
        }

        service = HederaIdentityService(nft_client=mock_client)
        result = await service.check_capability(
            token_id="0.0.9999", serial_number=4, capability="payment"
        )

        assert result is False

    @pytest.mark.asyncio
    async def it_raises_identity_error_for_invalid_capability_name(self):
        """check_capability raises HederaIdentityError for unknown capability name."""
        from app.services.hedera_identity_service import (
            HederaIdentityService,
            HederaIdentityError,
        )

        service = HederaIdentityService(nft_client=AsyncMock())
        with pytest.raises(HederaIdentityError):
            await service.check_capability(
                token_id="0.0.9999",
                serial_number=1,
                capability="fly_to_the_moon",
            )
