"""
OpenConvAI HCS-10 Discovery Service.

Issue #207: Agent Capability Discovery.

Provides:
- advertise_capabilities — broadcast HCS-10 discovery message
- discover_agents        — find agents by capability via mirror node
- ping_agent             — check if agent is online (recent heartbeat)

Discovery message format:
    {protocol, type, agent_did, capabilities, service_endpoint,
     heartbeat_timestamp}

An agent is considered "online" when its most recent heartbeat timestamp
is within 5 minutes of now.

Built by AINative Dev Team
Refs #207
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

import os
HCS10_DISCOVERY_TOPIC_ID = os.getenv(
    "HCS10_DISCOVERY_TOPIC_ID",
    os.getenv("HCS10_TOPIC_ID", "0.0.5000000"),
)

# Agent is online if heartbeat is within this window
HEARTBEAT_WINDOW_SECONDS = 300  # 5 minutes


class OpenConvAIDiscoveryService:
    """
    Manages agent capability discovery over HCS-10.

    Agents broadcast discovery messages to the shared topic.
    Other agents query the mirror node to find peers with specific capabilities.
    """

    def __init__(self, hedera_client: Any = None):
        """
        Initialise the discovery service.

        Args:
            hedera_client: HederaClient instance (injected for testability).
                           If None, a default is created from env vars.
        """
        if hedera_client is not None:
            self._hedera = hedera_client
        else:
            from app.services.hedera_client import get_hedera_client
            self._hedera = get_hedera_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def advertise_capabilities(
        self,
        agent_did: str,
        capabilities: List[str],
        service_endpoint: str,
    ) -> Dict[str, Any]:
        """
        Broadcast an HCS-10 discovery message for the agent.

        Args:
            agent_did:        DID of the advertising agent.
            capabilities:     List of capability identifiers.
            service_endpoint: URL where the agent is reachable.

        Returns:
            Dict with transaction_id, agent_did, and heartbeat_timestamp.
        """
        heartbeat_timestamp = datetime.now(timezone.utc).isoformat()

        discovery_msg: Dict[str, Any] = {
            "protocol": "hcs-10",
            "type": "discovery",
            "agent_did": agent_did,
            "capabilities": capabilities,
            "service_endpoint": service_endpoint,
            "heartbeat_timestamp": heartbeat_timestamp,
        }

        message_json = json.dumps(discovery_msg)

        logger.info(
            "Advertising agent capabilities",
            extra={"agent_did": agent_did, "capabilities": capabilities},
        )

        receipt = await self._hedera.submit_topic_message(
            topic_id=HCS10_DISCOVERY_TOPIC_ID,
            message=message_json,
        )

        return {
            "transaction_id": receipt.get("transaction_id"),
            "status": receipt.get("status", "SUCCESS"),
            "agent_did": agent_did,
            "heartbeat_timestamp": heartbeat_timestamp,
            "sequence_number": receipt.get("sequence_number"),
        }

    async def discover_agents(
        self,
        capability: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find agents that have broadcast discovery messages.

        Queries the mirror node for discovery messages and optionally
        filters results by capability.

        Args:
            capability:   If provided, only return agents with this capability.
            message_type: Unused (reserved for future message-type filtering).

        Returns:
            List of AgentCapabilityRecord dicts.
        """
        raw = await self._hedera.get_topic_messages(
            topic_id=HCS10_DISCOVERY_TOPIC_ID,
            since_sequence=0,
            limit=200,
        )

        # Collect the latest record per agent_did
        latest: Dict[str, Dict[str, Any]] = {}
        for item in raw.get("messages", []):
            try:
                msg = json.loads(item["message"])
            except (json.JSONDecodeError, KeyError):
                continue

            if msg.get("protocol") != "hcs-10" or msg.get("type") != "discovery":
                continue

            agent_did = msg.get("agent_did")
            if not agent_did:
                continue

            # Keep the most recent record (by consensus_timestamp)
            existing = latest.get(agent_did)
            if existing is None or item.get("consensus_timestamp", "") >= existing.get(
                "_consensus_timestamp", ""
            ):
                latest[agent_did] = {
                    "agent_did": agent_did,
                    "capabilities": msg.get("capabilities", []),
                    "service_endpoint": msg.get("service_endpoint", ""),
                    "heartbeat_timestamp": msg.get("heartbeat_timestamp"),
                    "_consensus_timestamp": item.get("consensus_timestamp", ""),
                }

        agents = list(latest.values())

        # Apply capability filter
        if capability is not None:
            agents = [a for a in agents if capability in a.get("capabilities", [])]

        # Remove internal key
        for a in agents:
            a.pop("_consensus_timestamp", None)

        return agents

    async def ping_agent(self, agent_did: str) -> Dict[str, Any]:
        """
        Check whether an agent is online by inspecting its most recent heartbeat.

        An agent is considered online when its latest discovery message
        heartbeat_timestamp is within HEARTBEAT_WINDOW_SECONDS of now.

        Args:
            agent_did: DID of the agent to ping.

        Returns:
            Dict with agent_did, online (bool), and last_heartbeat.
        """
        raw = await self._hedera.get_topic_messages(
            topic_id=HCS10_DISCOVERY_TOPIC_ID,
            since_sequence=0,
            limit=200,
        )

        latest_heartbeat: Optional[str] = None
        latest_ts: str = ""

        for item in raw.get("messages", []):
            try:
                msg = json.loads(item["message"])
            except (json.JSONDecodeError, KeyError):
                continue

            if (
                msg.get("protocol") != "hcs-10"
                or msg.get("type") != "discovery"
                or msg.get("agent_did") != agent_did
            ):
                continue

            item_ts = item.get("consensus_timestamp", "")
            if item_ts >= latest_ts:
                latest_ts = item_ts
                latest_heartbeat = msg.get("heartbeat_timestamp")

        if latest_heartbeat is None:
            return {
                "agent_did": agent_did,
                "online": False,
                "last_heartbeat": None,
            }

        # Parse the heartbeat timestamp and compare to now
        try:
            # Handle both offset-aware and offset-naive ISO strings
            hb_str = latest_heartbeat
            if hb_str.endswith("Z"):
                hb_str = hb_str[:-1] + "+00:00"
            hb_dt = datetime.fromisoformat(hb_str)
            now_dt = datetime.now(timezone.utc)
            if hb_dt.tzinfo is None:
                # Make offset-naive if needed
                now_dt = datetime.utcnow()
            delta = (now_dt - hb_dt).total_seconds()
            online = delta <= HEARTBEAT_WINDOW_SECONDS
        except (ValueError, TypeError):
            online = False

        return {
            "agent_did": agent_did,
            "online": online,
            "last_heartbeat": latest_heartbeat,
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_discovery_service: Optional[OpenConvAIDiscoveryService] = None


def get_openconvai_discovery_service() -> OpenConvAIDiscoveryService:
    """Return the shared OpenConvAIDiscoveryService singleton."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = OpenConvAIDiscoveryService()
    return _discovery_service
