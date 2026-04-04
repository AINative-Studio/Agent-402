"""
Pydantic schemas for the Hedera Reputation System.

Issues #196-#199: HCS-Anchored Reputation System.

Schemas:
- FeedbackSubmission: Input schema for submitting feedback
- FeedbackEntry: Output schema for a single feedback record
- ReputationScore: Output schema for calculated reputation
- TrustTier: IntEnum for tier levels
- AgentRanking / RankedAgent: Output schemas for ranked agents
- PaymentVerificationResult: Output schema for payment verification
- FeedbackValidationResult: Output schema for feedback validation

Built by AINative Dev Team
Refs #196, #197, #198, #199
"""
from __future__ import annotations

from enum import IntEnum
from datetime import datetime
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field, validator


class TrustTier(IntEnum):
    """
    Trust tier levels for agent reputation.

    Tiers map to:
    - NEW (0): Fewer than 3 reviews
    - BASIC (1): Score < 2.0 or fewer than 10 reviews
    - TRUSTED (2): Score >= 2.0 and >= 10 reviews
    - VERIFIED (3): Score >= 3.5 and >= 25 reviews
    - ESTABLISHED (4): Score >= 4.0 and >= 50 reviews

    Mirrors the Solidity ReputationRegistry.sol tier definitions.
    """

    NEW = 0
    BASIC = 1
    TRUSTED = 2
    VERIFIED = 3
    ESTABLISHED = 4


# Human-readable tier names
TIER_NAMES: Dict[int, str] = {
    TrustTier.NEW: "New",
    TrustTier.BASIC: "Basic",
    TrustTier.TRUSTED: "Trusted",
    TrustTier.VERIFIED: "Verified",
    TrustTier.ESTABLISHED: "Established",
}


class FeedbackSubmission(BaseModel):
    """
    Input schema for submitting feedback about an agent.

    Rating must be an integer between 1 and 5 inclusive.
    The agent_did is taken from the URL path parameter, not the body.
    """

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 (lowest) to 5 (highest)"
    )
    comment: str = Field(
        default="",
        description="Optional textual comment about the agent's work"
    )
    payment_proof_tx: str = Field(
        ...,
        description="Hedera transaction ID proving payment was made to the agent"
    )
    task_id: str = Field(
        ...,
        description="Unique identifier for the task this feedback relates to"
    )
    submitter_did: str = Field(
        ...,
        description="DID of the entity submitting this feedback"
    )

    @validator("payment_proof_tx")
    def payment_proof_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("payment_proof_tx cannot be empty")
        return v

    @validator("task_id")
    def task_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("task_id cannot be empty")
        return v

    @validator("submitter_did")
    def submitter_did_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("submitter_did cannot be empty")
        return v


class FeedbackEntry(BaseModel):
    """
    Output schema for a single feedback record retrieved from HCS.

    Includes all submitted fields plus the HCS consensus metadata.
    """

    agent_did: str = Field(..., description="DID of the agent being reviewed")
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="")
    payment_proof_tx: str
    task_id: str
    submitter_did: str
    consensus_timestamp: str = Field(
        ...,
        description="HCS consensus timestamp in seconds.nanoseconds format"
    )
    sequence_number: int = Field(
        ...,
        description="HCS topic sequence number for this message"
    )


class ReputationScore(BaseModel):
    """
    Output schema for a calculated agent reputation score.

    The score is a weighted average with recency decay applied.
    Trust tier is derived from score and total_reviews count.
    """

    agent_did: str
    score: float = Field(
        ...,
        ge=0.0,
        le=5.0,
        description="Weighted reputation score from 0.0 to 5.0"
    )
    total_reviews: int = Field(..., ge=0)
    trust_tier: int = Field(
        ...,
        ge=0,
        le=4,
        description="Trust tier level (0=New, 1=Basic, 2=Trusted, 3=Verified, 4=Established)"
    )
    tier_name: str = Field(..., description="Human-readable tier name")
    last_updated: Optional[str] = Field(
        default=None,
        description="ISO timestamp of when score was last calculated"
    )


class FeedbackSubmissionReceipt(BaseModel):
    """Output schema for feedback submission confirmation."""

    sequence_number: int = Field(
        ...,
        description="HCS sequence number assigned to this feedback message"
    )
    consensus_timestamp: str = Field(
        ...,
        description="HCS consensus timestamp"
    )
    topic_id: str = Field(
        ...,
        description="HCS topic ID where feedback was anchored"
    )
    agent_did: str = Field(..., description="DID of the agent receiving feedback")


class RankedAgent(BaseModel):
    """A single agent in the ranked list."""

    agent_did: str
    score: float = Field(..., ge=0.0, le=5.0)
    trust_tier: int = Field(..., ge=0, le=4)
    capabilities: List[str] = Field(default_factory=list)


class AgentRanking(BaseModel):
    """Output schema for ranked agents list."""

    agents: List[RankedAgent] = Field(
        default_factory=list,
        description="Agents sorted by score descending"
    )
    total: int = Field(..., ge=0, description="Total number of agents returned")


class PaymentVerificationResult(BaseModel):
    """Output schema for payment proof verification."""

    verified: bool = Field(
        ...,
        description="True if payment proof is valid and confirmed"
    )
    reason: str = Field(
        ...,
        description="Human-readable reason for verification result"
    )
    transaction_id: Optional[str] = Field(
        default=None,
        description="The verified Hedera transaction ID"
    )
    amount: Optional[int] = Field(
        default=None,
        description="Transfer amount in token smallest unit"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="Consensus timestamp of the verified transaction"
    )


class FeedbackValidationResult(BaseModel):
    """Output schema for feedback validation (before HCS submission)."""

    valid: bool = Field(
        ...,
        description="True if feedback passes all validation checks"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages (empty if valid)"
    )
