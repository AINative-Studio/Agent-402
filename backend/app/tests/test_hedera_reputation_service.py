"""
Tests for HederaReputationService.
Issues #196 (HCS-Anchored Feedback Submission) and #197 (Score Calculation).

TDD Approach: Tests written FIRST, then implementation.
BDD-style: class Describe* / def it_* naming.

Test Coverage:
- Feedback submission to HCS topics
- Rating validation (1-5 range)
- Message format verification
- Mirror node feedback retrieval
- Reputation score calculation with recency decay
- Trust tier assignment
- Edge cases: empty feedback, boundary ratings, zero decay
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, List, Any


class DescribeHederaReputationServiceInit:
    """Tests for HederaReputationService initialization."""

    def it_initializes_with_default_hedera_client(self):
        """Service initializes with a lazily-created Hedera client."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        assert service._hedera_client is None  # lazy init

    def it_accepts_injected_hedera_client(self):
        """Service accepts an injected Hedera client for testing."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = MagicMock()
        service = HederaReputationService(hedera_client=mock_client)
        assert service.hedera_client is mock_client

    def it_uses_configurable_half_life_days(self):
        """Service accepts configurable decay half-life."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService(half_life_days=60)
        assert service.half_life_days == 60

    def it_defaults_to_30_day_half_life(self):
        """Default decay half-life is 30 days."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        assert service.half_life_days == 30


class DescribeSubmitFeedback:
    """Tests for submit_feedback method — Issue #196."""

    @pytest.mark.asyncio
    async def it_submits_feedback_with_valid_rating(self):
        """Submits feedback to HCS and returns sequence number."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message = AsyncMock(return_value={
            "sequence_number": 42,
            "consensus_timestamp": "1234567890.000000000",
            "topic_id": "0.0.99999"
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.submit_feedback(
            agent_did="did:hedera:testnet:abc123",
            rating=5,
            comment="Excellent agent",
            payment_proof_tx="0.0.12345@1234567890.000000000",
            task_id="task_abc",
            submitter_did="did:hedera:testnet:submitter1"
        )

        assert result["sequence_number"] == 42

    @pytest.mark.asyncio
    async def it_rejects_rating_below_1(self):
        """Raises error when rating is below 1."""
        from app.services.hedera_reputation_service import (
            HederaReputationService,
            HederaReputationError
        )

        service = HederaReputationService(hedera_client=AsyncMock())
        with pytest.raises(HederaReputationError) as exc_info:
            await service.submit_feedback(
                agent_did="did:hedera:testnet:abc123",
                rating=0,
                comment="Bad",
                payment_proof_tx="0.0.12345@123.000",
                task_id="task_1",
                submitter_did="did:hedera:testnet:sub1"
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def it_rejects_rating_above_5(self):
        """Raises error when rating exceeds 5."""
        from app.services.hedera_reputation_service import (
            HederaReputationService,
            HederaReputationError
        )

        service = HederaReputationService(hedera_client=AsyncMock())
        with pytest.raises(HederaReputationError) as exc_info:
            await service.submit_feedback(
                agent_did="did:hedera:testnet:abc123",
                rating=6,
                comment="Too high",
                payment_proof_tx="0.0.12345@123.000",
                task_id="task_1",
                submitter_did="did:hedera:testnet:sub1"
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def it_accepts_boundary_ratings_1_and_5(self):
        """Accepts exactly 1 and 5 as valid ratings."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message = AsyncMock(return_value={
            "sequence_number": 1,
            "consensus_timestamp": "1234567890.000000000",
            "topic_id": "0.0.99999"
        })

        service = HederaReputationService(hedera_client=mock_client)

        result_min = await service.submit_feedback(
            agent_did="did:hedera:testnet:abc123",
            rating=1,
            comment="Minimum rating",
            payment_proof_tx="0.0.12345@123.000",
            task_id="task_min",
            submitter_did="did:hedera:testnet:sub1"
        )
        assert result_min["sequence_number"] == 1

        result_max = await service.submit_feedback(
            agent_did="did:hedera:testnet:abc123",
            rating=5,
            comment="Maximum rating",
            payment_proof_tx="0.0.12345@123.000",
            task_id="task_max",
            submitter_did="did:hedera:testnet:sub1"
        )
        assert result_max["sequence_number"] == 1

    @pytest.mark.asyncio
    async def it_submits_correct_message_format(self):
        """HCS message contains all required fields in correct format."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        submitted_message = {}

        async def capture_message(topic_id, message):
            submitted_message.update(message)
            return {"sequence_number": 10, "consensus_timestamp": "123.000", "topic_id": topic_id}

        mock_client.submit_hcs_message = capture_message

        service = HederaReputationService(hedera_client=mock_client)
        await service.submit_feedback(
            agent_did="did:hedera:testnet:agent1",
            rating=4,
            comment="Good work",
            payment_proof_tx="0.0.11111@999.000",
            task_id="task_xyz",
            submitter_did="did:hedera:testnet:user1"
        )

        assert submitted_message["type"] == "feedback"
        assert submitted_message["agent_did"] == "did:hedera:testnet:agent1"
        assert submitted_message["rating"] == 4
        assert submitted_message["comment"] == "Good work"
        assert submitted_message["payment_proof_tx"] == "0.0.11111@999.000"
        assert submitted_message["task_id"] == "task_xyz"
        assert submitted_message["submitter_did"] == "did:hedera:testnet:user1"
        assert "timestamp" in submitted_message

    @pytest.mark.asyncio
    async def it_rejects_empty_agent_did(self):
        """Raises error when agent_did is empty."""
        from app.services.hedera_reputation_service import (
            HederaReputationService,
            HederaReputationError
        )

        service = HederaReputationService(hedera_client=AsyncMock())
        with pytest.raises(HederaReputationError):
            await service.submit_feedback(
                agent_did="",
                rating=3,
                comment="Good",
                payment_proof_tx="0.0.12345@123.000",
                task_id="task_1",
                submitter_did="did:hedera:testnet:sub1"
            )

    @pytest.mark.asyncio
    async def it_rejects_empty_task_id(self):
        """Raises error when task_id is empty."""
        from app.services.hedera_reputation_service import (
            HederaReputationService,
            HederaReputationError
        )

        service = HederaReputationService(hedera_client=AsyncMock())
        with pytest.raises(HederaReputationError):
            await service.submit_feedback(
                agent_did="did:hedera:testnet:abc",
                rating=3,
                comment="Good",
                payment_proof_tx="0.0.12345@123.000",
                task_id="",
                submitter_did="did:hedera:testnet:sub1"
            )

    @pytest.mark.asyncio
    async def it_returns_consensus_timestamp_in_receipt(self):
        """Receipt includes consensus timestamp from HCS."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.submit_hcs_message = AsyncMock(return_value={
            "sequence_number": 7,
            "consensus_timestamp": "9999999999.123456789",
            "topic_id": "0.0.88888"
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.submit_feedback(
            agent_did="did:hedera:testnet:agent2",
            rating=3,
            comment="Average",
            payment_proof_tx="0.0.22222@888.000",
            task_id="task_abc",
            submitter_did="did:hedera:testnet:sub2"
        )

        assert result["consensus_timestamp"] == "9999999999.123456789"


