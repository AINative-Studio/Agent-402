"""
Hedera Wallet Service.
Implements agent wallet creation and management via Hedera Hashgraph.

Issue #188: Agent Wallet Creation
- Create Hedera accounts for agents
- HBAR + USDC balance queries
- Token association for USDC (required before receiving HTS tokens on Hedera)
- Store wallet info in ZeroDB

Hedera technical notes:
- USDC on Hedera is a native HTS (Hedera Token Service) token
- Token association is REQUIRED before an account can receive HTS tokens
- Network: testnet (testnet.mirrornode.hedera.com)
- USDC token ID (testnet): 0.0.456858

Built by AINative Dev Team
Refs #188
"""
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.errors import APIError
from app.services.hedera_client import HederaClient, get_hedera_client, USDC_TOKEN_ID_TESTNET
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# ZeroDB table for storing Hedera wallet info
HEDERA_WALLETS_TABLE = "hedera_wallets"

# Default USDC token ID for testnet
DEFAULT_USDC_TOKEN_ID = USDC_TOKEN_ID_TESTNET


class HederaWalletError(APIError):
    """
    Raised when a Hedera wallet operation fails.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: HEDERA_WALLET_ERROR
        - detail: Human-readable error message
    """

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(
            status_code=status_code,
            error_code="HEDERA_WALLET_ERROR",
            detail=detail or "Hedera wallet error"
        )


class HederaWalletNotFoundError(APIError):
    """
    Raised when a Hedera wallet is not found for the given agent.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: HEDERA_WALLET_NOT_FOUND
        - detail: Message including agent ID
    """

    def __init__(self, agent_id: str):
        detail = (
            f"No Hedera wallet found for agent: {agent_id}"
            if agent_id
            else "Hedera wallet not found"
        )
        super().__init__(
            status_code=404,
            error_code="HEDERA_WALLET_NOT_FOUND",
            detail=detail
        )
        self.agent_id = agent_id


