"""
Pydantic schemas for Hedera Agent Identity System.

Issues #191, #192, #193, #194:
- HTS NFT Agent Registry schemas
- did:hedera DID Document schemas
- HCS-14 Directory schemas
- AAP Capability mapping schemas

Built by AINative Dev Team
Refs #191, #192, #193, #194
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Issue #194: AAP Capability enum
# ---------------------------------------------------------------------------


class AAPCapability(str, Enum):
    """
    Defined AAP (Agent Action Protocol) capabilities.

    These are the only valid capability values that can be assigned to agents.
    """
    CHAT = "chat"
    MEMORY = "memory"
    VECTOR_SEARCH = "vector_search"
    FILE_STORAGE = "file_storage"
    PAYMENT = "payment"
    COMPLIANCE = "compliance"
    ANALYTICS = "analytics"


class AAPCapabilityMapping(BaseModel):
    """Maps AAP capabilities to HTS NFT metadata flags."""
    capabilities: List[AAPCapability] = Field(
        default_factory=list,
        description="List of AAP capabilities assigned to this agent"
    )
    kyc_verified: bool = Field(
        default=False,
        description="KYC flag — maps to compliance verification status"
    )
    is_suspended: bool = Field(
        default=False,
        description="Freeze flag — maps to agent suspension status"
    )


# ---------------------------------------------------------------------------
# Issue #191: HTS NFT Agent Registry schemas
# ---------------------------------------------------------------------------


class AgentNFTMetadata(BaseModel):
    """
    Metadata stored in each Agent NFT.

    This is encoded as JSON and stored as the NFT metadata bytes on HTS.
    """
    name: str = Field(description="Human-readable agent name")
    role: str = Field(description="Agent role (analyst, compliance, transaction, etc.)")
    did: str = Field(description="Agent DID string (did:hedera:testnet:{account}_{topic})")
    capabilities: List[str] = Field(
        default_factory=list,
        description="AAP capability strings assigned to this agent"
    )
    created_at: str = Field(description="ISO8601 creation timestamp")
    status: str = Field(default="active", description="Agent status (active, suspended)")


class AgentNFTResponse(BaseModel):
    """Response from NFT creation or retrieval."""
    token_id: str = Field(description="HTS token ID (e.g. 0.0.9999)")
    serial_number: int = Field(description="NFT serial number")
    metadata: AgentNFTMetadata
    owner_account: Optional[str] = Field(
        default=None,
        description="Hedera account ID that owns this NFT"
    )


# ---------------------------------------------------------------------------
# Issue #192: did:hedera DID Document schemas
# ---------------------------------------------------------------------------


class VerificationMethod(BaseModel):
    """W3C Verification Method for DID Documents."""
    id: str
    type: str = "Ed25519VerificationKey2018"
    controller: str
    public_key_base58: Optional[str] = Field(
        default=None, alias="publicKeyBase58"
    )

    class Config:
        populate_by_name = True


class ServiceEndpoint(BaseModel):
    """W3C DID Document Service Endpoint."""
    id: str
    type: str
    service_endpoint: Optional[str] = Field(
        default=None, alias="serviceEndpoint"
    )

    class Config:
        populate_by_name = True


class DIDDocument(BaseModel):
    """
    W3C-compliant DID Document.

    Follows the W3C DID Core spec:
    https://www.w3.org/TR/did-core/
    """
    id: str = Field(description="The DID string (did:hedera:testnet:...)")
    controller: str = Field(description="Controller DID string")
    verification_method: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="verificationMethod",
        description="List of verification methods"
    )
    authentication: List[Any] = Field(
        default_factory=list,
        description="Authentication verification method references"
    )
    service: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Service endpoints"
    )

    class Config:
        populate_by_name = True


class DIDResolutionMetadata(BaseModel):
    """Metadata about a DID resolution operation."""
    created: Optional[str] = None
    updated: Optional[str] = None
    deactivated: bool = False
    resolved_at: Optional[str] = None


class DIDResolutionResult(BaseModel):
    """Result of resolving a DID string to a DID Document."""
    did_document: DIDDocument
    metadata: DIDResolutionMetadata = Field(
        default_factory=DIDResolutionMetadata
    )


# ---------------------------------------------------------------------------
# Issue #193: HCS-14 Directory schemas
# ---------------------------------------------------------------------------


class HCS14RegistrationMessage(BaseModel):
    """
    HCS-14 compliant directory registration message.

    Submitted to the Hedera Consensus Service topic for agent discovery.
    """
    type: str = Field(description="Message type: register, update, deregister")
    did: str = Field(description="Agent DID string")
    capabilities: List[str] = Field(
        default_factory=list,
        description="AAP capabilities of this agent"
    )
    role: str = Field(description="Agent role")
    reputation: int = Field(
        default=0,
        description="Agent reputation score (0+)"
    )
    timestamp: str = Field(description="ISO8601 timestamp of this message")


class DirectoryEntry(BaseModel):
    """A single entry in the HCS-14 agent directory."""
    did: str
    capabilities: List[str] = Field(default_factory=list)
    role: str
    reputation: int = 0
    registered_at: Optional[str] = None
    consensus_timestamp: Optional[str] = None


class DirectoryQueryResult(BaseModel):
    """Result of querying the HCS-14 agent directory."""
    agents: List[DirectoryEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API Request/Response schemas for the router
# ---------------------------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    """Request body for POST /api/v1/hedera/identity/register."""
    name: str = Field(description="Agent name")
    role: str = Field(description="Agent role")
    capabilities: List[str] = Field(
        default_factory=list,
        description="AAP capabilities to assign"
    )
    token_id: Optional[str] = Field(
        default=None,
        description="Existing HTS token ID to mint under; creates new class if omitted"
    )
    admin_key: Optional[str] = Field(
        default=None,
        description="Admin public key hex for new token class creation"
    )


class AgentRegisterResponse(BaseModel):
    """Response from POST /api/v1/hedera/identity/register."""
    agent_id: str
    token_id: str
    serial_number: int
    did: Optional[str] = None
    status: str
    transaction_id: Optional[str] = None


class DirectorySearchRequest(BaseModel):
    """Request body for POST /api/v1/hedera/identity/directory/search."""
    capability: Optional[str] = None
    role: Optional[str] = None
    min_reputation: Optional[int] = None


class CapabilitiesUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/hedera/identity/{agent_id}/capabilities."""
    token_id: str
    serial_number: int
    capabilities: List[str]


class CapabilitiesResponse(BaseModel):
    """Response from GET or PUT /api/v1/hedera/identity/{agent_id}/capabilities."""
    capabilities: List[str]
    token_id: Optional[str] = None
    serial_number: Optional[int] = None
    status: Optional[str] = None
