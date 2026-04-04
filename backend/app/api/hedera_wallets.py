"""
Hedera Wallets API endpoints.
Implements agent wallet creation and management via Hedera Hashgraph.

Issue #188: Agent Wallet Creation

Endpoints:
- POST /v1/public/{project_id}/hedera/wallets
    Create a new Hedera account for an agent
- GET  /v1/public/{project_id}/hedera/wallets/{agent_id}
    Get stored wallet info for an agent
- GET  /v1/public/{project_id}/hedera/wallets/{account_id}/balance
    Get HBAR + USDC balance for a Hedera account
- POST /v1/public/{project_id}/hedera/wallets/{account_id}/associate-usdc
    Associate USDC HTS token with a Hedera account

All endpoints require X-API-Key authentication.

Built by AINative Dev Team
Refs #188
"""
import logging
from fastapi import APIRouter, Depends, status

from app.schemas.hedera import (
    HederaWalletCreateRequest,
    HederaWalletResponse,
    HederaBalanceResponse,
    HederaTokenAssociationResponse
)
from app.services.hedera_wallet_service import (
    HederaWalletService,
    HederaWalletNotFoundError,
    get_hedera_wallet_service
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/v1/public",
    tags=["hedera-wallets"]
)


@router.post(
    "/{project_id}/hedera/wallets",
    response_model=HederaWalletResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Wallet created successfully",
            "model": HederaWalletResponse
        },
        400: {
            "description": "Invalid request (empty agent_id)"
        },
        422: {
            "description": "Validation error"
        },
        502: {
            "description": "Hedera network error"
        }
    },
    summary="Create Hedera wallet for agent",
    description="""
    Create a new Hedera account for an agent.

    **Authentication:** Requires X-API-Key header

    **Issue #188:** Agent Wallet Creation

    Creates a Hedera account via AccountCreateTransaction and stores
    wallet metadata in ZeroDB. After creation, call associate-usdc
    to enable USDC token receipt.

    **Required fields:**
    - agent_id: Agent identifier to link wallet to

    **Optional fields:**
    - initial_balance: Initial HBAR funding in whole HBAR units (default: 0)

    **Returns:**
    - account_id: Hedera account ID (e.g., 0.0.12345)
    - public_key: Account public key
    - network: "testnet" or "mainnet"
    """
)
async def create_hedera_wallet(
    project_id: str,
    request: HederaWalletCreateRequest,
    wallet_service: HederaWalletService = Depends(get_hedera_wallet_service)
) -> HederaWalletResponse:
    """
    Create a Hedera wallet for an agent.

    Args:
        project_id: Project identifier from URL
        request: Wallet creation request body
        wallet_service: Injected HederaWalletService

    Returns:
        HederaWalletResponse with created wallet details
    """
    logger.info(
        f"POST /hedera/wallets: project={project_id}, "
        f"agent={request.agent_id}, initial_balance={request.initial_balance}"
    )

    wallet = await wallet_service.create_agent_wallet(
        agent_id=request.agent_id,
        initial_balance=request.initial_balance
    )

    return HederaWalletResponse(
        agent_id=wallet["agent_id"],
        account_id=wallet["account_id"],
        public_key=wallet["public_key"],
        network=wallet["network"],
        created_at=wallet["created_at"]
    )


@router.get(
    "/{project_id}/hedera/wallets/{agent_id}",
    response_model=HederaWalletResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Wallet info retrieved",
            "model": HederaWalletResponse
        },
        404: {
            "description": "No Hedera wallet found for agent"
        },
        502: {
            "description": "ZeroDB query error"
        }
    },
    summary="Get Hedera wallet info for agent",
    description="""
    Get stored Hedera wallet info for a specific agent.

    **Authentication:** Requires X-API-Key header

    Retrieves previously created wallet details from ZeroDB.
    Returns 404 if no wallet has been created for the agent.

    **Returns:**
    - account_id: Hedera account ID
    - public_key: Account public key
    - network: Network name
    - created_at: Creation timestamp
    """
)
async def get_wallet_info(
    project_id: str,
    agent_id: str,
    wallet_service: HederaWalletService = Depends(get_hedera_wallet_service)
) -> HederaWalletResponse:
    """
    Get wallet info for an agent from ZeroDB.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL
        wallet_service: Injected HederaWalletService

    Returns:
        HederaWalletResponse with wallet details

    Raises:
        HederaWalletNotFoundError: If no wallet exists for the agent
    """
    logger.info(
        f"GET /hedera/wallets/{agent_id}: project={project_id}"
    )

    wallet = await wallet_service.get_wallet_info(agent_id=agent_id)

    return HederaWalletResponse(
        agent_id=wallet["agent_id"],
        account_id=wallet["account_id"],
        public_key=wallet["public_key"],
        network=wallet.get("network", "testnet"),
        created_at=wallet["created_at"]
    )


