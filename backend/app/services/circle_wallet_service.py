"""
Circle Wallet Service Layer.
Implements wallet management for agent wallets and USDC transfers.

Issue #114: Implement Circle Wallets and USDC Payments

This service handles:
- Wallet creation linked to agent DIDs
- Wallet management for 3 agent types (analyst, compliance, transaction)
- USDC transfer initiation and tracking
- Payment receipt generation and storage

Uses ZeroDB for persistence via the circle_wallets and circle_transfers tables.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from app.core.errors import APIError
from app.services.circle_service import (
    CircleService,
    get_circle_service,
    WalletNotFoundError,
    TransferNotFoundError,
    InsufficientFundsError
)
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table names
WALLETS_TABLE = "circle_wallets"
TRANSFERS_TABLE = "circle_transfers"
RECEIPTS_TABLE = "payment_receipts"


class DuplicateWalletError(APIError):
    """
    Raised when attempting to create a duplicate wallet for an agent/type.

    Returns:
        - HTTP 409 (Conflict)
        - error_code: DUPLICATE_WALLET
        - detail: Message about duplicate wallet
    """

    def __init__(self, agent_did: str, wallet_type: str):
        detail = (
            f"Wallet of type '{wallet_type}' already exists "
            f"for agent: {agent_did}"
        )
        super().__init__(
            status_code=409,
            error_code="DUPLICATE_WALLET",
            detail=detail
        )
        self.agent_did = agent_did
        self.wallet_type = wallet_type


class CircleWalletService:
    """
    Wallet management service for agent Circle wallets.

    Manages the lifecycle of Circle wallets linked to agent DIDs:
    - Creates wallets via Circle API
    - Stores wallet metadata in ZeroDB
    - Tracks wallet balances
    - Initiates and tracks USDC transfers
    - Generates payment receipts

    Each agent can have up to 3 wallets (analyst, compliance, transaction).
    """

    def __init__(self, client=None, circle_service: CircleService = None):
        """
        Initialize the wallet service.

        Args:
            client: Optional ZeroDB client instance (for testing)
            circle_service: Optional Circle service instance (for testing)
        """
        self._client = client
        self._circle_service = circle_service

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    @property
    def circle_service(self) -> CircleService:
        """Lazy initialization of Circle service."""
        if self._circle_service is None:
            self._circle_service = get_circle_service()
        return self._circle_service

    def _generate_wallet_id(self) -> str:
        """Generate a unique wallet ID."""
        return f"wallet_{uuid.uuid4().hex[:12]}"

    def _generate_transfer_id(self) -> str:
        """Generate a unique transfer ID."""
        return f"transfer_{uuid.uuid4().hex[:12]}"

    def _generate_receipt_id(self) -> str:
        """Generate a unique receipt ID."""
        return f"receipt_{uuid.uuid4().hex[:12]}"

    async def _wallet_exists(
        self,
        agent_did: str,
        wallet_type: str,
        project_id: str
    ) -> bool:
        """
        Check if a wallet already exists for the agent/type combination.

        Args:
            agent_did: Agent DID
            wallet_type: Type of wallet (analyst, compliance, transaction)
            project_id: Project identifier

        Returns:
            True if wallet exists, False otherwise
        """
        try:
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={
                    "agent_did": agent_did,
                    "wallet_type": wallet_type,
                    "project_id": project_id
                },
                limit=1
            )
            return len(result.get("rows", [])) > 0
        except Exception as e:
            logger.error(f"Error checking wallet existence: {e}")
            return False

    async def create_agent_wallet(
        self,
        project_id: str,
        agent_did: str,
        wallet_type: str,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Circle wallet for an agent.

        Args:
            project_id: Project identifier
            agent_did: Agent DID to link wallet to
            wallet_type: Type of wallet (analyst, compliance, transaction)
            description: Optional wallet description
            idempotency_key: Optional idempotency key

        Returns:
            Dict containing wallet details

        Raises:
            DuplicateWalletError: If wallet already exists for agent/type
        """
        # Check for duplicate
        if await self._wallet_exists(agent_did, wallet_type, project_id):
            raise DuplicateWalletError(agent_did, wallet_type)

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"wlt_{uuid.uuid4().hex}"

        # Create wallet via Circle API
        circle_response = await self.circle_service.create_wallet(
            idempotency_key=idempotency_key,
            blockchain="ETH-SEPOLIA"
        )

        circle_data = circle_response.get("data", circle_response)

        # Build wallet record
        wallet_id = self._generate_wallet_id()
        now = datetime.now(timezone.utc)

        wallet_data = {
            "wallet_id": wallet_id,
            "project_id": project_id,
            "circle_wallet_id": circle_data.get("walletId"),
            "agent_did": agent_did,
            "wallet_type": wallet_type,
            "status": "active",
            "blockchain_address": circle_data.get("address"),
            "blockchain": circle_data.get("blockchain", "ETH-SEPOLIA"),
            "balance": "0.00",
            "description": description,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        # Store in ZeroDB
        try:
            await self.client.insert_row(WALLETS_TABLE, wallet_data)
            logger.info(f"Created wallet {wallet_id} for agent {agent_did}")
        except Exception as e:
            logger.error(f"Failed to store wallet in ZeroDB: {e}")
            raise

        return wallet_data

    async def get_wallet(
        self,
        wallet_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get wallet details by ID.

        Args:
            wallet_id: Wallet identifier
            project_id: Project identifier

        Returns:
            Dict containing wallet details

        Raises:
            WalletNotFoundError: If wallet not found
        """
        try:
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"wallet_id": wallet_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise WalletNotFoundError(wallet_id)

            wallet = rows[0]

            # Get current balance from Circle
            try:
                balance_data = await self.circle_service.get_wallet_balance(
                    wallet.get("circle_wallet_id")
                )
                wallet["balance"] = balance_data.get("amount", "0.00")
            except Exception as e:
                logger.warning(f"Could not fetch balance: {e}")

            return wallet

        except WalletNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get wallet {wallet_id}: {e}")
            raise WalletNotFoundError(wallet_id)

    async def get_wallet_by_agent(
        self,
        agent_did: str,
        wallet_type: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get wallet by agent DID and wallet type.

        Args:
            agent_did: Agent DID
            wallet_type: Type of wallet
            project_id: Project identifier

        Returns:
            Dict containing wallet details

        Raises:
            WalletNotFoundError: If wallet not found
        """
        try:
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={
                    "agent_did": agent_did,
                    "wallet_type": wallet_type,
                    "project_id": project_id
                },
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise WalletNotFoundError(f"{agent_did}/{wallet_type}")

            return rows[0]

        except WalletNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get wallet for agent {agent_did}: {e}")
            raise WalletNotFoundError(f"{agent_did}/{wallet_type}")

    async def list_agent_wallets(
        self,
        agent_did: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all wallets for an agent.

        Args:
            agent_did: Agent DID
            project_id: Project identifier

        Returns:
            List of wallet records
        """
        try:
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"agent_did": agent_did, "project_id": project_id},
                limit=10
            )

            return result.get("rows", [])

        except Exception as e:
            logger.error(f"Failed to list wallets for agent {agent_did}: {e}")
            return []

    async def list_wallets(
        self,
        project_id: str,
        wallet_type: Optional[str] = None,
        agent_did: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List wallets with optional filters.

        Args:
            project_id: Project identifier
            wallet_type: Optional filter by wallet type
            agent_did: Optional filter by agent DID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (list of wallets, total count)
        """
        try:
            query_filter: Dict[str, Any] = {"project_id": project_id}
            if wallet_type:
                query_filter["wallet_type"] = wallet_type
            if agent_did:
                query_filter["agent_did"] = agent_did

            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter=query_filter,
                limit=limit,
                skip=offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            return rows, total

        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            return [], 0

    async def initiate_transfer(
        self,
        project_id: str,
        source_wallet_id: str,
        destination_wallet_id: str,
        amount: str,
        x402_request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate a USDC transfer between wallets.

        Args:
            project_id: Project identifier
            source_wallet_id: Source wallet ID
            destination_wallet_id: Destination wallet ID
            amount: Transfer amount as string
            x402_request_id: Optional linked X402 request ID
            idempotency_key: Optional idempotency key
            metadata: Optional additional metadata

        Returns:
            Dict containing transfer details

        Raises:
            WalletNotFoundError: If source or destination wallet not found
            InsufficientFundsError: If source wallet has insufficient funds
        """
        # Get source and destination wallets
        source_wallet = await self.get_wallet(source_wallet_id, project_id)
        dest_wallet = await self.get_wallet(destination_wallet_id, project_id)

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"xfr_{uuid.uuid4().hex}"

        # Create transfer via Circle API
        circle_response = await self.circle_service.create_transfer(
            source_wallet_id=source_wallet.get("circle_wallet_id"),
            destination_wallet_id=dest_wallet.get("circle_wallet_id"),
            amount=amount,
            idempotency_key=idempotency_key
        )

        circle_data = circle_response.get("data", circle_response)

        # Build transfer record
        transfer_id = self._generate_transfer_id()
        now = datetime.now(timezone.utc)

        transfer_data = {
            "transfer_id": transfer_id,
            "project_id": project_id,
            "circle_transfer_id": circle_data.get("transferId"),
            "source_wallet_id": source_wallet_id,
            "destination_wallet_id": destination_wallet_id,
            "amount": amount,
            "currency": "USD",
            "status": circle_data.get("status", "pending"),
            "x402_request_id": x402_request_id,
            "transaction_hash": circle_data.get("transactionHash"),
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "completed_at": None
        }

        # Store in ZeroDB
        try:
            await self.client.insert_row(TRANSFERS_TABLE, transfer_data)
            logger.info(
                f"Created transfer {transfer_id}: "
                f"{source_wallet_id} -> {destination_wallet_id}, "
                f"amount: {amount}"
            )
        except Exception as e:
            logger.error(f"Failed to store transfer in ZeroDB: {e}")
            raise

        return transfer_data

    async def get_transfer(
        self,
        transfer_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get transfer details by ID.

        Args:
            transfer_id: Transfer identifier
            project_id: Project identifier

        Returns:
            Dict containing transfer details

        Raises:
            TransferNotFoundError: If transfer not found
        """
        try:
            result = await self.client.query_rows(
                TRANSFERS_TABLE,
                filter={"transfer_id": transfer_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise TransferNotFoundError(transfer_id)

            transfer = rows[0]

            # Get current status from Circle
            try:
                circle_transfer = await self.circle_service.get_transfer(
                    transfer.get("circle_transfer_id")
                )
                circle_data = circle_transfer.get("data", circle_transfer)
                transfer["status"] = circle_data.get("status", transfer["status"])
                transfer["transaction_hash"] = circle_data.get(
                    "transactionHash",
                    transfer.get("transaction_hash")
                )

                # Update status in ZeroDB if changed
                if transfer["status"] == "complete" and not transfer.get("completed_at"):
                    transfer["completed_at"] = datetime.now(timezone.utc).isoformat()
                    await self._update_transfer_status(transfer_id, transfer)

            except Exception as e:
                logger.warning(f"Could not fetch transfer status from Circle: {e}")

            return transfer

        except TransferNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get transfer {transfer_id}: {e}")
            raise TransferNotFoundError(transfer_id)

    async def _update_transfer_status(
        self,
        transfer_id: str,
        transfer_data: Dict[str, Any]
    ) -> None:
        """Update transfer status in ZeroDB."""
        try:
            result = await self.client.query_rows(
                TRANSFERS_TABLE,
                filter={"transfer_id": transfer_id},
                limit=1
            )

            rows = result.get("rows", [])
            if rows:
                row_id = rows[0].get("row_id", rows[0].get("id"))
                if row_id:
                    await self.client.update_row(TRANSFERS_TABLE, str(row_id), transfer_data)

        except Exception as e:
            logger.error(f"Failed to update transfer status: {e}")

    async def list_transfers(
        self,
        project_id: str,
        status: Optional[str] = None,
        x402_request_id: Optional[str] = None,
        source_wallet_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List transfers with optional filters.

        Args:
            project_id: Project identifier
            status: Optional filter by status
            x402_request_id: Optional filter by X402 request ID
            source_wallet_id: Optional filter by source wallet
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (list of transfers, total count)
        """
        try:
            query_filter: Dict[str, Any] = {"project_id": project_id}
            if status:
                query_filter["status"] = status
            if x402_request_id:
                query_filter["x402_request_id"] = x402_request_id
            if source_wallet_id:
                query_filter["source_wallet_id"] = source_wallet_id

            result = await self.client.query_rows(
                TRANSFERS_TABLE,
                filter=query_filter,
                limit=limit,
                skip=offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            # Sort by created_at descending
            rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return rows, total

        except Exception as e:
            logger.error(f"Failed to list transfers: {e}")
            return [], 0

    async def update_wallet_status(
        self,
        wallet_id: str,
        project_id: str,
        status: str,
        reason: Optional[str] = None,
        frozen_until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update wallet status in ZeroDB.

        Args:
            wallet_id: Wallet identifier
            project_id: Project identifier
            status: New wallet status
            reason: Optional reason for status change
            frozen_until: Optional timestamp for automatic unfreeze

        Returns:
            Dict containing updated wallet data

        Raises:
            WalletNotFoundError: If wallet not found
        """
        try:
            # Query to find the wallet row
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"wallet_id": wallet_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise WalletNotFoundError(wallet_id)

            wallet = rows[0]
            row_id = wallet.get("row_id", wallet.get("id"))

            if not row_id:
                logger.error(f"No row_id found for wallet {wallet_id}")
                raise WalletNotFoundError(wallet_id)

            # Update wallet data
            now = datetime.now(timezone.utc)
            updated_data = {
                **wallet,
                "status": status,
                "updated_at": now.isoformat()
            }

            # Add optional fields if provided
            if reason:
                updated_data["status_reason"] = reason
            if frozen_until:
                updated_data["frozen_until"] = frozen_until

            # Update in ZeroDB
            await self.client.update_row(WALLETS_TABLE, str(row_id), updated_data)
            logger.info(f"Updated wallet {wallet_id} status to {status}")

            return updated_data

        except WalletNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update wallet status: {e}")
            raise WalletNotFoundError(wallet_id)

    async def generate_receipt(
        self,
        transfer_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate a payment receipt for a completed transfer.

        Args:
            transfer_id: Transfer identifier
            project_id: Project identifier

        Returns:
            Dict containing receipt details
        """
        # Get transfer details
        transfer = await self.get_transfer(transfer_id, project_id)

        # Get source and destination wallets for agent DIDs
        source_wallet = await self.get_wallet(
            transfer["source_wallet_id"],
            project_id
        )
        dest_wallet = await self.get_wallet(
            transfer["destination_wallet_id"],
            project_id
        )

        # Build receipt record
        receipt_id = self._generate_receipt_id()
        now = datetime.now(timezone.utc)

        receipt_data = {
            "receipt_id": receipt_id,
            "transfer_id": transfer_id,
            "project_id": project_id,
            "x402_request_id": transfer.get("x402_request_id"),
            "source_agent_did": source_wallet.get("agent_did"),
            "destination_agent_did": dest_wallet.get("agent_did"),
            "amount": transfer.get("amount"),
            "currency": transfer.get("currency", "USD"),
            "status": transfer.get("status"),
            "transaction_hash": transfer.get("transaction_hash"),
            "blockchain": source_wallet.get("blockchain", "ETH-SEPOLIA"),
            "metadata": transfer.get("metadata", {}),
            "created_at": now.isoformat()
        }

        # Store receipt in ZeroDB
        try:
            await self.client.insert_row(RECEIPTS_TABLE, receipt_data)
            logger.info(f"Generated receipt {receipt_id} for transfer {transfer_id}")
        except Exception as e:
            logger.error(f"Failed to store receipt: {e}")
            raise

        return receipt_data


# Global service instance
circle_wallet_service = CircleWalletService()
