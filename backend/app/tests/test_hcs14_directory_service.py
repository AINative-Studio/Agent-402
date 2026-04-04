"""
Tests for HCS14DirectoryService — Issue #193 (HCS-14 Directory Registration).

TDD: Tests written FIRST, RED phase.

Refs #193
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List


class DescribeHCS14DirectoryServiceInit:
    """HCS14DirectoryService initializes correctly."""

    def it_initializes_with_no_nft_client(self):
        """Service uses lazy initialization for its NFT/HCS client."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        service = HCS14DirectoryService()
        assert service._nft_client is None

    def it_accepts_an_injected_nft_client(self):
        """Service accepts an injected client for testing."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = MagicMock()
        service = HCS14DirectoryService(nft_client=mock_client)
        assert service._nft_client is mock_client


class DescribeRegisterAgent:
    """HCS14DirectoryService.register_agent submits HCS-14 registration message."""

    @pytest.mark.asyncio
    async def it_returns_success_on_registration(self):
        """register_agent returns a result with SUCCESS status."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.register_agent(
            agent_did="did:hedera:testnet:0.0.111_0.0.222",
            capabilities=["chat", "memory"],
            role="analyst",
            reputation_score=100,
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_submits_hcs14_formatted_message(self):
        """register_agent submits a message conforming to HCS-14 format."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_reg",
            "status": "SUCCESS",
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        await service.register_agent(
            agent_did="did:hedera:testnet:0.0.111_0.0.222",
            capabilities=["chat"],
            role="analyst",
            reputation_score=50,
        )

        mock_client.submit_hcs_message.assert_called_once()
        call_args = mock_client.submit_hcs_message.call_args
        message = call_args[1].get("message") or call_args[0][1]

        # HCS-14 message must contain these fields
        assert "register" in str(message).lower() or "type" in str(message).lower()

    @pytest.mark.asyncio
    async def it_raises_directory_error_for_empty_agent_did(self):
        """register_agent raises HCS14DirectoryError when agent_did is empty."""
        from app.services.hcs14_directory_service import (
            HCS14DirectoryService,
            HCS14DirectoryError,
        )

        service = HCS14DirectoryService(nft_client=AsyncMock())
        with pytest.raises(HCS14DirectoryError):
            await service.register_agent(
                agent_did="",
                capabilities=["chat"],
                role="analyst",
                reputation_score=100,
            )

    @pytest.mark.asyncio
    async def it_raises_directory_error_for_negative_reputation(self):
        """register_agent raises HCS14DirectoryError for negative reputation score."""
        from app.services.hcs14_directory_service import (
            HCS14DirectoryService,
            HCS14DirectoryError,
        )

        service = HCS14DirectoryService(nft_client=AsyncMock())
        with pytest.raises(HCS14DirectoryError):
            await service.register_agent(
                agent_did="did:hedera:testnet:0.0.111_0.0.222",
                capabilities=["chat"],
                role="analyst",
                reputation_score=-1,
            )

    @pytest.mark.asyncio
    async def it_includes_timestamp_in_registration_message(self):
        """register_agent includes a timestamp in the HCS-14 message."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json

        submitted_messages: list = []

        async def capture_message(topic_id: str, message: Any) -> Dict[str, str]:
            submitted_messages.append(message)
            return {"transaction_id": "tx_ts", "status": "SUCCESS"}

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.side_effect = capture_message

        service = HCS14DirectoryService(nft_client=mock_client)
        await service.register_agent(
            agent_did="did:hedera:testnet:0.0.111_0.0.222",
            capabilities=["analytics"],
            role="analyst",
            reputation_score=75,
        )

        assert len(submitted_messages) == 1
        msg = submitted_messages[0]
        if isinstance(msg, str):
            msg = json.loads(msg)
        assert "timestamp" in msg


