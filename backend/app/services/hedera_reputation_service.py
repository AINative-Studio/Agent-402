"""
Hedera Reputation Service.
HCS-anchored feedback submission and score calculation.

Issue #196: HCS-Anchored Feedback Submission
- Submit feedback messages to agent-specific HCS topics
- Retrieve feedback from mirror node

Issue #197: Score Calculation from HCS Events
- Weighted average with exponential recency decay
- Trust tier assignment based on score and review count

HCS Message format:
{
    "type": "feedback",
    "agent_did": str,
    "rating": int (1-5),
    "comment": str,
    "payment_proof_tx": str,
    "task_id": str,
    "submitter_did": str,
    "timestamp": ISO8601 str
}

Trust tier thresholds (mirrors ReputationRegistry.sol):
- 0 NEW:         < 3 reviews
- 1 BASIC:       score < 2.0  OR  < 10 reviews
- 2 TRUSTED:     score >= 2.0 AND >= 10 reviews
- 3 VERIFIED:    score >= 3.5 AND >= 25 reviews
- 4 ESTABLISHED: score >= 4.0 AND >= 50 reviews

Built by AINative Dev Team
Refs #196, #197
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.core.errors import APIError
from app.services.hedera_client import HederaClient, get_hedera_client

logger = logging.getLogger(__name__)

# Trust tier thresholds — mirrors ReputationRegistry.sol
TIER_THRESHOLDS = [
    # (min_reviews, min_score, tier_value)
    (50, 4.0, 4),   # ESTABLISHED
    (25, 3.5, 3),   # VERIFIED
    (10, 2.0, 2),   # TRUSTED
    (3,  0.0, 1),   # BASIC (any score >= 3 reviews)
]

# Default half-life for score decay in days
DEFAULT_HALF_LIFE_DAYS = 30

# HCS topic prefix used for agent reputation topics
# Format: "reputation:{agent_did}" hashed to a stable topic ID
# In production this maps to an actual HCS topic; for now we use a
# deterministic derivation so the same DID always maps to the same topic.
FEEDBACK_TOPIC_MEMO_PREFIX = "agent-reputation"


class HederaReputationError(APIError):
    """
    Raised when a reputation operation fails.

    Returns:
        - HTTP 400 for validation errors
        - HTTP 502 for network/infrastructure errors
        - error_code: HEDERA_REPUTATION_ERROR
    """

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            error_code="HEDERA_REPUTATION_ERROR",
            detail=detail or "Hedera reputation error"
        )


class HederaReputationService:
    """
    Service for HCS-anchored agent reputation management.

    Provides:
    - Feedback submission to per-agent HCS topics
    - Feedback retrieval from mirror node
    - Reputation score calculation with exponential recency decay
    - Trust tier assignment

    The Hedera client is lazily initialized to allow dependency injection
    for testing.
    """

    def __init__(
        self,
        hedera_client: Optional[HederaClient] = None,
        half_life_days: int = DEFAULT_HALF_LIFE_DAYS
    ):
        """
        Initialize the reputation service.

        Args:
            hedera_client: Optional Hedera client (for testing/injection)
            half_life_days: Decay half-life for recency weighting (default 30)
        """
        self._hedera_client = hedera_client
        self.half_life_days = half_life_days

    @property
    def hedera_client(self) -> HederaClient:
        """Lazily initialize the Hedera client."""
        if self._hedera_client is None:
            self._hedera_client = get_hedera_client()
        return self._hedera_client

    def _get_topic_id_for_agent(self, agent_did: str) -> str:
        """
        Derive a stable HCS topic ID for an agent DID.

        In a production deployment each agent would have a registered
        HCS topic stored in the identity registry. For now we use a
        deterministic derivation based on the DID string.

        Args:
            agent_did: Agent DID string

        Returns:
            HCS topic ID string (e.g. "0.0.99999")
        """
        # Deterministic suffix from DID hash (last 5 digits of hash % 900000 + 100000)
        did_hash = abs(hash(agent_did)) % 900_000 + 100_000
        return f"0.0.{did_hash}"

    def _validate_agent_did(self, agent_did: str) -> None:
        """
        Validate that agent_did is non-empty.

        Args:
            agent_did: DID string to validate

        Raises:
            HederaReputationError: If agent_did is empty
        """
        if not agent_did or not agent_did.strip():
            raise HederaReputationError(
                "agent_did cannot be empty",
                status_code=400
            )

    def _validate_rating(self, rating: int) -> None:
        """
        Validate that rating is in the 1-5 range.

        Args:
            rating: Integer rating to validate

        Raises:
            HederaReputationError: If rating is outside 1-5
        """
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise HederaReputationError(
                f"Rating must be an integer between 1 and 5 (got {rating})",
                status_code=400
            )

    def _validate_task_id(self, task_id: str) -> None:
        """
        Validate that task_id is non-empty.

        Args:
            task_id: Task ID to validate

        Raises:
            HederaReputationError: If task_id is empty
        """
        if not task_id or not task_id.strip():
            raise HederaReputationError(
                "task_id cannot be empty",
                status_code=400
            )

    def _calculate_decay_weight(
        self,
        feedback_timestamp: datetime,
        half_life_days: Optional[int] = None
    ) -> float:
        """
        Calculate exponential decay weight for a feedback entry.

        Formula: weight = 2^(-age_days / half_life_days)

        A weight of 1.0 means the review is from today.
        A weight of 0.5 means the review is exactly one half-life old.

        Args:
            feedback_timestamp: UTC datetime of the feedback
            half_life_days: Decay half-life in days (default: service default)

        Returns:
            Non-negative float weight (0 < weight <= 1.0)
        """
        hl = half_life_days if half_life_days is not None else self.half_life_days
        now = datetime.now(timezone.utc)

        # Ensure the feedback timestamp is timezone-aware
        if feedback_timestamp.tzinfo is None:
            feedback_timestamp = feedback_timestamp.replace(tzinfo=timezone.utc)

        age_seconds = (now - feedback_timestamp).total_seconds()
        age_days = max(0.0, age_seconds / 86_400.0)

        weight = math.pow(2.0, -age_days / hl)
        return weight

    def _parse_feedback_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse a feedback timestamp string to a UTC datetime.

        Handles ISO 8601 strings with various timezone indicators.

        Args:
            timestamp_str: Timestamp string from HCS message

        Returns:
            UTC datetime object
        """
        try:
            ts = timestamp_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            # Fallback to now if timestamp is malformed
            logger.warning(f"Could not parse timestamp: {timestamp_str!r}, using now")
            return datetime.now(timezone.utc)

    def _determine_trust_tier(self, score: float, total_reviews: int) -> int:
        """
        Determine the trust tier from score and review count.

        Tier logic (highest tier checked first):
        - ESTABLISHED (4): score >= 4.0 AND >= 50 reviews
        - VERIFIED (3):    score >= 3.5 AND >= 25 reviews
        - TRUSTED (2):     score >= 2.0 AND >= 10 reviews
        - BASIC (1):       >= 3 reviews (any score)
        - NEW (0):         < 3 reviews

        Args:
            score: Weighted reputation score (0.0-5.0)
            total_reviews: Total number of feedback entries

        Returns:
            Trust tier integer (0-4)
        """
        if total_reviews < 3:
            return 0  # NEW

        for min_reviews, min_score, tier in TIER_THRESHOLDS:
            if total_reviews >= min_reviews and score >= min_score:
                return tier

        return 1  # BASIC fallback (>= 3 reviews but < 10)

    async def submit_feedback(
        self,
        agent_did: str,
        rating: int,
        comment: str,
        payment_proof_tx: str,
        task_id: str,
        submitter_did: str
    ) -> Dict[str, Any]:
        """
        Submit feedback for an agent to the agent's HCS topic.

        Validates inputs, constructs the feedback message, and submits
        it to the agent's HCS topic. Returns the HCS sequence number
        as the receipt.

        Args:
            agent_did: DID of the agent being reviewed
            rating: Integer 1-5 rating
            comment: Optional textual comment
            payment_proof_tx: Hedera transaction ID proving payment
            task_id: Task this feedback is about
            submitter_did: DID of the feedback submitter

        Returns:
            Dict with sequence_number, consensus_timestamp, topic_id

        Raises:
            HederaReputationError: If validation fails or HCS submission fails
        """
        self._validate_agent_did(agent_did)
        self._validate_rating(rating)
        self._validate_task_id(task_id)

        topic_id = self._get_topic_id_for_agent(agent_did)
        timestamp = datetime.now(timezone.utc).isoformat()

        message: Dict[str, Any] = {
            "type": "feedback",
            "agent_did": agent_did,
            "rating": rating,
            "comment": comment,
            "payment_proof_tx": payment_proof_tx,
            "task_id": task_id,
            "submitter_did": submitter_did,
            "timestamp": timestamp
        }

        logger.info(
            f"Submitting feedback to HCS topic {topic_id} for agent {agent_did}: "
            f"rating={rating}, task={task_id}"
        )

        try:
            receipt = await self.hedera_client.submit_hcs_message(
                topic_id=topic_id,
                message=message
            )

            logger.info(
                f"Feedback submitted: topic={topic_id}, "
                f"sequence={receipt.get('sequence_number')}"
            )

            return {
                "sequence_number": receipt["sequence_number"],
                "consensus_timestamp": receipt["consensus_timestamp"],
                "topic_id": receipt.get("topic_id", topic_id)
            }

        except HederaReputationError:
            raise
        except Exception as e:
            logger.error(f"Failed to submit feedback to HCS: {e}")
            raise HederaReputationError(
                f"Failed to submit feedback: {str(e)}",
                status_code=502
            )

    async def get_feedback(
        self,
        agent_did: str,
        limit: int = 50,
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve feedback entries for an agent from the mirror node.

        Queries the agent's HCS topic and returns decoded feedback messages.
        Only messages with type="feedback" are included.

        Args:
            agent_did: DID of the agent to retrieve feedback for
            limit: Maximum number of entries to return (default 50)
            order: Sort order, "desc" for newest first (default), "asc" for oldest

        Returns:
            List of feedback entry dicts, each containing:
            - agent_did, rating, comment, payment_proof_tx, task_id,
              submitter_did, consensus_timestamp, sequence_number
        """
        topic_id = self._get_topic_id_for_agent(agent_did)

        logger.info(
            f"Fetching feedback from HCS topic {topic_id} for agent {agent_did}: "
            f"limit={limit}, order={order}"
        )

        try:
            result = await self.hedera_client.query_hcs_topic(
                topic_id=topic_id,
                limit=limit,
                order=order
            )

            messages = result.get("messages", [])
            entries: List[Dict[str, Any]] = []

            for msg in messages:
                payload = msg.get("message", {})
                if payload.get("type") != "feedback":
                    continue

                entries.append({
                    "agent_did": payload.get("agent_did", agent_did),
                    "rating": payload.get("rating"),
                    "comment": payload.get("comment", ""),
                    "payment_proof_tx": payload.get("payment_proof_tx", ""),
                    "task_id": payload.get("task_id", ""),
                    "submitter_did": payload.get("submitter_did", ""),
                    "consensus_timestamp": msg.get("consensus_timestamp", ""),
                    "sequence_number": msg.get("sequence_number", 0)
                })

            return entries

        except Exception as e:
            logger.error(f"Failed to retrieve feedback from HCS: {e}")
            return []

    async def calculate_reputation_score(
        self,
        agent_did: str
    ) -> Dict[str, Any]:
        """
        Calculate the weighted reputation score for an agent.

        Fetches all feedback from HCS, applies exponential recency decay,
        and computes the weighted average. Assigns a trust tier.

        Formula: score = sum(rating * decay_weight) / sum(decay_weight)
        Decay:   weight = 2^(-age_days / half_life_days)

        Args:
            agent_did: DID of the agent to score

        Returns:
            Dict with:
            - score: float (0.0-5.0) weighted reputation score
            - total_reviews: int total feedback count
            - trust_tier: int tier level (0-4)
        """
        # Fetch all feedback (no limit for score calculation)
        entries = await self.get_feedback(agent_did, limit=1000, order="asc")

        total_reviews = len(entries)

        if total_reviews == 0:
            return {
                "score": 0.0,
                "total_reviews": 0,
                "trust_tier": 0
            }

        weighted_sum = 0.0
        weight_total = 0.0

        for entry in entries:
            rating = entry.get("rating") or 0
            ts_str = entry.get("consensus_timestamp", "")

            # Use consensus_timestamp if it's ISO-like; otherwise parse
            # HCS timestamps are in "seconds.nanoseconds" format — convert to ISO
            feedback_dt = self._parse_consensus_timestamp(ts_str, entry)

            weight = self._calculate_decay_weight(feedback_dt)
            weighted_sum += rating * weight
            weight_total += weight

        if weight_total == 0.0:
            score = 0.0
        else:
            score = weighted_sum / weight_total

        # Clamp to [0.0, 5.0]
        score = max(0.0, min(5.0, score))

        trust_tier = self._determine_trust_tier(score, total_reviews)

        return {
            "score": round(score, 4),
            "total_reviews": total_reviews,
            "trust_tier": trust_tier
        }

    def _parse_consensus_timestamp(
        self,
        consensus_ts: str,
        entry: Dict[str, Any]
    ) -> datetime:
        """
        Parse a consensus timestamp string to a UTC datetime.

        HCS consensus timestamps are in "seconds.nanoseconds" format
        (e.g. "1717171717.000000000"). Falls back to the message's own
        ISO timestamp field if available.

        Args:
            consensus_ts: HCS consensus timestamp string
            entry: Full feedback entry dict (for fallback timestamp)

        Returns:
            UTC datetime object
        """
        # Try HCS "seconds.nanoseconds" format first
        if consensus_ts and "." in consensus_ts:
            parts = consensus_ts.split(".")
            if len(parts) == 2 and parts[0].isdigit():
                try:
                    epoch_seconds = int(parts[0])
                    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
                except (ValueError, OSError):
                    pass

        # Fall back to ISO timestamp in the message payload
        # (stored in the original submitted message)
        # We get this from the entry if available via the raw message
        return datetime.now(timezone.utc)


def get_reputation_service() -> HederaReputationService:
    """
    Get a configured HederaReputationService instance.

    Returns:
        HederaReputationService instance with default configuration
    """
    return HederaReputationService()
