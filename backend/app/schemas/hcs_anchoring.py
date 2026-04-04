"""
Pydantic schemas for HCS Anchoring API (Issues #200, #201, #202, #203).

Provides request and response models for:
- Memory operation anchoring to HCS topic (Issue #200)
- Compliance event anchoring to HCS (Issue #201)
- Memory integrity verification via HCS anchor (Issue #202)
- Consolidation output anchoring to HCS (Issue #203)

Built by AINative Dev Team
Refs #200, #201, #202, #203
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class AnchorMemoryRequest(BaseModel):
    """
    Request body for POST /anchor/memory.

    Issue #200: Anchor a memory operation hash to HCS so that the content
    can be verified for tampering at any future point.
    """
    memory_id: str = Field(
        ...,
        min_length=1,
        description="Unique memory identifier (format: mem_{uuid})"
    )
    content_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the memory content"
    )
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Agent that owns this memory"
    )
    namespace: str = Field(
        default="default",
        min_length=1,
        description="Namespace for multi-agent isolation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem_abc123",
                "content_hash": "a" * 64,
                "agent_id": "compliance_agent_001",
                "namespace": "default",
            }
        }


class AnchorComplianceRequest(BaseModel):
    """
    Request body for POST /anchor/compliance.

    Issue #201: Anchor a compliance event to HCS for immutable audit trail.
    """
    event_id: str = Field(
        ...,
        min_length=1,
        description="Unique compliance event identifier"
    )
    event_type: str = Field(
        ...,
        min_length=1,
        description="Type of compliance event (KYC_CHECK, KYT_CHECK, RISK_ASSESSMENT, etc.)"
    )
    classification: str = Field(
        ...,
        min_length=1,
        description="Event classification outcome (PASS, FAIL, PENDING, ESCALATED, ERROR)"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk score 0.0 (low) to 1.0 (high)"
    )
    agent_id: str = Field(
        ...,
        min_length=1,
        description="Agent that produced the compliance event"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_kyc_001",
                "event_type": "KYC_CHECK",
                "classification": "PASS",
                "risk_score": 0.1,
                "agent_id": "compliance_agent_001",
            }
        }


class AnchorConsolidationRequest(BaseModel):
    """
    Request body for POST /anchor/consolidation.

    Issue #203: Anchor a NousCoder synthesis consolidation output to HCS.
    """
    consolidation_id: str = Field(
        ...,
        min_length=1,
        description="Unique consolidation identifier"
    )
    synthesis_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the synthesized output"
    )
    source_memory_ids: List[str] = Field(
        ...,
        description="List of source memory IDs used in this consolidation"
    )
    model_used: str = Field(
        ...,
        min_length=1,
        description="Model used for synthesis (e.g., nous-codestral-22b)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "consolidation_id": "cons_001",
                "synthesis_hash": "b" * 64,
                "source_memory_ids": ["mem_a", "mem_b", "mem_c"],
                "model_used": "nous-codestral-22b",
            }
        }


# ---------------------------------------------------------------------------
# Response / Record Schemas
# ---------------------------------------------------------------------------

class AnchorRecord(BaseModel):
    """
    Stored anchor record retrieved from the HCS mirror node.

    Used by get_anchor (Issue #200) and as the basis for integrity checks.
    """
    memory_id: str = Field(..., description="Memory identifier")
    content_hash: str = Field(..., description="SHA-256 hash stored at anchor time")
    sequence_number: Optional[int] = Field(
        default=None, description="HCS topic sequence number"
    )
    timestamp: Optional[str] = Field(
        default=None, description="ISO timestamp when anchor was submitted"
    )
    agent_id: Optional[str] = Field(default=None, description="Owning agent ID")
    namespace: Optional[str] = Field(default=None, description="Memory namespace")

    class Config:
        from_attributes = True


class AnchorMessage(BaseModel):
    """
    Internal HCS message payload structure.

    Represents the JSON body submitted to the HCS topic for any anchor type.
    Used for serialisation validation in tests.
    """
    type: str = Field(..., description="Message type: memory_anchor | compliance_anchor | consolidation_anchor")
    timestamp: str = Field(..., description="ISO timestamp of the anchor operation")
    extra: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional type-specific fields"
    )

    class Config:
        from_attributes = True


class MemoryAnchorResponse(BaseModel):
    """
    Response for POST /anchor/memory (Issue #200).
    """
    memory_id: str = Field(..., description="Anchored memory identifier")
    sequence_number: int = Field(..., description="HCS sequence number of the submitted message")
    timestamp: str = Field(..., description="ISO timestamp of the anchor operation")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "memory_id": "mem_abc123",
                "sequence_number": 42,
                "timestamp": "2026-04-03T12:00:00Z",
            }
        }


class ComplianceAnchorResponse(BaseModel):
    """
    Response for POST /anchor/compliance (Issue #201).
    """
    event_id: str = Field(..., description="Anchored compliance event identifier")
    sequence_number: int = Field(..., description="HCS sequence number")
    timestamp: str = Field(..., description="ISO timestamp of the anchor operation")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": "evt_kyc_001",
                "sequence_number": 77,
                "timestamp": "2026-04-03T12:00:00Z",
            }
        }


class MemoryIntegrityResult(BaseModel):
    """
    Response for GET /anchor/{memory_id}/verify (Issue #202).

    When anchor is found:
      verified, match, anchor_hash, current_hash, anchor_timestamp are populated.

    When no anchor exists:
      verified=False, reason="no_anchor_found".
    """
    verified: bool = Field(..., description="True if an anchor was found and the hashes matched")
    match: Optional[bool] = Field(
        default=None,
        description="True if current_hash == anchor_hash; absent when no anchor found"
    )
    anchor_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash stored in HCS at anchor time"
    )
    current_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the supplied current content"
    )
    anchor_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp recorded when the memory was anchored"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for failed verification (e.g., 'no_anchor_found')"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "verified": True,
                "match": True,
                "anchor_hash": "a" * 64,
                "current_hash": "a" * 64,
                "anchor_timestamp": "2026-04-03T12:00:00Z",
                "reason": None,
            }
        }


class ConsolidationAnchor(BaseModel):
    """
    Response for POST /anchor/consolidation (Issue #203).
    """
    consolidation_id: str = Field(..., description="Anchored consolidation identifier")
    sequence_number: int = Field(..., description="HCS sequence number")
    timestamp: str = Field(..., description="ISO timestamp of the anchor operation")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "consolidation_id": "cons_001",
                "sequence_number": 88,
                "timestamp": "2026-04-03T12:00:00Z",
            }
        }
