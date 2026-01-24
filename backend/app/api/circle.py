"""
Circle API endpoints.
Implements Circle Wallet and USDC Payment endpoints per Issue #114.

Endpoints:
- POST /v1/public/{project_id}/circle/wallets - Create wallet for agent
- GET /v1/public/{project_id}/circle/wallets - List wallets
- GET /v1/public/{project_id}/circle/wallets/{wallet_id} - Get wallet details
- POST /v1/public/{project_id}/circle/transfers - Initiate USDC transfer
- GET /v1/public/{project_id}/circle/transfers - List transfers
- GET /v1/public/{project_id}/circle/transfers/{transfer_id} - Get transfer status

All endpoints require X-API-Key authentication.
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from app.core.auth import get_current_user
from app.schemas.circle import (
    WalletCreateRequest,
    WalletResponse,
    WalletListResponse,
    TransferCreateRequest,
    TransferResponse,
    TransferListResponse,
    AgentPaymentRequest,
    AgentPaymentResponse,
    ErrorResponse,
    WalletType,
    WalletStatus,
    TransferStatus
)
from app.services.circle_wallet_service import (
    circle_wallet_service,
    DuplicateWalletError
)
from app.services.circle_service import (
    WalletNotFoundError,
    TransferNotFoundError
)
from app.services.project_service import project_service
from datetime import datetime


router = APIRouter(
    prefix="/v1/public",
    tags=["circle"]
)


def validate_project_access(project_id: str, user_id: str) -> None:
    """
    Validate that the user has access to the project.

    Args:
        project_id: Project identifier
        user_id: Authenticated user ID

    Raises:
        ProjectNotFoundError: If project not found
        UnauthorizedError: If user doesn't have access
    """
    project_service.get_project(project_id, user_id)


@router.post(
    "/{project_id}/circle/wallets",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Wallet created successfully",
            "model": WalletResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        },
        409: {
            "description": "Wallet already exists for agent/type",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Create Circle wallet for agent",
    description="""
    Create a new Circle wallet for an agent.

    **Authentication:** Requires X-API-Key header

    **Issue #114:** Circle Wallets and USDC Payments

    **Wallet Types:**
    - analyst: Wallet for analyst agent
    - compliance: Wallet for compliance agent
    - transaction: Wallet for transaction agent

    **Required fields:**
    - agent_did: Agent DID to link wallet to (did:key:z6Mk... format)
    - wallet_type: Type of wallet (analyst, compliance, transaction)

    **Optional fields:**
    - description: Wallet description
    - idempotency_key: Key for idempotent creation

    **Returns:**
    - wallet_id: Unique wallet identifier
    - circle_wallet_id: Circle platform wallet ID
    - blockchain_address: Address for USDC transfers
    - status: Wallet status (active)
    """
)
async def create_wallet(
    project_id: str,
    request: WalletCreateRequest,
    current_user: str = Depends(get_current_user)
) -> WalletResponse:
    """
    Create a new Circle wallet for an agent.

    Args:
        project_id: Project identifier from URL
        request: Wallet creation request body
        current_user: User ID from X-API-Key authentication

    Returns:
        WalletResponse with created wallet details
    """
    validate_project_access(project_id, current_user)

    wallet = await circle_wallet_service.create_agent_wallet(
        project_id=project_id,
        agent_did=request.agent_did,
        wallet_type=request.wallet_type.value,
        description=request.description,
        idempotency_key=request.idempotency_key
    )

    return WalletResponse(
        wallet_id=wallet["wallet_id"],
        circle_wallet_id=wallet["circle_wallet_id"],
        agent_did=wallet["agent_did"],
        wallet_type=WalletType(wallet["wallet_type"]),
        status=WalletStatus(wallet["status"]),
        blockchain_address=wallet["blockchain_address"],
        blockchain=wallet["blockchain"],
        balance=wallet.get("balance", "0.00"),
        description=wallet.get("description"),
        created_at=datetime.fromisoformat(wallet["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(wallet["updated_at"].replace("Z", "+00:00")) if wallet.get("updated_at") else None
    )


@router.get(
    "/{project_id}/circle/wallets",
    response_model=WalletListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved wallets list",
            "model": WalletListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="List Circle wallets",
    description="""
    List all Circle wallets in a project.

    **Authentication:** Requires X-API-Key header

    **Optional filters:**
    - wallet_type: Filter by wallet type
    - agent_did: Filter by agent DID

    **Returns:**
    - wallets: Array of wallet objects
    - total: Total number of wallets
    """
)
async def list_wallets(
    project_id: str,
    wallet_type: Optional[str] = Query(None, description="Filter by wallet type"),
    agent_did: Optional[str] = Query(None, description="Filter by agent DID"),
    current_user: str = Depends(get_current_user)
) -> WalletListResponse:
    """
    List all wallets for a project.

    Args:
        project_id: Project identifier from URL
        wallet_type: Optional filter by wallet type
        agent_did: Optional filter by agent DID
        current_user: User ID from X-API-Key authentication

    Returns:
        WalletListResponse with list of wallets and total count
    """
    validate_project_access(project_id, current_user)

    wallets, total = await circle_wallet_service.list_wallets(
        project_id=project_id,
        wallet_type=wallet_type,
        agent_did=agent_did
    )

    wallet_responses = [
        WalletResponse(
            wallet_id=w["wallet_id"],
            circle_wallet_id=w["circle_wallet_id"],
            agent_did=w["agent_did"],
            wallet_type=WalletType(w["wallet_type"]),
            status=WalletStatus(w.get("status", "active")),
            blockchain_address=w["blockchain_address"],
            blockchain=w.get("blockchain", "ETH-SEPOLIA"),
            balance=w.get("balance", "0.00"),
            description=w.get("description"),
            created_at=datetime.fromisoformat(w["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(w["updated_at"].replace("Z", "+00:00")) if w.get("updated_at") else None
        )
        for w in wallets
    ]

    return WalletListResponse(
        wallets=wallet_responses,
        total=total
    )


@router.get(
    "/{project_id}/circle/wallets/{wallet_id}",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved wallet",
            "model": WalletResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Wallet not found",
            "model": ErrorResponse
        }
    },
    summary="Get Circle wallet by ID",
    description="""
    Get a Circle wallet by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Full wallet details including current balance
    """
)
async def get_wallet(
    project_id: str,
    wallet_id: str,
    current_user: str = Depends(get_current_user)
) -> WalletResponse:
    """
    Get a single wallet by ID.

    Args:
        project_id: Project identifier from URL
        wallet_id: Wallet identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        WalletResponse with wallet details
    """
    validate_project_access(project_id, current_user)

    wallet = await circle_wallet_service.get_wallet(wallet_id, project_id)

    return WalletResponse(
        wallet_id=wallet["wallet_id"],
        circle_wallet_id=wallet["circle_wallet_id"],
        agent_did=wallet["agent_did"],
        wallet_type=WalletType(wallet["wallet_type"]),
        status=WalletStatus(wallet.get("status", "active")),
        blockchain_address=wallet["blockchain_address"],
        blockchain=wallet.get("blockchain", "ETH-SEPOLIA"),
        balance=wallet.get("balance", "0.00"),
        description=wallet.get("description"),
        created_at=datetime.fromisoformat(wallet["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(wallet["updated_at"].replace("Z", "+00:00")) if wallet.get("updated_at") else None
    )


@router.post(
    "/{project_id}/circle/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Transfer initiated successfully",
            "model": TransferResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Wallet not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Initiate USDC transfer",
    description="""
    Initiate a USDC transfer between Circle wallets.

    **Authentication:** Requires X-API-Key header

    **Issue #114:** X402 payments can trigger USDC transfers

    **Required fields:**
    - source_wallet_id: Source wallet ID
    - destination_wallet_id: Destination wallet ID
    - amount: Transfer amount in USDC

    **Optional fields:**
    - x402_request_id: Link to X402 payment request
    - idempotency_key: Key for idempotent transfer
    - metadata: Additional transfer metadata

    **Returns:**
    - transfer_id: Unique transfer identifier
    - status: Transfer status (pending, complete, failed)
    - transaction_hash: Blockchain transaction hash (when complete)
    """
)
async def create_transfer(
    project_id: str,
    request: TransferCreateRequest,
    current_user: str = Depends(get_current_user)
) -> TransferResponse:
    """
    Initiate a USDC transfer between wallets.

    Args:
        project_id: Project identifier from URL
        request: Transfer creation request body
        current_user: User ID from X-API-Key authentication

    Returns:
        TransferResponse with transfer details
    """
    validate_project_access(project_id, current_user)

    transfer = await circle_wallet_service.initiate_transfer(
        project_id=project_id,
        source_wallet_id=request.source_wallet_id,
        destination_wallet_id=request.destination_wallet_id,
        amount=request.amount,
        x402_request_id=request.x402_request_id,
        idempotency_key=request.idempotency_key,
        metadata=request.metadata
    )

    return TransferResponse(
        transfer_id=transfer["transfer_id"],
        circle_transfer_id=transfer["circle_transfer_id"],
        source_wallet_id=transfer["source_wallet_id"],
        destination_wallet_id=transfer["destination_wallet_id"],
        amount=transfer["amount"],
        currency=transfer.get("currency", "USD"),
        status=TransferStatus(transfer["status"]),
        x402_request_id=transfer.get("x402_request_id"),
        transaction_hash=transfer.get("transaction_hash"),
        created_at=datetime.fromisoformat(transfer["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(transfer["completed_at"].replace("Z", "+00:00")) if transfer.get("completed_at") else None,
        metadata=transfer.get("metadata")
    )


@router.get(
    "/{project_id}/circle/transfers",
    response_model=TransferListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved transfers list",
            "model": TransferListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="List USDC transfers",
    description="""
    List all USDC transfers in a project.

    **Authentication:** Requires X-API-Key header

    **Optional filters:**
    - status: Filter by transfer status (pending, complete, failed)
    - x402_request_id: Filter by linked X402 request

    **Pagination:**
    - limit: Maximum results (default 100)
    - offset: Pagination offset (default 0)

    **Returns:**
    - transfers: Array of transfer objects
    - total: Total number of transfers
    - limit: Current limit
    - offset: Current offset
    """
)
async def list_transfers(
    project_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    x402_request_id: Optional[str] = Query(None, description="Filter by X402 request ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: str = Depends(get_current_user)
) -> TransferListResponse:
    """
    List all transfers for a project.

    Args:
        project_id: Project identifier from URL
        status_filter: Optional filter by transfer status
        x402_request_id: Optional filter by X402 request ID
        limit: Maximum number of results
        offset: Pagination offset
        current_user: User ID from X-API-Key authentication

    Returns:
        TransferListResponse with list of transfers and pagination metadata
    """
    validate_project_access(project_id, current_user)

    transfers, total = await circle_wallet_service.list_transfers(
        project_id=project_id,
        status=status_filter,
        x402_request_id=x402_request_id,
        limit=limit,
        offset=offset
    )

    transfer_responses = [
        TransferResponse(
            transfer_id=t["transfer_id"],
            circle_transfer_id=t["circle_transfer_id"],
            source_wallet_id=t["source_wallet_id"],
            destination_wallet_id=t["destination_wallet_id"],
            amount=t["amount"],
            currency=t.get("currency", "USD"),
            status=TransferStatus(t["status"]),
            x402_request_id=t.get("x402_request_id"),
            transaction_hash=t.get("transaction_hash"),
            created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
            completed_at=datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00")) if t.get("completed_at") else None,
            metadata=t.get("metadata")
        )
        for t in transfers
    ]

    return TransferListResponse(
        transfers=transfer_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{project_id}/circle/transfers/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved transfer",
            "model": TransferResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Transfer not found",
            "model": ErrorResponse
        }
    },
    summary="Get USDC transfer by ID",
    description="""
    Get a USDC transfer by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Full transfer details including current status
    - transaction_hash when transfer is complete
    """
)
async def get_transfer(
    project_id: str,
    transfer_id: str,
    current_user: str = Depends(get_current_user)
) -> TransferResponse:
    """
    Get a single transfer by ID.

    Args:
        project_id: Project identifier from URL
        transfer_id: Transfer identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        TransferResponse with transfer details
    """
    validate_project_access(project_id, current_user)

    transfer = await circle_wallet_service.get_transfer(transfer_id, project_id)

    return TransferResponse(
        transfer_id=transfer["transfer_id"],
        circle_transfer_id=transfer["circle_transfer_id"],
        source_wallet_id=transfer["source_wallet_id"],
        destination_wallet_id=transfer["destination_wallet_id"],
        amount=transfer["amount"],
        currency=transfer.get("currency", "USD"),
        status=TransferStatus(transfer["status"]),
        x402_request_id=transfer.get("x402_request_id"),
        transaction_hash=transfer.get("transaction_hash"),
        created_at=datetime.fromisoformat(transfer["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(transfer["completed_at"].replace("Z", "+00:00")) if transfer.get("completed_at") else None,
        metadata=transfer.get("metadata")
    )


@router.post(
    "/{project_id}/agents/{agent_id}/pay",
    response_model=AgentPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Payment initiated successfully",
            "model": AgentPaymentResponse
        },
        400: {
            "description": "Invalid payment request or insufficient funds",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Agent or wallet not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Pay an agent for task completion",
    description="""
    Initiate a USDC payment to an agent from the platform treasury.

    **Authentication:** Requires X-API-Key header

    This endpoint transfers USDC from the platform treasury wallet to the
    specified agent's Circle wallet as payment for completed tasks.

    **Required fields:**
    - amount: Payment amount in USDC (e.g., "10.00")
    - reason: Reason for the payment (e.g., "Task completion payment")

    **Optional fields:**
    - task_id: Reference to the completed task
    - idempotency_key: Key for retry safety

    **Process:**
    1. Looks up the agent's Circle wallet by agent_id
    2. Gets the platform treasury wallet as payment source
    3. Initiates USDC transfer from treasury to agent
    4. Records payment in ZeroDB for audit trail

    **Returns:**
    - payment_id: Unique payment identifier
    - transfer_id: Associated Circle transfer ID
    - status: Payment status (pending, complete, failed)
    - transaction_hash: Blockchain hash when complete
    """
)
async def pay_agent(
    project_id: str,
    agent_id: str,
    request: AgentPaymentRequest,
    current_user: str = Depends(get_current_user)
) -> AgentPaymentResponse:
    """
    Pay an agent for task completion.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL
        request: Payment request body
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentPaymentResponse with payment details
    """
    validate_project_access(project_id, current_user)

    payment = await circle_wallet_service.pay_agent(
        project_id=project_id,
        agent_id=agent_id,
        amount=request.amount,
        reason=request.reason,
        task_id=request.task_id,
        idempotency_key=request.idempotency_key
    )

    return AgentPaymentResponse(
        payment_id=payment["payment_id"],
        agent_id=payment["agent_id"],
        agent_did=payment["agent_did"],
        amount=payment["amount"],
        currency=payment.get("currency", "USD"),
        reason=payment["reason"],
        task_id=payment.get("task_id"),
        transfer_id=payment["transfer_id"],
        circle_transfer_id=payment["circle_transfer_id"],
        status=TransferStatus(payment["status"]),
        transaction_hash=payment.get("transaction_hash"),
        source_wallet_id=payment["source_wallet_id"],
        destination_wallet_id=payment["destination_wallet_id"],
        created_at=datetime.fromisoformat(payment["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(payment["completed_at"].replace("Z", "+00:00")) if payment.get("completed_at") else None
    )


@router.get(
    "/{project_id}/agents/{agent_id}/payments/{payment_id}",
    response_model=AgentPaymentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved payment",
            "model": AgentPaymentResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Payment not found",
            "model": ErrorResponse
        }
    },
    summary="Get agent payment by ID",
    description="""
    Get an agent payment by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Full payment details including current status
    - transaction_hash when payment is complete
    """
)
async def get_agent_payment(
    project_id: str,
    agent_id: str,
    payment_id: str,
    current_user: str = Depends(get_current_user)
) -> AgentPaymentResponse:
    """
    Get a single agent payment by ID.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL (for validation)
        payment_id: Payment identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentPaymentResponse with payment details
    """
    validate_project_access(project_id, current_user)

    payment = await circle_wallet_service.get_agent_payment(payment_id, project_id)

    # Validate that the payment belongs to the specified agent
    if payment.get("agent_id") != agent_id:
        from app.services.circle_service import TransferNotFoundError
        raise TransferNotFoundError(payment_id)

    return AgentPaymentResponse(
        payment_id=payment["payment_id"],
        agent_id=payment["agent_id"],
        agent_did=payment["agent_did"],
        amount=payment["amount"],
        currency=payment.get("currency", "USD"),
        reason=payment["reason"],
        task_id=payment.get("task_id"),
        transfer_id=payment["transfer_id"],
        circle_transfer_id=payment["circle_transfer_id"],
        status=TransferStatus(payment["status"]),
        transaction_hash=payment.get("transaction_hash"),
        source_wallet_id=payment["source_wallet_id"],
        destination_wallet_id=payment["destination_wallet_id"],
        created_at=datetime.fromisoformat(payment["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(payment["completed_at"].replace("Z", "+00:00")) if payment.get("completed_at") else None
    )
