"""
Hedera Reputation API endpoints.
HCS-anchored agent reputation system.

Issues #196-#199: HCS-Anchored Reputation System

Endpoints:
- POST /api/v1/hedera/reputation/{agent_did}/feedback
    Submit feedback for an agent (validates payment proof first)
- GET  /api/v1/hedera/reputation/{agent_did}
    Get reputation score and trust tier for an agent
- GET  /api/v1/hedera/reputation/ranked
    Get agents ranked by reputation (accepts filter params)
- GET  /api/v1/hedera/reputation/{agent_did}/feedback
    List feedback entries for an agent from HCS

NOTE: This router is NOT registered in main.py.
      Another group handles router registration.

Built by AINative Dev Team
Refs #196, #197, #198, #199
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.hedera_reputation import (
    FeedbackSubmission,
    FeedbackEntry,
    ReputationScore,
    FeedbackSubmissionReceipt,
    AgentRanking,
    RankedAgent,
    TIER_NAMES,
    TrustTier,
)
from app.services.hedera_reputation_service import (
    HederaReputationService,
    HederaReputationError,
    get_reputation_service,
)
from app.services.reputation_agent_selector import (
    ReputationAgentSelector,
    get_agent_selector,
)
from app.services.feedback_payment_verifier import (
    FeedbackPaymentVerifier,
    get_payment_verifier,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/hedera/reputation",
    tags=["hedera-reputation"]
)


@router.post(
    "/{agent_did}/feedback",
    response_model=FeedbackSubmissionReceipt,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Feedback submitted to HCS successfully"},
        400: {"description": "Invalid payment proof or validation failure"},
        422: {"description": "Request body validation error (e.g. rating out of range)"},
        502: {"description": "Hedera network error"},
    },
    summary="Submit feedback for an agent",
    description="""
    Submit feedback for an agent anchored to Hedera Consensus Service (HCS).

    **Payment Proof Required:** A valid Hedera transaction ID proving payment
    to the agent must be provided. The transaction is verified against the
    mirror node before feedback is accepted.

    **Self-Review Prevention:** The submitter_did cannot match the agent_did.

    **Rating:** Integer from 1 (lowest) to 5 (highest).

    Refs #196, #199
    """,
)
async def submit_feedback(
    agent_did: str,
    body: FeedbackSubmission,
    reputation_service: HederaReputationService = Depends(get_reputation_service),
    payment_verifier: FeedbackPaymentVerifier = Depends(get_payment_verifier),
) -> FeedbackSubmissionReceipt:
    """Submit feedback for an agent to HCS."""
    feedback_dict = {
        "agent_did": agent_did,
        "rating": body.rating,
        "comment": body.comment,
        "payment_proof_tx": body.payment_proof_tx,
        "task_id": body.task_id,
        "submitter_did": body.submitter_did,
    }

    # Validate payment proof and other submission rules
    validation = await payment_verifier.validate_feedback_submission(feedback_dict)
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FEEDBACK_VALIDATION_FAILED",
                "errors": validation["errors"]
            }
        )

    try:
        receipt = await reputation_service.submit_feedback(
            agent_did=agent_did,
            rating=body.rating,
            comment=body.comment,
            payment_proof_tx=body.payment_proof_tx,
            task_id=body.task_id,
            submitter_did=body.submitter_did,
        )
    except HederaReputationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "detail": exc.detail}
        )

    return FeedbackSubmissionReceipt(
        sequence_number=receipt["sequence_number"],
        consensus_timestamp=receipt["consensus_timestamp"],
        topic_id=receipt["topic_id"],
        agent_did=agent_did,
    )


@router.get(
    "/ranked",
    response_model=AgentRanking,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Ranked list of agents by reputation"},
    },
    summary="Get agents ranked by reputation",
    description="""
    Returns agents ranked by their reputation score (highest first).

    Optional filters:
    - **min_trust_tier**: Minimum trust tier (0=New, 1=Basic, 2=Trusted, 3=Verified, 4=Established)
    - **min_score**: Minimum reputation score (0.0-5.0)

    The candidates list must be provided as query parameters.
    In production this integrates with the agent registry.

    Refs #198
    """,
)
async def get_ranked_agents(
    min_trust_tier: int = Query(default=0, ge=0, le=4),
    min_score: float = Query(default=0.0, ge=0.0, le=5.0),
    agent_selector: ReputationAgentSelector = Depends(get_agent_selector),
) -> AgentRanking:
    """Get agents ranked by reputation score."""
    # In a full implementation this would query the agent registry.
    # For now, return an empty filtered list that respects the query params.
    candidates: List[Dict[str, Any]] = []

    ranked = await agent_selector.select_agents_by_reputation(
        candidates=candidates,
        min_trust_tier=min_trust_tier,
        min_score=min_score,
    )

    agents = [
        RankedAgent(
            agent_did=a["agent_did"],
            score=a["score"],
            trust_tier=a["trust_tier"],
            capabilities=a.get("capabilities", []),
        )
        for a in ranked
    ]

    return AgentRanking(agents=agents, total=len(agents))


@router.get(
    "/{agent_did}",
    response_model=ReputationScore,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Agent reputation score and trust tier"},
    },
    summary="Get reputation score for an agent",
    description="""
    Calculate and return the reputation score for an agent.

    The score is a weighted average of all HCS-anchored feedback with
    exponential recency decay (30-day half-life by default).

    Trust tier is derived from score and total review count:
    - **New (0)**: < 3 reviews
    - **Basic (1)**: < 10 reviews (any score)
    - **Trusted (2)**: score >= 2.0 and >= 10 reviews
    - **Verified (3)**: score >= 3.5 and >= 25 reviews
    - **Established (4)**: score >= 4.0 and >= 50 reviews

    Refs #197
    """,
)
async def get_reputation_score(
    agent_did: str,
    reputation_service: HederaReputationService = Depends(get_reputation_service),
) -> ReputationScore:
    """Get reputation score and trust tier for an agent."""
    try:
        result = await reputation_service.calculate_reputation_score(agent_did)
    except HederaReputationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "detail": exc.detail}
        )

    tier = result["trust_tier"]
    tier_name = TIER_NAMES.get(tier, "Unknown")

    from datetime import datetime, timezone
    return ReputationScore(
        agent_did=agent_did,
        score=float(result["score"]),
        total_reviews=result["total_reviews"],
        trust_tier=tier,
        tier_name=tier_name,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/{agent_did}/feedback",
    response_model=List[FeedbackEntry],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of feedback entries for the agent"},
    },
    summary="List feedback entries for an agent",
    description="""
    Retrieve feedback entries anchored to HCS for an agent.

    Results are fetched from the Hedera mirror node and sorted by
    consensus timestamp (newest first by default).

    Refs #196
    """,
)
async def list_feedback(
    agent_did: str,
    limit: int = Query(default=50, ge=1, le=200),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    reputation_service: HederaReputationService = Depends(get_reputation_service),
) -> List[FeedbackEntry]:
    """List HCS-anchored feedback entries for an agent."""
    try:
        entries = await reputation_service.get_feedback(
            agent_did=agent_did,
            limit=limit,
            order=order,
        )
    except HederaReputationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "detail": exc.detail}
        )

    return [
        FeedbackEntry(
            agent_did=entry.get("agent_did", agent_did),
            rating=entry["rating"],
            comment=entry.get("comment", ""),
            payment_proof_tx=entry.get("payment_proof_tx", ""),
            task_id=entry.get("task_id", ""),
            submitter_did=entry.get("submitter_did", ""),
            consensus_timestamp=entry.get("consensus_timestamp", ""),
            sequence_number=entry.get("sequence_number", 0),
        )
        for entry in entries
    ]
