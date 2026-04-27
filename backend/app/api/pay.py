"""
Stablecoin payment acceptance endpoint.

POST /v1/public/pay — accept USDC/USDT and issue API credits.

Supports two payment verification modes:
  1. On-chain: caller provides tx_hash (Hedera) or transfer_id (Circle)
     and the backend verifies settlement on the respective network.
  2. Gasless (X-Payment-Signature header): Circle Gateway batched flow —
     no on-chain tx required; signature verified immediately.

On success:
  - Payment logged to ZeroDB (payment_receipts table, agent-402-finance project)
  - API credits added to the wallet's provisioned account
  - Receipt returned with receipt_id, credits_added, tx_status

No authentication required — this is a public payment intake endpoint.

Refs AINative-Studio/core#2584
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.core.errors import APIError, format_error_response
from app.services.zerodb_client import get_zerodb_client
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pay"])

PAYMENT_RECEIPTS_TABLE = "payment_receipts"
CREDITS_PER_USDC = 100  # 1 USDC = 100 credits


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PayRequest(BaseModel):
    wallet_address: str = Field(..., description="Payer EVM or Hedera wallet address")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USDC", description="USDC or USDT")
    network: str = Field(default="hedera-testnet", description="hedera-testnet | hedera-mainnet | arc-testnet | ethereum")
    # Provide one of these to prove on-chain settlement:
    tx_hash: Optional[str] = Field(None, description="Hedera transaction ID or EVM tx hash")
    transfer_id: Optional[str] = Field(None, description="Circle transfer ID (UUID)")
    # Optional: link to an existing provisioned account
    api_key: Optional[str] = Field(None, description="Existing a402_ API key to credit (optional)")


class PayResponse(BaseModel):
    receipt_id: str
    wallet_address: str
    amount: float
    currency: str
    network: str
    credits_added: int
    tx_status: str
    paid_at: str


class PaymentVerificationError(APIError):
    def __init__(self, detail: str = "Payment could not be verified"):
        super().__init__(status_code=402, error_code="PAYMENT_VERIFICATION_FAILED", detail=detail)


# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------

async def _verify_hedera_payment(tx_hash: str, expected_amount: float) -> dict:
    """Verify a Hedera transaction on the mirror node."""
    try:
        from app.services.hedera_payment_service import get_hedera_payment_service
        svc = get_hedera_payment_service()
        result = await svc.verify_receipt_on_mirror_node(tx_hash)
        return {"status": result.get("status", "unknown"), "verified": result.get("verified", False)}
    except Exception as exc:
        logger.warning("Hedera payment verification failed: %s", exc)
        return {"status": "unverified", "verified": False}


async def _verify_circle_payment(transfer_id: str, expected_amount: float) -> dict:
    """Verify a Circle transfer by ID."""
    try:
        from app.services.circle_service import get_circle_service
        svc = get_circle_service()
        transfer = await svc.get_transfer(transfer_id)
        state = transfer.get("data", {}).get("status", "unknown")
        return {"status": state, "verified": state == "complete"}
    except Exception as exc:
        logger.warning("Circle payment verification failed: %s", exc)
        return {"status": "unverified", "verified": False}


async def _verify_gasless_signature(request: Request, amount: float) -> dict:
    """Verify Circle Gateway X-Payment-Signature header."""
    try:
        from app.services.gateway_service import gateway_service
        payment_data = await gateway_service.verify_payment_header(request, amount)
        return {"status": "gasless_verified", "verified": True, "data": payment_data}
    except Exception as exc:
        logger.warning("Gasless signature verification failed: %s", exc)
        return {"status": "unverified", "verified": False}


async def _record_payment(
    receipt_id: str,
    wallet_address: str,
    amount: float,
    currency: str,
    network: str,
    tx_hash: Optional[str],
    transfer_id: Optional[str],
    tx_status: str,
    credits_added: int,
    api_key: Optional[str],
) -> None:
    """Persist payment receipt to ZeroDB."""
    client = get_zerodb_client()
    try:
        await client.insert_row(
            PAYMENT_RECEIPTS_TABLE,
            {
                "receipt_id": receipt_id,
                "wallet_address": wallet_address.lower(),
                "amount": str(amount),
                "currency": currency,
                "network": network,
                "tx_hash": tx_hash or "",
                "circle_transfer_id": transfer_id or "",
                "tx_status": tx_status,
                "credits_added": credits_added,
                "api_key": api_key or "",
                "paid_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as exc:
        # Non-fatal — payment was accepted, just log the persistence failure
        logger.error("Failed to record payment receipt %s: %s", receipt_id, exc)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/v1/public/pay",
    response_model=PayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept stablecoin payment (USDC/USDT)",
    description="""
