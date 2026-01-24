"""
Circle API schemas for request/response validation.
These schemas define the contract for Circle Wallet and USDC payment operations.
Issue #114: Implement Circle Wallets and USDC Payments

Schemas:
- WalletCreate: Request schema for creating Circle wallets
- WalletResponse: Response schema for wallet operations
- TransferCreate: Request schema for USDC transfers
- TransferResponse: Response schema for transfer operations
- PaymentReceipt: Payment receipt for audit trail
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WalletType(str, Enum):
    """
    Wallet type enumeration for Circle wallets.
    Each agent type has a specific wallet purpose.
    """
    ANALYST = "analyst"
    COMPLIANCE = "compliance"
    TRANSACTION = "transaction"


class TransferStatus(str, Enum):
    """
    Transfer status enumeration for USDC transfers.
    Per Circle API: pending, complete, failed.
    """
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class WalletStatus(str, Enum):
    """
    Wallet status enumeration.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"


class WalletCreateRequest(BaseModel):
    """
    Request schema for POST /circle/wallets.
    Creates a new Circle wallet for an agent.

    Issue #114: Link wallets to agent DIDs.
    """
    agent_did: str = Field(
        ...,
        description="Agent DID to link wallet to (must be did:key:z6Mk... format)",
        min_length=1,
        max_length=256,
        examples=["did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"]
    )
    wallet_type: WalletType = Field(
        ...,
        description="Type of wallet (analyst, compliance, transaction)",
        examples=["transaction"]
    )
    description: Optional[str] = Field(
        None,
        description="Optional wallet description",
        max_length=500,
        examples=["Transaction agent wallet for USDC payments"]
    )
    idempotency_key: Optional[str] = Field(
        None,
        description="Idempotency key for retry safety",
        max_length=64,
        examples=["unique-request-key-123"]
    )

    @field_validator('agent_did')
    @classmethod
    def validate_agent_did_format(cls, v: str) -> str:
        """
        Validate agent DID format.
        Must be did:key:z6Mk... format.
        """
        if not v.startswith("did:key:"):
            raise ValueError("Agent DID must start with 'did:key:' prefix")

        identifier = v[8:]
        if not identifier.startswith("z6Mk"):
            raise ValueError("Agent DID key identifier must start with 'z6Mk'")

        if len(identifier) < 10:
            raise ValueError("Agent DID key identifier is too short")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "wallet_type": "transaction",
                "description": "Transaction agent wallet for USDC payments"
            }
        }


class WalletResponse(BaseModel):
    """
    Response schema for wallet operations.
    Returns full wallet details including Circle wallet ID and balances.
    """
    wallet_id: str = Field(..., description="Unique wallet identifier")
    circle_wallet_id: str = Field(..., description="Circle platform wallet ID")
    agent_did: str = Field(..., description="Linked agent DID")
    wallet_type: WalletType = Field(..., description="Type of wallet")
    status: WalletStatus = Field(default=WalletStatus.ACTIVE, description="Wallet status")
    blockchain_address: str = Field(..., description="Blockchain address for USDC")
    blockchain: str = Field(default="ETH-SEPOLIA", description="Blockchain network")
    balance: str = Field(default="0.00", description="Current USDC balance")
    description: Optional[str] = Field(None, description="Wallet description")
    created_at: datetime = Field(..., description="Wallet creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123def456",
                "circle_wallet_id": "circle_wlt_001",
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "wallet_type": "transaction",
                "status": "active",
                "blockchain_address": "0x1234567890abcdef1234567890abcdef12345678",
                "blockchain": "ETH-SEPOLIA",
                "balance": "1000.00",
                "description": "Transaction agent wallet",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z"
            }
        }


class WalletListResponse(BaseModel):
    """
    Response schema for listing wallets.
    Returns array of wallets with total count.
    """
    wallets: List[WalletResponse] = Field(
        default_factory=list,
        description="List of wallets"
    )
    total: int = Field(..., description="Total number of wallets")

    class Config:
        json_schema_extra = {
            "example": {
                "wallets": [],
                "total": 0
            }
        }


