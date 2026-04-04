"""
Core Tests for SpendTrackingService - Daily Spending Limits.
Issue #153: Implement per-agent daily spending limits.

Simplified test structure for pytest discovery.

Built by AINative Dev Team
All Data Services Built on ZeroDB
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from app.services.spend_tracking_service import SpendTrackingService


class TestGetDailySpend:
    """Test suite for get_daily_spend method."""

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_transactions(self):
        """Should return Decimal('0') when agent has no transactions today."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value={"rows": [], "total": 0})

        service = SpendTrackingService(client=mock_client)

        daily_spend = await service.get_daily_spend("agent_001", "project_001")

        assert daily_spend == Decimal("0")
        assert isinstance(daily_spend, Decimal)

    @pytest.mark.asyncio
    async def test_calculates_daily_spend_correctly(self):
        """Should sum all transactions for agent today."""
        now = datetime.now(timezone.utc)
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "10.50", "created_at": now.isoformat(), "status": "confirmed"}},
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "25.75", "created_at": now.isoformat(), "status": "confirmed"}},
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "5.00", "created_at": now.isoformat(), "status": "confirmed"}}
            ],
            "total": 3
        })

        service = SpendTrackingService(client=mock_client)

        daily_spend = await service.get_daily_spend("agent_001", "project_001")

        assert daily_spend == Decimal("41.25")

    @pytest.mark.asyncio
    async def test_handles_decimal_precision(self):
        """Should maintain decimal precision for USDC amounts."""
        now = datetime.now(timezone.utc)
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "10.123456", "created_at": now.isoformat(), "status": "confirmed"}},
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "5.654321", "created_at": now.isoformat(), "status": "confirmed"}}
            ],
            "total": 2
        })

        service = SpendTrackingService(client=mock_client)

        daily_spend = await service.get_daily_spend("agent_001", "project_001")

        expected = Decimal("10.123456") + Decimal("5.654321")
        assert daily_spend == expected


class TestCheckDailyBudget:
    """Test suite for check_daily_budget method."""

    @pytest.mark.asyncio
    async def test_allows_transaction_within_budget(self):
        """Should return allowed=True when under daily limit."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("50.00"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("30.00"), Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["current_spend"] == Decimal("50.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("50.00")
        assert result["proposed_total"] == Decimal("80.00")

    @pytest.mark.asyncio
    async def test_blocks_transaction_exceeding_budget(self):
        """Should return allowed=False when over daily limit."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("80.00"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("30.00"), Decimal("100.00")
        )

        assert result["allowed"] is False
        assert result["current_spend"] == Decimal("80.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("20.00")
        assert result["proposed_total"] == Decimal("110.00")
        assert result["exceeded_by"] == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_handles_exact_limit(self):
        """Should allow transaction that exactly hits limit."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("70.00"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("30.00"), Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["proposed_total"] == Decimal("100.00")
        assert result["remaining"] == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_allows_unlimited_when_no_limit_set(self):
        """Should always allow when daily_limit is None."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("1000.00"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("500.00"), None
        )

        assert result["allowed"] is True
        assert result["limit"] is None
        assert result["remaining"] is None
        assert "exceeded_by" not in result

    @pytest.mark.asyncio
    async def test_handles_first_transaction_of_day(self):
        """Should allow first transaction if under limit."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("0"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("50.00"), Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["current_spend"] == Decimal("0")
        assert result["remaining"] == Decimal("100.00")
        assert result["proposed_total"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_handles_zero_amount_transaction(self):
        """Should handle edge case of zero amount."""
        mock_client = AsyncMock()
        service = SpendTrackingService(client=mock_client)
        service.get_daily_spend = AsyncMock(return_value=Decimal("50.00"))

        result = await service.check_daily_budget(
            "agent_001", "project_001", Decimal("0"), Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["proposed_total"] == Decimal("50.00")


class TestGetDailySpendEdgeCases:
    """Additional edge case tests for get_daily_spend."""

    @pytest.mark.asyncio
    async def test_handles_invalid_amount_values(self):
        """Should skip invalid amount_usdc values and continue processing."""
        now = datetime.now(timezone.utc)
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "10.00", "created_at": now.isoformat(), "status": "confirmed"}},
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "invalid", "created_at": now.isoformat(), "status": "confirmed"}},
                {"row_data": {"from_agent_id": "agent_001", "amount_usdc": "5.00", "created_at": now.isoformat(), "status": "confirmed"}}
            ],
            "total": 3
        })

        service = SpendTrackingService(client=mock_client)

        daily_spend = await service.get_daily_spend("agent_001", "project_001")

        # Should skip invalid amount and sum only valid ones
        assert daily_spend == Decimal("15.00")

    @pytest.mark.asyncio
    async def test_client_property_lazy_initialization(self):
        """Should lazy-initialize ZeroDB client when accessed."""
        service = SpendTrackingService(client=None)

        # Client should be initialized on first access
        client = service.client

        assert client is not None

    @pytest.mark.asyncio
    async def test_get_current_date_key_format(self):
        """Should return date key in YYYY-MM-DD format."""
        service = SpendTrackingService()

        date_key = service._get_current_date_key()

        # Verify format (e.g., "2026-02-03")
        assert len(date_key) == 10
        assert date_key.count("-") == 2
        parts = date_key.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day
