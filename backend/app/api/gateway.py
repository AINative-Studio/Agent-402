"""
Circle Gateway API endpoints.
Implements gasless payment flow for agent hiring using Circle x402 Batching SDK.

Issue #147: Backend Circle Gateway Service for Payment Verification

Endpoints:
- POST /v1/public/gateway/{project_id}/hire-agent - Hire agent with gasless payment
- POST /v1/public/gateway/deposit - Get deposit instructions

All endpoints require X-API-Key authentication.
Payment endpoints require X-Payment-Signature header.
"""
import uuid
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, status
from app.core.auth import get_current_user
from app.services.gateway_service import gateway_service
from app.services.x402_service import x402_service
from app.services.project_service import project_service
from app.schemas.gateway import (
    HireAgentGatewayRequest,
    HireAgentGatewayResponse,
    GatewayDepositRequest,
    GatewayDepositResponse,
    ErrorResponse
)
from app.schemas.x402_requests import X402RequestStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/public/gateway",
    tags=["gateway"]
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
    "/{project_id}/hire-agent",
    response_model=HireAgentGatewayResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Task created successfully with gasless payment",
            "model": HireAgentGatewayResponse
        },
        401: {
            "description": "Invalid or missing API key / Invalid signature",
            "model": ErrorResponse
        },
        402: {
            "description": "Payment required / Insufficient payment",
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
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Hire agent with gasless payment (Circle Gateway)",
    description="""
    Hire an agent using Circle x402 Batching SDK (gasless payment).

    **Payment Flow:**
    1. User deposits USDC to Gateway (one-time setup)
    2. User signs payment intent with wallet (gasless, no blockchain transaction)
    3. Frontend sends X-Payment-Signature header with request
    4. Backend verifies signature and creates task
    5. Gateway batches multiple payments and settles on-chain periodically

    **Headers Required:**
    - X-API-Key: AINative authentication
    - X-Payment-Signature: Gateway payment intent signature
      Format: "payer=0x...,amount=10.50,signature=0x...,network=arc-testnet"

    **Benefits:**
    - No gas fees for users (gasless payments)
    - Instant confirmation (no waiting for blockchain)
    - Cost-effective for micropayments ($1-5 tasks)
    - Batched settlement reduces gas by 10-100x

    **Returns:**
    - task_id: Unique task identifier
    - x402_request_id: Audit trail ID
    - payment_status: "pending_settlement" (will settle in batch)
    - estimated_settlement_time: When batch settlement will occur
    """
)
async def hire_agent_gasless(
    project_id: str,
    request_body: HireAgentGatewayRequest,
    fastapi_request: Request,
    current_user: str = Depends(get_current_user)
) -> HireAgentGatewayResponse:
    """
    Hire an agent using gasless Gateway payment.

    This endpoint:
    1. Verifies X-Payment-Signature header (returns 402 if missing)
    2. Validates payment amount meets requirement (returns 402 if insufficient)
    3. Verifies signature with Circle Gateway API (returns 401 if invalid)
    4. Creates task record
    5. Logs X402 request for audit trail
    6. Returns task receipt to user

    Actual USDC settlement happens in batches via Circle Gateway.
    See Issue #150 for auto-settlement cron job implementation.
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Calculate required payment based on task
    # Simple formula: $10 base + $0.01 per character over 100
    base_rate = 10.0
    complexity_multiplier = 1.0 + max(0, (len(request_body.task_description) - 100)) / 1000
    required_amount = base_rate * complexity_multiplier

    logger.info(
        f"Hire agent request: project={project_id}, agent={request_body.agent_token_id}, "
        f"required_amount=${required_amount:.2f}"
    )

    # Verify payment signature and amount
    # This will raise PaymentRequiredError (402) or InvalidSignatureError (401) if fails
    payment_data = await gateway_service.verify_payment_header(
        fastapi_request,
        required_amount
    )

    # Generate IDs
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    # Log X402 request for audit trail
    # This integrates with existing X402 infrastructure
    x402_request = await x402_service.create_request(
        project_id=project_id,
        agent_id=str(request_body.agent_token_id),
        task_id=task_id,
        run_id=run_id,
        request_payload={
            "method": "POST",
            "url": f"/gateway/{project_id}/hire-agent",
            "task_description": request_body.task_description,
            "amount": payment_data["amount"],
            "payer": payment_data["payer"],
            "payment_type": "gateway_gasless"
        },
        signature=payment_data["signature"],
        status=X402RequestStatus.PENDING,
        metadata={
            "payment_method": "circle_gateway",
            "network": payment_data.get("network", "arc-testnet"),
            "settlement_status": "pending_batch",
            "task_id": task_id,
            "agent_token_id": request_body.agent_token_id
        }
    )

    # Estimate settlement time (batches settle every 10 minutes)
    estimated_settlement = datetime.utcnow() + timedelta(minutes=10)

    logger.info(
        f"Task created successfully: task_id={task_id}, "
        f"x402_request_id={x402_request['request_id']}, "
        f"payment_amount=${payment_data['amount']}"
    )

    return HireAgentGatewayResponse(
        task_id=task_id,
        x402_request_id=x402_request["request_id"],
        agent_token_id=request_body.agent_token_id,
        payment_status="pending_settlement",
        amount_paid=payment_data["amount"],
        payer_address=payment_data["payer"],
        estimated_settlement_time=estimated_settlement.isoformat() + "Z",
        message="Task created. Payment will settle in next batch (approx 10 min)."
    )


@router.post(
    "/deposit",
    response_model=GatewayDepositResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Deposit instructions returned successfully",
            "model": GatewayDepositResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Get Gateway deposit instructions",
    description="""
    Get instructions for depositing USDC to Circle Gateway.

    **One-Time Setup:**
    Users must deposit USDC to Gateway before making gasless payments.
    This is a one-time setup step (similar to funding a prepaid card).

    **Process:**
    1. User calls this endpoint to get deposit address
    2. User sends USDC to deposit address on Arc Testnet
    3. User can then make unlimited gasless payments until balance runs out

    **Returns:**
    - deposit_address: Wallet address to send USDC to
    - network: Blockchain network (arc-testnet)
    - minimum_deposit: Minimum amount to deposit
    - qr_code_url: QR code for easy mobile deposit
    - instructions: Human-readable instructions
    """
)
async def get_deposit_info(
    request_body: GatewayDepositRequest,
    current_user: str = Depends(get_current_user)
) -> GatewayDepositResponse:
    """
    Get Gateway deposit information for a user.

    Returns the seller's Circle Gateway deposit address where users
    can send USDC to fund their gasless payment balance.

    In production, this would:
    1. Call Circle Gateway API to get user-specific deposit address
    2. Generate QR code for easy mobile deposit
    3. Track user's Gateway balance

    For MVP, we return the seller's address for demonstration.
    """
    logger.info(f"Deposit info requested by user={current_user}")

    return GatewayDepositResponse(
        deposit_address=gateway_service.seller_address,
        network="arc-testnet",
        minimum_deposit="10.00",
        qr_code_url=f"{gateway_service.gateway_url}/qr/{current_user}",
        instructions=(
            "Send USDC to the address above on Arc Testnet. "
            "Once confirmed, you can make gasless payments with no transaction fees!"
        )
    )
