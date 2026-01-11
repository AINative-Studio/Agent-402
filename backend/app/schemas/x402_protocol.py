"""
X402 Protocol schemas for root-level /x402 endpoint.
Implements Issue #77: Add /x402 Root Signed POST Endpoint.

Per PRD Section 9 (System Architecture):
- /x402 signed POST endpoint accepts protocol requests
- Signature verification for DID-based authentication
- Payload validation per X402 protocol specification

Per PRD Section 8 (AIKit Integration):
- X402 request tool schema: { did, signature, payload }
- Automatic request logging and tracing
- Non-repudiation through signature verification

This endpoint is PUBLIC and does not require X-API-Key authentication.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class X402ProtocolRequest(BaseModel):
    """
    X402 protocol signed request schema.

    This schema represents the root-level /x402 endpoint request format.

    Per PRD Section 8:
    - did: Decentralized Identifier of the requesting agent
    - signature: Cryptographic signature (hex-encoded)
    - payload: X402 protocol payload (payment authorization or other action)

    For MVP: Signature verification is TODO (Issue #75).
    All requests are accepted and logged for audit trail.
    """
    did: str = Field(
        ...,
        min_length=1,
        description=(
            "Decentralized Identifier (DID) of the requesting agent. "
            "Format: did:method:identifier (e.g., did:ethr:0xabc123...)"
        )
    )
    signature: str = Field(
        ...,
        min_length=1,
        description=(
            "Cryptographic signature of the payload in hex format. "
            "Used for verifying request authenticity and non-repudiation. "
            "Format: 0x followed by hex characters."
        )
    )
    payload: Dict[str, Any] = Field(
        ...,
        description=(
            "X402 protocol payload containing the action to be performed. "
            "Common fields: type, amount, currency, recipient, memo. "
            "Exact schema depends on the action type."
        )
    )

    @validator('did')
    def validate_did_format(cls, v):
        """
        Validate DID format.

        Basic validation: must start with 'did:' prefix.
        Full DID spec validation is TODO for future enhancement.
        """
        if not v or not v.strip():
            raise ValueError("DID cannot be empty or whitespace")

        v = v.strip()
        if not v.startswith('did:'):
            raise ValueError("DID must start with 'did:' prefix")

        return v

    @validator('signature')
    def validate_signature_format(cls, v):
        """
        Validate signature format.

        Basic validation: non-empty hex string.
        Cryptographic verification is TODO (Issue #75).
        """
        if not v or not v.strip():
            raise ValueError("Signature cannot be empty or whitespace")

        v = v.strip()

        # Accept with or without 0x prefix
        if v.startswith('0x'):
            hex_part = v[2:]
        else:
            hex_part = v

        # Validate hex characters
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Signature must be a valid hex string")

        return v

    @validator('payload')
    def validate_payload_not_empty(cls, v):
        """Ensure payload is not empty."""
        if not v:
            raise ValueError("Payload cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "did": "did:ethr:0xabc123def456789",
                "signature": "0x8f3e9a7c2b1d4e6f5a8c9b0e3d7f1a4c6b8e9f2a5d7c0b3e6f8a1d4c7b9e2f5a8",
                "payload": {
                    "type": "payment_authorization",
                    "amount": "100.00",
                    "currency": "USD",
                    "recipient": "did:ethr:0xdef789abc012345",
                    "memo": "Payment for task completion",
                    "timestamp": "2026-01-11T12:34:56.789Z"
                }
            }
        }


class X402ProtocolResponse(BaseModel):
    """
    X402 protocol response schema.

    Returned after successfully receiving and storing an X402 request.

    Per Issue #77 Requirements:
    - request_id: Unique identifier for the stored request
    - status: Always "received" for MVP (verification is TODO)
    - timestamp: ISO 8601 timestamp when request was received
    """
    request_id: str = Field(
        ...,
        description="Unique identifier for the X402 request record"
    )
    status: str = Field(
        ...,
        description=(
            "Request status. For MVP: always 'received'. "
            "Future: 'verified', 'rejected', 'pending', etc."
        )
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when request was received and stored"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "x402_req_a1b2c3d4e5f6g7h8",
                "status": "received",
                "timestamp": "2026-01-11T12:34:56.789Z"
            }
        }