class DescribeGetFeedback:
    """Tests for get_feedback method — Issue #196."""

    @pytest.mark.asyncio
    async def it_returns_feedback_entries_for_agent(self):
        """Returns list of feedback entries from mirror node."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": "1234567890.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 5,
                        "comment": "Great",
                        "payment_proof_tx": "0.0.11111@123.000",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": "2026-03-01T00:00:00Z"
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.get_feedback("did:hedera:testnet:agent1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["rating"] == 5

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_feedback(self):
        """Returns empty list when no feedback exists."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": []})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.get_feedback("did:hedera:testnet:new_agent")

        assert result == []

    @pytest.mark.asyncio
    async def it_respects_limit_parameter(self):
        """Passes limit parameter to mirror node query."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        captured_params = {}

        async def capture_query(topic_id, limit, order):
            captured_params["limit"] = limit
            captured_params["order"] = order
            return {"messages": []}

        mock_client.query_hcs_topic = capture_query

        service = HederaReputationService(hedera_client=mock_client)
        await service.get_feedback("did:hedera:testnet:agent1", limit=10)

        assert captured_params["limit"] == 10

    @pytest.mark.asyncio
    async def it_defaults_to_desc_order(self):
        """Default order is descending (newest first)."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        captured_params = {}

        async def capture_query(topic_id, limit, order):
            captured_params["order"] = order
            return {"messages": []}

        mock_client.query_hcs_topic = capture_query

        service = HederaReputationService(hedera_client=mock_client)
        await service.get_feedback("did:hedera:testnet:agent1")

        assert captured_params["order"] == "desc"

    @pytest.mark.asyncio
    async def it_includes_consensus_timestamps_in_entries(self):
        """Each feedback entry includes consensus_timestamp."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 3,
                    "consensus_timestamp": "1717171717.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 4,
                        "comment": "Good",
                        "payment_proof_tx": "0.0.11111@123.000",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": "2026-01-01T00:00:00Z"
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.get_feedback("did:hedera:testnet:agent1")

        assert result[0]["consensus_timestamp"] == "1717171717.000000000"
        assert result[0]["sequence_number"] == 3


class DescribeCalculateReputationScore:
    """Tests for calculate_reputation_score method — Issue #197."""

    @pytest.mark.asyncio
    async def it_returns_zero_score_for_no_reviews(self):
        """Returns zero score when agent has no feedback."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": []})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:new_agent")

        assert result["score"] == 0.0
        assert result["total_reviews"] == 0

    @pytest.mark.asyncio
    async def it_calculates_simple_average_for_recent_reviews(self):
        """Calculates weighted average for reviews from same day."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": "1234567890.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 4,
                        "comment": "Good",
                        "payment_proof_tx": "tx1",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": ts
                    }
                },
                {
                    "sequence_number": 2,
                    "consensus_timestamp": "1234567891.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 4,
                        "comment": "Also good",
                        "payment_proof_tx": "tx2",
                        "task_id": "task_2",
                        "submitter_did": "did:hedera:testnet:sub2",
                        "timestamp": ts
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert abs(result["score"] - 4.0) < 0.01
        assert result["total_reviews"] == 2

    @pytest.mark.asyncio
    async def it_applies_recency_decay_to_older_reviews(self):
        """Older reviews have less weight than newer reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        recent_ts = now.isoformat()
        old_ts = (now - timedelta(days=90)).isoformat()  # 3 half-lives old

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": "1234567890.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 5,
                        "comment": "Recent 5-star",
                        "payment_proof_tx": "tx1",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": recent_ts
                    }
                },
                {
                    "sequence_number": 2,
                    "consensus_timestamp": "1111111111.000000000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 1,
                        "comment": "Old 1-star",
                        "payment_proof_tx": "tx2",
                        "task_id": "task_2",
                        "submitter_did": "did:hedera:testnet:sub2",
                        "timestamp": old_ts
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        # Score should be much closer to 5 than to 3 (unweighted average)
        assert result["score"] > 4.0

    @pytest.mark.asyncio
    async def it_assigns_new_tier_for_under_3_reviews(self):
        """Assigns NEW tier (0) when agent has fewer than 3 reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": "123.000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 5,
                        "comment": "Great",
                        "payment_proof_tx": "tx1",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": ts
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert result["trust_tier"] == 0

    @pytest.mark.asyncio
    async def it_assigns_basic_tier_for_low_score(self):
        """Assigns BASIC tier (1) for score < 2.0 or < 10 reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()
        messages = []
        for i in range(5):  # 5 reviews, meets >= 3 threshold but < 10
            messages.append({
                "sequence_number": i + 1,
                "consensus_timestamp": f"12345678{i:02d}.000000000",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:agent1",
                    "rating": 3,
                    "comment": f"Review {i}",
                    "payment_proof_tx": f"tx{i}",
                    "task_id": f"task_{i}",
                    "submitter_did": f"did:hedera:testnet:sub{i}",
                    "timestamp": ts
                }
            })

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": messages})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert result["trust_tier"] == 1  # BASIC: >= 3 reviews but < 10

    @pytest.mark.asyncio
    async def it_assigns_trusted_tier_for_score_2_and_10_reviews(self):
        """Assigns TRUSTED tier (2) for score >= 2.0 and >= 10 reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()
        messages = []
        for i in range(10):  # exactly 10 reviews with score >= 2.0
            messages.append({
                "sequence_number": i + 1,
                "consensus_timestamp": f"12345678{i:02d}.000000000",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:agent1",
                    "rating": 3,
                    "comment": f"Review {i}",
                    "payment_proof_tx": f"tx{i}",
                    "task_id": f"task_{i}",
                    "submitter_did": f"did:hedera:testnet:sub{i}",
                    "timestamp": ts
                }
            })

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": messages})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert result["trust_tier"] == 2  # TRUSTED

    @pytest.mark.asyncio
    async def it_assigns_verified_tier_for_score_3_5_and_25_reviews(self):
        """Assigns VERIFIED tier (3) for score >= 3.5 and >= 25 reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()
        messages = []
        for i in range(25):  # exactly 25 reviews with score >= 3.5
            messages.append({
                "sequence_number": i + 1,
                "consensus_timestamp": f"123456{i:04d}.000000000",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:agent1",
                    "rating": 4,
                    "comment": f"Review {i}",
                    "payment_proof_tx": f"tx{i}",
                    "task_id": f"task_{i}",
                    "submitter_did": f"did:hedera:testnet:sub{i}",
                    "timestamp": ts
                }
            })

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": messages})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert result["trust_tier"] == 3  # VERIFIED

    @pytest.mark.asyncio
    async def it_assigns_established_tier_for_score_4_and_50_reviews(self):
        """Assigns ESTABLISHED tier (4) for score >= 4.0 and >= 50 reviews."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()
        messages = []
        for i in range(50):  # exactly 50 reviews with high score
            messages.append({
                "sequence_number": i + 1,
                "consensus_timestamp": f"123{i:07d}.000000000",
                "message": {
                    "type": "feedback",
                    "agent_did": "did:hedera:testnet:agent1",
                    "rating": 5,
                    "comment": f"Excellent {i}",
                    "payment_proof_tx": f"tx{i}",
                    "task_id": f"task_{i}",
                    "submitter_did": f"did:hedera:testnet:sub{i}",
                    "timestamp": ts
                }
            })

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={"messages": messages})

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert result["trust_tier"] == 4  # ESTABLISHED

    @pytest.mark.asyncio
    async def it_returns_score_as_float_between_0_and_5(self):
        """Score is always a float between 0.0 and 5.0."""
        from app.services.hedera_reputation_service import HederaReputationService

        now = datetime.now(timezone.utc)
        ts = now.isoformat()

        mock_client = AsyncMock()
        mock_client.query_hcs_topic = AsyncMock(return_value={
            "messages": [
                {
                    "sequence_number": 1,
                    "consensus_timestamp": "123.000",
                    "message": {
                        "type": "feedback",
                        "agent_did": "did:hedera:testnet:agent1",
                        "rating": 3,
                        "comment": "OK",
                        "payment_proof_tx": "tx1",
                        "task_id": "task_1",
                        "submitter_did": "did:hedera:testnet:sub1",
                        "timestamp": ts
                    }
                }
            ]
        })

        service = HederaReputationService(hedera_client=mock_client)
        result = await service.calculate_reputation_score("did:hedera:testnet:agent1")

        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 5.0


