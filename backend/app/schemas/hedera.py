"""
Pydantic schemas for Hedera payment and wallet API requests/responses.

Issue #187: USDC Payment Settlement via HTS
Issue #188: Agent Wallet Creation
Issue #189: Payment Receipt Verification

All request/response models use Pydantic v2 conventions.

Built by AINative Dev Team
Refs #187, #188, #189
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ─── Wallet Schemas (#188) ────────────────────────────────────────────────────────

class HederaWalletCreateRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/hedera/wallets.

    Creates a new Hedera account for an agent with optional initial HBAR balance.
    After creation, call the associate-usdc endpoint to enable USDC receipt.
    """
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Agent identifier to link with the new Hedera wallet"
    )
    initial_balance: int = Field(
        default=0,
        ge=0,
        description="Initial HBAR balance to fund the new account (whole HBAR units)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_abc123",
                "initial_balance": 10
            }
        }


class HederaWalletResponse(BaseModel):
    """
    Response schema for Hedera wallet operations.

    Returned by wallet creation and wallet info endpoints.
    """
    agent_id: str = Field(
        ...,
        description="Agent identifier associated with this wallet"
    )
    account_id: str = Field(
        ...,
        description="Hedera account ID in format 0.0.{number}"
    )
    public_key: str = Field(
        ...,
        description="Account public key (DER-encoded hex)"
    )
    network: str = Field(
        ...,
        description="Hedera network (testnet or mainnet)"
    )
    created_at: str = Field(
        ...,
        description="ISO timestamp when the wallet was created"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "agent_id": "agent_abc123",
                "account_id": "0.0.12345",
                "public_key": "302a300506032b6570032100abc123...",
                "network": "testnet",
                "created_at": "2026-04-03T12:00:00Z"
            }
        }


class HederaBalanceResponse(BaseModel):
    """
    Response schema for wallet balance queries.

    Returns HBAR and USDC balances for a Hedera account.
    USDC balance is in decimal format (e.g., "50.000000").
    """
    account_id: str = Field(
        ...,
        description="Hedera account ID"
    )
    hbar: str = Field(
        ...,
        description="HBAR balance in whole HBAR units"
    )
    usdc: str = Field(
        ...,
        description="USDC balance in decimal format (6 decimal places)"
    )
    usdc_raw: Optional[str] = Field(
        default=None,
        description="USDC balance in smallest unit (integer)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "account_id": "0.0.12345",
                "hbar": "100.0",
                "usdc": "50.000000",
                "usdc_raw": "50000000"
            }
        }


class HederaTokenAssociationResponse(BaseModel):
    """
    Response schema for USDC token association.

    Returned after successfully associating the USDC HTS token
    with a Hedera account. Token association is required before
    the account can receive USDC transfers.
    """
    transaction_id: str = Field(
        ...,
        description="Hedera transaction ID for the association"
    )
    status: str = Field(
        ...,
        description="Association status (SUCCESS)"
    )
    account_id: str = Field(
        ...,
        description="Account that was associated"
    )
    token_id: Optional[str] = Field(
        default=None,
        description="USDC HTS token ID that was associated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "0.0.12345@1234567890.000000000",
                "status": "SUCCESS",
                "account_id": "0.0.12345",
                "token_id": "0.0.456858"
            }
        }


# ─── Payment Schemas (#187) ───────────────────────────────────────────────────────

class HederaPaymentCreateRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/hedera/payments.

    Creates and executes a USDC payment via Hedera Token Service (HTS)
    as part of the X402 protocol flow.

    Amounts use USDC smallest unit: 1 USDC = 1,000,000 units.
    """
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Agent identifier initiating the payment"
    )
    amount: int = Field(
        ...,
        gt=0,
        description="Payment amount in USDC smallest unit (1 USDC = 1,000,000)"
    )
    recipient: str = Field(
        ...,
        min_length=1,
        description="Destination Hedera account ID (e.g., 0.0.22222)"
    )
    task_id: str = Field(
        ...,
        min_length=1,
        description="Task identifier linking this payment to agent work"
    )
    from_account: Optional[str] = Field(
        default=None,
        description="Source Hedera account (defaults to platform operator account)"
    )
    memo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional transaction memo (max 100 bytes)"
    )

    @field_validator("recipient")
    @classmethod
    def validate_recipient_not_empty(cls, v: str) -> str:
        """Ensure recipient is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("recipient cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "agent_abc123",
                "amount": 5000000,
                "recipient": "0.0.22222",
                "task_id": "task_xyz789",
                "memo": "Payment for task completion"
            }
        }


