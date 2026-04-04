"""
Tests for Issue #190 — Discovery Endpoint Hedera Metadata.

Covers:
- x402_discovery() returns Hedera fields
- Backward compatibility: all original fields still present
- Hedera block has network, usdc_token_id, operator_account_id, mirror_node_url
- supported_dids now includes did:hedera
- signature_methods now includes Ed25519

TDD RED phase: all tests written before implementation.

Built by AINative Dev Team
Refs #190
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# ─── Discovery Endpoint Tests ──────────────────────────────────────────────────


class DescribeX402DiscoveryHederaFields:
    """The /.well-known/x402 endpoint returns Hedera metadata."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Import app inside each test to pick up patched env."""
        try:
            from app.main_simple import app
        except ImportError:
            from app.main import app
        self.client = TestClient(app)

    def it_returns_200_status(self):
        response = self.client.get("/.well-known/x402")
        assert response.status_code == 200

    def it_includes_hedera_block_in_response(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "hedera" in data

    def it_includes_hedera_network_field(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "network" in data["hedera"]

    def it_includes_usdc_token_id_in_hedera_block(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "usdc_token_id" in data["hedera"]

    def it_includes_operator_account_id_in_hedera_block(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "operator_account_id" in data["hedera"]

    def it_includes_mirror_node_url_in_hedera_block(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "mirror_node_url" in data["hedera"]

    def it_uses_correct_usdc_token_id(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert data["hedera"]["usdc_token_id"] == "0.0.456858"

    def it_uses_correct_mirror_node_base_url(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert data["hedera"]["mirror_node_url"] == "https://testnet.mirrornode.hedera.com/api/v1"

    def it_includes_did_hedera_in_supported_dids(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "did:hedera" in data["supported_dids"]

    def it_includes_ed25519_in_signature_methods(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "Ed25519" in data["signature_methods"]

    # ─── Backward Compatibility ───────────────────────────────────────────────

    def it_still_returns_version_field(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert data["version"] == "1.0"

    def it_still_returns_endpoint_field(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert data["endpoint"] == "/x402"

    def it_still_includes_did_ethr_in_supported_dids(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "did:ethr" in data["supported_dids"]

    def it_still_includes_ecdsa_in_signature_methods(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "ECDSA" in data["signature_methods"]

    def it_still_returns_server_info_block(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "server_info" in data

    def it_still_returns_server_name(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert data["server_info"]["name"] == "ZeroDB Agent Finance API"

    def it_still_returns_server_description(self):
        response = self.client.get("/.well-known/x402")
        data = response.json()
        assert "Autonomous Fintech Agent Crew" in data["server_info"]["description"]


class DescribeX402DiscoveryHederaNetworkFromEnv:
    """Hedera network is read from HEDERA_NETWORK environment variable."""

    def it_defaults_to_testnet_when_env_var_not_set(self):
        import os
        env_without_hedera = {k: v for k, v in os.environ.items() if k != "HEDERA_NETWORK"}
        with patch.dict(os.environ, env_without_hedera, clear=True):
            try:
                from app.main_simple import app
            except ImportError:
                from app.main import app
            client = TestClient(app)
            response = client.get("/.well-known/x402")
            data = response.json()
            assert data["hedera"]["network"] == "testnet"

    def it_uses_hedera_network_env_var_when_set(self):
        import os
        with patch.dict(os.environ, {"HEDERA_NETWORK": "mainnet"}):
            # Re-call the endpoint — env is read at request time via os.environ.get
            try:
                from app.main_simple import app
            except ImportError:
                from app.main import app
            client = TestClient(app)
            response = client.get("/.well-known/x402")
            data = response.json()
            assert data["hedera"]["network"] == "mainnet"

    def it_uses_hedera_operator_id_env_var_when_set(self):
        import os
        with patch.dict(os.environ, {"HEDERA_OPERATOR_ID": "0.0.99999"}):
            try:
                from app.main_simple import app
            except ImportError:
                from app.main import app
            client = TestClient(app)
            response = client.get("/.well-known/x402")
            data = response.json()
            assert data["hedera"]["operator_account_id"] == "0.0.99999"