class DescribeQueryDirectory:
    """HCS14DirectoryService.query_directory queries agents via mirror node."""

    @pytest.mark.asyncio
    async def it_returns_list_of_directory_entries(self):
        """query_directory returns a DirectoryQueryResult with agents list."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json
        import base64

        reg_message = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["chat", "memory"],
            "role": "analyst",
            "reputation": 100,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        encoded = base64.b64encode(reg_message.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {
                    "message": encoded,
                    "consensus_timestamp": "1234567890.000000000",
                    "sequence_number": 1,
                }
            ]
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.query_directory()

        assert "agents" in result
        assert isinstance(result["agents"], list)
        assert len(result["agents"]) >= 1

    @pytest.mark.asyncio
    async def it_filters_by_capability_when_provided(self):
        """query_directory filters results to agents having the requested capability."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json
        import base64

        # Two agents: one with "payment", one without
        msg1 = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["payment", "analytics"],
            "role": "transaction",
            "reputation": 90,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        msg2 = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.333_0.0.444",
            "capabilities": ["chat"],
            "role": "analyst",
            "reputation": 80,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        encoded1 = base64.b64encode(msg1.encode()).decode()
        encoded2 = base64.b64encode(msg2.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {"message": encoded1, "consensus_timestamp": "1234567890.000000000", "sequence_number": 1},
                {"message": encoded2, "consensus_timestamp": "1234567891.000000000", "sequence_number": 2},
            ]
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.query_directory(capability="payment")

        assert len(result["agents"]) == 1
        assert result["agents"][0]["did"] == "did:hedera:testnet:0.0.111_0.0.222"

    @pytest.mark.asyncio
    async def it_filters_by_role_when_provided(self):
        """query_directory filters results to agents with the requested role."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json
        import base64

        msg1 = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["payment"],
            "role": "transaction",
            "reputation": 90,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        msg2 = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.333_0.0.444",
            "capabilities": ["chat"],
            "role": "analyst",
            "reputation": 80,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        encoded1 = base64.b64encode(msg1.encode()).decode()
        encoded2 = base64.b64encode(msg2.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {"message": encoded1, "consensus_timestamp": "1234567890.000000000", "sequence_number": 1},
                {"message": encoded2, "consensus_timestamp": "1234567891.000000000", "sequence_number": 2},
            ]
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.query_directory(role="analyst")

        assert len(result["agents"]) == 1
        assert result["agents"][0]["role"] == "analyst"

    @pytest.mark.asyncio
    async def it_filters_by_min_reputation_when_provided(self):
        """query_directory filters out agents below the minimum reputation threshold."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json
        import base64

        msg_low = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.111_0.0.222",
            "capabilities": ["chat"],
            "role": "analyst",
            "reputation": 30,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        msg_high = json.dumps({
            "type": "register",
            "did": "did:hedera:testnet:0.0.333_0.0.444",
            "capabilities": ["chat"],
            "role": "analyst",
            "reputation": 90,
            "timestamp": "2026-04-03T00:00:00+00:00",
        })
        enc_low = base64.b64encode(msg_low.encode()).decode()
        enc_high = base64.b64encode(msg_high.encode()).decode()

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {
            "messages": [
                {"message": enc_low, "consensus_timestamp": "1234567890.000000000", "sequence_number": 1},
                {"message": enc_high, "consensus_timestamp": "1234567891.000000000", "sequence_number": 2},
            ]
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.query_directory(min_reputation=50)

        assert len(result["agents"]) == 1
        assert result["agents"][0]["did"] == "did:hedera:testnet:0.0.333_0.0.444"

    @pytest.mark.asyncio
    async def it_returns_empty_agents_list_when_no_registrations(self):
        """query_directory returns empty list when directory has no messages."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = AsyncMock()
        mock_client.get_hcs_messages.return_value = {"messages": []}

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.query_directory()

        assert result["agents"] == []


class DescribeUpdateRegistration:
    """HCS14DirectoryService.update_registration updates a directory entry."""

    @pytest.mark.asyncio
    async def it_returns_success_on_update(self):
        """update_registration returns SUCCESS status after submitting update."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_update",
            "status": "SUCCESS",
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.update_registration(
            agent_did="did:hedera:testnet:0.0.111_0.0.222",
            updates={"reputation": 150},
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_raises_directory_error_when_updates_are_empty(self):
        """update_registration raises HCS14DirectoryError when updates are empty."""
        from app.services.hcs14_directory_service import (
            HCS14DirectoryService,
            HCS14DirectoryError,
        )

        service = HCS14DirectoryService(nft_client=AsyncMock())
        with pytest.raises(HCS14DirectoryError):
            await service.update_registration(
                agent_did="did:hedera:testnet:0.0.111_0.0.222",
                updates={},
            )


class DescribeDeregisterAgent:
    """HCS14DirectoryService.deregister_agent removes agent from directory."""

    @pytest.mark.asyncio
    async def it_returns_success_on_deregistration(self):
        """deregister_agent returns SUCCESS status after submitting removal message."""
        from app.services.hcs14_directory_service import HCS14DirectoryService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.return_value = {
            "transaction_id": "tx_dereg",
            "status": "SUCCESS",
        }

        service = HCS14DirectoryService(nft_client=mock_client)
        result = await service.deregister_agent(
            agent_did="did:hedera:testnet:0.0.111_0.0.222"
        )

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_submits_deregister_type_message(self):
        """deregister_agent submits a message with type=deregister."""
        from app.services.hcs14_directory_service import HCS14DirectoryService
        import json

        submitted_messages: list = []

        async def capture_message(topic_id: str, message: Any) -> Dict[str, str]:
            submitted_messages.append(message)
            return {"transaction_id": "tx_dereg", "status": "SUCCESS"}

        mock_client = AsyncMock()
        mock_client.submit_hcs_message.side_effect = capture_message

        service = HCS14DirectoryService(nft_client=mock_client)
        await service.deregister_agent(
            agent_did="did:hedera:testnet:0.0.111_0.0.222"
        )

        assert len(submitted_messages) == 1
        msg = submitted_messages[0]
        if isinstance(msg, str):
            msg = json.loads(msg)
        msg_type = msg.get("type", "")
        assert "deregister" in msg_type.lower() or "remove" in msg_type.lower()

    @pytest.mark.asyncio
    async def it_raises_directory_error_for_empty_agent_did(self):
        """deregister_agent raises HCS14DirectoryError when agent_did is empty."""
        from app.services.hcs14_directory_service import (
            HCS14DirectoryService,
            HCS14DirectoryError,
        )

        service = HCS14DirectoryService(nft_client=AsyncMock())
        with pytest.raises(HCS14DirectoryError):
            await service.deregister_agent(agent_did="")
