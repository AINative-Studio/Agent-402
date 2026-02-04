"""
BDD tests for monthly spending limits.

Tests monthly spending limit tracking and enforcement for Agent402.
Verifies correct calculation, month boundary handling, and combined limit enforcement.

Built by AINative Dev Team
All Data Services Built on ZeroDB
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from app.services.spend_tracking_service import SpendTrackingService


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client for testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def spend_service(mock_zerodb_client):
    """Create SpendTrackingService instance with mocked client."""
    service = SpendTrackingService(client=mock_zerodb_client)
    return service


class TestGetMonthlySpend:
    """Tests for get_monthly_spend method."""

    @pytest.mark.asyncio
    async def test_calculates_monthly_spend_correctly(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should sum all transactions for agent this month."""
        # Given: Multiple transactions this month
        mock_zerodb_client.query_rows.return_value = {
            "rows": [
                {"row_data": {"amount_usdc": "10.50"}},
                {"row_data": {"amount_usdc": "25.00"}},
                {"row_data": {"amount_usdc": "5.75"}}
            ]
        }

        # When: Getting monthly spend
        result = await spend_service.get_monthly_spend(
            agent_id="agent_123",
            project_id="project_456"
        )

        # Then: Should sum all amounts
        assert result == Decimal("41.25")

        # And: Should query with correct filter
        call_args = mock_zerodb_client.query_rows.call_args
        assert call_args[0][0] == "payment_receipts"
        filter_arg = call_args[1]["filter"]
        assert filter_arg["from_agent_id"] == "agent_123"
        # Project ID not used in filter
        assert filter_arg["status"] == "confirmed"
        assert "created_at" in filter_arg

    @pytest.mark.asyncio
    async def test_resets_on_first_of_month(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should reset counter at UTC midnight on day 1."""
        # Given: It's February 3, 2026
        with patch('app.services.spend_tracking_service.datetime') as mock_datetime:
            mock_now = datetime(2026, 2, 3, 15, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            mock_zerodb_client.query_rows.return_value = {
                "rows": [
                    {"row_data": {"amount_usdc": "100.00"}}
                ]
            }

            # When: Getting monthly spend
            await spend_service.get_monthly_spend(
                agent_id="agent_123",
                project_id="project_456"
            )

            # Then: Should filter from Feb 1, 2026 00:00:00 UTC
            call_args = mock_zerodb_client.query_rows.call_args
            filter_arg = call_args[1]["filter"]
            expected_start = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
            assert filter_arg["created_at"]["$gte"] == expected_start.isoformat()

    @pytest.mark.asyncio
    async def test_handles_empty_results(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should return zero when no transactions exist."""
        # Given: No transactions this month
        mock_zerodb_client.query_rows.return_value = {
            "rows": []
        }

        # When: Getting monthly spend
        result = await spend_service.get_monthly_spend(
            agent_id="agent_123",
            project_id="project_456"
        )

        # Then: Should return zero
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_ignores_failed_transactions(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should only count completed transactions."""
        # Given: Mix of complete and failed transactions
        # Note: Failed transactions are filtered OUT by the query, so only confirmed ones are returned
        mock_zerodb_client.query_rows.return_value = {
            "rows": [
                {"row_data": {"amount_usdc": "10.00"}},
                {"row_data": {"amount_usdc": "20.00"}}
            ]
        }

        # When: Getting monthly spend
        result = await spend_service.get_monthly_spend(
            agent_id="agent_123",
            project_id="project_456"
        )

        # Then: Should only sum confirmed (filter enforced by query)
        assert result == Decimal("30.00")  # All returned rows are summed

        # And: Query should filter by status=confirmed
        call_args = mock_zerodb_client.query_rows.call_args
        assert call_args[1]["filter"]["status"] == "confirmed"


class TestCheckMonthlyBudget:
    """Tests for check_monthly_budget method."""

    @pytest.mark.asyncio
    async def test_allows_transaction_within_monthly_limit(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should allow when under monthly limit."""
        # Given: Current spend is $50, limit is $100, transaction is $30
        mock_zerodb_client.query_rows.return_value = {
            "rows": [{"row_data": {"amount_usdc": "50.00"}}]
        }

        # When: Checking budget
        result = await spend_service.check_monthly_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("30.00"),
            monthly_limit=Decimal("100.00")
        )

        # Then: Should allow transaction
        assert result["allowed"] is True
        assert result["current_spend"] == Decimal("50.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("50.00")
        assert "period" in result

    @pytest.mark.asyncio
    async def test_blocks_transaction_exceeding_monthly_limit(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should block when over monthly limit."""
        # Given: Current spend is $90, limit is $100, transaction is $20
        mock_zerodb_client.query_rows.return_value = {
            "rows": [
                {"row_data": {"amount_usdc": "50.00"}},
                {"row_data": {"amount_usdc": "40.00"}}
            ]
        }

        # When: Checking budget
        result = await spend_service.check_monthly_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("20.00"),
            monthly_limit=Decimal("100.00")
        )

        # Then: Should block transaction
        assert result["allowed"] is False
        assert result["current_spend"] == Decimal("90.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_blocks_transaction_at_exact_limit(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should block when transaction would reach exact limit."""
        # Given: Current spend is $100, limit is $100, transaction is $0.01
        mock_zerodb_client.query_rows.return_value = {
            "rows": [{"row_data": {"amount_usdc": "100.00"}}]
        }

        # When: Checking budget
        result = await spend_service.check_monthly_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("0.01"),
            monthly_limit=Decimal("100.00")
        )

        # Then: Should block (already at limit)
        assert result["allowed"] is False
        assert result["remaining"] == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_includes_period_in_response(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should include current period (YYYY-MM format) in response."""
        # Given: Current date is February 2026
        with patch('app.services.spend_tracking_service.datetime') as mock_datetime:
            mock_now = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            mock_zerodb_client.query_rows.return_value = {"rows": []}

            # When: Checking budget
            result = await spend_service.check_monthly_budget(
                agent_id="agent_123",
                project_id="project_456",
                amount=Decimal("10.00"),
                monthly_limit=Decimal("100.00")
            )

            # Then: Should include period
            assert result["period"] == "2026-02"


class TestCombinedLimits:
    """Tests for combined daily and monthly limit enforcement."""

    @pytest.mark.asyncio
    async def test_enforces_both_daily_and_monthly_limits(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should check both limits, fail if either exceeded."""
        # Given: Current daily spend is $5, current monthly spend is $95
        # Daily limit is $10, monthly limit is $100, transaction is $8

        # Mock get_monthly_spend to return $95
        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("95.00")

        # Mock get_daily_spend to return $5
        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("5.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend
        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking combined budget
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("8.00"),
            daily_limit=Decimal("10.00"),
            monthly_limit=Decimal("100.00")
        )

        # Then: Should fail due to monthly limit (95 + 8 = 103 > 100)
        # But also fails daily (5 + 8 = 13 > 10), so 2 violations
        assert result["allowed"] is False
        assert len(result["violations"]) == 2
        violation_types = [v["type"] for v in result["violations"]]
        assert "monthly_limit_exceeded" in violation_types
        assert "daily_limit_exceeded" in violation_types

    @pytest.mark.asyncio
    async def test_fails_when_daily_limit_exceeded_but_monthly_ok(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should block if daily limit exceeded even if monthly is OK."""
        # Given: Current daily spend is $45, current monthly spend is $50
        # Daily limit is $50, monthly limit is $1000, transaction is $10

        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("50.00")

        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("45.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend
        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking combined budget
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("10.00"),
            daily_limit=Decimal("50.00"),
            monthly_limit=Decimal("1000.00")
        )

        # Then: Should fail due to daily limit (45 + 10 = 55 > 50)
        assert result["allowed"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "daily_limit_exceeded"

    @pytest.mark.asyncio
    async def test_fails_when_monthly_limit_exceeded_but_daily_ok(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should block if monthly limit exceeded even if daily is OK."""
        # Given: Current daily spend is $5, current monthly spend is $195
        # Daily limit is $50, monthly limit is $200, transaction is $10

        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("195.00")

        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("5.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend
        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking combined budget
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("10.00"),
            daily_limit=Decimal("50.00"),
            monthly_limit=Decimal("200.00")
        )

        # Then: Should fail due to monthly limit (195 + 10 = 205 > 200)
        assert result["allowed"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "monthly_limit_exceeded"

    @pytest.mark.asyncio
    async def test_fails_with_multiple_violations_when_both_exceeded(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should report both violations when both limits exceeded."""
        # Given: Current daily spend is $48, current monthly spend is $198
        # Daily limit is $50, monthly limit is $200, transaction is $5

        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("198.00")

        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("48.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend
        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking combined budget
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("5.00"),
            daily_limit=Decimal("50.00"),
            monthly_limit=Decimal("200.00")
        )

        # Then: Should fail with both violations
        assert result["allowed"] is False
        assert len(result["violations"]) == 2
        violation_types = [v["type"] for v in result["violations"]]
        assert "daily_limit_exceeded" in violation_types
        assert "monthly_limit_exceeded" in violation_types

    @pytest.mark.asyncio
    async def test_allows_transaction_when_both_limits_satisfied(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should allow transaction when both daily and monthly limits OK."""
        # Given: Current daily spend is $10, current monthly spend is $50
        # Daily limit is $50, monthly limit is $200, transaction is $20

        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("50.00")

        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("10.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend
        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking combined budget
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("20.00"),
            daily_limit=Decimal("50.00"),
            monthly_limit=Decimal("200.00")
        )

        # Then: Should allow transaction
        assert result["allowed"] is True
        assert len(result.get("violations", [])) == 0

    @pytest.mark.asyncio
    async def test_only_checks_provided_limits(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should only check limits that are provided."""
        # Given: Only daily limit provided
        async def mock_get_daily_spend(*args, **kwargs):
            return Decimal("10.00")

        spend_service.get_daily_spend = mock_get_daily_spend

        # When: Checking with only daily limit
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("20.00"),
            daily_limit=Decimal("50.00"),
            monthly_limit=None
        )

        # Then: Should only check daily limit
        assert result["allowed"] is True

        # When: Checking with only monthly limit
        async def mock_get_monthly_spend(*args, **kwargs):
            return Decimal("50.00")

        spend_service.get_monthly_spend = mock_get_monthly_spend

        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("20.00"),
            daily_limit=None,
            monthly_limit=Decimal("100.00")
        )

        # Then: Should only check monthly limit
        assert result["allowed"] is True



    @pytest.mark.asyncio
    async def test_combined_budget_with_no_limits(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should allow transaction when no limits are provided."""
        # When: Checking with no limits
        result = await spend_service.check_combined_budget(
            agent_id="agent_123",
            project_id="project_456",
            amount=Decimal("1000.00"),
            daily_limit=None,
            monthly_limit=None
        )

        # Then: Should allow transaction
        assert result["allowed"] is True
        assert len(result.get("violations", [])) == 0


class TestErrorHandling:
    """Tests for error handling in spend tracking."""

    @pytest.mark.asyncio
    async def test_get_monthly_spend_handles_query_error(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should raise exception when query fails."""
        # Given: Query will raise an exception
        mock_zerodb_client.query_rows.side_effect = Exception("Database error")

        # When/Then: Should raise exception
        with pytest.raises(Exception) as exc_info:
            await spend_service.get_monthly_spend(
                agent_id="agent_123",
                project_id="project_456"
            )
        
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_monthly_spend_handles_invalid_amount(
        self,
        spend_service,
        mock_zerodb_client
    ):
        """Should skip rows with invalid amounts."""
        # Given: Rows with invalid amounts
        mock_zerodb_client.query_rows.return_value = {
            "rows": [
                {"row_data": {"amount_usdc": "10.00"}},
                {"row_data": {"amount_usdc": "invalid"}},  # Will be skipped
                {"row_data": {}},  # Missing amount_usdc, will be skipped
                {"row_data": {"amount_usdc": "20.00"}}
            ]
        }

        # When: Getting monthly spend
        result = await spend_service.get_monthly_spend(
            agent_id="agent_123",
            project_id="project_456"
        )

        # Then: Should only sum valid amounts
        assert result == Decimal("30.00")
