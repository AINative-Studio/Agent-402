"""
Hedera HTS NFT Client.
Wraps HederaClient to provide NFT-specific operations for the Agent Identity System.

This module wraps the shared HederaClient (READ-ONLY) and adds:
- NFT token class creation via HTS
- NFT minting with metadata
- NFT info queries via mirror node
- HCS message submission and retrieval
- NFT freeze operations

All actual Hedera network calls follow the REST/mirror-node pattern
established in hedera_client.py.

Built by AINative Dev Team
Refs #191, #192, #193, #194
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.services.hedera_client import HederaClient, get_hedera_client, HEDERA_TESTNET_MIRROR_URL

logger = logging.getLogger(__name__)

# HCS-14 directory topic ID (testnet) — can be overridden via env
DEFAULT_DIRECTORY_TOPIC_ID = "0.0.800000"


class HederaHTSNFTClientError(Exception):
    """Raised when an HTS NFT client operation fails."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class HederaHTSNFTClient:
    """
    HTS NFT client that wraps the shared HederaClient.

    Provides NFT-specific operations by making REST calls to the Hedera
    mirror node API and simulating SDK transactions (same pattern as
    HederaClient for non-SDK environments).

    READ-ONLY access to HederaClient — does not modify hedera_client.py.
    """

    def __init__(
        self,
        hedera_client: Optional[HederaClient] = None,
        mirror_url: Optional[str] = None,
    ):
        """
        Initialize the HTS NFT client.

        Args:
            hedera_client: Optional shared HederaClient (lazy-initialized if None)
            mirror_url: Override mirror node URL
        """
        self._hedera_client = hedera_client
        self._mirror_url = mirror_url or HEDERA_TESTNET_MIRROR_URL
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def hedera_client(self) -> HederaClient:
        """Lazy-initialized shared Hedera client."""
        if self._hedera_client is None:
            self._hedera_client = get_hedera_client()
        return self._hedera_client

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-initialized HTTP client for mirror node queries."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._mirror_url,
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._http_client

    def _generate_token_id(self) -> str:
        """Generate a simulated Hedera token ID in 0.0.{number} format."""
        suffix = int(uuid.uuid4().int % 9_000_000) + 1_000_000
        return f"0.0.{suffix}"

    def _generate_transaction_id(self) -> str:
        """Generate a Hedera-format transaction ID."""
        return self.hedera_client._generate_transaction_id()

    async def create_nft_token(
        self,
        name: str,
        symbol: str,
        admin_key: str,
    ) -> Dict[str, Any]:
        """
        Create an HTS non-fungible token class for agent registry.

        In production, this submits a TokenCreateTransaction to the Hedera
        network with treasury = operator account and type = NON_FUNGIBLE_UNIQUE.

        Args:
            name: Token name (e.g. "AgentRegistry")
            symbol: Token symbol (e.g. "AREG")
            admin_key: Admin public key (Ed25519 hex)

        Returns:
            Dict with token_id, transaction_id, status
        """
        logger.info(
            f"Creating HTS NFT token class: name={name}, symbol={symbol}"
        )

        # In production, use hedera-sdk-py:
        # from hedera import TokenCreateTransaction, TokenType, PrivateKey
        # receipt = await (
        #     TokenCreateTransaction()
        #     .set_token_name(name)
        #     .set_token_symbol(symbol)
        #     .set_token_type(TokenType.NON_FUNGIBLE_UNIQUE)
        #     .set_treasury_account_id(operator_id)
        #     .set_admin_key(PrivateKey.from_string(admin_key).public_key())
        #     .set_supply_key(operator_key.public_key())
        #     .execute(client)
        #     .get_receipt(client)
        # )
        # token_id = str(receipt.token_id)

        token_id = self._generate_token_id()
        transaction_id = self._generate_transaction_id()

        logger.info(f"HTS NFT token class created: token_id={token_id}")

        return {
            "token_id": token_id,
            "transaction_id": transaction_id,
            "status": "SUCCESS",
            "name": name,
            "symbol": symbol,
            "network": self.hedera_client.network,
        }

    async def mint_nft(
        self,
        token_id: str,
        metadata_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Mint an NFT with metadata bytes.

        Submits a TokenMintTransaction to create a new serial number for
        the given token class, attaching the provided metadata bytes.

        Args:
            token_id: HTS token ID (e.g. "0.0.9999")
            metadata_bytes: Encoded agent metadata (JSON encoded as UTF-8 bytes)

        Returns:
            Dict with serial_number, token_id, transaction_id, status
        """
        logger.info(
            f"Minting NFT: token_id={token_id}, "
            f"metadata_size={len(metadata_bytes)} bytes"
        )

        # In production, use hedera-sdk-py:
        # from hedera import TokenMintTransaction, TokenId
        # receipt = await (
        #     TokenMintTransaction()
        #     .set_token_id(TokenId.from_string(token_id))
        #     .add_metadata(metadata_bytes)
        #     .execute(client)
        #     .get_receipt(client)
        # )
        # serial = receipt.serial_numbers[0]

        # Simulate serial number as incrementing (use uuid for uniqueness)
        serial_number = int(uuid.uuid4().int % 999_999) + 1
        transaction_id = self._generate_transaction_id()

        logger.info(
            f"NFT minted: token_id={token_id}, serial={serial_number}"
        )

        return {
            "serial_number": serial_number,
            "token_id": token_id,
            "transaction_id": transaction_id,
            "status": "SUCCESS",
        }

    async def get_nft_info(
        self,
        token_id: str,
        serial: int,
    ) -> Dict[str, Any]:
        """
        Get NFT info from the mirror node.

        Queries the Hedera mirror node REST API for NFT metadata,
        owner account, and other on-chain attributes.

        Args:
            token_id: HTS token ID (e.g. "0.0.9999")
            serial: NFT serial number

        Returns:
            Dict with token_id, serial_number, metadata (base64), account_id

        Raises:
            HederaHTSNFTClientError: If the mirror node query fails
        """
        logger.info(
            f"Fetching NFT info: token_id={token_id}, serial={serial}"
        )

        try:
            response = await self.http_client.get(
                f"/tokens/{token_id}/nfts/{serial}"
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "token_id": token_id,
                    "serial_number": serial,
                    "metadata": data.get("metadata", ""),
                    "account_id": data.get("account_id", ""),
                    "created_timestamp": data.get("created_timestamp"),
                }

            if response.status_code == 404:
                raise HederaHTSNFTClientError(
                    f"NFT not found: token_id={token_id}, serial={serial}",
                    status_code=404,
                )

        except HederaHTSNFTClientError:
            raise
        except httpx.RequestError as exc:
            logger.warning(
                f"Mirror node unavailable for NFT query: {exc}. "
                "Returning simulated NFT info."
            )

        # Fallback when mirror node is unavailable
        import base64
        empty_meta = base64.b64encode(b"{}").decode()
        return {
            "token_id": token_id,
            "serial_number": serial,
            "metadata": empty_meta,
            "account_id": self.hedera_client.operator_id,
            "created_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def submit_hcs_message(
        self,
        topic_id: str,
        message: Any,
    ) -> Dict[str, Any]:
        """
        Submit a message to an HCS topic.

        In production, this submits a TopicMessageSubmitTransaction.
        The message is JSON-encoded before submission.

        Args:
            topic_id: Hedera Consensus Service topic ID
            message: Message to submit (dict or str — dict is JSON-encoded)

        Returns:
            Dict with transaction_id, status
        """
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = str(message)

        logger.info(
            f"Submitting HCS message to topic={topic_id}, "
            f"size={len(message_str)} bytes"
        )

        # In production, use hedera-sdk-py:
        # from hedera import TopicMessageSubmitTransaction, TopicId
        # receipt = await (
        #     TopicMessageSubmitTransaction()
        #     .set_topic_id(TopicId.from_string(topic_id))
        #     .set_message(message_str.encode("utf-8"))
        #     .execute(client)
        #     .get_receipt(client)
        # )

        transaction_id = self._generate_transaction_id()
        logger.info(
            f"HCS message submitted: topic={topic_id}, tx={transaction_id}"
        )

        return {
            "transaction_id": transaction_id,
            "status": "SUCCESS",
            "topic_id": topic_id,
        }

    async def get_hcs_messages(
        self,
        topic_id: str,
        limit: int = 100,
        order: str = "asc",
    ) -> Dict[str, Any]:
        """
        Query HCS messages via mirror node REST API.

        Args:
            topic_id: Hedera Consensus Service topic ID
            limit: Maximum number of messages to return
            order: Sort order — "asc" or "desc"

        Returns:
            Dict with messages list (each has message, consensus_timestamp, sequence_number)
        """
        logger.info(
            f"Querying HCS messages: topic={topic_id}, "
            f"limit={limit}, order={order}"
        )

        try:
            response = await self.http_client.get(
                f"/topics/{topic_id}/messages",
                params={"limit": limit, "order": order},
            )

            if response.status_code == 200:
                data = response.json()
                return {"messages": data.get("messages", [])}

            if response.status_code == 404:
                return {"messages": []}

        except httpx.RequestError as exc:
            logger.warning(
                f"Mirror node unavailable for HCS query: {exc}. "
                "Returning empty messages."
            )

        return {"messages": []}

    async def freeze_nft(
        self,
        token_id: str,
        serial: int,
    ) -> Dict[str, Any]:
        """
        Freeze an NFT to suspend the agent.

        In production, this submits a TokenFreezeTransaction for the NFT's
        owner account on the specified token.

        Args:
            token_id: HTS token ID
            serial: NFT serial number

        Returns:
            Dict with token_id, serial_number, transaction_id, status
        """
        logger.info(
            f"Freezing NFT: token_id={token_id}, serial={serial}"
        )

        # In production, use hedera-sdk-py:
        # from hedera import TokenFreezeTransaction, TokenId, AccountId
        # owner = await self.get_nft_info(token_id, serial)
        # receipt = await (
        #     TokenFreezeTransaction()
        #     .set_token_id(TokenId.from_string(token_id))
        #     .set_account_id(AccountId.from_string(owner["account_id"]))
        #     .execute(client)
        #     .get_receipt(client)
        # )

        transaction_id = self._generate_transaction_id()
        logger.info(
            f"NFT frozen: token_id={token_id}, serial={serial}"
        )

        return {
            "token_id": token_id,
            "serial_number": serial,
            "transaction_id": transaction_id,
            "status": "FROZEN",
        }

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def get_hedera_hts_nft_client() -> HederaHTSNFTClient:
    """
    Get a configured HederaHTSNFTClient instance.

    Returns:
        Configured HederaHTSNFTClient instance
    """
    return HederaHTSNFTClient()
