"""
Tests for per-transaction spend limit enforcement.
Issues #239: Agent Spend Limits Enforcement — per-transaction check.

TDD: RED phase — tests written before implementation.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, Any


class DescribeCheckPerTransactionLimit:
    """Describe SpendTrackingService.check_per_transaction_limit behavior."""

    def _make_service(self):
        """Helper: return service with a mocked ZeroDB client."""
        from app.services.spend_tracking_service import SpendTrackingService
        mock_client = MagicMock()
        return SpendTrackingService(client=mock_client)

    @pytest.mark.asyncio
    async def it_returns_true_when_amount_is_below_limit(self):
        """Amount strictly less than max_per_tx should return True."""
        svc = self._make_service()
        result = await svc.check_per_transaction_limit(
            agent_id="did:hedera:testnet:agent-1",
            amount=Decimal("5.00"),
            max_per_tx=Decimal("10.00"),
        )
        assert result is True

    @pytest.mark.asyncio
    async def it_returns_true_when_amount_equals_limit(self):
        """Amount exactly equal to max_per_tx should return True (boundary)."""
        svc = self._make_service()
        result = await svc.check_per_transaction_limit(
            agent_id="did:hedera:testnet:agent-1",
            amount=Decimal("10.00"),
            max_per_tx=Decimal("10.00"),
        )
        assert result is True

    @pytest.mark.asyncio
    async def it_raises_when_amount_exceeds_limit(self):
        """Amount exceeding max_per_tx must raise PerTransactionLimitExceededError."""
        from app.core.errors import APIError
        svc = self._make_service()
        with pytest.raises(APIError) as exc_info:
            await svc.check_per_transaction_limit(
                agent_id="did:hedera:testnet:agent-1",
                amount=Decimal("15.00"),
                max_per_tx=Decimal("10.00"),
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.error_code == "PER_TX_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def it_raises_with_agent_id_in_detail(self):
        """Error detail must include the agent_id for traceability."""
        from app.core.errors import APIError
        svc = self._make_service()
        agent_id = "did:hedera:testnet:agent-trace"
        with pytest.raises(APIError) as exc_info:
            await svc.check_per_transaction_limit(
                agent_id=agent_id,
                amount=Decimal("99.99"),
                max_per_tx=Decimal("50.00"),
            )
        assert agent_id in exc_info.value.detail

    @pytest.mark.asyncio
    async def it_raises_with_exceeded_amount_in_detail(self):
        """Error detail must state how much the transaction exceeds the limit."""
        from app.core.errors import APIError
        svc = self._make_service()
        with pytest.raises(APIError) as exc_info:
            await svc.check_per_transaction_limit(
                agent_id="did:hedera:testnet:agent-1",
                amount=Decimal("20.00"),
                max_per_tx=Decimal("10.00"),
            )
        # Detail should mention the overage (10.00) or at least the amounts
        assert "10.00" in exc_info.value.detail or "20.00" in exc_info.value.detail

    @pytest.mark.asyncio
    async def it_returns_true_when_no_limit_configured(self):
        """None max_per_tx means unlimited — must return True for any amount."""
        svc = self._make_service()
        result = await svc.check_per_transaction_limit(
            agent_id="did:hedera:testnet:agent-1",
            amount=Decimal("999999.00"),
            max_per_tx=None,
        )
        assert result is True

    @pytest.mark.asyncio
    async def it_raises_for_zero_amount_below_positive_limit(self):
        """Zero amount is always within any positive limit."""
        svc = self._make_service()
        result = await svc.check_per_transaction_limit(
            agent_id="did:hedera:testnet:agent-1",
            amount=Decimal("0.00"),
            max_per_tx=Decimal("10.00"),
        )
        assert result is True


class DescribeCombinedDailyAndPerTxLimits:
    """
    Describe check_combined_budget with both daily and per-tx limits applied.
    Issue #239: daily + per-tx combination enforcement.
    """

    def _make_service_with_daily_spend(self, daily_spend: Decimal):
        """Helper: service whose get_daily_spend returns a fixed value."""
        from app.services.spend_tracking_service import SpendTrackingService
        mock_client = MagicMock()
        svc = SpendTrackingService(client=mock_client)
        svc.get_daily_spend = AsyncMock(return_value=daily_spend)
        return svc

    @pytest.mark.asyncio
    async def it_allows_when_both_limits_pass(self):
        """Transaction within both daily and per-tx limits must be allowed."""
        svc = self._make_service_with_daily_spend(Decimal("30.00"))
        result = await svc.check_combined_budget(
            agent_id="did:hedera:testnet:agent-1",
            project_id="proj-1",
            amount=Decimal("5.00"),
            daily_limit=Decimal("100.00"),
            monthly_limit=None,
            max_per_tx=Decimal("20.00"),
        )
        assert result["allowed"] is True
        assert result["violations"] == []

    @pytest.mark.asyncio
    async def it_blocks_when_per_tx_limit_exceeded_even_if_daily_ok(self):
        """Per-tx violation must block even when daily budget has room."""
        svc = self._make_service_with_daily_spend(Decimal("10.00"))
        result = await svc.check_combined_budget(
            agent_id="did:hedera:testnet:agent-1",
            project_id="proj-1",
            amount=Decimal("50.00"),
            daily_limit=Decimal("100.00"),
            monthly_limit=None,
            max_per_tx=Decimal("20.00"),
        )
        assert result["allowed"] is False
        violation_types = [v["type"] for v in result["violations"]]
        assert "per_tx_limit_exceeded" in violation_types

    @pytest.mark.asyncio
    async def it_blocks_when_daily_limit_exceeded_even_if_per_tx_ok(self):
        """Daily limit violation must block even when per-tx is within limit."""
        svc = self._make_service_with_daily_spend(Decimal("95.00"))
        result = await svc.check_combined_budget(
            agent_id="did:hedera:testnet:agent-1",
            project_id="proj-1",
            amount=Decimal("10.00"),
            daily_limit=Decimal("100.00"),
            monthly_limit=None,
            max_per_tx=Decimal("20.00"),
        )
        assert result["allowed"] is False
        violation_types = [v["type"] for v in result["violations"]]
        assert "daily_limit_exceeded" in violation_types

    @pytest.mark.asyncio
    async def it_reports_both_violations_when_both_limits_exceeded(self):
        """Both per-tx and daily violations must both appear in result."""
        svc = self._make_service_with_daily_spend(Decimal("95.00"))
        result = await svc.check_combined_budget(
            agent_id="did:hedera:testnet:agent-1",
            project_id="proj-1",
            amount=Decimal("50.00"),
            daily_limit=Decimal("100.00"),
            monthly_limit=None,
            max_per_tx=Decimal("20.00"),
        )
        assert result["allowed"] is False
        violation_types = [v["type"] for v in result["violations"]]
        assert "per_tx_limit_exceeded" in violation_types
        assert "daily_limit_exceeded" in violation_types

    @pytest.mark.asyncio
    async def it_ignores_per_tx_limit_when_none(self):
        """When max_per_tx is None, no per-tx violation should be reported."""
        svc = self._make_service_with_daily_spend(Decimal("10.00"))
        result = await svc.check_combined_budget(
            agent_id="did:hedera:testnet:agent-1",
            project_id="proj-1",
            amount=Decimal("500.00"),
            daily_limit=Decimal("1000.00"),
            monthly_limit=None,
            max_per_tx=None,
        )
        assert result["allowed"] is True
        violation_types = [v["type"] for v in result["violations"]]
        assert "per_tx_limit_exceeded" not in violation_types
