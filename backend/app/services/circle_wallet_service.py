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
    InsufficientFundsError,
    DEFAULT_BLOCKCHAIN
)
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table names
WALLETS_TABLE = "circle_wallets"
TRANSFERS_TABLE = "circle_transfers"
RECEIPTS_TABLE = "payment_receipts"
WALLET_SETS_TABLE = "circle_wallet_sets"


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

    async def _get_or_create_wallet_set(
        self,
        project_id: str
    ) -> str:
        """
        Get or create a wallet set for the project.

        Each project has one wallet set that contains all agent wallets.
        If circle_wallet_set_id is configured in settings, use it directly.

        Args:
            project_id: Project identifier

        Returns:
            Wallet set ID (Circle's UUID)
        """
        # First, check if wallet set ID is configured in settings
        from app.core.config import settings
        if settings.circle_wallet_set_id:
            logger.debug(f"Using configured wallet set ID: {settings.circle_wallet_set_id}")
            return settings.circle_wallet_set_id

        # Check if we already have a wallet set for this project in ZeroDB
        try:
            result = await self.client.query_rows(
                WALLET_SETS_TABLE,
                filter={"project_id": project_id},
                limit=1
            )
            rows = result.get("rows", [])
            if rows:
                return rows[0].get("circle_wallet_set_id")
        except Exception as e:
            logger.debug(f"No existing wallet set found: {e}")

        # Create a new wallet set via Circle API
        idempotency_key = f"walletset_{project_id}_{uuid.uuid4().hex[:8]}"

        try:
            response = await self.circle_service.create_wallet_set(
                idempotency_key=idempotency_key,
                name=f"Agent wallets for {project_id}"
            )

            wallet_set = response.get("data", {}).get("walletSet", {})
            circle_wallet_set_id = wallet_set.get("id")

            if not circle_wallet_set_id:
                raise ValueError("Failed to get wallet set ID from Circle response")

            # Store in ZeroDB
            wallet_set_data = {
                "wallet_set_id": f"ws_{uuid.uuid4().hex[:12]}",
                "project_id": project_id,
                "circle_wallet_set_id": circle_wallet_set_id,
                "name": f"Agent wallets for {project_id}",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            await self.client.insert_row(WALLET_SETS_TABLE, wallet_set_data)
            logger.info(f"Created wallet set {circle_wallet_set_id} for project {project_id}")

            return circle_wallet_set_id

        except Exception as e:
            logger.error(f"Failed to create wallet set: {e}")
            raise

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
            idempotency_key = str(uuid.uuid4())

        # Get or create wallet set for this project
        wallet_set_id = await self._get_or_create_wallet_set(project_id)

        # Create wallet via Circle API
        circle_response = await self.circle_service.create_wallet(
            idempotency_key=idempotency_key,
            blockchain=DEFAULT_BLOCKCHAIN,
            wallet_set_id=wallet_set_id,
            metadata=[{"name": f"{wallet_type} wallet for {agent_did[:20]}..."}]
        )

        # Get the first wallet from the response (we create 1 at a time)
        wallets = circle_response.get("data", {}).get("wallets", [])
        if not wallets:
            raise ValueError("No wallets returned from Circle API")

        circle_data = wallets[0]

        # Build wallet record
        wallet_id = self._generate_wallet_id()
        now = datetime.now(timezone.utc)

        wallet_data = {
            "wallet_id": wallet_id,
            "project_id": project_id,
            "circle_wallet_id": circle_data.get("id"),
            "agent_did": agent_did,
            "wallet_type": wallet_type,
            "status": "active",
            "blockchain_address": circle_data.get("address"),
            "blockchain": circle_data.get("blockchain", DEFAULT_BLOCKCHAIN),
            "wallet_set_id": wallet_set_id,
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

        First tries ZeroDB, then falls back to Circle API directly.

        Args:
            wallet_id: Wallet identifier (can be our ID or Circle wallet ID)
            project_id: Project identifier

        Returns:
            Dict containing wallet details

        Raises:
            WalletNotFoundError: If wallet not found
        """
        rows = []

        # Try ZeroDB first
        try:
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"wallet_id": wallet_id, "project_id": project_id},
                limit=1
            )
            rows = result.get("rows", [])
        except Exception as e:
            logger.debug(f"ZeroDB query failed, will try Circle API: {e}")

        # If not in ZeroDB, try Circle API directly
        if not rows:
            wallet = await self._get_wallet_from_circle(wallet_id)
            if wallet:
                # Fetch balance
                try:
                    balance_data = await self.circle_service.get_wallet_balance(wallet_id)
                    wallet["balance"] = balance_data.get("amount", "0.00")
                except Exception as e:
                    logger.warning(f"Could not fetch balance: {e}")
                return wallet
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

        First tries ZeroDB, then falls back to Circle API directly
        if no wallets found (for wallets created outside our API).

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

            # If no wallets in ZeroDB, try Circle API directly
            if not rows:
                rows = await self._list_wallets_from_circle()
                total = len(rows)

            return rows, total

        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            # Fallback to Circle API on error
            try:
                rows = await self._list_wallets_from_circle()
                return rows, len(rows)
            except Exception:
                return [], 0

    async def _list_wallets_from_circle(self) -> List[Dict[str, Any]]:
        """
        List wallets directly from Circle API using configured wallet set.

        Returns:
            List of wallet dicts in our internal format
        """
        from app.core.config import settings

        if not settings.circle_wallet_set_id:
            return []

        try:
            response = await self.circle_service.list_wallets(
                wallet_set_id=settings.circle_wallet_set_id
            )

            circle_wallets = response.get("data", {}).get("wallets", [])
            now = datetime.now(timezone.utc).isoformat()

            # Convert Circle format to our internal format
            wallets = []
            for cw in circle_wallets:
                # Extract wallet type from name (e.g., "Analyst Agent" -> "analyst")
                name = cw.get("name", "").lower()
                if "analyst" in name:
                    wallet_type = "analyst"
                elif "compliance" in name:
                    wallet_type = "compliance"
                elif "transaction" in name:
                    wallet_type = "transaction"
                else:
                    wallet_type = "unknown"

                wallet = {
                    "wallet_id": cw.get("id"),  # Use Circle ID as wallet_id
                    "circle_wallet_id": cw.get("id"),
                    "agent_did": cw.get("refId", ""),
                    "wallet_type": wallet_type,
                    "status": "active" if cw.get("state") == "LIVE" else "inactive",
                    "blockchain_address": cw.get("address"),
                    "blockchain": cw.get("blockchain", DEFAULT_BLOCKCHAIN),
                    "wallet_set_id": cw.get("walletSetId"),
                    "balance": "0.00",  # Will be fetched separately
                    "description": cw.get("name"),
                    "created_at": cw.get("createDate", now),
                    "updated_at": cw.get("updateDate", now)
                }
                wallets.append(wallet)

            return wallets

        except Exception as e:
            logger.error(f"Failed to list wallets from Circle: {e}")
            return []

    async def _get_wallet_from_circle(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single wallet directly from Circle API.

        Args:
            wallet_id: Circle wallet ID

        Returns:
            Wallet dict in our internal format, or None if not found
        """
        try:
            response = await self.circle_service.get_wallet(wallet_id)
            cw = response.get("data", {}).get("wallet", {})

            if not cw:
                return None

            # Extract wallet type from name
            name = cw.get("name", "").lower()
            if "analyst" in name:
                wallet_type = "analyst"
            elif "compliance" in name:
                wallet_type = "compliance"
            elif "transaction" in name:
                wallet_type = "transaction"
            else:
                wallet_type = "unknown"

            now = datetime.now(timezone.utc).isoformat()

            return {
                "wallet_id": cw.get("id"),
                "circle_wallet_id": cw.get("id"),
                "agent_did": cw.get("refId", ""),
                "wallet_type": wallet_type,
                "status": "active" if cw.get("state") == "LIVE" else "inactive",
                "blockchain_address": cw.get("address"),
                "blockchain": cw.get("blockchain", DEFAULT_BLOCKCHAIN),
                "wallet_set_id": cw.get("walletSetId"),
                "balance": "0.00",
                "description": cw.get("name"),
                "created_at": cw.get("createDate", now),
                "updated_at": cw.get("updateDate", now)
            }

        except Exception as e:
            logger.error(f"Failed to get wallet from Circle: {e}")
            return None

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

        # Generate idempotency key if not provided (must be UUID format for Circle)
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Create transfer via Circle API
        # Note: Circle API requires destination_address (blockchain address), not wallet ID
        circle_response = await self.circle_service.create_transfer(
            source_wallet_id=source_wallet.get("circle_wallet_id"),
            destination_address=dest_wallet.get("blockchain_address"),
            amount=amount,
            idempotency_key=idempotency_key
        )

        circle_data = circle_response.get("data", circle_response)

        # Build transfer record
        # Note: Circle API returns 'id' (transaction ID) and 'state' (not 'status')
        transfer_id = self._generate_transfer_id()
        now = datetime.now(timezone.utc)

        # Map Circle's transaction state to our status
        circle_state = circle_data.get("state", "INITIATED")
        status_map = {
            "INITIATED": "pending",
            "QUEUED": "pending",
            "SENT": "pending",
            "CONFIRMED": "pending",
            "COMPLETE": "complete",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "DENIED": "denied"
        }
        status = status_map.get(circle_state, "pending")

        transfer_data = {
            "transfer_id": transfer_id,
            "project_id": project_id,
            "circle_transfer_id": circle_data.get("id"),
            "source_wallet_id": source_wallet_id,
            "destination_wallet_id": destination_wallet_id,
            "amount": amount,
            "currency": "USD",
            "status": status,
            "circle_state": circle_state,
            "x402_request_id": x402_request_id,
            "transaction_hash": circle_data.get("transactionHash"),
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "completed_at": None
        }

        # Store in ZeroDB (non-fatal - Circle transfer already succeeded)
        try:
            await self.client.insert_row(TRANSFERS_TABLE, transfer_data)
            logger.info(
                f"Created transfer {transfer_id}: "
                f"{source_wallet_id} -> {destination_wallet_id}, "
                f"amount: {amount}"
            )
        except Exception as e:
            logger.warning(f"Failed to store transfer in ZeroDB (transfer succeeded on Circle): {e}")

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

                # Map Circle's state to our status
                circle_state = circle_data.get("state", transfer.get("circle_state"))
                status_map = {
                    "INITIATED": "pending",
                    "QUEUED": "pending",
                    "SENT": "pending",
                    "CONFIRMED": "pending",
                    "COMPLETE": "complete",
                    "FAILED": "failed",
                    "CANCELLED": "cancelled",
                    "DENIED": "denied"
                }
                transfer["status"] = status_map.get(circle_state, transfer["status"])
                transfer["circle_state"] = circle_state
                transfer["transaction_hash"] = circle_data.get(
                    "txHash",
                    circle_data.get("transactionHash", transfer.get("transaction_hash"))
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

    async def get_treasury_wallet(self, project_id: str) -> Dict[str, Any]:
        """
        Get the platform treasury wallet for a project.

        The treasury wallet is the source for agent payments.
        If no treasury wallet exists, this will raise an error.

        Args:
            project_id: Project identifier

        Returns:
            Dict containing treasury wallet details

        Raises:
            WalletNotFoundError: If no treasury wallet found
        """
        try:
            # Query for a wallet with wallet_type = "treasury"
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"project_id": project_id, "wallet_type": "treasury"},
                limit=1
            )

            rows = result.get("rows", [])
            if rows:
                return rows[0]

            # Fallback: check for a wallet with "treasury" in description
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"project_id": project_id},
                limit=100
            )

            for row in result.get("rows", []):
                desc = row.get("description", "").lower()
                if "treasury" in desc or "platform" in desc:
                    return row

            raise WalletNotFoundError("treasury")

        except WalletNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get treasury wallet: {e}")
            raise WalletNotFoundError("treasury")

    async def pay_agent(
        self,
        project_id: str,
        agent_id: str,
        amount: str,
        reason: str,
        task_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pay an agent from the platform treasury wallet.

        This method:
        1. Looks up the agent's Circle wallet
        2. Gets the treasury wallet as the payment source
        3. Initiates a USDC transfer from treasury to agent
        4. Records the payment in ZeroDB

        Args:
            project_id: Project identifier
            agent_id: Agent identifier (agent_xxx format)
            amount: Payment amount in USDC (e.g., "10.00")
            reason: Reason for the payment
            task_id: Optional task reference ID
            idempotency_key: Optional idempotency key

        Returns:
            Dict containing payment details

        Raises:
            WalletNotFoundError: If agent or treasury wallet not found
            InsufficientFundsError: If treasury has insufficient funds
        """
        logger.info(f"Processing agent payment: agent={agent_id}, amount={amount}")

        # First, get the agent's wallet
        # We need to look up by agent_id to find their DID, then find their wallet
        agent_wallet = await self._get_agent_wallet_by_id(agent_id, project_id)

        if not agent_wallet:
            raise WalletNotFoundError(f"agent:{agent_id}")

        # Get the treasury wallet
        treasury_wallet = await self.get_treasury_wallet(project_id)

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Initiate the transfer
        transfer = await self.initiate_transfer(
            project_id=project_id,
            source_wallet_id=treasury_wallet["wallet_id"],
            destination_wallet_id=agent_wallet["wallet_id"],
            amount=amount,
            idempotency_key=idempotency_key,
            metadata={
                "payment_type": "agent_payment",
                "agent_id": agent_id,
                "reason": reason,
                "task_id": task_id
            }
        )

        # Build payment record
        payment_id = f"payment_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        payment_data = {
            "payment_id": payment_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "agent_did": agent_wallet.get("agent_did"),
            "amount": amount,
            "currency": "USD",
            "reason": reason,
            "task_id": task_id,
            "transfer_id": transfer["transfer_id"],
            "circle_transfer_id": transfer["circle_transfer_id"],
            "status": transfer["status"],
            "transaction_hash": transfer.get("transaction_hash"),
            "source_wallet_id": treasury_wallet["wallet_id"],
            "destination_wallet_id": agent_wallet["wallet_id"],
            "created_at": now.isoformat(),
            "completed_at": transfer.get("completed_at")
        }

        # Store payment record
        try:
            await self.client.insert_row("agent_payments", payment_data)
            logger.info(f"Created agent payment {payment_id} for agent {agent_id}")
        except Exception as e:
            logger.warning(f"Failed to store payment record (transfer still succeeded): {e}")

        return payment_data

    async def _get_agent_wallet_by_id(
        self,
        agent_id: str,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an agent's wallet by their agent ID.

        First looks up the agent to get their DID, then finds their wallet.

        Args:
            agent_id: Agent identifier
            project_id: Project identifier

        Returns:
            Wallet dict if found, None otherwise
        """
        try:
            # Try to find wallet by agent_id stored in metadata
            result = await self.client.query_rows(
                WALLETS_TABLE,
                filter={"project_id": project_id},
                limit=100
            )

            for wallet in result.get("rows", []):
                # Check if this wallet belongs to the agent
                wallet_agent_id = wallet.get("agent_id")
                if wallet_agent_id == agent_id:
                    return wallet

            # If not found by agent_id, try looking up the agent's DID
            # and then finding the wallet by DID
            from app.services.agent_service import agent_service
            try:
                agent = await agent_service.get_agent(agent_id, project_id)
                if agent:
                    # Now find wallet by agent DID
                    for wallet in result.get("rows", []):
                        if wallet.get("agent_did") == agent.did:
                            return wallet
            except Exception:
                pass

            return None

        except Exception as e:
            logger.error(f"Error looking up agent wallet: {e}")
            return None

    async def get_agent_payment(
        self,
        payment_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get an agent payment by ID.

        Args:
            payment_id: Payment identifier
            project_id: Project identifier

        Returns:
            Dict containing payment details

        Raises:
            TransferNotFoundError: If payment not found
        """
        try:
            result = await self.client.query_rows(
                "agent_payments",
                filter={"payment_id": payment_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise TransferNotFoundError(payment_id)

            payment = rows[0]

            # Get current transfer status
            try:
                transfer = await self.get_transfer(
                    payment["transfer_id"],
                    project_id
                )
                payment["status"] = transfer["status"]
                payment["transaction_hash"] = transfer.get("transaction_hash")
                if transfer.get("completed_at"):
                    payment["completed_at"] = transfer["completed_at"]
            except Exception as e:
                logger.warning(f"Could not fetch transfer status: {e}")

            return payment

        except TransferNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment {payment_id}: {e}")
            raise TransferNotFoundError(payment_id)


# Global service instance
circle_wallet_service = CircleWalletService()
