"""
Tests for Hedera Identity API endpoints.
Issues #191, #192, #193, #194.

TDD: Tests were written FIRST (RED phase), then production code (GREEN).

Uses FastAPI dependency_overrides for clean service isolation.

Refs #191, #192, #193, #194
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone
from typing import Any, Dict


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with the hedera_identity router for testing."""
    from app.api.hedera_identity import router

    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# POST /api/v1/hedera/identity/register
# ---------------------------------------------------------------------------


class DescribeRegisterAgentEndpoint:
    """POST /api/v1/hedera/identity/register registers an agent as HTS NFT."""

    def it_returns_201_on_successful_registration(self):
        """Registration endpoint returns 201 when agent is successfully registered."""
        from app.api.hedera_identity import get_hedera_identity_service

        mock_service = AsyncMock()
        mock_service.mint_agent_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "tx_mint",
            "status": "SUCCESS",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/register",
            json={
                "name": "Agent Alpha",
                "role": "analyst",
                "capabilities": ["chat", "memory"],
                "token_id": "0.0.9999",
                "admin_key": "ed25519_key_hex",
            },
        )

        assert response.status_code == 201

    def it_returns_agent_nft_metadata_in_response(self):
        """Registration endpoint returns token_id and serial_number in response."""
        from app.api.hedera_identity import get_hedera_identity_service

        mock_service = AsyncMock()
        mock_service.mint_agent_nft.return_value = {
            "serial_number": 1,
            "token_id": "0.0.9999",
            "transaction_id": "tx_mint",
            "status": "SUCCESS",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/register",
            json={
                "name": "Agent Beta",
                "role": "compliance",
                "capabilities": ["compliance"],
                "token_id": "0.0.9999",
                "admin_key": "key_hex",
            },
        )

        data = response.json()
        assert "token_id" in data or "agent_id" in data or "serial_number" in data

    def it_returns_422_when_name_is_missing(self):
        """Registration endpoint returns 422 when required name field is missing."""
        from app.api.hedera_identity import get_hedera_identity_service

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: AsyncMock()

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/register",
            json={
                "role": "analyst",
                "capabilities": ["chat"],
                "token_id": "0.0.9999",
            },
        )

        assert response.status_code == 422

    def it_returns_422_when_role_is_missing(self):
        """Registration endpoint returns 422 when required role field is missing."""
        from app.api.hedera_identity import get_hedera_identity_service

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: AsyncMock()

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/register",
            json={
                "name": "Agent Gamma",
                "capabilities": ["chat"],
                "token_id": "0.0.9999",
            },
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/hedera/identity/{agent_id}/did
# ---------------------------------------------------------------------------