class DescribeCalculateDecayWeight:
    """Tests for _calculate_decay_weight helper — Issue #197."""

    def it_returns_weight_1_for_today(self):
        """Weight is 1.0 for feedback from today."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        now = datetime.now(timezone.utc)
        weight = service._calculate_decay_weight(now, half_life_days=30)

        assert abs(weight - 1.0) < 0.001

    def it_returns_weight_half_after_one_half_life(self):
        """Weight is 0.5 after one half-life period."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        weight = service._calculate_decay_weight(thirty_days_ago, half_life_days=30)

        assert abs(weight - 0.5) < 0.001

    def it_returns_weight_quarter_after_two_half_lives(self):
        """Weight is 0.25 after two half-life periods."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        now = datetime.now(timezone.utc)
        sixty_days_ago = now - timedelta(days=60)
        weight = service._calculate_decay_weight(sixty_days_ago, half_life_days=30)

        assert abs(weight - 0.25) < 0.001

    def it_uses_configurable_half_life(self):
        """Decay uses the provided half_life_days parameter."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        now = datetime.now(timezone.utc)
        sixty_days_ago = now - timedelta(days=60)

        weight_30 = service._calculate_decay_weight(sixty_days_ago, half_life_days=30)
        weight_60 = service._calculate_decay_weight(sixty_days_ago, half_life_days=60)

        assert weight_60 > weight_30  # longer half-life = slower decay

    def it_never_returns_negative_weight(self):
        """Weight is always non-negative even for very old feedback."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        now = datetime.now(timezone.utc)
        ancient = now - timedelta(days=3650)  # 10 years ago
        weight = service._calculate_decay_weight(ancient, half_life_days=30)

        assert weight >= 0.0

    def it_handles_naive_datetime_without_timezone(self):
        """Handles naive datetime by treating it as UTC."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        naive_dt = datetime.now()  # no tzinfo
        weight = service._calculate_decay_weight(naive_dt, half_life_days=30)

        assert weight >= 0.0
        assert weight <= 1.0