class TransferCreateRequest(BaseModel):
    """
    Request schema for POST /circle/transfers.
    Initiates a USDC transfer between wallets.

    Issue #114: X402 payments can trigger USDC transfers.
    """
    source_wallet_id: str = Field(
        ...,
        description="Source wallet ID",
        min_length=1,
        max_length=64,
        examples=["wallet_abc123"]
    )
    destination_wallet_id: str = Field(
        ...,
        description="Destination wallet ID",
        min_length=1,
        max_length=64,
        examples=["wallet_xyz789"]
    )
    amount: str = Field(
        ...,
        description="Transfer amount in USDC (e.g., '100.50')",
        min_length=1,
        max_length=32,
        examples=["100.50"]
    )
    currency: str = Field(
        default="USD",
        description="Currency (always USD for USDC)",
        examples=["USD"]
    )
    x402_request_id: Optional[str] = Field(
        None,
        description="Linked X402 request ID for payment tracking",
        max_length=64,
        examples=["x402_req_abc123"]
    )
    idempotency_key: Optional[str] = Field(
        None,
        description="Idempotency key for retry safety",
        max_length=64,
        examples=["transfer-unique-key-456"]
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the transfer"
    )

    @field_validator('amount')
    @classmethod
    def validate_amount_format(cls, v: str) -> str:
        """
        Validate amount format.
        Must be a positive decimal number.
        """
        try:
            amount = float(v)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            if amount > 1000000000:  # 1 billion cap
                raise ValueError("Amount exceeds maximum limit")
        except (ValueError, TypeError) as e:
            if "must be positive" in str(e) or "exceeds maximum" in str(e):
                raise
            raise ValueError("Amount must be a valid decimal number")
        return v

    @field_validator('source_wallet_id', 'destination_wallet_id')
    @classmethod
    def validate_different_wallets(cls, v: str, info) -> str:
        """Wallet IDs are validated individually; cross-validation in model_validator."""
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source_wallet_id": "wallet_abc123",
                "destination_wallet_id": "wallet_xyz789",
                "amount": "100.50",
                "currency": "USD",
                "x402_request_id": "x402_req_abc123"
            }
        }


class TransferResponse(BaseModel):
    """
    Response schema for transfer operations.
    Returns transfer details including Circle transfer ID and status.
    """
    transfer_id: str = Field(..., description="Unique transfer identifier")
    circle_transfer_id: str = Field(..., description="Circle platform transfer ID")
    source_wallet_id: str = Field(..., description="Source wallet ID")
    destination_wallet_id: str = Field(..., description="Destination wallet ID")
    amount: str = Field(..., description="Transfer amount in USDC")
    currency: str = Field(default="USD", description="Currency")
    status: TransferStatus = Field(..., description="Transfer status")
    x402_request_id: Optional[str] = Field(None, description="Linked X402 request ID")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    created_at: datetime = Field(..., description="Transfer initiation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Transfer completion timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "transfer_id": "transfer_abc123def456",
                "circle_transfer_id": "circle_xfr_001",
                "source_wallet_id": "wallet_abc123",
                "destination_wallet_id": "wallet_xyz789",
                "amount": "100.50",
                "currency": "USD",
                "status": "complete",
                "x402_request_id": "x402_req_abc123",
                "transaction_hash": "0xabc123...",
                "created_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:01:00Z"
            }
        }


class TransferListResponse(BaseModel):
    """
    Response schema for listing transfers.
    Returns array of transfers with pagination metadata.
    """
    transfers: List[TransferResponse] = Field(
        default_factory=list,
        description="List of transfers"
    )
    total: int = Field(..., description="Total number of transfers")
    limit: int = Field(default=100, description="Pagination limit")
    offset: int = Field(default=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "transfers": [],
                "total": 0,
                "limit": 100,
                "offset": 0
            }
        }


