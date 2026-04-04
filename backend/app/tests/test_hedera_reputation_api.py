"""
Tests for Hedera Reputation API endpoints.
Issues #196-#199: HCS-Anchored Reputation System API.

TDD Approach: Tests written FIRST, then implementation.
BDD-style: class Describe* / def it_* naming.

Test Coverage:
- POST /api/v1/hedera/reputation/{agent_did}/feedback
- GET  /api/v1/hedera/reputation/{agent_did}
- GET  /api/v1/hedera/reputation/ranked
- GET  /api/v1/hedera/reputation/{agent_did}/feedback
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Optional, Dict, List, Any


def _build_app_with_overrides(reputation_svc=None, payment_verifier=None, agent_selector=None):
    """
    Build a FastAPI test app with dependency overrides injected.

    Uses FastAPI's dependency_overrides mechanism to inject mocks,
    which is the correct way to override Depends() in tests.
    """
    from app.api.hedera_reputation import router
    from app.services.hedera_reputation_service import get_reputation_service
    from app.services.feedback_payment_verifier import get_payment_verifier
    from app.services.reputation_agent_selector import get_agent_selector

    app = FastAPI()
    app.include_router(router)

    if reputation_svc is not None:
        app.dependency_overrides[get_reputation_service] = lambda: reputation_svc
    if payment_verifier is not None:
        app.dependency_overrides[get_payment_verifier] = lambda: payment_verifier
    if agent_selector is not None:
        app.dependency_overrides[get_agent_selector] = lambda: agent_selector

    return app


class DescribeSubmitFeedbackEndpoint:
    """Tests for POST /api/v1/hedera/reputation/{agent_did}/feedback."""

    def it_returns_201_for_valid_feedback(self):
        """Returns HTTP 201 when feedback is successfully submitted."""
        from app.services.hedera_reputation_service import HederaReputationService
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_reputation_svc = AsyncMock(spec=HederaReputationService)
        mock_reputation_svc.submit_feedback = AsyncMock(return_value={
            "sequence_number": 5,
            "consensus_timestamp": "1234567890.000000000",
            "topic_id": "0.0.88888"
        })

        mock_verifier = AsyncMock(spec=FeedbackPaymentVerifier)
        mock_verifier.validate_feedback_submission = AsyncMock(return_value={
            "valid": True,
            "errors": []
        })

        app = _build_app_with_overrides(
            reputation_svc=mock_reputation_svc,
            payment_verifier=mock_verifier
        )
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback",
            json={
                "rating": 4,
                "comment": "Great work",
                "payment_proof_tx": "0.0.12345@1234567890.000000000",
                "task_id": "task_abc",
                "submitter_did": "did:hedera:testnet:user1"
            }
        )

        assert response.status_code == 201

    def it_returns_422_for_invalid_rating(self):
        """Returns HTTP 422 when rating is out of range."""
        app = _build_app_with_overrides()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback",
            json={
                "rating": 10,  # invalid: > 5
                "comment": "Too high",
                "payment_proof_tx": "0.0.12345@1234567890.000000000",
                "task_id": "task_abc",
                "submitter_did": "did:hedera:testnet:user1"
            }
        )

        assert response.status_code == 422

    def it_returns_400_for_invalid_payment_proof(self):
        """Returns HTTP 400 when payment proof validation fails."""
        from app.services.hedera_reputation_service import HederaReputationService
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_reputation_svc = AsyncMock(spec=HederaReputationService)
        mock_verifier = AsyncMock(spec=FeedbackPaymentVerifier)
        mock_verifier.validate_feedback_submission = AsyncMock(return_value={
            "valid": False,
            "errors": ["Payment proof not found"]
        })

        app = _build_app_with_overrides(
            reputation_svc=mock_reputation_svc,
            payment_verifier=mock_verifier
        )
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback",
            json={
                "rating": 4,
                "comment": "Good",
                "payment_proof_tx": "bad_tx",
                "task_id": "task_abc",
                "submitter_did": "did:hedera:testnet:user1"
            }
        )

        assert response.status_code == 400

    def it_returns_sequence_number_in_response(self):
        """Response includes HCS sequence number."""
        from app.services.hedera_reputation_service import HederaReputationService
        from app.services.feedback_payment_verifier import FeedbackPaymentVerifier

        mock_reputation_svc = AsyncMock(spec=HederaReputationService)
        mock_reputation_svc.submit_feedback = AsyncMock(return_value={
            "sequence_number": 42,
            "consensus_timestamp": "1234567890.000000000",
            "topic_id": "0.0.88888"
        })

        mock_verifier = AsyncMock(spec=FeedbackPaymentVerifier)
        mock_verifier.validate_feedback_submission = AsyncMock(return_value={
            "valid": True,
            "errors": []
        })

        app = _build_app_with_overrides(
            reputation_svc=mock_reputation_svc,
            payment_verifier=mock_verifier
        )
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback",
            json={
                "rating": 5,
                "comment": "Excellent",
                "payment_proof_tx": "0.0.12345@1234567890.000000000",
                "task_id": "task_abc",
                "submitter_did": "did:hedera:testnet:user1"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sequence_number"] == 42


class DescribeGetReputationScoreEndpoint:
    """Tests for GET /api/v1/hedera/reputation/{agent_did}."""

    def it_returns_200_with_reputation_score(self):
        """Returns HTTP 200 with reputation data for the agent."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = AsyncMock(spec=HederaReputationService)
        mock_service.calculate_reputation_score = AsyncMock(return_value={
            "score": 4.2,
            "total_reviews": 15,
            "trust_tier": 2
        })

        app = _build_app_with_overrides(reputation_svc=mock_service)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1"
        )

        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "trust_tier" in data

    def it_returns_score_and_tier_in_response(self):
        """Response body contains score and trust_tier fields."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = AsyncMock(spec=HederaReputationService)
        mock_service.calculate_reputation_score = AsyncMock(return_value={
            "score": 3.7,
            "total_reviews": 20,
            "trust_tier": 2
        })

        app = _build_app_with_overrides(reputation_svc=mock_service)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1"
        )

        data = response.json()
        assert data["score"] == 3.7
        assert data["trust_tier"] == 2
        assert data["total_reviews"] == 20


class DescribeGetRankedAgentsEndpoint:
    """Tests for GET /api/v1/hedera/reputation/ranked."""

    def it_returns_200_with_ranked_agents(self):
        """Returns HTTP 200 with a list of ranked agents."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        mock_selector = AsyncMock(spec=ReputationAgentSelector)
        mock_selector.select_agents_by_reputation = AsyncMock(return_value=[
            {"agent_did": "did:hedera:testnet:agent1", "score": 4.5, "trust_tier": 3, "capabilities": []},
            {"agent_did": "did:hedera:testnet:agent2", "score": 3.0, "trust_tier": 2, "capabilities": []}
        ])

        app = _build_app_with_overrides(agent_selector=mock_selector)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/hedera/reputation/ranked")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

    def it_accepts_min_trust_tier_query_param(self):
        """Accepts min_trust_tier as query parameter."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        mock_selector = AsyncMock(spec=ReputationAgentSelector)
        mock_selector.select_agents_by_reputation = AsyncMock(return_value=[])

        app = _build_app_with_overrides(agent_selector=mock_selector)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/hedera/reputation/ranked?min_trust_tier=2")

        assert response.status_code == 200

    def it_accepts_min_score_query_param(self):
        """Accepts min_score as query parameter."""
        from app.services.reputation_agent_selector import ReputationAgentSelector

        mock_selector = AsyncMock(spec=ReputationAgentSelector)
        mock_selector.select_agents_by_reputation = AsyncMock(return_value=[])

        app = _build_app_with_overrides(agent_selector=mock_selector)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/hedera/reputation/ranked?min_score=3.5")

        assert response.status_code == 200


class DescribeListFeedbackEndpoint:
    """Tests for GET /api/v1/hedera/reputation/{agent_did}/feedback."""

    def it_returns_200_with_feedback_entries(self):
        """Returns HTTP 200 with list of feedback entries."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = AsyncMock(spec=HederaReputationService)
        mock_service.get_feedback = AsyncMock(return_value=[
            {
                "agent_did": "did:hedera:testnet:agent1",
                "rating": 5,
                "comment": "Excellent",
                "payment_proof_tx": "tx1",
                "task_id": "task_1",
                "submitter_did": "did:hedera:testnet:sub1",
                "consensus_timestamp": "1234567890.000000000",
                "sequence_number": 1
            }
        ])

        app = _build_app_with_overrides(reputation_svc=mock_service)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def it_accepts_limit_query_param(self):
        """Accepts limit as query parameter."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = AsyncMock(spec=HederaReputationService)
        mock_service.get_feedback = AsyncMock(return_value=[])

        app = _build_app_with_overrides(reputation_svc=mock_service)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Aagent1/feedback?limit=10"
        )

        assert response.status_code == 200

    def it_returns_empty_list_when_no_feedback(self):
        """Returns empty list when no feedback exists for agent."""
        from app.services.hedera_reputation_service import HederaReputationService

        mock_service = AsyncMock(spec=HederaReputationService)
        mock_service.get_feedback = AsyncMock(return_value=[])

        app = _build_app_with_overrides(reputation_svc=mock_service)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/v1/hedera/reputation/did%3Ahedera%3Atestnet%3Anew_agent/feedback"
        )

        assert response.status_code == 200
        assert response.json() == []
