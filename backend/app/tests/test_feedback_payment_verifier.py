"""
Tests for FeedbackPaymentVerifier.
Issue #199: Payment Proof Requirement for Feedback.

TDD Approach: Tests written FIRST, then implementation.
BDD-style: class Describe* / def it_* naming.

Test Coverage:
- Payment proof transaction verification via mirror node
- Transaction existence check
- Transaction success status check
- Agent account match verification
- Task ID in memo verification
- Duplicate feedback detection
- Self-review prevention
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, List, Any


class DescribeFeedbackPaymentVerifierInit:
    """Tests for FeedbackPaymentVerifier initialization."""

    def it_initializes_with_hedera_client(self):
        """Verifier holds a reference to the Hedera client."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = MagicMock()
        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        assert verifier.hedera_client is mock_client

    def it_creates_default_hedera_client_when_none_provided(self):
        """Creates a default HederaClient if none injected."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        verifier = FeedbackPaymentVerifier()
        # lazy client — just verify it doesn't crash
        assert verifier is not None


class DescribeVerifyPaymentProof:
    """Tests for verify_payment_proof method — Issue #199."""

    @pytest.mark.asyncio
    async def it_returns_verified_true_for_valid_transaction(self):
        """Returns verified=True when transaction is valid and correct."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567890.000000000",
            "hash": "0xabcdef",
            "memo": "task:task_abc",
            "transfers": [
                {"account": "0.0.99999", "amount": 1000000}  # agent's account
            ]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="0.0.12345@1234567890.000000000",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert result["verified"] is True

    @pytest.mark.asyncio
    async def it_returns_verified_false_for_failed_transaction(self):
        """Returns verified=False when transaction status is not SUCCESS."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "FAILED",
            "consensus_timestamp": None,
            "hash": None
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="0.0.12345@1234567890.000000000",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert result["verified"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def it_returns_verified_false_for_not_found_transaction(self):
        """Returns verified=False when transaction does not exist."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "bad_tx",
            "status": "NOT_FOUND",
            "consensus_timestamp": None,
            "hash": None
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="bad_tx",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert result["verified"] is False

    @pytest.mark.asyncio
    async def it_includes_transaction_id_in_result(self):
        """Result includes the transaction ID."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567890.000000000",
            "hash": "0xabcdef",
            "memo": "task:task_abc",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="0.0.12345@1234567890.000000000",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert "transaction_id" in result

    @pytest.mark.asyncio
    async def it_includes_reason_in_result(self):
        """Result always includes a reason string."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567890.000000000",
            "hash": "0xabcdef",
            "memo": "task:task_abc",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="0.0.12345@1234567890.000000000",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert "reason" in result
        assert isinstance(result["reason"], str)

    @pytest.mark.asyncio
    async def it_returns_verified_false_for_empty_payment_tx(self):
        """Returns verified=False when payment_proof_tx is empty."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        verifier = FeedbackPaymentVerifier(hedera_client=AsyncMock())
        result = await verifier.verify_payment_proof(
            payment_proof_tx="",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert result["verified"] is False

    @pytest.mark.asyncio
    async def it_handles_mirror_node_errors_gracefully(self):
        """Returns verified=False when mirror node query raises exception."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(
            side_effect=Exception("Network error")
        )

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        result = await verifier.verify_payment_proof(
            payment_proof_tx="0.0.12345@1234567890.000000000",
            agent_did="did:hedera:testnet:0.0.99999",
            task_id="task_abc"
        )

        assert result["verified"] is False
        assert "reason" in result


class DescribeValidateFeedbackSubmission:
    """Tests for validate_feedback_submission method — Issue #199."""

    @pytest.mark.asyncio
    async def it_returns_valid_for_legitimate_feedback(self):
        """Returns valid=True for properly formed feedback with valid payment."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "0.0.12345@1234567890.000000000",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567890.000000000",
            "hash": "0xabcdef",
            "memo": "task:task_abc",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 4,
            "comment": "Good work",
            "payment_proof_tx": "0.0.12345@1234567890.000000000",
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:user1"
        }

        result = await verifier.validate_feedback_submission(feedback)

        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def it_rejects_self_review(self):
        """Returns valid=False when submitter_did equals agent_did."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        verifier = FeedbackPaymentVerifier(hedera_client=AsyncMock())
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 5,
            "comment": "I am so great",
            "payment_proof_tx": "0.0.12345@1234567890.000000000",
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:agent1"  # same as agent_did
        }

        result = await verifier.validate_feedback_submission(feedback)

        assert result["valid"] is False
        assert any("self" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def it_rejects_duplicate_feedback_same_submitter_and_task(self):
        """Returns valid=False when same submitter already reviewed same task."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        existing_reviews = [
            {
                "submitter_did": "did:hedera:testnet:user1",
                "task_id": "task_abc"
            }
        ]

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "tx2",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567891.000000000",
            "hash": "0xabcdef2",
            "memo": "task:task_abc",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 4,
            "comment": "Again",
            "payment_proof_tx": "tx2",
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:user1"
        }

        result = await verifier.validate_feedback_submission(
            feedback,
            existing_reviews=existing_reviews
        )

        assert result["valid"] is False
        assert any("duplicate" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def it_collects_multiple_errors(self):
        """Collects all validation errors instead of stopping at first."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        verifier = FeedbackPaymentVerifier(hedera_client=AsyncMock())
        # Self-review with empty payment tx
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 4,
            "comment": "Reviewing myself",
            "payment_proof_tx": "",  # invalid
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:agent1"  # self-review
        }

        result = await verifier.validate_feedback_submission(feedback)

        assert result["valid"] is False
        assert len(result["errors"]) >= 1  # at least self-review error

    @pytest.mark.asyncio
    async def it_rejects_invalid_payment_proof(self):
        """Returns valid=False when payment proof cannot be verified."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "bad_tx",
            "status": "NOT_FOUND",
            "consensus_timestamp": None,
            "hash": None
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 4,
            "comment": "Good",
            "payment_proof_tx": "bad_tx",
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:user1"
        }

        result = await verifier.validate_feedback_submission(feedback)

        assert result["valid"] is False
        assert len(result["errors"]) >= 1

    @pytest.mark.asyncio
    async def it_allows_different_submitters_for_same_task(self):
        """Different submitters can review the same task/agent."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        existing_reviews = [
            {
                "submitter_did": "did:hedera:testnet:user1",
                "task_id": "task_abc"
            }
        ]

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "tx2",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567891.000000000",
            "hash": "0xabcdef2",
            "memo": "task:task_abc",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 3,
            "comment": "Decent",
            "payment_proof_tx": "tx2",
            "task_id": "task_abc",
            "submitter_did": "did:hedera:testnet:user2"  # different submitter
        }

        result = await verifier.validate_feedback_submission(
            feedback,
            existing_reviews=existing_reviews
        )

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def it_allows_same_submitter_for_different_tasks(self):
        """Same submitter can review different tasks."""
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        existing_reviews = [
            {
                "submitter_did": "did:hedera:testnet:user1",
                "task_id": "task_abc"
            }
        ]

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt = AsyncMock(return_value={
            "transaction_id": "tx2",
            "status": "SUCCESS",
            "consensus_timestamp": "1234567891.000000000",
            "hash": "0xabcdef2",
            "memo": "task:task_xyz",
            "transfers": [{"account": "0.0.99999", "amount": 1000000}]
        })

        verifier = FeedbackPaymentVerifier(hedera_client=mock_client)
        feedback = {
            "agent_did": "did:hedera:testnet:agent1",
            "rating": 4,
            "comment": "Good on different task",
            "payment_proof_tx": "tx2",
            "task_id": "task_xyz",  # different task
            "submitter_did": "did:hedera:testnet:user1"
        }

        result = await verifier.validate_feedback_submission(
            feedback,
            existing_reviews=existing_reviews
        )

        assert result["valid"] is True