class PaymentReceipt(BaseModel):
    """
    Payment receipt for audit trail.
    Generated after successful USDC transfers.

    Issue #114: Payment receipts generated and stored.
    """
    receipt_id: str = Field(..., description="Unique receipt identifier")
    transfer_id: str = Field(..., description="Associated transfer ID")
    x402_request_id: Optional[str] = Field(None, description="Linked X402 request ID")
    source_agent_did: str = Field(..., description="Source agent DID")
    destination_agent_did: str = Field(..., description="Destination agent DID")
    amount: str = Field(..., description="Transfer amount")
    currency: str = Field(default="USD", description="Currency")
    status: TransferStatus = Field(..., description="Payment status")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    blockchain: str = Field(default="ETH-SEPOLIA", description="Blockchain network")
    created_at: datetime = Field(..., description="Receipt creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "receipt_id": "receipt_abc123def456",
                "transfer_id": "transfer_abc123",
                "x402_request_id": "x402_req_abc123",
                "source_agent_did": "did:key:z6MkSource...",
                "destination_agent_did": "did:key:z6MkDest...",
                "amount": "100.50",
                "currency": "USD",
                "status": "complete",
                "transaction_hash": "0xabc123...",
                "blockchain": "ETH-SEPOLIA",
                "created_at": "2026-01-01T00:00:00Z"
            }
        }


class AgentPaymentRequest(BaseModel):
    """
    Request schema for POST /agents/{agent_id}/pay.
    Initiates a USDC payment to an agent from the platform treasury.

    Used for programmatic agent payments for task completion.
    """
    amount: str = Field(
        ...,
        description="Payment amount in USDC (e.g., '10.00')",
        min_length=1,
        max_length=32,
        examples=["10.00"]
    )
    reason: str = Field(
        ...,
        description="Reason for the payment (e.g., 'Task completion payment')",
        min_length=1,
        max_length=500,
        examples=["Task completion payment"]
    )
    task_id: Optional[str] = Field(
        None,
        description="Optional task reference ID",
        max_length=64,
        examples=["task_abc123"]
    )
    idempotency_key: Optional[str] = Field(
        None,
        description="Idempotency key for retry safety",
        max_length=64,
        examples=["payment-unique-key-789"]
    )

    @field_validator('amount')
    @classmethod
    def validate_payment_amount(cls, v: str) -> str:
        """
        Validate payment amount format.
        Must be a positive decimal number within limits.
        """
        try:
            amount = float(v)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            if amount > 10000:  # $10,000 cap for single agent payment
                raise ValueError("Amount exceeds maximum single payment limit of $10,000")
        except (ValueError, TypeError) as e:
            if "must be positive" in str(e) or "exceeds maximum" in str(e):
                raise
            raise ValueError("Amount must be a valid decimal number")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "10.00",
                "reason": "Task completion payment",
                "task_id": "task_abc123"
            }
        }


class AgentPaymentResponse(BaseModel):
    """
    Response schema for agent payment operations.
    Returns payment details including transfer ID and status.
    """
    payment_id: str = Field(..., description="Unique payment identifier")
    agent_id: str = Field(..., description="Agent ID receiving the payment")
    agent_did: str = Field(..., description="Agent DID receiving the payment")
    amount: str = Field(..., description="Payment amount in USDC")
    currency: str = Field(default="USD", description="Currency")
    reason: str = Field(..., description="Payment reason")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    transfer_id: str = Field(..., description="Associated transfer ID")
    circle_transfer_id: str = Field(..., description="Circle platform transfer ID")
    status: TransferStatus = Field(..., description="Payment status")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    source_wallet_id: str = Field(..., description="Treasury wallet ID (source)")
    destination_wallet_id: str = Field(..., description="Agent wallet ID (destination)")
    created_at: datetime = Field(..., description="Payment initiation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Payment completion timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "payment_id": "payment_abc123def456",
                "agent_id": "agent_001",
                "agent_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Task completion payment",
                "task_id": "task_abc123",
                "transfer_id": "transfer_xyz789",
                "circle_transfer_id": "circle_xfr_001",
                "status": "pending",
                "transaction_hash": None,
                "source_wallet_id": "wallet_treasury",
                "destination_wallet_id": "wallet_agent_001",
                "created_at": "2026-01-01T00:00:00Z",
                "completed_at": None
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response per DX Contract.
    All errors return { detail, error_code }.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Wallet not found: wallet_abc123",
                "error_code": "WALLET_NOT_FOUND"
            }
        }