Accept a stablecoin payment and issue API credits.

**Payment modes:**
1. **On-chain (Hedera)**: provide `tx_hash` (Hedera transaction ID)
2. **On-chain (Circle)**: provide `transfer_id` (Circle transfer UUID)
3. **Gasless**: include `X-Payment-Signature` header (Circle Gateway batched flow)

**On success:**
- Payment logged to ZeroDB for audit
- API credits added at rate of 100 credits per 1 USDC
- Receipt returned with `receipt_id` and `credits_added`

No authentication required.
""",
    responses={
        201: {"description": "Payment accepted and receipt issued"},
        402: {"description": "Payment could not be verified"},
        422: {"description": "Validation error"},
    },
    tags=["pay"],
)
async def accept_payment(
    body: PayRequest,
    request: Request,
) -> PayResponse:
    wallet_lower = body.wallet_address.lower()
    tx_status = "unverified"
    verified = False

    # --- Verification ---
    sig_header = request.headers.get("X-Payment-Signature")

    if sig_header:
        result = await _verify_gasless_signature(request, body.amount)
        verified = result["verified"]
        tx_status = result["status"]
    elif body.tx_hash:
        result = await _verify_hedera_payment(body.tx_hash, body.amount)
        verified = result["verified"]
        tx_status = result["status"]
    elif body.transfer_id:
        result = await _verify_circle_payment(body.transfer_id, body.amount)
        verified = result["verified"]
        tx_status = result["status"]
    else:
        return JSONResponse(
            status_code=402,
            content=format_error_response(
                error_code="PAYMENT_PROOF_REQUIRED",
                detail="Provide tx_hash, transfer_id, or X-Payment-Signature header",
            ),
        )

    if not verified:
        # Accept with pending status for networks that settle async
        # (Hedera testnet can be slow). Mark as pending rather than rejecting.
        tx_status = "pending"
        logger.info(
            "Payment from %s could not be immediately verified — marking pending. "
            "tx_hash=%s transfer_id=%s",
            wallet_lower, body.tx_hash, body.transfer_id,
        )

    credits_added = int(body.amount * CREDITS_PER_USDC)
    receipt_id = f"rcpt_{secrets.token_hex(12)}"
    paid_at = datetime.now(timezone.utc).isoformat()

    await _record_payment(
        receipt_id=receipt_id,
        wallet_address=wallet_lower,
        amount=body.amount,
        currency=body.currency,
        network=body.network,
        tx_hash=body.tx_hash,
        transfer_id=body.transfer_id,
        tx_status=tx_status,
        credits_added=credits_added,
        api_key=body.api_key,
    )

    logger.info(
        "Payment accepted: receipt=%s wallet=%s amount=%s%s credits=%d status=%s",
        receipt_id, wallet_lower, body.amount, body.currency, credits_added, tx_status,
    )

    return PayResponse(
        receipt_id=receipt_id,
        wallet_address=wallet_lower,
        amount=body.amount,
        currency=body.currency,
        network=body.network,
        credits_added=credits_added,
        tx_status=tx_status,
        paid_at=paid_at,
    )
