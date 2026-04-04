"""
Tests for OpenConvAI HCS-10 API Router.

Issues #204–#207: OpenConvAI REST API layer.

TDD Red phase: tests define the API contract before the router is written.

Built by AINative Dev Team
Refs #204, #205, #206, #207
"""
from __future__ import annotations

import json
import pytest
from typing import Optional, Dict, List, Any
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App fixture — mounts only the openconvai router
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_messaging_service():
    svc = AsyncMock()
    svc.send_message = AsyncMock(return_value={
        "transaction_id": "0.0.12345@9999.000",
        "status": "SUCCESS",
        "conversation_id": "conv-api-001",
    })
    svc.receive_messages = AsyncMock(return_value=[
        {
            "protocol": "hcs-10",
            "version": "1.0",
            "sender_did": "did:hedera:testnet:z6MkSender",
            "recipient_did": "did:hedera:testnet:z6MkAgent",
            "message_type": "text",
            "payload": {"text": "hello"},
            "conversation_id": "conv-api-001",
            "timestamp": "2026-04-03T12:00:00Z",
        }
    ])
    return svc


@pytest.fixture
def mock_coordination_service():
    svc = AsyncMock()
    svc.coordinate_workflow = AsyncMock(return_value={
        "workflow_id": "wf-api-001",
        "status": "initiated",
        "stages": {
            "analyst_review": {"status": "pending"},
            "compliance_check": {"status": "pending"},
            "transaction_execute": {"status": "pending"},
        },
    })
    return svc


@pytest.fixture
def mock_audit_service():
    svc = AsyncMock()
    svc.get_audit_trail = AsyncMock(return_value=[
        {
            "audit_id": "aud-001",
            "conversation_id": "conv-api-001",
            "sender_did": "did:hedera:testnet:z6MkSender",
            "message_type": "text",
            "consensus_timestamp": "2026-04-03T12:00:00Z",
            "sequence_number": 1,
        }
    ])
    return svc


@pytest.fixture
def mock_discovery_service():
    svc = AsyncMock()
    svc.discover_agents = AsyncMock(return_value=[
        {
            "agent_did": "did:hedera:testnet:z6MkAgent",
            "capabilities": ["text_analysis"],
            "service_endpoint": "https://agent.example.com/hcs10",
        }
    ])
    return svc


@pytest.fixture
def api_client(
    mock_messaging_service,
    mock_coordination_service,
    mock_audit_service,
    mock_discovery_service,
):
    """TestClient with the openconvai router and mocked services."""
    from app.api.openconvai import router, get_messaging_service, get_coordination_service, get_audit_service, get_discovery_service

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_messaging_service] = lambda: mock_messaging_service
    app.dependency_overrides[get_coordination_service] = lambda: mock_coordination_service
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
    app.dependency_overrides[get_discovery_service] = lambda: mock_discovery_service

    return TestClient(app)


# ---------------------------------------------------------------------------
# DescribeSendEndpoint
# ---------------------------------------------------------------------------

class DescribeSendEndpoint:
    """Tests for POST /hcs10/send."""

    def it_returns_200_with_transaction_id_for_valid_payload(
        self, api_client
    ):
        """POST /hcs10/send returns 200 and transaction_id."""
        payload = {
            "sender_did": "did:hedera:testnet:z6MkSender",
            "recipient_did": "did:hedera:testnet:z6MkRecipient",
            "message_type": "text",
            "payload": {"text": "hello"},
            "conversation_id": "conv-001",
        }
        response = api_client.post("/hcs10/send", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data

    def it_returns_422_when_sender_did_is_missing(
        self, api_client
    ):
        """POST /hcs10/send returns 422 for missing sender_did."""
        payload = {
            "recipient_did": "did:hedera:testnet:z6MkRecipient",
            "message_type": "text",
            "payload": {},
        }
        response = api_client.post("/hcs10/send", json=payload)
        assert response.status_code == 422

    def it_returns_422_when_message_type_is_missing(
        self, api_client
    ):
        """POST /hcs10/send returns 422 for missing message_type."""
        payload = {
            "sender_did": "did:hedera:testnet:z6MkSender",
            "recipient_did": "did:hedera:testnet:z6MkRecipient",
            "payload": {},
        }
        response = api_client.post("/hcs10/send", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DescribeReceiveMessagesEndpoint
# ---------------------------------------------------------------------------

class DescribeReceiveMessagesEndpoint:
    """Tests for GET /hcs10/messages/{agent_did}."""

    def it_returns_200_with_a_list_of_messages(
        self, api_client
    ):
        """GET /hcs10/messages/{agent_did} returns 200 and a list."""
        agent_did = "did:hedera:testnet:z6MkAgent"
        response = api_client.get(f"/hcs10/messages/{agent_did}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def it_accepts_since_sequence_query_param(
        self, api_client
    ):
        """GET /hcs10/messages/{agent_did}?since_sequence=5 returns 200."""
        agent_did = "did:hedera:testnet:z6MkAgent"
        response = api_client.get(
            f"/hcs10/messages/{agent_did}?since_sequence=5"
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DescribeWorkflowEndpoint
# ---------------------------------------------------------------------------

class DescribeWorkflowEndpoint:
    """Tests for POST /hcs10/workflow."""

    def it_returns_200_with_workflow_id(
        self, api_client
    ):
        """POST /hcs10/workflow returns 200 and workflow_id."""
        payload = {
            "workflow_id": "wf-api-001",
            "stages": [
                {
                    "name": "analyst_review",
                    "agent_did": "did:hedera:testnet:z6MkAnalyst",
                    "inputs": {},
                },
                {
                    "name": "compliance_check",
                    "agent_did": "did:hedera:testnet:z6MkCompliance",
                    "inputs": {},
                },
                {
                    "name": "transaction_execute",
                    "agent_did": "did:hedera:testnet:z6MkTransaction",
                    "inputs": {},
                },
            ],
        }
        response = api_client.post("/hcs10/workflow", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data

    def it_returns_422_when_workflow_id_is_missing(
        self, api_client
    ):
        """POST /hcs10/workflow returns 422 for missing workflow_id."""
        payload = {"stages": []}
        response = api_client.post("/hcs10/workflow", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DescribeAuditEndpoint
# ---------------------------------------------------------------------------

class DescribeAuditEndpoint:
    """Tests for GET /hcs10/audit/{conversation_id}."""

    def it_returns_200_with_list_of_audit_entries(
        self, api_client
    ):
        """GET /hcs10/audit/{conversation_id} returns 200 and a list."""
        response = api_client.get("/hcs10/audit/conv-api-001")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def it_accepts_limit_query_param(
        self, api_client
    ):
        """GET /hcs10/audit/{conversation_id}?limit=10 returns 200."""
        response = api_client.get("/hcs10/audit/conv-api-001?limit=10")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DescribeDiscoverEndpoint
# ---------------------------------------------------------------------------

class DescribeDiscoverEndpoint:
    """Tests for POST /hcs10/discover."""

    def it_returns_200_with_list_of_agents(
        self, api_client
    ):
        """POST /hcs10/discover returns 200 and a list of agents."""
        response = api_client.post("/hcs10/discover", json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def it_accepts_capability_filter(
        self, api_client
    ):
        """POST /hcs10/discover with capability filter returns 200."""
        response = api_client.post(
            "/hcs10/discover",
            json={"capability": "text_analysis"},
        )
        assert response.status_code == 200