class DescribeParseTimestamps:
    """Tests for timestamp parsing helpers."""

    def it_parses_iso_timestamp_string(self):
        """_parse_feedback_timestamp parses a valid ISO 8601 string."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        dt = service._parse_feedback_timestamp("2026-03-01T00:00:00Z")

        assert dt.tzinfo is not None
        assert dt.year == 2026

    def it_falls_back_to_now_for_invalid_timestamp(self):
        """_parse_feedback_timestamp returns now() for an unparseable string."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        before = datetime.now(timezone.utc)
        dt = service._parse_feedback_timestamp("not-a-timestamp")
        after = datetime.now(timezone.utc)

        assert before <= dt <= after

    def it_parses_consensus_timestamp_hcs_format(self):
        """_parse_consensus_timestamp handles seconds.nanoseconds format."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        dt = service._parse_consensus_timestamp("1717171717.000000000", {})

        assert dt.tzinfo is not None
        assert dt.year >= 2024  # 1717171717 epoch is year 2024

    def it_falls_back_for_non_hcs_consensus_timestamp(self):
        """_parse_consensus_timestamp returns now() for non-HCS format."""
        from app.services.hedera_reputation_service import HederaReputationService

        service = HederaReputationService()
        before = datetime.now(timezone.utc)
        dt = service._parse_consensus_timestamp("", {})
        after = datetime.now(timezone.utc)

        assert before <= dt <= after


class DescribeGetReputationService:
    """Tests for the module-level factory function."""

    def it_returns_a_hedera_reputation_service_instance(self):
        """get_reputation_service returns a properly configured instance."""
        from app.services.hedera_reputation_service import (
            HederaReputationService,
            get_reputation_service
        )

        svc = get_reputation_service()
        assert isinstance(svc, HederaReputationService)
        assert svc.half_life_days == 30
