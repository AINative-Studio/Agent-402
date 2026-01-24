"""
Circle API Service Layer.
Implements Circle API client for USDC wallet and transfer operations.

Issue #114: Implement Circle Wallets and USDC Payments

This service handles:
- Wallet set creation via Circle API
- Wallet creation via Circle API
- Wallet balance retrieval
- USDC transfer operations
- Transfer status tracking

Per PRD Section 8 (X402 Protocol):
- Circle wallets enable USDC payments for X402 transactions
- All operations are logged for audit trail

Security:
- API key is stored securely (never logged)
- All requests use HTTPS
- Idempotency keys prevent duplicate operations
- Entity secret is encrypted using Circle's public key

API Documentation:
- Base URL: https://api.circle.com
- Auth: Bearer token with format PREFIX:ID:SECRET
- Blockchain: ARC-TESTNET for testnet operations
"""
import uuid
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.errors import APIError
from app.services.circle_crypto import (
    generate_entity_secret_ciphertext,
    CircleCryptoError
)

logger = logging.getLogger(__name__)

# Circle API Configuration
CIRCLE_PRODUCTION_URL = "https://api.circle.com"
CIRCLE_SANDBOX_URL = "https://api-sandbox.circle.com"

# Default blockchain for testnet operations
DEFAULT_BLOCKCHAIN = "ARC-TESTNET"


class CircleAPIError(APIError):
    """
    Raised when Circle API calls fail.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: CIRCLE_API_ERROR
        - detail: Message about the Circle API failure
    """

    def __init__(self, detail: str, status_code: int = 502):
        """
        Initialize CircleAPIError.

        Args:
            detail: Human-readable error message about the failure
            status_code: HTTP status code from Circle API
        """
        super().__init__(
            status_code=status_code,
            error_code="CIRCLE_API_ERROR",
            detail=detail or "Circle API error"
        )
        self.circle_status_code = status_code


class WalletNotFoundError(APIError):
    """
    Raised when a Circle wallet is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: WALLET_NOT_FOUND
        - detail: Message including wallet ID
    """

    def __init__(self, wallet_id: str):
        detail = f"Wallet not found: {wallet_id}" if wallet_id else "Wallet not found"
        super().__init__(
            status_code=404,
            error_code="WALLET_NOT_FOUND",
            detail=detail
        )
        self.wallet_id = wallet_id


class TransferNotFoundError(APIError):
    """
    Raised when a Circle transfer is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: TRANSFER_NOT_FOUND
        - detail: Message including transfer ID
    """

    def __init__(self, transfer_id: str):
        detail = f"Transfer not found: {transfer_id}" if transfer_id else "Transfer not found"
        super().__init__(
            status_code=404,
            error_code="TRANSFER_NOT_FOUND",
            detail=detail
        )
        self.transfer_id = transfer_id


class InsufficientFundsError(APIError):
    """
    Raised when a wallet has insufficient funds for transfer.

    Returns:
        - HTTP 400 (Bad Request)
        - error_code: INSUFFICIENT_FUNDS
        - detail: Message with requested and available amounts
    """

    def __init__(self, wallet_id: str, requested: str, available: str):
        detail = (
            f"Insufficient funds in wallet {wallet_id}. "
            f"Requested: {requested} USDC, Available: {available} USDC"
        )
        super().__init__(
            status_code=400,
            error_code="INSUFFICIENT_FUNDS",
            detail=detail
        )
        self.wallet_id = wallet_id
        self.requested = requested
        self.available = available


