"""
Tests for OpenConvAI HCS-10 Discovery Service.

Issue #207: Agent Capability Discovery.

TDD Red phase: tests define the contract for OpenConvAIDiscoveryService
before the implementation is written.

Built by AINative Dev Team
Refs #207
"""
from __future__ import annotations

import pytest
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AGENT_DID = "did:hedera:testnet:z6MkDiscoveryAgent"
SERVICE_ENDPOINT = "https://agent.example.com/hcs10"
CAPABILITIES = ["text_analysis", "compliance_check", "market_data"]


@pytest.fixture
def mock_hedera_client():
    """Mock HederaClient for isolation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    recent_heartbeat_iso = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    ).isoformat()

    client = AsyncMock()
    client.submit_topic_message = AsyncMock(return_value={
        "transaction_id": "0.0.12345@9999.000",
        "status": "SUCCESS",
        "sequence_number": 5,
        "consensus_timestamp": now_iso,
    })
    client.get_topic_messages = AsyncMock(return_value={
        "messages": [
            {
                "sequence_number": 5,
                "consensus_timestamp": recent_heartbeat_iso,
                "message": (
                    f'{{"protocol":"hcs-10","type":"discovery",'
                    f'"agent_did":"{AGENT_DID}",'
                    f'"capabilities":["text_analysis","market_data"],'
                    f'"service_endpoint":"{SERVICE_ENDPOINT}",'
                    f'"heartbeat_timestamp":"{recent_heartbeat_iso}"}}'
                ),
            }
        ]
    })
    return client


@pytest.fixture
def discovery_service(mock_hedera_client):
    """OpenConvAIDiscoveryService with mocked Hedera client."""
    from app.services.openconvai_discovery_service import OpenConvAIDiscoveryService
    return OpenConvAIDiscoveryService(hedera_client=mock_hedera_client)


# ---------------------------------------------------------------------------
# DescribeAdvertiseCapabilities
# ---------------------------------------------------------------------------

class DescribeAdvertiseCapabilities:
    """Tests for OpenConvAIDiscoveryService.advertise_capabilities."""

    @pytest.mark.asyncio
    async def it_returns_transaction_id_on_success(
        self, discovery_service
    ):
        """advertise_capabilities returns a dict with transaction_id."""
        result = await discovery_service.advertise_capabilities(
            agent_did=AGENT_DID,
            capabilities=CAPABILITIES,
            service_endpoint=SERVICE_ENDPOINT,
        )
        assert "transaction_id" in result

    @pytest.mark.asyncio
    async def it_submits_hcs10_discovery_message_to_topic(
        self, discovery_service, mock_hedera_client
    ):
        """advertise_capabilities submits a properly formatted discovery message."""
        await discovery_service.advertise_capabilities(
            agent_did=AGENT_DID,
            capabilities=CAPABILITIES,
            service_endpoint=SERVICE_ENDPOINT,
        )
        mock_hedera_client.submit_topic_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def it_includes_required_discovery_fields_in_message(
        self, discovery_service, mock_hedera_client
    ):
        """advertise_capabilities includes protocol, type, agent_did, capabilities, service_endpoint, heartbeat_timestamp."""
        await discovery_service.advertise_capabilities(
            agent_did=AGENT_DID,
            capabilities=CAPABILITIES,
            service_endpoint=SERVICE_ENDPOINT,
        )
        submitted_args = mock_hedera_client.submit_topic_message.call_args
        message_body = (
            submitted_args[1].get("message") or submitted_args[0][1]
        )
        import json
        parsed = json.loads(message_body)
        assert parsed["protocol"] == "hcs-10"
        assert parsed["type"] == "discovery"
        assert parsed["agent_did"] == AGENT_DID
        assert parsed["capabilities"] == CAPABILITIES
        assert parsed["service_endpoint"] == SERVICE_ENDPOINT
        assert "heartbeat_timestamp" in parsed

    @pytest.mark.asyncio
    async def it_returns_the_agent_did_in_the_result(
        self, discovery_service
    ):
        """advertise_capabilities echoes back the agent_did."""
        result = await discovery_service.advertise_capabilities(
            agent_did=AGENT_DID,
            capabilities=CAPABILITIES,
            service_endpoint=SERVICE_ENDPOINT,
        )
        assert result["agent_did"] == AGENT_DID


# ---------------------------------------------------------------------------
# DescribeDiscoverAgents
# ---------------------------------------------------------------------------

class DescribeDiscoverAgents:
    """Tests for OpenConvAIDiscoveryService.discover_agents."""

    @pytest.mark.asyncio
    async def it_returns_a_list_of_agent_records(
        self, discovery_service
    ):
        """discover_agents returns a list."""
        agents = await discovery_service.discover_agents()
        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def it_returns_agents_from_discovery_messages(
        self, discovery_service
    ):
        """discover_agents finds agents who have broadcast discovery messages."""
        agents = await discovery_service.discover_agents()
        assert len(agents) > 0

    @pytest.mark.asyncio
    async def it_filters_by_capability_when_provided(
        self, discovery_service
    ):
        """discover_agents only returns agents with the requested capability."""
        agents = await discovery_service.discover_agents(
            capability="text_analysis"
        )
        for agent in agents:
            assert "text_analysis" in agent["capabilities"]

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_capability_not_matched(
        self, discovery_service
    ):
        """discover_agents returns [] when no agent has the requested capability."""
        agents = await discovery_service.discover_agents(
            capability="quantum_teleportation"
        )
        assert agents == []

    @pytest.mark.asyncio
    async def it_returns_agent_did_and_service_endpoint_in_each_record(
        self, discovery_service
    ):
        """discover_agents includes agent_did and service_endpoint in each record."""
        agents = await discovery_service.discover_agents()
        for agent in agents:
            assert "agent_did" in agent
            assert "service_endpoint" in agent


# ---------------------------------------------------------------------------
# DescribePingAgent
# ---------------------------------------------------------------------------

class DescribePingAgent:
    """Tests for OpenConvAIDiscoveryService.ping_agent."""

    @pytest.mark.asyncio
    async def it_returns_online_true_for_agent_with_recent_heartbeat(
        self, discovery_service
    ):
        """ping_agent returns online=True when agent sent heartbeat within 5 minutes."""
        result = await discovery_service.ping_agent(agent_did=AGENT_DID)
        assert result["online"] is True

    @pytest.mark.asyncio
    async def it_returns_the_agent_did_in_ping_result(
        self, discovery_service
    ):
        """ping_agent echoes back the agent_did."""
        result = await discovery_service.ping_agent(agent_did=AGENT_DID)
        assert result["agent_did"] == AGENT_DID

    @pytest.mark.asyncio
    async def it_returns_online_false_for_agent_with_stale_heartbeat(
        self, discovery_service, mock_hedera_client
    ):
        """ping_agent returns online=False when last heartbeat is older than 5 minutes."""
        stale_ts = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        mock_hedera_client.get_topic_messages.return_value = {
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": stale_ts,
                    "message": (
                        f'{{"protocol":"hcs-10","type":"discovery",'
                        f'"agent_did":"{AGENT_DID}",'
                        f'"capabilities":[],'
                        f'"service_endpoint":"{SERVICE_ENDPOINT}",'
                        f'"heartbeat_timestamp":"{stale_ts}"}}'
                    ),
                }
            ]
        }
        result = await discovery_service.ping_agent(agent_did=AGENT_DID)
        assert result["online"] is False

    @pytest.mark.asyncio
    async def it_returns_online_false_when_no_heartbeat_exists(
        self, discovery_service, mock_hedera_client
    ):
        """ping_agent returns online=False when no discovery message found."""
        mock_hedera_client.get_topic_messages.return_value = {"messages": []}
        result = await discovery_service.ping_agent(agent_did=AGENT_DID)
        assert result["online"] is False