class HederaPaymentResponse(BaseModel):
    """
    Response schema for Hedera payment creation.

    Returned after successfully initiating an X402 payment via HTS.
    """
    payment_id: str = Field(
        ...,
        description="Unique payment identifier (format: hdr_pay_{uuid})"
    )
    agent_id: str = Field(
        ...,
        description="Agent that initiated the payment"
    )
    task_id: str = Field(
        ...,
        description="Associated task identifier"
    )
    amount: int = Field(
        ...,
        description="Transfer amount in USDC smallest unit"
    )
    recipient: str = Field(
        ...,
        description="Destination Hedera account ID"
    )
    transaction_id: str = Field(
        ...,
        description="Hedera transaction ID"
    )
    status: str = Field(
        ...,
        description="Payment status (SUCCESS, PENDING, FAILED)"
    )
    created_at: str = Field(
        ...,
        description="ISO timestamp when payment was created"
    )
    transaction_hash: Optional[str] = Field(
        default=None,
        description="Hedera transaction hash for on-chain verification"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "payment_id": "hdr_pay_abc123def456",
                "agent_id": "agent_abc123",
                "task_id": "task_xyz789",
                "amount": 5000000,
                "recipient": "0.0.22222",
                "transaction_id": "0.0.12345@1234567890.000000000",
                "status": "SUCCESS",
                "created_at": "2026-04-03T12:00:00Z",
                "transaction_hash": "0xabcdef1234567890"
            }
        }


class HederaSettlementVerifyRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/hedera/payments/verify.

    Verifies whether a Hedera transaction has settled on-chain.
    """
    transaction_id: str = Field(
        ...,
        min_length=1,
        description="Hedera transaction ID to verify (format: 0.0.{acct}@{ts})"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "0.0.12345@1234567890.000000000"
            }
        }


class HederaSettlementVerifyResponse(BaseModel):
    """
    Response schema for settlement verification.

    Indicates whether a Hedera transaction has reached consensus.
    Hedera targets sub-3 second settlement finality.
    """
    transaction_id: str = Field(
        ...,
        description="The verified transaction ID"
    )
    settled: bool = Field(
        ...,
        description="True if transaction status is SUCCESS (reached consensus)"
    )
    status: str = Field(
        ...,
        description="Transaction status from the Hedera network"
    )
    consensus_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp when the transaction reached consensus"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "0.0.12345@1234567890.000000000",
                "settled": True,
                "status": "SUCCESS",
                "consensus_timestamp": "2026-04-03T12:00:00Z"
            }
        }


class HederaPaymentReceiptResponse(BaseModel):
    """
    Response schema for payment receipt retrieval.

    Full receipt including hash for on-chain verification.
    Extended by Issue #189 with mirror_node_url, agent_id, and task_id
    fields for audit trail linkage.
    """
    transaction_id: str = Field(
        ...,
        description="Hedera transaction ID"
    )
    hash: Optional[str] = Field(
        default=None,
        description="Transaction hash for external verification"
    )
    status: str = Field(
        ...,
        description="Final transaction status"
    )
    consensus_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp of consensus"
    )
    charged_tx_fee: Optional[int] = Field(
        default=None,
        description="Network fee charged in tinybars"
    )
    # Issue #189: audit trail and mirror node linkage fields
    mirror_node_url: Optional[str] = Field(
        default=None,
        description=(
            "Direct URL to this transaction on the Hedera mirror node. "
            "Format: https://testnet.mirrornode.hedera.com/api/v1/transactions/{encoded_tx_id}"
        )
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Agent identifier associated with this payment (for audit trail)"
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Task identifier associated with this payment (for audit trail)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "0.0.12345@1234567890.000000000",
                "hash": "0xabcdef1234567890abcdef1234567890",
                "status": "SUCCESS",
                "consensus_timestamp": "2026-04-03T12:00:00.123Z",
                "charged_tx_fee": 100000,
                "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345-1234567890-000000000",
                "agent_id": "agent_abc123",
                "task_id": "task_xyz789"
            }
        }


class ReceiptVerificationResponse(BaseModel):
    """
    Response schema for mirror node receipt verification.

    Returned by GET /api/v1/hedera/payments/{transaction_id}/verify.
    Provides verification status from the Hedera mirror node with a
    direct link for independent verification.

    Issue #189: Payment Receipt Verification
    """
    verified: bool = Field(
        ...,
        description="True if the transaction is verified on the mirror node (status=SUCCESS)"
    )
    transaction_status: str = Field(
        ...,
        description="Transaction status returned by the Hedera mirror node"
    )
    mirror_node_url: str = Field(
        ...,
        description="Direct URL to this transaction on the Hedera mirror node"
    )
    consensus_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp when the transaction reached consensus (if settled)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "transaction_status": "SUCCESS",
                "mirror_node_url": "https://testnet.mirrornode.hedera.com/api/v1/transactions/0-0-12345-1234567890-000000000",
                "consensus_timestamp": "2026-04-03T12:00:00Z"
            }
        }