class CircleService:
    """
    Circle API client service.

    Handles direct communication with Circle's API for:
    - Wallet set creation
    - Wallet creation and management
    - Balance queries
    - Transfer operations

    Uses Circle's Developer-Controlled Wallets API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        entity_secret: str = None
    ):
        """
        Initialize the Circle service.

        Args:
            api_key: Circle API key (required)
            base_url: Optional custom base URL (defaults to production)
            entity_secret: Entity secret for signing operations (32-byte hex string)
        """
        self.api_key = api_key
        self.base_url = base_url or CIRCLE_PRODUCTION_URL
        self.entity_secret = entity_secret
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        return self._client

    async def _get_entity_secret_ciphertext(self) -> str:
        """
        Generate a fresh entity secret ciphertext for API requests.

        Returns:
            Base64-encoded entity secret ciphertext

        Raises:
            CircleAPIError: If ciphertext generation fails
        """
        if not self.entity_secret:
            raise CircleAPIError(
                "Entity secret not configured. Set circle_entity_secret in config.",
                status_code=500
            )

        try:
            ciphertext = await generate_entity_secret_ciphertext(
                entity_secret_hex=self.entity_secret,
                api_key=self.api_key,
                base_url=self.base_url
            )
            return ciphertext
        except CircleCryptoError as e:
            logger.error(f"Failed to generate entity secret ciphertext: {e.message}")
            raise CircleAPIError(
                f"Entity secret encryption failed: {e.message}",
                status_code=500
            )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Circle API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            API response data

        Raises:
            CircleAPIError: If API call fails
            WalletNotFoundError: If wallet not found (404)
            TransferNotFoundError: If transfer not found (404)
        """
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params
            )

            if response.status_code == 404:
                # Determine if it's a wallet or transfer not found
                if "wallet" in endpoint.lower():
                    wallet_id = endpoint.split("/")[-1]
                    if "/balances" in endpoint:
                        wallet_id = endpoint.split("/")[-2]
                    raise WalletNotFoundError(wallet_id)
                elif "transaction" in endpoint.lower():
                    transfer_id = endpoint.split("/")[-1]
                    raise TransferNotFoundError(transfer_id)

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("message", f"Circle API error: {response.status_code}")
                raise CircleAPIError(error_message, response.status_code)

            return response.json()

        except (WalletNotFoundError, TransferNotFoundError, CircleAPIError):
            raise
        except httpx.TimeoutException:
            raise CircleAPIError("Circle API request timed out", 504)
        except httpx.RequestError as e:
            raise CircleAPIError(f"Circle API connection error: {str(e)}", 502)
        except Exception as e:
            logger.error(f"Unexpected error in Circle API request: {e}")
            raise CircleAPIError(f"Unexpected error: {str(e)}", 500)

    async def create_wallet_set(
        self,
        idempotency_key: str,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Create a new wallet set.

        A wallet set groups related wallets together. Each entity can have
        up to 1,000 wallet sets, with each set supporting up to 10 million wallets.

        Args:
            idempotency_key: Unique key for idempotent creation (UUID v4)
            name: Optional name for the wallet set

        Returns:
            Dict containing wallet set details:
            - id: Wallet set identifier
            - custodyType: DEVELOPER or ENDUSER
            - createDate: ISO-8601 timestamp
            - updateDate: ISO-8601 timestamp

        Raises:
            CircleAPIError: If wallet set creation fails
        """
        logger.info(f"Creating Circle wallet set with idempotency key: {idempotency_key}")

        ciphertext = await self._get_entity_secret_ciphertext()

        request_data = {
            "entitySecretCiphertext": ciphertext,
            "idempotencyKey": idempotency_key
        }

        if name:
            request_data["name"] = name

        result = await self._make_request(
            method="POST",
            endpoint="/v1/w3s/developer/walletSets",
            data=request_data
        )

        logger.info(f"Created wallet set: {result.get('data', {}).get('walletSet', {}).get('id')}")
        return result

    async def create_wallet(
        self,
        idempotency_key: str,
        blockchain: str = DEFAULT_BLOCKCHAIN,
        wallet_set_id: str = None,
        count: int = 1,
        metadata: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new Circle wallet.

        Args:
            idempotency_key: Unique key for idempotent creation (UUID v4)
            blockchain: Target blockchain (default: ARC-TESTNET)
            wallet_set_id: Required wallet set ID for grouping
            count: Number of wallets to create (1-200, default: 1)
            metadata: Optional list of metadata dicts with name/refId

        Returns:
            Dict containing wallet details:
            - wallets: List of created wallet objects, each with:
              - id: Wallet identifier (UUID)
              - address: Blockchain address
              - blockchain: Target blockchain
              - state: Wallet state (LIVE, FROZEN)
              - walletSetId: Parent wallet set ID
              - createDate: ISO-8601 timestamp

        Raises:
            CircleAPIError: If wallet creation fails
        """
        logger.info(
            f"Creating Circle wallet(s) with idempotency key: {idempotency_key}, "
            f"blockchain: {blockchain}, count: {count}"
        )

        if not wallet_set_id:
            raise CircleAPIError(
                "wallet_set_id is required for wallet creation",
                status_code=400
            )

        ciphertext = await self._get_entity_secret_ciphertext()

        request_data = {
            "entitySecretCiphertext": ciphertext,
            "idempotencyKey": idempotency_key,
            "blockchains": [blockchain],
            "walletSetId": wallet_set_id,
            "count": count
        }

        if metadata:
            request_data["metadata"] = metadata

        result = await self._make_request(
            method="POST",
            endpoint="/v1/w3s/developer/wallets",
            data=request_data
        )

        wallets = result.get("data", {}).get("wallets", [])
        wallet_ids = [w.get("id") for w in wallets]
        logger.info(f"Created wallet(s): {wallet_ids}")

        return result

    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """
        Get wallet details by Circle wallet ID.

        Args:
            wallet_id: Circle wallet identifier (UUID)

        Returns:
            Dict containing wallet details

        Raises:
            WalletNotFoundError: If wallet not found
            CircleAPIError: If API call fails
        """
        logger.info(f"Getting Circle wallet: {wallet_id}")

        result = await self._make_request(
            method="GET",
            endpoint=f"/v1/w3s/wallets/{wallet_id}"
        )

        return result

    async def get_wallet_balance(self, wallet_id: str) -> Dict[str, Any]:
        """
        Get USDC balance for a wallet.

        Args:
            wallet_id: Circle wallet identifier (UUID)

        Returns:
            Dict containing balance information:
            - data.tokenBalances: List of token balance objects, each with:
              - token: Token details (id, name, symbol, blockchain)
              - amount: Balance amount as string
              - updateDate: ISO-8601 timestamp
            - amount: Convenience field with first token balance
            - currency: Currency code (e.g., "USDC")

        Raises:
            WalletNotFoundError: If wallet not found
            CircleAPIError: If API call fails
        """
        logger.info(f"Getting wallet balance: {wallet_id}")

        result = await self._make_request(
            method="GET",
            endpoint=f"/v1/w3s/wallets/{wallet_id}/balances"
        )

        # Add convenience fields for easier access
        token_balances = result.get("data", {}).get("tokenBalances", [])
        if token_balances:
            first_balance = token_balances[0]
            result["amount"] = first_balance.get("amount", "0")
            result["currency"] = first_balance.get("token", {}).get("symbol", "USDC")
        else:
            result["amount"] = "0"
            result["currency"] = "USDC"

        return result

    async def create_transfer(
        self,
        source_wallet_id: str,
        destination_address: str,
        amount: str,
        idempotency_key: str,
        blockchain: str = DEFAULT_BLOCKCHAIN,
        token_address: str = None,
        fee_level: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Create a USDC transfer from a wallet.

        Args:
            source_wallet_id: Source Circle wallet ID (UUID)
            destination_address: Destination blockchain address
            amount: Transfer amount as string (e.g., "100.00")
            idempotency_key: Unique key for idempotent transfer (UUID v4)
            blockchain: Target blockchain (default: ARC-TESTNET)
            token_address: Optional token contract address (for non-native tokens)
            fee_level: Transaction fee level (LOW, MEDIUM, HIGH)

        Returns:
            Dict containing transfer details:
            - data.id: Transaction identifier (UUID)
            - data.state: Transaction state (INITIATED, SENT, CONFIRMED, COMPLETE, FAILED)

        Raises:
            InsufficientFundsError: If source wallet has insufficient funds
            WalletNotFoundError: If source wallet not found
            CircleAPIError: If transfer creation fails
        """
        logger.info(
            f"Creating transfer: wallet {source_wallet_id} -> {destination_address}, "
            f"amount: {amount}, blockchain: {blockchain}"
        )

        ciphertext = await self._get_entity_secret_ciphertext()

        request_data = {
            "entitySecretCiphertext": ciphertext,
            "idempotencyKey": idempotency_key,
            "walletId": source_wallet_id,
            "destinationAddress": destination_address,
            "blockchain": blockchain,
            "amounts": [amount],
            "feeLevel": fee_level
        }

        # Add token address if specified (for non-native tokens)
        if token_address:
            request_data["tokenAddress"] = token_address

        try:
            result = await self._make_request(
                method="POST",
                endpoint="/v1/w3s/developer/transactions/transfer",
                data=request_data
            )
        except CircleAPIError as e:
            # Check if this is an insufficient funds error
            if "insufficient" in e.detail.lower():
                raise InsufficientFundsError(source_wallet_id, amount, "unknown")
            raise

        transfer_id = result.get("data", {}).get("id")
        state = result.get("data", {}).get("state")
        logger.info(f"Created transfer: {transfer_id}, state: {state}")

        return result

    async def get_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """
        Get transfer details and status.

        Args:
            transfer_id: Circle transaction identifier (UUID)

        Returns:
            Dict containing transfer details:
            - data.id: Transaction ID
            - data.state: Transaction state
            - data.transactionHash: Blockchain transaction hash (when complete)
            - data.amounts: Transfer amounts
            - data.sourceAddress: Source wallet address
            - data.destinationAddress: Destination address

        Raises:
            TransferNotFoundError: If transfer not found
            CircleAPIError: If API call fails
        """
        logger.info(f"Getting transfer status: {transfer_id}")

        result = await self._make_request(
            method="GET",
            endpoint=f"/v1/w3s/transactions/{transfer_id}"
        )

        return result

    async def list_wallets(
        self,
        wallet_set_id: str = None,
        blockchain: str = None,
        page_size: int = 50,
        page_before: str = None,
        page_after: str = None
    ) -> Dict[str, Any]:
        """
        List wallets with optional filtering.

        Args:
            wallet_set_id: Filter by wallet set ID
            blockchain: Filter by blockchain
            page_size: Number of results per page (1-50, default: 50)
            page_before: Pagination cursor for previous page
            page_after: Pagination cursor for next page

        Returns:
            Dict containing:
            - data.wallets: List of wallet objects
        """
        logger.info(f"Listing wallets, wallet_set_id: {wallet_set_id}, blockchain: {blockchain}")

        params = {
            "pageSize": min(page_size, 50)
        }

        if wallet_set_id:
            params["walletSetId"] = wallet_set_id
        if blockchain:
            params["blockchain"] = blockchain
        if page_before:
            params["pageBefore"] = page_before
        if page_after:
            params["pageAfter"] = page_after

        result = await self._make_request(
            method="GET",
            endpoint="/v1/w3s/wallets",
            params=params
        )

        return result

    async def list_transactions(
        self,
        wallet_id: str = None,
        blockchain: str = None,
        page_size: int = 50,
        page_before: str = None,
        page_after: str = None
    ) -> Dict[str, Any]:
        """
        List transactions with optional filtering.

        Args:
            wallet_id: Filter by wallet ID
            blockchain: Filter by blockchain
            page_size: Number of results per page (1-50, default: 50)
            page_before: Pagination cursor for previous page
            page_after: Pagination cursor for next page

        Returns:
            Dict containing:
            - data.transactions: List of transaction objects
        """
        logger.info(f"Listing transactions, wallet_id: {wallet_id}, blockchain: {blockchain}")

        params = {
            "pageSize": min(page_size, 50)
        }

        if wallet_id:
            params["walletIds"] = wallet_id
        if blockchain:
            params["blockchain"] = blockchain
        if page_before:
            params["pageBefore"] = page_before
        if page_after:
            params["pageAfter"] = page_after

        result = await self._make_request(
            method="GET",
            endpoint="/v1/w3s/transactions",
            params=params
        )

        return result

    async def close(self):
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Helper function to get Circle service instance
def get_circle_service() -> CircleService:
    """
    Get a Circle service instance.

    Uses environment configuration for API key and entity secret.
    In production, this should use proper secret management.

    Returns:
        Configured CircleService instance
    """
    from app.core.config import settings

    # Get API key from settings
    api_key = getattr(settings, 'circle_api_key', None)
    if not api_key:
        raise CircleAPIError("Circle API key not configured", status_code=500)

    # Get base URL (defaults to production)
    base_url = getattr(settings, 'circle_base_url', CIRCLE_PRODUCTION_URL)

    # Get entity secret
    entity_secret = getattr(settings, 'circle_entity_secret', None)

    return CircleService(
        api_key=api_key,
        base_url=base_url,
        entity_secret=entity_secret
    )