class DescribeGetAgentDIDEndpoint:
    """GET /api/v1/hedera/identity/{agent_id}/did resolves agent DID."""

    def it_returns_200_with_did_document(self):
        """DID resolution endpoint returns 200 with a W3C DID Document."""
        from app.api.hedera_identity import get_hedera_did_service

        mock_did_service = AsyncMock()
        mock_did_service.resolve_did.return_value = {
            "did_document": {
                "id": "did:hedera:testnet:0.0.111_0.0.222",
                "controller": "did:hedera:testnet:0.0.111_0.0.222",
                "verificationMethod": [],
                "authentication": [],
                "service": [],
            },
            "metadata": {"created": "2026-04-03T00:00:00+00:00"},
        }

        app = _make_test_app()
        app.dependency_overrides[get_hedera_did_service] = lambda: mock_did_service

        client = TestClient(app)
        response = client.get(
            "/api/v1/hedera/identity/agent_test_001/did",
            params={"did": "did:hedera:testnet:0.0.111_0.0.222"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "did_document" in data

    def it_returns_404_when_agent_did_not_found(self):
        """DID resolution endpoint returns 404 when agent has no registered DID."""
        from app.api.hedera_identity import get_hedera_did_service
        from app.services.hedera_did_service import HederaDIDNotFoundError

        mock_did_service = AsyncMock()
        mock_did_service.resolve_did.side_effect = HederaDIDNotFoundError(
            "did:hedera:testnet:0.0.999_0.0.888"
        )

        app = _make_test_app()
        app.dependency_overrides[get_hedera_did_service] = lambda: mock_did_service

        client = TestClient(app)
        response = client.get(
            "/api/v1/hedera/identity/nonexistent_agent/did",
            params={"did": "did:hedera:testnet:0.0.999_0.0.888"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/hedera/identity/directory/search
# ---------------------------------------------------------------------------


class DescribeDirectorySearchEndpoint:
    """POST /api/v1/hedera/identity/directory/search queries HCS-14 directory."""

    def it_returns_200_with_list_of_agents(self):
        """Directory search endpoint returns 200 with agents list."""
        from app.api.hedera_identity import get_hcs14_directory_service

        mock_dir_service = AsyncMock()
        mock_dir_service.query_directory.return_value = {
            "agents": [
                {
                    "did": "did:hedera:testnet:0.0.111_0.0.222",
                    "role": "analyst",
                    "capabilities": ["chat", "memory"],
                    "reputation": 100,
                }
            ]
        }

        app = _make_test_app()
        app.dependency_overrides[get_hcs14_directory_service] = lambda: mock_dir_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/directory/search",
            json={"capability": "chat"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

    def it_returns_empty_list_when_no_agents_match(self):
        """Directory search endpoint returns empty agents list when none match."""
        from app.api.hedera_identity import get_hcs14_directory_service

        mock_dir_service = AsyncMock()
        mock_dir_service.query_directory.return_value = {"agents": []}

        app = _make_test_app()
        app.dependency_overrides[get_hcs14_directory_service] = lambda: mock_dir_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/hedera/identity/directory/search",
            json={"role": "nonexistent_role"},
        )

        assert response.status_code == 200
        assert response.json()["agents"] == []

    def it_passes_capability_filter_to_service(self):
        """Directory search endpoint forwards capability filter to directory service."""
        from app.api.hedera_identity import get_hcs14_directory_service

        mock_dir_service = AsyncMock()
        mock_dir_service.query_directory.return_value = {"agents": []}

        app = _make_test_app()
        app.dependency_overrides[get_hcs14_directory_service] = lambda: mock_dir_service

        client = TestClient(app)
        client.post(
            "/api/v1/hedera/identity/directory/search",
            json={"capability": "payment"},
        )

        mock_dir_service.query_directory.assert_called_once()
        kwargs = mock_dir_service.query_directory.call_args[1]
        assert kwargs.get("capability") == "payment"


# ---------------------------------------------------------------------------
# GET /api/v1/hedera/identity/{agent_id}/capabilities
# ---------------------------------------------------------------------------


class DescribeGetCapabilitiesEndpoint:
    """GET /api/v1/hedera/identity/{agent_id}/capabilities returns AAP capabilities."""

    def it_returns_200_with_capabilities_list(self):
        """Capabilities GET endpoint returns 200 with a list of capability strings."""
        from app.api.hedera_identity import get_hedera_identity_service

        mock_service = AsyncMock()
        mock_service.get_agent_capabilities.return_value = ["chat", "memory", "analytics"]

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get(
            "/api/v1/hedera/identity/agent_test_001/capabilities",
            params={"token_id": "0.0.9999", "serial_number": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)

    def it_returns_404_when_agent_token_not_found(self):
        """Capabilities endpoint returns 404 when the agent NFT does not exist."""
        from app.api.hedera_identity import get_hedera_identity_service
        from app.services.hedera_identity_service import HederaIdentityError

        mock_service = AsyncMock()
        mock_service.get_agent_capabilities.side_effect = HederaIdentityError(
            "NFT not found", status_code=404
        )

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.get(
            "/api/v1/hedera/identity/nonexistent/capabilities",
            params={"token_id": "0.0.9999", "serial_number": 999},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/hedera/identity/{agent_id}/capabilities
# ---------------------------------------------------------------------------


class DescribeUpdateCapabilitiesEndpoint:
    """PUT /api/v1/hedera/identity/{agent_id}/capabilities updates AAP capabilities."""

    def it_returns_200_on_successful_update(self):
        """Capabilities PUT endpoint returns 200 after updating capabilities."""
        from app.api.hedera_identity import get_hedera_identity_service

        mock_service = AsyncMock()
        mock_service.map_aap_capabilities.return_value = {
            "status": "SUCCESS",
            "token_id": "0.0.9999",
            "serial_number": 1,
            "capabilities": ["chat", "payment"],
            "transaction_id": "tx_cap",
        }

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.put(
            "/api/v1/hedera/identity/agent_test_001/capabilities",
            json={
                "token_id": "0.0.9999",
                "serial_number": 1,
                "capabilities": ["chat", "payment"],
            },
        )

        assert response.status_code == 200

    def it_returns_422_when_capabilities_list_is_missing(self):
        """Capabilities PUT endpoint returns 422 when capabilities field is absent."""
        from app.api.hedera_identity import get_hedera_identity_service

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: AsyncMock()

        client = TestClient(app)
        response = client.put(
            "/api/v1/hedera/identity/agent_test_001/capabilities",
            json={
                "token_id": "0.0.9999",
                "serial_number": 1,
                # missing capabilities
            },
        )

        assert response.status_code == 422

    def it_returns_400_for_invalid_capability_name(self):
        """Capabilities PUT endpoint returns 400 for unknown capability name."""
        from app.api.hedera_identity import get_hedera_identity_service
        from app.services.hedera_identity_service import HederaIdentityError

        mock_service = AsyncMock()
        mock_service.map_aap_capabilities.side_effect = HederaIdentityError(
            "Invalid capability: fly_to_moon", status_code=400
        )

        app = _make_test_app()
        app.dependency_overrides[get_hedera_identity_service] = lambda: mock_service

        client = TestClient(app)
        response = client.put(
            "/api/v1/hedera/identity/agent_test_001/capabilities",
            json={
                "token_id": "0.0.9999",
                "serial_number": 1,
                "capabilities": ["fly_to_moon"],
            },
        )

        assert response.status_code == 400
