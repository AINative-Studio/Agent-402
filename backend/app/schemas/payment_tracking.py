"""
Payment Tracking Schemas for X402 Protocol.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 8 (X402 Protocol):
- Payment receipts stored in ZeroDB
- Linked to Arc blockchain transactions
- USDC transaction tracking via Circle Wallets
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """
    Payment status enumeration per X402 protocol.
    Tracks lifecycle of payment receipts.
    """
    PENDING = "pending"           # Payment initiated, awaiting confirmation
    CONFIRMED = "confirmed"       # Payment confirmed on-chain
    FAILED = "failed"             # Payment failed
    REFUNDED = "refunded"         # Payment was refunded


class PaymentReceipt(BaseModel):
    """
    X402 Payment Receipt schema.

    Stores payment details linked to X402 requests and
    Arc blockchain transactions.
    """
    receipt_id: str = Field(
        ...,
        description="Unique receipt identifier"
    )
    x402_request_id: str = Field(
        ...,
        description="Associated X402 request ID"
    )
    transaction_hash: Optional[str] = Field(
        None,
        description="USDC transaction hash on-chain"
    )
    arc_payment_id: Optional[int] = Field(
        None,
        description="Payment ID from AgentTreasury contract"
    )
    from_agent_id: str = Field(
        ...,
        description="Agent ID making the payment"
    )
    to_agent_id: str = Field(
        ...,
        description="Agent ID receiving the payment"
    )
    amount_usdc: str = Field(
        ...,
        description="Amount in USDC (6 decimals, string to preserve precision)"
    )
    purpose: str = Field(
        ...,
        description="Payment purpose (e.g., 'x402-api-call', 'task-completion')"
    )
    status: PaymentStatus = Field(
        PaymentStatus.PENDING,
        description="Current payment status"
    )
    treasury_from_id: Optional[int] = Field(
        None,
        description="Source treasury ID from AgentTreasury contract"
    )
    treasury_to_id: Optional[int] = Field(
        None,
        description="Destination treasury ID from AgentTreasury contract"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when receipt was created"
    )
    confirmed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when payment was confirmed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional payment metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "receipt_id": "pay_rcpt_a1b2c3d4e5f6",
                "x402_request_id": "x402_req_abc123def456",
                "transaction_hash": "0xabc123def456...",
                "arc_payment_id": 42,
                "from_agent_id": "agent_001",
                "to_agent_id": "agent_002",
                "amount_usdc": "1.500000",
                "purpose": "x402-api-call",
                "status": "confirmed",
                "treasury_from_id": 1,
                "treasury_to_id": 2,
                "created_at": "2026-01-23T12:00:00Z",
                "confirmed_at": "2026-01-23T12:00:05Z",
                "metadata": {"task_id": "task_xyz"}
            }
        }


class PaymentReceiptCreate(BaseModel):
    """
    Schema for creating a new payment receipt.
    """
    x402_request_id: str = Field(
        ...,
        description="Associated X402 request ID"
    )
    from_agent_id: str = Field(
        ...,
        description="Agent ID making the payment"
    )
    to_agent_id: str = Field(
        ...,
        description="Agent ID receiving the payment"
    )
    amount_usdc: str = Field(
        ...,
        description="Amount in USDC (6 decimals)"
    )
    purpose: str = Field(
        ...,
        description="Payment purpose"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional payment metadata"
    )


class PaymentReceiptResponse(BaseModel):
    """
    Response schema for payment receipt operations.
    """
    receipt: PaymentReceipt
    message: str = Field(
        "Payment receipt created successfully",
        description="Operation result message"
    )


class PaymentReceiptListResponse(BaseModel):
    """
    Response schema for listing payment receipts.
    """
    receipts: List[PaymentReceipt] = Field(
        default_factory=list,
        description="List of payment receipts"
    )
    total: int = Field(
        ...,
        description="Total count of receipts"
    )