@router.get(
    "/{project_id}/hedera/wallets/{account_id}/balance",
    response_model=HederaBalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Balance retrieved",
            "model": HederaBalanceResponse
        },
        400: {
            "description": "Invalid account ID"
        },
        502: {
            "description": "Hedera mirror node error"
        }
    },
    summary="Get HBAR and USDC balance",
    description="""
    Get HBAR and USDC balances for a Hedera account.

    **Authentication:** Requires X-API-Key header

    Queries the Hedera mirror node for live balance data.
    USDC balance is returned in decimal format (e.g., "50.000000").

    **Returns:**
    - hbar: HBAR balance in whole HBAR units
    - usdc: USDC balance in decimal format (6 decimal places)
    - usdc_raw: USDC balance in smallest unit (integer)
    """
)
async def get_wallet_balance(
    project_id: str,
    account_id: str,
    wallet_service: HederaWalletService = Depends(get_hedera_wallet_service)
) -> HederaBalanceResponse:
    """
    Get HBAR and USDC balance for a Hedera account.

    Args:
        project_id: Project identifier from URL
        account_id: Hedera account ID from URL (e.g., "0.0.12345")
        wallet_service: Injected HederaWalletService

    Returns:
        HederaBalanceResponse with HBAR and USDC balances
    """
    logger.info(
        f"GET /hedera/wallets/{account_id}/balance: project={project_id}"
    )

    balance = await wallet_service.get_balance(account_id=account_id)

    return HederaBalanceResponse(
        account_id=balance["account_id"],
        hbar=balance["hbar"],
        usdc=balance["usdc"],
        usdc_raw=balance.get("usdc_raw")
    )


@router.post(
    "/{project_id}/hedera/wallets/{account_id}/associate-usdc",
    response_model=HederaTokenAssociationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "USDC token associated successfully",
            "model": HederaTokenAssociationResponse
        },
        400: {
            "description": "Invalid account ID"
        },
        502: {
            "description": "Hedera network error"
        }
    },
    summary="Associate USDC token with Hedera account",
    description="""
    Associate the USDC HTS token with a Hedera account.

    **Authentication:** Requires X-API-Key header

    **Issue #188:** Token association for USDC

    Token association is REQUIRED before an account can receive HTS tokens
    on the Hedera network. This is a unique Hedera requirement not present
    on EVM-compatible chains.

    Must be called once per account before the account can receive USDC.
    After association, the account is ready to receive USDC transfers.

    **Returns:**
    - transaction_id: Hedera transaction ID for the association
    - status: "SUCCESS" on completion
    """
)
async def associate_usdc_token(
    project_id: str,
    account_id: str,
    wallet_service: HederaWalletService = Depends(get_hedera_wallet_service)
) -> HederaTokenAssociationResponse:
    """
    Associate USDC HTS token with a Hedera account.

    Args:
        project_id: Project identifier from URL
        account_id: Hedera account ID from URL (e.g., "0.0.12345")
        wallet_service: Injected HederaWalletService

    Returns:
        HederaTokenAssociationResponse with transaction details
    """
    logger.info(
        f"POST /hedera/wallets/{account_id}/associate-usdc: project={project_id}"
    )

    result = await wallet_service.associate_usdc_token(account_id=account_id)

    return HederaTokenAssociationResponse(
        transaction_id=result["transaction_id"],
        status=result["status"],
        account_id=result.get("account_id", account_id),
        token_id=result.get("token_id")
    )
