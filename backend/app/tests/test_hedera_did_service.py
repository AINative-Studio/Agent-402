"""
Tests for HederaDIDService — Issue #192 (did:hedera DID Integration).

TDD: Tests written FIRST, RED phase.

Refs #192
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


class DescribeHederaDIDServiceInit:
    """HederaDIDService initializes correctly."""

    def it_initializes_with_no_nft_client(self):
        """Service creates its NFT/HCS client lazily."""
        from app.services.hedera_did_service import HederaDIDService

        service = HederaDIDService()
        assert service._nft_client is None

    def it_accepts_an_injected_nft_client(self):
        """Service accepts an injected client for testing."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = MagicMock()
        service = HederaDIDService(nft_client=mock_client)
        assert service._nft_client is mock_client


class DescribeCreateDID:
    """HederaDIDService.create_did creates a DID Document on HCS."""

    @pytest.mark.asyncio
    async def it_returns_did_string_in_hedera_format(self):
        """create_did returns a DID string in did:hedera:testnet format."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.create_did(
            account_id="0.0.111", topic_id="0.0.222"
        )

        assert "did" in result
        assert result["did"].startswith("did:hedera:testnet:")
        assert "0.0.111" in result["did"]
        assert "0.0.222" in result["did"]

    @pytest.mark.asyncio
    async def it_formats_did_as_account_id_underscore_topic_id(self):
        """create_did formats DID as did:hedera:testnet:{account_id}_{topic_id}."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_123",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.create_did(
            account_id="0.0.111", topic_id="0.0.222"
        )

        assert result["did"] == "did:hedera:testnet:0.0.111_0.0.222"

    @pytest.mark.asyncio
    async def it_returns_w3c_did_document_structure(self):
        """create_did returns a did_document conforming to W3C spec structure."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_123",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.create_did(
            account_id="0.0.111", topic_id="0.0.222"
        )

        assert "did_document" in result
        doc = result["did_document"]
        assert "id" in doc
        assert "controller" in doc
        assert "verificationMethod" in doc
        assert "authentication" in doc
        assert "service" in doc

    @pytest.mark.asyncio
    async def it_raises_did_error_when_account_id_is_empty(self):
        """create_did raises HederaDIDError when account_id is empty."""
        from app.services.hedera_did_service import HederaDIDService, HederaDIDError

        service = HederaDIDService(nft_client=AsyncMock())
        with pytest.raises(HederaDIDError):
            await service.create_did(account_id="", topic_id="0.0.222")

    @pytest.mark.asyncio
    async def it_raises_did_error_when_topic_id_is_empty(self):
        """create_did raises HederaDIDError when topic_id is empty."""
        from app.services.hedera_did_service import HederaDIDService, HederaDIDError

        service = HederaDIDService(nft_client=AsyncMock())
        with pytest.raises(HederaDIDError):
            await service.create_did(account_id="0.0.111", topic_id="")

    @pytest.mark.asyncio
    async def it_submits_hcs_message_on_create(self):
        """create_did submits a DID Document message to the HCS topic."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_123",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        await service.create_did(account_id="0.0.111", topic_id="0.0.222")

        mock_client.submit_hcs_message.assert_called_once()
        call_kwargs = mock_client.submit_hcs_message.call_args
        # Verify the topic_id is passed correctly
        passed_topic = (
            call_kwargs[1].get("topic_id") or call_kwargs[0][0]
        )
        assert passed_topic == "0.0.222"