class HederaWalletService:
    """
    Service for managing Hedera agent wallets.

    Provides methods for:
    - Creating Hedera accounts for agents
    - Querying HBAR and USDC balances
    - Associating USDC HTS token with accounts
    - Storing and retrieving wallet info from ZeroDB

    Token association is REQUIRED before an account can receive HTS tokens.
    Always call associate_usdc_token() after create_agent_wallet().
    """

    def __init__(
        self,
        zerodb_client=None,
        hedera_client: Optional[HederaClient] = None
    ):
        """
        Initialize the Hedera wallet service.

        Args:
            zerodb_client: Optional ZeroDB client instance (for testing)
            hedera_client: Optional Hedera client instance (for testing)
        """
        self._zerodb_client = zerodb_client
        self._hedera_client = hedera_client

    @property
    def zerodb_client(self):
        """Lazy initialization of ZeroDB client."""
        if self._zerodb_client is None:
            self._zerodb_client = get_zerodb_client()
        return self._zerodb_client

    @property
    def hedera_client(self) -> HederaClient:
        """Lazy initialization of Hedera client."""
        if self._hedera_client is None:
            self._hedera_client = get_hedera_client()
        return self._hedera_client

    async def create_agent_wallet(
        self,
        agent_id: str,
        initial_balance: int = 0
    ) -> Dict[str, Any]:
        """
        Create a new Hedera account for an agent.

        Submits an AccountCreateTransaction to the Hedera network and stores
        the resulting wallet info in ZeroDB for future retrieval.

        Note: After creating a wallet, call associate_usdc_token() to enable
        the account to receive USDC HTS tokens.

        Args:
            agent_id: Agent identifier to associate with the wallet
            initial_balance: Initial HBAR balance to fund the account (whole HBAR)

        Returns:
            Dict containing:
            - agent_id: Agent identifier
            - account_id: Hedera account ID (e.g., "0.0.12345")
            - public_key: Account public key (hex-encoded)
            - network: Network name ("testnet" or "mainnet")
            - created_at: ISO timestamp

        Raises:
            ValueError: If agent_id is empty
            HederaWalletError: If account creation fails
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        logger.info(
            f"Creating Hedera wallet for agent: {agent_id}, "
            f"initial_balance={initial_balance} HBAR"
        )

        try:
            # Create Hedera account via SDK
            account_result = await self.hedera_client.create_account(
                initial_balance=initial_balance
            )

            timestamp = datetime.now(timezone.utc).isoformat()

            wallet_data = {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "account_id": account_result["account_id"],
                "public_key": account_result["public_key"],
                "network": account_result.get("network", "testnet"),
                "initial_balance_hbar": initial_balance,
                "created_at": timestamp,
                "updated_at": timestamp
            }

            # Persist to ZeroDB
            await self.zerodb_client.insert_row(HEDERA_WALLETS_TABLE, wallet_data)
            logger.info(
                f"Hedera wallet created and stored: agent={agent_id}, "
                f"account={account_result['account_id']}"
            )

            return wallet_data

        except (ValueError, HederaWalletError):
            raise
        except Exception as e:
            logger.error(f"Failed to create Hedera wallet for agent {agent_id}: {e}")
            raise HederaWalletError(
                f"Failed to create Hedera wallet: {str(e)}"
            )

    async def associate_usdc_token(
        self,
        account_id: str,
        token_id: str = DEFAULT_USDC_TOKEN_ID
    ) -> Dict[str, Any]:
        """
        Associate the USDC HTS token with a Hedera account.

        Token association is REQUIRED before an account can receive HTS tokens
        on the Hedera network. This is a Hedera-specific requirement that differs
        from EVM-compatible chains.

        Args:
            account_id: Hedera account ID to associate the token with
            token_id: HTS token ID (defaults to USDC testnet: 0.0.456858)

        Returns:
            Dict containing:
            - transaction_id: Hedera transaction ID
            - status: "SUCCESS" on success
            - account_id: The account that was associated

        Raises:
            ValueError: If account_id is empty
            HederaWalletError: If token association fails
        """
        if not account_id or not account_id.strip():
            raise ValueError("account_id cannot be empty")

        logger.info(
            f"Associating USDC token {token_id} with account: {account_id}"
        )

        try:
            result = await self.hedera_client.associate_token(
                account_id=account_id,
                token_id=token_id
            )

            logger.info(
                f"USDC token associated: account={account_id}, "
                f"token={token_id}, tx={result.get('transaction_id')}"
            )

            return result

        except (ValueError, HederaWalletError):
            raise
        except Exception as e:
            logger.error(
                f"Failed to associate USDC token with account {account_id}: {e}"
            )
            raise HederaWalletError(
                f"Token association failed for account {account_id}: {str(e)}"
            )

    async def get_balance(self, account_id: str) -> Dict[str, Any]:
        """
        Get HBAR and USDC balances for a Hedera account.

        Queries the Hedera mirror node for live balance data.
        USDC balance is returned in the token's smallest unit (6 decimal places).

        Args:
            account_id: Hedera account ID (e.g., "0.0.12345")

        Returns:
            Dict containing:
            - account_id: The queried account
            - hbar: HBAR balance as string (whole HBAR units)
            - usdc: USDC balance as string (decimal format, e.g., "50.000000")
            - usdc_raw: USDC balance in smallest unit (integer string)

        Raises:
            ValueError: If account_id is empty
            HederaWalletError: If balance query fails
        """
        if not account_id or not account_id.strip():
            raise ValueError("account_id cannot be empty")

        logger.info(f"Querying balance for Hedera account: {account_id}")

        try:
            balance_result = await self.hedera_client.get_account_balance(
                account_id=account_id
            )

            # Extract USDC balance
            tokens = balance_result.get("tokens", {})
            usdc_raw = tokens.get(DEFAULT_USDC_TOKEN_ID, "0")
            usdc_decimal = str(int(usdc_raw) / 1_000_000) if usdc_raw else "0.000000"

            return {
                "account_id": account_id,
                "hbar": balance_result.get("hbar", "0"),
                "usdc": usdc_decimal,
                "usdc_raw": usdc_raw
            }

        except (ValueError, HederaWalletError):
            raise
        except Exception as e:
            logger.error(f"Failed to get balance for account {account_id}: {e}")
            raise HederaWalletError(
                f"Balance query failed for account {account_id}: {str(e)}"
            )

    async def get_wallet_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Get stored wallet info for an agent from ZeroDB.

        Args:
            agent_id: Agent identifier

        Returns:
            Dict containing wallet details as stored in ZeroDB

        Raises:
            HederaWalletNotFoundError: If no wallet exists for the agent
            HederaWalletError: If the ZeroDB query fails
        """
        logger.info(f"Getting wallet info for agent: {agent_id}")

        try:
            result = await self.zerodb_client.query_rows(
                HEDERA_WALLETS_TABLE,
                filter={"agent_id": agent_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise HederaWalletNotFoundError(agent_id)

            return rows[0]

        except HederaWalletNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get wallet info for agent {agent_id}: {e}")
            raise HederaWalletError(
                f"Failed to retrieve wallet info for agent {agent_id}: {str(e)}"
            )


# Global service instance
hedera_wallet_service = HederaWalletService()


def get_hedera_wallet_service() -> HederaWalletService:
    """
    Get a HederaWalletService instance.

    Returns:
        Configured HederaWalletService instance
    """
    return hedera_wallet_service
