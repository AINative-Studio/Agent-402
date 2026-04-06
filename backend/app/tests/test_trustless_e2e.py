"""
End-to-end user journey test for the Trustless V1 Runtime + Marketplace.

Issue #237: E2E User Journey Test.

Journey:
  1. Register agent DID identity
  2. Publish agent to marketplace
  3. Discover service via x402 registry
  4. Execute service call (x402 payment simulation)
  5. Verify receipt returned
  6. Check governance policy enforcement
  7. Confirm reputation anchoring data structure

Uses all services from Sprints 1-4 where available;
mocks external network calls.

TDD: BDD-style class DescribeE2E / def it_*
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class DescribeTrustlessE2EJourney:
    """
    Full trustless agent lifecycle: register → publish → discover
    → execute service → verify receipt → governance check.
    """

    @pytest.mark.asyncio
    async def it_completes_full_agent_publish_and_service_execution_journey(
        self, mock_zerodb_client
    ):
        """
        An agent can be published, discovered as a service, invoked via x402,
        and a receipt is produced — end-to-end.
        """
        from app.services.marketplace_service import MarketplaceService
        from app.services.trustless_runtime_service import TrustlessRuntimeService
        from app.services.governance_policy_service import GovernancePolicyService

        marketplace = MarketplaceService(client=mock_zerodb_client)
        runtime = TrustlessRuntimeService(client=mock_zerodb_client)
        governance = GovernancePolicyService(client=mock_zerodb_client)

        agent_did = "did:hedera:testnet:e2e_agent_001"
        caller_did = "did:hedera:testnet:e2e_caller_001"

        # Step 1: Publish agent to marketplace
        listing = await marketplace.publish_agent(
            agent_config={"name": "E2E Analytics Agent", "model": "gpt-4"},
            publisher_did=agent_did,
            pricing={"price_per_call": 0.01},
            category="analytics",
            description="End-to-end analytics service for testing",
        )
        assert listing["marketplace_id"].startswith("mkt_")
        assert listing["publisher_did"] == agent_did

        # Step 2: Register service for x402 discovery
        service = await runtime.register_service(
            agent_did=agent_did,
            service_description="E2E analytics",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://e2e-agent.example/x402",
            capabilities=["analytics", "finance"],
        )
        assert service["service_id"].startswith("svc_")

        # Step 3: Discover service by capability
        discovered = await runtime.discover_services(
            capability="analytics", max_price=1.0
        )
        assert len(discovered) >= 1
        assert any(s["agent_did"] == agent_did for s in discovered)

        # Step 4: Establish governance policy (spend limit)
        policy = await governance.create_policy(
            agent_did=caller_did,
            policy_type="spend_limit",
            rules={"daily_limit_usd": 100.0, "per_call_limit_usd": 5.0},
        )
        assert policy["policy_id"].startswith("pol_")

        # Step 5: Evaluate governance before executing
        gov_result = await governance.evaluate_policy(
            agent_did=caller_did,
            action="spend",
            context={"amount_usd": 0.01},
        )
        assert gov_result["allowed"] is True

        # Step 6: Execute service call (x402 payment simulation)
        service_id = service["service_id"]
        receipt = await runtime.execute_service_call(
            caller_did=caller_did,
            service_id=service_id,
            payload={"query": "revenue trend Q1 2026"},
        )

        # Step 7: Verify receipt
        assert "receipt_id" in receipt
        assert receipt["receipt_id"].startswith("rcpt_")
        assert "payment_tx" in receipt
        assert receipt["service_id"] == service_id
        assert receipt["caller_did"] == caller_did
        assert receipt["agent_did"] == agent_did
        assert "executed_at" in receipt

        # Verify receipt persisted
        receipts = mock_zerodb_client.get_table_data("service_receipts")
        assert len(receipts) == 1
        assert receipts[0]["receipt_id"] == receipt["receipt_id"]

    @pytest.mark.asyncio
    async def it_blocks_e2e_journey_when_governance_policy_violated(
        self, mock_zerodb_client
    ):
        """
        When an agent's spend_limit policy blocks a call, the governance
        check returns allowed=False before any service invocation.
        """
        from app.services.governance_policy_service import GovernancePolicyService

        governance = GovernancePolicyService(client=mock_zerodb_client)
        caller_did = "did:hedera:testnet:restricted_caller"

        await governance.create_policy(
            agent_did=caller_did,
            policy_type="spend_limit",
            rules={"daily_limit_usd": 10.0, "per_call_limit_usd": 0.005},
        )

        result = await governance.evaluate_policy(
            agent_did=caller_did,
            action="spend",
            context={"amount_usd": 1.0},  # exceeds per_call_limit
        )

        assert result["allowed"] is False
        assert len(result["violated_policies"]) > 0

    @pytest.mark.asyncio
    async def it_verifies_on_chain_identity_during_marketplace_publish(self):
        """
        When an agent publishes with a DID that encodes an NFT, the on-chain
        identity can be verified via MarketplaceHederaService.
        """
        from app.services.marketplace_hedera_service import MarketplaceHederaService
        from app.services.hedera_hts_nft_client import HederaHTSNFTClientError

        mock_nft = AsyncMock()
        mock_nft.get_nft_info = AsyncMock(
            return_value={
                "token_id": "0.0.888",
                "serial_number": 7,
                "metadata": "e30=",
                "account_id": "0.0.222",
            }
        )
        hedera_svc = MarketplaceHederaService(nft_client=mock_nft)

        # DID encodes token_id=0.0.888, serial=7
        result = await hedera_svc.verify_on_chain_identity(
            "did:hedera:testnet:e2eagent_0.0.888_7"
        )
        assert result["verified"] is True
        assert result["token_id"] == "0.0.888"
        assert result["serial"] == 7

    @pytest.mark.asyncio
    async def it_can_link_marketplace_listing_to_nft_after_publish(self):
        """
        After publishing, a listing can be cross-referenced with its NFT via
        link_marketplace_to_nft.
        """
        from app.services.marketplace_hedera_service import MarketplaceHederaService

        hedera_svc = MarketplaceHederaService(nft_client=AsyncMock())
        linkage = await hedera_svc.link_marketplace_to_nft(
            marketplace_id="mkt_e2e001",
            nft_token_id="0.0.777",
            serial=3,
        )
        assert linkage["marketplace_id"] == "mkt_e2e001"
        assert linkage["nft_token_id"] == "0.0.777"
        assert linkage["serial"] == 3

    @pytest.mark.asyncio
    async def it_supports_browse_then_install_workflow(self, mock_zerodb_client):
        """
        A user can browse the marketplace, find an agent, and install it
        into their project — the standard end-user onboarding flow.
        """
        from app.services.marketplace_service import MarketplaceService

        marketplace = MarketplaceService(client=mock_zerodb_client)

        # Publisher side: publish two agents
        for i in range(2):
            await marketplace.publish_agent(
                agent_config={"name": f"PublicAgent{i}"},
                publisher_did="did:hedera:testnet:publisher",
                pricing={"price_per_call": 0.01 * (i + 1)},
                category="analytics",
            )

        # Consumer side: browse then install
        browse_result = await marketplace.browse_agents(
            category="analytics", sort_by="newest", limit=10, offset=0
        )
        assert browse_result["total"] == 2

        first_agent = browse_result["items"][0]
        installation = await marketplace.install_agent(
            project_id="consumer_project_001",
            marketplace_agent_id=first_agent["marketplace_id"],
        )
        assert installation["project_id"] == "consumer_project_001"

        installed = await marketplace.list_installed("consumer_project_001")
        assert len(installed) == 1