class DescribeResolveDID:
    """HederaDIDService.resolve_did resolves a DID to agent metadata."""

    @pytest.mark.asyncio
    async def it_returns_did_document_for_valid_did(self):
        """resolve_did returns a DIDResolutionResult with did_document for valid DID."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {
                    "message": "eyJpZCI6ICJkaWQ6aGVkZXJhOnRlc3RuZXQ6MC4wLjExMV8wLjAuMjIyIn0=",
                    "consensus_timestamp": "1234567890.000000000",
                    "sequence_number": 1,
                }
            ]
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.resolve_did(
            did_string="did:hedera:testnet:0.0.111_0.0.222"
        )

        assert "did_document" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def it_raises_did_not_found_error_for_missing_did(self):
        """resolve_did raises HederaDIDNotFoundError when DID has no HCS messages."""
        from app.services.hedera_did_service import (
            HederaDIDService,
            HederaDIDNotFoundError,
        )

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {"messages": []}

        service = HederaDIDService(nft_client=mock_client)
        with pytest.raises(HederaDIDNotFoundError):
            await service.resolve_did(
                did_string="did:hedera:testnet:0.0.999_0.0.888"
            )

    @pytest.mark.asyncio
    async def it_raises_did_error_for_invalid_did_format(self):
        """resolve_did raises HederaDIDError when DID string format is invalid."""
        from app.services.hedera_did_service import HederaDIDService, HederaDIDError

        service = HederaDIDService(nft_client=AsyncMock())
        with pytest.raises(HederaDIDError):
            await service.resolve_did(did_string="not:a:valid:did")

    @pytest.mark.asyncio
    async def it_extracts_topic_id_from_did_for_hcs_query(self):
        """resolve_did parses the DID string to extract topic_id for HCS query."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {
                    "message": "eyJpZCI6ICJkaWQ6aGVkZXJhOnRlc3RuZXQ6MC4wLjExMV8wLjAuMjIyIn0=",
                    "consensus_timestamp": "1234567890.000000000",
                    "sequence_number": 1,
                }
            ]
        }

        service = HederaDIDService(nft_client=mock_client)
        await service.resolve_did(
            did_string="did:hedera:testnet:0.0.111_0.0.222"
        )

        mock_client.get_hcs_messages.assert_called_once()
        call_args = mock_client.get_hcs_messages.call_args
        passed_topic = (
            call_args[1].get("topic_id") or call_args[0][0]
        )
        assert passed_topic == "0.0.222"


class DescribeUpdateDIDDocument:
    """HederaDIDService.update_did_document submits an update to the HCS topic."""

    @pytest.mark.asyncio
    async def it_returns_success_on_update(self):
        """update_did_document returns SUCCESS status after submitting HCS update."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_update",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.update_did_document(
            did_string="did:hedera:testnet:0.0.111_0.0.222",
            updates={"service": [{"id": "service-1", "type": "AgentService"}]},
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_raises_did_error_when_updates_are_empty(self):
        """update_did_document raises HederaDIDError when updates dict is empty."""
        from app.services.hedera_did_service import HederaDIDService, HederaDIDError

        service = HederaDIDService(nft_client=AsyncMock())
        with pytest.raises(HederaDIDError):
            await service.update_did_document(
                did_string="did:hedera:testnet:0.0.111_0.0.222",
                updates={},
            )


class DescribeRevokeDID:
    """HederaDIDService.revoke_did marks a DID as deactivated."""

    @pytest.mark.asyncio
    async def it_returns_deactivated_status(self):
        """revoke_did returns a result showing the DID is deactivated."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_revoke",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        result = await service.revoke_did(
            did_string="did:hedera:testnet:0.0.111_0.0.222"
        )

        assert result["deactivated"] is True

    @pytest.mark.asyncio
    async def it_submits_deactivation_message_to_hcs(self):
        """revoke_did submits a deactivation message to the HCS topic."""
        from app.services.hedera_did_service import HederaDIDService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_revoke",
            "status": "SUCCESS",
        }

        service = HederaDIDService(nft_client=mock_client)
        await service.revoke_did(
            did_string="did:hedera:testnet:0.0.111_0.0.222"
        )

        mock_client.submit_hcs_message.assert_called_once()
        call_args = mock_client.submit_hcs_message.call_args
        # Message should contain deactivation info
        message = call_args[1].get("message") or call_args[0][1]
        assert "deactivat" in str(message).lower() or "revoke" in str(message).lower()

    @pytest.mark.asyncio
    async def it_raises_did_error_for_invalid_did_format(self):
        """revoke_did raises HederaDIDError when DID string format is invalid."""
        from app.services.hedera_did_service import HederaDIDService, HederaDIDError

        service = HederaDIDService(nft_client=AsyncMock())
        with pytest.raises(HederaDIDError):
            await service.revoke_did(did_string="bad-did-format")
