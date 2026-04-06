"""
Tests for TrustlessRuntimeService.
Issue #235: Agent Runtime with x402 Service Advertising.

TDD: RED phase — tests written before implementation.
BDD-style: class Describe* / def it_*
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest


class DescribeTrustlessRuntimeServiceInit:
    """TrustlessRuntimeService initializes correctly."""

    def it_initializes_with_lazy_zerodb_client(self):
        """Service starts with no client stored."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService()
        assert svc._client is None

    def it_accepts_injected_client(self):
        """Service accepts a pre-built client."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        mock = MagicMock()
        svc = TrustlessRuntimeService(client=mock)
        assert svc.client is mock


class DescribeRegisterService:
    """Tests for register_service — Issue #235."""

    @pytest.mark.asyncio
    async def it_registers_service_and_returns_entry(self, mock_zerodb_client):
        """register_service stores entry and returns service_id."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        result = await svc.register_service(
            agent_did="did:hedera:testnet:agent1",
            service_description="Pricing analytics service",
            pricing={"price_per_call": 0.02},
            x402_endpoint="https://agent1.example/x402",
        )

        assert "service_id" in result
        assert result["agent_did"] == "did:hedera:testnet:agent1"
        assert result["x402_endpoint"] == "https://agent1.example/x402"

    @pytest.mark.asyncio
    async def it_stores_service_in_service_registry_table(self, mock_zerodb_client):
        """register_service inserts exactly one row into service_registry."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        await svc.register_service(
            agent_did="did:hedera:testnet:agent2",
            service_description="Document summariser",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://agent2.example/x402",
        )

        rows = mock_zerodb_client.get_table_data("service_registry")
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def it_generates_unique_service_ids(self, mock_zerodb_client):
        """Two register_service calls produce different service_ids."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        r1 = await svc.register_service(
            agent_did="did:hedera:testnet:a1",
            service_description="Service A",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://a1.example/x402",
        )
        r2 = await svc.register_service(
            agent_did="did:hedera:testnet:a2",
            service_description="Service B",
            pricing={"price_per_call": 0.02},
            x402_endpoint="https://a2.example/x402",
        )

        assert r1["service_id"] != r2["service_id"]


class DescribeDiscoverServices:
    """Tests for discover_services — Issue #235."""

    @pytest.mark.asyncio
    async def it_returns_services_matching_capability(self, mock_zerodb_client):
        """discover_services returns entries that declare the requested capability."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        await svc.register_service(
            agent_did="did:hedera:testnet:a1",
            service_description="Finance analytics",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://a1.example/x402",
            capabilities=["analytics", "finance"],
        )
        await svc.register_service(
            agent_did="did:hedera:testnet:a2",
            service_description="Weather forecasting",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://a2.example/x402",
            capabilities=["weather"],
        )

        results = await svc.discover_services(capability="finance", max_price=None)

        assert len(results) == 1
        assert results[0]["agent_did"] == "did:hedera:testnet:a1"

    @pytest.mark.asyncio
    async def it_filters_by_max_price(self, mock_zerodb_client):
        """discover_services excludes services above max_price."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        await svc.register_service(
            agent_did="did:hedera:testnet:cheap",
            service_description="Cheap analytics",
            pricing={"price_per_call": 0.005},
            x402_endpoint="https://cheap.example/x402",
            capabilities=["analytics"],
        )
        await svc.register_service(
            agent_did="did:hedera:testnet:expensive",
            service_description="Expensive analytics",
            pricing={"price_per_call": 5.0},
            x402_endpoint="https://expensive.example/x402",
            capabilities=["analytics"],
        )

        results = await svc.discover_services(capability="analytics", max_price=0.1)

        dids = [r["agent_did"] for r in results]
        assert "did:hedera:testnet:cheap" in dids
        assert "did:hedera:testnet:expensive" not in dids

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_match(self, mock_zerodb_client):
        """discover_services returns [] when no services match."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        results = await svc.discover_services(capability="quantum_teleportation", max_price=None)

        assert results == []


class DescribeExecuteServiceCall:
    """Tests for execute_service_call — Issue #235."""

    @pytest.mark.asyncio
    async def it_returns_receipt_with_payment_tx(self, mock_zerodb_client):
        """execute_service_call returns a receipt containing payment_tx."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        reg = await svc.register_service(
            agent_did="did:hedera:testnet:provider",
            service_description="Data fetch",
            pricing={"price_per_call": 0.01},
            x402_endpoint="https://provider.example/x402",
        )

        receipt = await svc.execute_service_call(
            caller_did="did:hedera:testnet:caller",
            service_id=reg["service_id"],
            payload={"query": "AAPL price"},
        )

        assert "receipt_id" in receipt
        assert "payment_tx" in receipt
        assert receipt["service_id"] == reg["service_id"]
        assert receipt["caller_did"] == "did:hedera:testnet:caller"

    @pytest.mark.asyncio
    async def it_raises_for_unknown_service_id(self, mock_zerodb_client):
        """execute_service_call raises ServiceNotFoundError for unknown service_id."""
        from app.services.trustless_runtime_service import (
            TrustlessRuntimeService,
            ServiceNotFoundError,
        )

        svc = TrustlessRuntimeService(client=mock_zerodb_client)

        with pytest.raises(ServiceNotFoundError):
            await svc.execute_service_call(
                caller_did="did:hedera:testnet:caller",
                service_id="ghost_service",
                payload={},
            )

    @pytest.mark.asyncio
    async def it_stores_receipt_in_service_receipts_table(self, mock_zerodb_client):
        """execute_service_call persists a receipt row."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        reg = await svc.register_service(
            agent_did="did:hedera:testnet:prov2",
            service_description="Summarizer",
            pricing={"price_per_call": 0.02},
            x402_endpoint="https://prov2.example/x402",
        )

        await svc.execute_service_call(
            caller_did="did:hedera:testnet:caller2",
            service_id=reg["service_id"],
            payload={"text": "Hello world"},
        )

        rows = mock_zerodb_client.get_table_data("service_receipts")
        assert len(rows) == 1


class DescribeGetServiceRegistry:
    """Tests for get_service_registry — Issue #235."""

    @pytest.mark.asyncio
    async def it_returns_all_registered_services(self, mock_zerodb_client):
        """get_service_registry returns every registered service."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        for i in range(3):
            await svc.register_service(
                agent_did=f"did:hedera:testnet:a{i}",
                service_description=f"Service {i}",
                pricing={"price_per_call": 0.01},
                x402_endpoint=f"https://a{i}.example/x402",
            )

        registry = await svc.get_service_registry()

        assert len(registry) == 3

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_nothing_registered(self, mock_zerodb_client):
        """get_service_registry returns [] when no services exist."""
        from app.services.trustless_runtime_service import TrustlessRuntimeService

        svc = TrustlessRuntimeService(client=mock_zerodb_client)
        registry = await svc.get_service_registry()

        assert registry == []
