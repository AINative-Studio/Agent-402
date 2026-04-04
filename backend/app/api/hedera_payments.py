"""
Hedera Payments API endpoints.
Implements USDC payment settlement via Hedera Token Service (HTS).

Issue #187: USDC Payment Settlement via HTS
Issue #189: Payment Receipt Verification

Endpoints:
- POST /v1/public/{project_id}/hedera/payments
    Create and execute a USDC X402 payment via HTS
- GET  /v1/public/{project_id}/hedera/payments/{payment_id}/receipt
    Get full payment receipt with Hedera transaction hash
- POST /v1/public/{project_id}/hedera/payments/verify
    Verify whether a Hedera transaction has settled
- GET  /v1/public/{project_id}/hedera/payments/{transaction_id}/verify
    Verify receipt on mirror node and return verification status

All endpoints require X-API-Key authentication.

Built by AINative Dev Team
Refs #187, #189
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, status

from app.schemas.hedera import (
    HederaPaymentCreateRequest,
    HederaPaymentResponse,
    HederaSettlementVerifyRequest,
    HederaSettlementVerifyResponse,
    HederaPaymentReceiptResponse,
    ReceiptVerificationResponse
)
from app.services.hedera_payment_service import (
    HederaPaymentService,
    get_hedera_payment_service
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/v1/public",
    tags=["hedera-payments"]
)


@router.post(
    "/{project_id}/hedera/payments",
    response_model=HederaPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Payment created and executed successfully",
            "model": HederaPaymentResponse
        },
        400: {
            "description": "Invalid payment request (zero/negative amount, empty fields)"
        },
        422: {
            "description": "Validation error"
        },
        502: {
            "description": "Hedera network error"
        }
    },
    summary="Create X402 USDC payment via Hedera HTS",
    description="""
    Create and execute a USDC payment via Hedera Token Service (HTS).

    **Authentication:** Requires X-API-Key header

    **Issue #187:** USDC Payment Settlement via HTS

    This endpoint executes a native HTS USDC transfer (NOT a smart contract call)
    as part of the X402 payment protocol flow. Hedera targets sub-3 second finality.

    **Required fields:**
    - agent_id: Agent initiating the payment
    - amount: Payment amount in USDC smallest unit (1 USDC = 1,000,000)
    - recipient: Destination Hedera account ID (e.g., 0.0.22222)
    - task_id: Task this payment is for

    **Returns:**
    - payment_id: Unique payment identifier (hdr_pay_{uuid})
    - transaction_id: Hedera transaction ID for verification
    - status: Payment status (SUCCESS)
    """
)
async def create_hedera_payment(
    project_id: str,
    request: HederaPaymentCreateRequest,
    payment_service: HederaPaymentService = Depends(get_hedera_payment_service)
) -> HederaPaymentResponse:
    """
    Create and execute an X402 USDC payment via Hedera HTS.

    Args:
        project_id: Project identifier from URL
        request: Payment creation request body
        payment_service: Injected HederaPaymentService

    Returns:
        HederaPaymentResponse with payment details and transaction info
    """
    logger.info(
        f"POST /hedera/payments: project={project_id}, "
        f"agent={request.agent_id}, amount={request.amount}, "
        f"recipient={request.recipient}, task={request.task_id}"
    )

    payment = await payment_service.create_x402_payment(
        agent_id=request.agent_id,
        amount=request.amount,
        recipient=request.recipient,
        task_id=request.task_id,
        from_account=request.from_account,
        memo=request.memo
    )

    return HederaPaymentResponse(
        payment_id=payment["payment_id"],
        agent_id=payment["agent_id"],
        task_id=payment["task_id"],
        amount=payment["amount"],
        recipient=payment["recipient"],
        transaction_id=payment["transaction_id"],
        status=payment["status"],
        created_at=payment["created_at"],
        transaction_hash=payment.get("transaction_hash")
    )


@router.get(
    "/{project_id}/hedera/payments/{payment_id}/receipt",
    response_model=HederaPaymentReceiptResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Payment receipt retrieved",
            "model": HederaPaymentReceiptResponse
        },
        404: {
            "description": "Payment not found"
        },
        502: {
            "description": "Hedera network error"
        }
    },
    summary="Get Hedera payment receipt",
    description="""
    Get the full receipt for a Hedera payment transaction.

    **Authentication:** Requires X-API-Key header

    Returns the complete receipt including:
    - Transaction hash for on-chain verification
    - Consensus timestamp for finality proof
    - Network fee charged

    The receipt can be used to prove payment to external parties.
    """
)
async def get_payment_receipt(
    project_id: str,
    payment_id: str,
    payment_service: HederaPaymentService = Depends(get_hedera_payment_service)
) -> HederaPaymentReceiptResponse:
    """
    Get receipt for a Hedera payment.

    Note: payment_id here is used as the transaction_id for receipt lookup.
    In production, map payment_id -> transaction_id via ZeroDB.

    Args:
        project_id: Project identifier from URL
        payment_id: Payment identifier from URL
        payment_service: Injected HederaPaymentService

    Returns:
        HederaPaymentReceiptResponse with full receipt details
    """
    logger.info(
        f"GET /hedera/payments/{payment_id}/receipt: project={project_id}"
    )

    # For now, treat payment_id as transaction_id for receipt lookup
    # In production this would look up the transaction_id from ZeroDB
    receipt = await payment_service.get_payment_receipt(
        transaction_id=payment_id
    )

    return HederaPaymentReceiptResponse(
        transaction_id=receipt["transaction_id"],
        hash=receipt.get("hash"),
        status=receipt["status"],
        consensus_timestamp=receipt.get("consensus_timestamp"),
        charged_tx_fee=receipt.get("charged_tx_fee")
    )


@router.post(
    "/{project_id}/hedera/payments/verify",
    response_model=HederaSettlementVerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Settlement status returned",
            "model": HederaSettlementVerifyResponse
        },
        400: {
            "description": "Invalid transaction_id"
        },
        422: {
            "description": "Validation error — transaction_id missing"
        },
        502: {
            "description": "Hedera network error"
        }
    },
    summary="Verify Hedera transaction settlement",
    description="""
    Verify whether a Hedera transaction has settled on-chain.

    **Authentication:** Requires X-API-Key header

    **Issue #187:** Sub-3 second settlement verification

    Queries the Hedera mirror node to check if the transaction has reached
    consensus. Hedera targets sub-3 second finality for all transactions.

    **Required fields:**
    - transaction_id: Hedera transaction ID (format: 0.0.{acct}@{ts})

    **Returns:**
    - settled: True if transaction reached consensus (status=SUCCESS)
    - consensus_timestamp: When consensus was reached
    """
)
async def verify_settlement(
    project_id: str,
    request: HederaSettlementVerifyRequest,
    payment_service: HederaPaymentService = Depends(get_hedera_payment_service)
) -> HederaSettlementVerifyResponse:
    """
    Verify settlement status of a Hedera transaction.

    Args:
        project_id: Project identifier from URL
        request: Verification request with transaction_id
        payment_service: Injected HederaPaymentService

    Returns:
        HederaSettlementVerifyResponse with settled status
    """
    logger.info(
        f"POST /hedera/payments/verify: project={project_id}, "
        f"tx={request.transaction_id}"
    )

    result = await payment_service.verify_settlement(
        transaction_id=request.transaction_id
    )

    return HederaSettlementVerifyResponse(
        transaction_id=result["transaction_id"],
        settled=result["settled"],
        status=result["status"],
        consensus_timestamp=result.get("consensus_timestamp")
    )


@router.get(
    "/{project_id}/hedera/payments/{transaction_id}/verify",
    response_model=ReceiptVerificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Receipt verification status from mirror node",
            "model": ReceiptVerificationResponse
        },
        400: {
            "description": "Invalid transaction_id"
        },
        502: {
            "description": "Hedera network or mirror node error"
        }
    },
    summary="Verify payment receipt on Hedera mirror node",
    description="""
    Verify a payment receipt directly against the Hedera mirror node.

    **Authentication:** Requires X-API-Key header

    **Issue #189:** Payment Receipt Verification

    Queries the Hedera mirror node for the transaction and returns:
    - verified: True if the transaction reached consensus (status=SUCCESS)
    - transaction_status: Raw status from the mirror node
    - mirror_node_url: Direct link for independent external verification
    - consensus_timestamp: When the transaction reached consensus

    **URL parameter:**
    - transaction_id: Hedera transaction ID (e.g., 0.0.12345@1234567890.000000000)
    """
)
async def verify_payment_receipt(
    project_id: str,
    transaction_id: str,
    payment_service: HederaPaymentService = Depends(get_hedera_payment_service)
) -> ReceiptVerificationResponse:
    """
    Verify a Hedera payment receipt on the mirror node.

    Args:
        project_id: Project identifier from URL
        transaction_id: Hedera transaction ID from URL path
        payment_service: Injected HederaPaymentService

    Returns:
        ReceiptVerificationResponse with verification status and mirror node URL
    """
    logger.info(
        f"GET /hedera/payments/{transaction_id}/verify: project={project_id}"
    )

    result = await payment_service.verify_receipt_on_mirror_node(
        transaction_id=transaction_id
    )

    return ReceiptVerificationResponse(
        verified=result["verified"],
        transaction_status=result["transaction_status"],
        mirror_node_url=result["mirror_node_url"],
        consensus_timestamp=result.get("consensus_timestamp")
    )
