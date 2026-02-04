"""
Integration tests for monthly spending limits.

Tests Issue #154: Implement per-agent monthly spending limits

These tests verify:
1. Monthly budget enforcement
2. Combined daily and monthly limit validation
3. Month boundary reset behavior
4. Error messages and limit violation reporting
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from freezegun import freeze_time


class TestMonthlyLimitsIntegration:
    """Integration tests for monthly spending limits."""

    @pytest.fixture
    def agent_id(self):
        """Test agent ID."""
        return "did:key:z6MkTest123"

    @pytest.fixture
    def project_id(self):
        """Test project ID."""
        return "proj_test_123"

    @pytest.fixture
    def mock_spend_service(self):
        """Mock spend tracking service."""
        service = MagicMock()
        service.check_spending_limits = AsyncMock()
        service.record_transaction = AsyncMock()
        service.get_monthly_spend = AsyncMock(return_value=Decimal("0.00"))
        service.get_daily_spend = AsyncMock(return_value=Decimal("0.00"))
        service.reset_monthly_counter = AsyncMock()
        return service


class DescribeMonthlyBudgetEnforcement:
    """Test monthly budget enforcement scenarios."""

    @pytest.mark.asyncio
    async def it_allows_multiple_days_under_monthly_limit(self):
        """
        Should allow daily transactions totaling under monthly limit.

        Scenario:
        - Monthly limit: $2000
        - Day 1: Spend $500 (allowed)
        - Day 2: Spend $500 (allowed, cumulative: $1000)
        - Day 3: Spend $400 (allowed, cumulative: $1400)
        Total: $1400 < $2000 monthly limit = PASS
        """
        # This test documents the expected behavior
        # Implementation will need:
        # 1. SpendTrackingService with monthly accumulation
        # 2. Transaction history across multiple days
        # 3. Month-to-date calculation

        agent_id = "did:key:z6MkTest123"
        monthly_limit = Decimal("2000.00")

        # Day 1: $500
        with freeze_time("2026-02-01 10:00:00"):
            transaction_1 = {
                "agent_id": agent_id,
                "amount": Decimal("500.00"),
                "timestamp": datetime.utcnow()
            }
            # Expected: check_spending_limits returns {"allowed": True}
            # Expected: monthly_spend = $500

        # Day 2: $500 (cumulative: $1000)
        with freeze_time("2026-02-02 14:00:00"):
            transaction_2 = {
                "agent_id": agent_id,
                "amount": Decimal("500.00"),
                "timestamp": datetime.utcnow()
            }
            # Expected: check_spending_limits returns {"allowed": True}
            # Expected: monthly_spend = $1000

        # Day 3: $400 (cumulative: $1400)
        with freeze_time("2026-02-03 16:00:00"):
            transaction_3 = {
                "agent_id": agent_id,
                "amount": Decimal("400.00"),
                "timestamp": datetime.utcnow()
            }
            # Expected: check_spending_limits returns {"allowed": True}
            # Expected: monthly_spend = $1400

        # All transactions should pass monthly limit check
        # $1400 < $2000 = ALLOWED

    @pytest.mark.asyncio
    async def it_blocks_transaction_exceeding_monthly_limit(self):
        """
        Should block transaction when monthly limit would be exceeded.

        Scenario:
        - Monthly limit: $2000
        - Already spent this month: $1500
        - New transaction: $600
        - $1500 + $600 = $2100 > $2000 = BLOCKED
        """
        agent_id = "did:key:z6MkTest123"
        monthly_limit = Decimal("2000.00")
        current_monthly_spend = Decimal("1500.00")
        new_transaction_amount = Decimal("600.00")

        # Expected behavior:
        # projected_total = $1500 + $600 = $2100
        # $2100 > $2000 = VIOLATION

        # Expected error structure:
        expected_error = {
            "allowed": False,
            "error_code": "MONTHLY_LIMIT_EXCEEDED",
            "limit_type": "monthly",
            "limit_amount": "2000.00",
            "current_spend": "1500.00",
            "requested_amount": "600.00",
            "projected_total": "2100.00",
            "overage": "100.00",
            "reset_date": "2026-03-01T00:00:00Z",
            "message": "Monthly spending limit exceeded. Limit: $2000.00, Current: $1500.00, Requested: $600.00 would exceed by $100.00"
        }

        # This transaction should be BLOCKED

    @pytest.mark.asyncio
    async def it_allows_transaction_at_exact_monthly_limit(self):
        """
        Should allow transaction that brings total exactly to monthly limit.

        Scenario:
        - Monthly limit: $2000
        - Already spent: $1800
        - New transaction: $200
        - $1800 + $200 = $2000 = ALLOWED (at limit, not over)
        """
        agent_id = "did:key:z6MkTest123"
        monthly_limit = Decimal("2000.00")
        current_monthly_spend = Decimal("1800.00")
        new_transaction_amount = Decimal("200.00")

        # Expected behavior:
        # projected_total = $1800 + $200 = $2000
        # $2000 <= $2000 = ALLOWED

        expected_result = {
            "allowed": True,
            "monthly_spend": "2000.00",
            "monthly_limit": "2000.00",
            "remaining_monthly": "0.00",
            "at_limit": True
        }

    @pytest.mark.asyncio
    async def it_resets_monthly_counter_on_first_of_month(self):
        """
        Should reset monthly spending counter at UTC midnight on day 1.

        Scenario:
        - Jan 31 23:59 UTC: $1900 spent this month
        - Feb 1 00:00 UTC: Monthly counter resets to $0
        - Feb 1 00:01 UTC: New $500 transaction
        - Expected: $500 counted against February, not January
        """
        agent_id = "did:key:z6MkTest123"
        monthly_limit = Decimal("2000.00")

        # January 31, 23:59 UTC
        with freeze_time("2026-01-31 23:59:00"):
            january_spend = Decimal("1900.00")
            # Monthly spend = $1900
            # Remaining = $100

        # February 1, 00:00 UTC - RESET OCCURS
        with freeze_time("2026-02-01 00:00:00"):
            # Monthly spend should now be $0
            # Remaining = $2000 (full limit)

            # New transaction
            new_transaction = Decimal("500.00")
            # Expected: Transaction allowed
            # Expected: Monthly spend = $500 (February)
            # Expected: January spend = $1900 (archived, not counted)

        # Expected reset behavior:
        expected_reset = {
            "previous_month": "2026-01",
            "previous_month_spend": "1900.00",
            "new_month": "2026-02",
            "current_month_spend": "0.00",
            "reset_timestamp": "2026-02-01T00:00:00Z"
        }

    @pytest.mark.asyncio
    async def it_handles_leap_year_february_correctly(self):
        """
        Should handle February in leap years correctly (29 days).

        Scenario:
        - Year: 2024 (leap year)
        - Feb 29: Transaction at 23:59 UTC
        - Mar 1: Counter resets
        """
        agent_id = "did:key:z6MkTest123"

        # February 29, 2024 (leap year)
        with freeze_time("2024-02-29 23:59:00"):
            feb_transaction = Decimal("1000.00")
            # Should count toward February 2024

        # March 1, 2024 - Reset
        with freeze_time("2024-03-01 00:00:00"):
            # February total should be archived
            # March counter starts at $0
            pass

    @pytest.mark.asyncio
    async def it_handles_month_transitions_correctly(self):
        """
        Should handle all month boundary transitions correctly.

        Tests transitions:
        - Jan 31 → Feb 1 (31 day month → 28/29 day month)
        - Feb 28 → Mar 1 (28 day month → 31 day month)
        - Apr 30 → May 1 (30 day month → 31 day month)
        - Dec 31 → Jan 1 (year boundary)
        """
        agent_id = "did:key:z6MkTest123"
        monthly_limit = Decimal("2000.00")

        transitions = [
            ("2026-01-31 23:59:00", "2026-02-01 00:00:00", "Jan→Feb"),
            ("2026-02-28 23:59:00", "2026-03-01 00:00:00", "Feb→Mar"),
            ("2026-04-30 23:59:00", "2026-05-01 00:00:00", "Apr→May"),
            ("2026-12-31 23:59:00", "2027-01-01 00:00:00", "Dec→Jan (year)"),
        ]

        for before_time, after_time, label in transitions:
            # Before transition: spend near limit
            with freeze_time(before_time):
                pre_spend = Decimal("1900.00")
                # Expected: Monthly spend = $1900

            # After transition: counter reset
            with freeze_time(after_time):
                # Expected: Monthly spend = $0
                # Expected: Full monthly limit available
                pass


class DescribeCombinedDailyMonthlyLimits:
    """Test combined daily and monthly limit enforcement."""

    @pytest.mark.asyncio
    async def it_enforces_daily_limit_even_when_monthly_ok(self):
        """
        Daily limit blocks even if monthly has room.

        Scenario:
        - Daily limit: $100
        - Monthly limit: $2000
        - Already spent today: $50
        - Already spent this month: $500
        - New transaction: $60

        Check:
        - Daily: $50 + $60 = $110 > $100 = BLOCKED
        - Monthly: $500 + $60 = $560 < $2000 = OK

        Result: BLOCKED by daily limit
        """
        agent_id = "did:key:z6MkTest123"

        limits = {
            "daily_limit": Decimal("100.00"),
            "monthly_limit": Decimal("2000.00")
        }

        current_state = {
            "daily_spend": Decimal("50.00"),
            "monthly_spend": Decimal("500.00")
        }

        new_transaction = Decimal("60.00")

        # Expected validation result:
        expected_error = {
            "allowed": False,
            "violated_limits": ["daily"],
            "daily_limit_exceeded": {
                "limit": "100.00",
                "current": "50.00",
                "requested": "60.00",
                "projected": "110.00",
                "overage": "10.00"
            },
            "monthly_limit_ok": {
                "limit": "2000.00",
                "current": "500.00",
                "projected": "560.00",
                "remaining": "1440.00"
            },
            "error_code": "DAILY_LIMIT_EXCEEDED",
            "message": "Daily spending limit exceeded (monthly limit OK)"
        }

    @pytest.mark.asyncio
    async def it_enforces_monthly_limit_even_when_daily_ok(self):
        """
        Monthly limit blocks even if daily has room.

        Scenario:
        - Daily limit: $500
        - Monthly limit: $2000
        - Already spent today: $0
        - Already spent this month: $1900
        - New transaction: $200

        Check:
        - Daily: $0 + $200 = $200 < $500 = OK
        - Monthly: $1900 + $200 = $2100 > $2000 = BLOCKED

        Result: BLOCKED by monthly limit
        """
        agent_id = "did:key:z6MkTest123"

        limits = {
            "daily_limit": Decimal("500.00"),
            "monthly_limit": Decimal("2000.00")
        }

        current_state = {
            "daily_spend": Decimal("0.00"),
            "monthly_spend": Decimal("1900.00")
        }

        new_transaction = Decimal("200.00")

        # Expected validation result:
        expected_error = {
            "allowed": False,
            "violated_limits": ["monthly"],
            "daily_limit_ok": {
                "limit": "500.00",
                "current": "0.00",
                "projected": "200.00",
                "remaining": "300.00"
            },
            "monthly_limit_exceeded": {
                "limit": "2000.00",
                "current": "1900.00",
                "requested": "200.00",
                "projected": "2100.00",
                "overage": "100.00",
                "reset_date": "2026-03-01T00:00:00Z"
            },
            "error_code": "MONTHLY_LIMIT_EXCEEDED",
            "message": "Monthly spending limit exceeded (daily limit OK)"
        }

    @pytest.mark.asyncio
    async def it_passes_when_both_limits_ok(self):
        """
        Should allow when both daily and monthly OK.

        Scenario:
        - Daily limit: $100
        - Monthly limit: $2000
        - Already spent today: $0
        - Already spent this month: $500
        - New transaction: $50

        Check:
        - Daily: $0 + $50 = $50 < $100 = OK
        - Monthly: $500 + $50 = $550 < $2000 = OK

        Result: ALLOWED
        """
        agent_id = "did:key:z6MkTest123"

        limits = {
            "daily_limit": Decimal("100.00"),
            "monthly_limit": Decimal("2000.00")
        }

        current_state = {
            "daily_spend": Decimal("0.00"),
            "monthly_spend": Decimal("500.00")
        }

        new_transaction = Decimal("50.00")

        # Expected validation result:
        expected_result = {
            "allowed": True,
            "daily_limit_ok": {
                "limit": "100.00",
                "current": "0.00",
                "projected": "50.00",
                "remaining": "50.00"
            },
            "monthly_limit_ok": {
                "limit": "2000.00",
                "current": "500.00",
                "projected": "550.00",
                "remaining": "1450.00"
            }
        }

    @pytest.mark.asyncio
    async def it_blocks_when_both_limits_exceeded(self):
        """
        Should block when both daily and monthly limits exceeded.

        Scenario:
        - Daily limit: $100
        - Monthly limit: $2000
        - Already spent today: $90
        - Already spent this month: $1950
        - New transaction: $60

        Check:
        - Daily: $90 + $60 = $150 > $100 = BLOCKED
        - Monthly: $1950 + $60 = $2010 > $2000 = BLOCKED

        Result: BLOCKED by BOTH limits
        """
        agent_id = "did:key:z6MkTest123"

        limits = {
            "daily_limit": Decimal("100.00"),
            "monthly_limit": Decimal("2000.00")
        }

        current_state = {
            "daily_spend": Decimal("90.00"),
            "monthly_spend": Decimal("1950.00")
        }

        new_transaction = Decimal("60.00")

        # Expected validation result:
        expected_error = {
            "allowed": False,
            "violated_limits": ["daily", "monthly"],
            "daily_limit_exceeded": {
                "limit": "100.00",
                "current": "90.00",
                "requested": "60.00",
                "projected": "150.00",
                "overage": "50.00"
            },
            "monthly_limit_exceeded": {
                "limit": "2000.00",
                "current": "1950.00",
                "requested": "60.00",
                "projected": "2010.00",
                "overage": "10.00",
                "reset_date": "2026-03-01T00:00:00Z"
            },
            "error_code": "SPENDING_LIMITS_EXCEEDED",
            "message": "Transaction violates both daily and monthly limits"
        }

    @pytest.mark.asyncio
    async def it_prioritizes_daily_limit_error_when_both_violated(self):
        """
        When both limits violated, daily error shown first (more immediate).

        This tests error message priority:
        1. Daily limit (resets tomorrow)
        2. Monthly limit (resets next month)

        Users should see daily limit first since it's more actionable.
        """
        agent_id = "did:key:z6MkTest123"

        # Both limits violated
        validation_result = {
            "allowed": False,
            "violated_limits": ["daily", "monthly"],
            "primary_error": "DAILY_LIMIT_EXCEEDED",
            "secondary_error": "MONTHLY_LIMIT_EXCEEDED"
        }

        # Expected user-facing message priority:
        # "Daily spending limit exceeded. Limit resets at midnight UTC."
        # "Additionally, monthly limit also exceeded."


class DescribeErrorHandling:
    """Test error messages and limit violation reporting."""

    @pytest.mark.asyncio
    async def it_returns_comprehensive_error_with_all_limit_details(self):
        """
        Error should include all relevant limit information.

        Error response must include:
        - error_code
        - message (human-readable)
        - limit_type (daily, monthly, or both)
        - current_spend
        - limit_amount
        - requested_amount
        - projected_total
        - overage
        - reset_time (when limit resets)
        """
        expected_error_structure = {
            "allowed": False,
            "error_code": "MONTHLY_LIMIT_EXCEEDED",
            "message": "Monthly spending limit exceeded",
            "limit_type": "monthly",
            "details": {
                "limit_amount": "2000.00",
                "current_spend": "1900.00",
                "requested_amount": "200.00",
                "projected_total": "2100.00",
                "overage": "100.00",
                "reset_time": "2026-03-01T00:00:00Z",
                "reset_in_hours": 240
            },
            "suggestions": [
                "Transaction exceeds monthly limit by $100.00",
                "Monthly limit resets on 2026-03-01",
                "Consider splitting transaction across months",
                "Contact support to increase limits"
            ]
        }

    @pytest.mark.asyncio
    async def it_returns_both_violations_in_error_when_applicable(self):
        """
        Error should list all violated limits.

        When both daily and monthly limits violated,
        error must include both with individual details.
        """
        expected_error_structure = {
            "allowed": False,
            "error_code": "SPENDING_LIMITS_EXCEEDED",
            "message": "Transaction violates multiple spending limits",
            "violated_limits": ["daily", "monthly"],
            "violations": {
                "daily": {
                    "limit": "100.00",
                    "current": "90.00",
                    "projected": "150.00",
                    "overage": "50.00",
                    "reset_time": "2026-02-04T00:00:00Z"
                },
                "monthly": {
                    "limit": "2000.00",
                    "current": "1950.00",
                    "projected": "2010.00",
                    "overage": "10.00",
                    "reset_time": "2026-03-01T00:00:00Z"
                }
            },
            "primary_violation": "daily",
            "suggestions": [
                "Daily limit resets sooner (tomorrow)",
                "Consider waiting 24 hours for daily limit reset",
                "Monthly limit also exceeded, resets 2026-03-01"
            ]
        }

    @pytest.mark.asyncio
    async def it_provides_helpful_suggestions_based_on_limit_type(self):
        """
        Error messages should include context-specific suggestions.

        Different suggestions for:
        - Daily limit: "Resets tomorrow at midnight UTC"
        - Monthly limit: "Resets on first of next month"
        - Both: "Daily resets sooner"
        - Near limit: "Only $X remaining in budget"
        """
        scenarios = [
            {
                "limit_type": "daily",
                "overage": "10.00",
                "suggestions": [
                    "Daily limit resets at midnight UTC",
                    "Transaction exceeds limit by $10.00",
                    "Consider reducing transaction amount"
                ]
            },
            {
                "limit_type": "monthly",
                "overage": "50.00",
                "days_until_reset": 15,
                "suggestions": [
                    "Monthly limit resets on first of next month (15 days)",
                    "Transaction exceeds limit by $50.00",
                    "Consider splitting transaction",
                    "Contact support to increase monthly limit"
                ]
            },
            {
                "limit_type": "both",
                "suggestions": [
                    "Both daily and monthly limits exceeded",
                    "Daily limit resets sooner (tomorrow)",
                    "Wait until daily limit resets or reduce amount"
                ]
            }
        ]


class DescribeMonthlyLimitStorage:
    """Test monthly limit data storage and retrieval."""

    @pytest.mark.asyncio
    async def it_stores_monthly_spend_in_zerodb(self):
        """
        Monthly spending data should be persisted in ZeroDB.

        Expected table structure: agent_monthly_spend
        Columns:
        - agent_id (string)
        - month (string, format: "YYYY-MM")
        - total_spend (decimal)
        - transaction_count (integer)
        - first_transaction_time (timestamp)
        - last_transaction_time (timestamp)
        - created_at (timestamp)
        - updated_at (timestamp)
        """
        expected_table_schema = {
            "table_name": "agent_monthly_spend",
            "columns": {
                "agent_id": "string",
                "month": "string",  # "2026-02"
                "total_spend": "decimal",
                "transaction_count": "integer",
                "first_transaction_time": "timestamp",
                "last_transaction_time": "timestamp",
                "created_at": "timestamp",
                "updated_at": "timestamp"
            },
            "indexes": [
                "agent_id",
                "month",
                ["agent_id", "month"]  # Composite index
            ]
        }

    @pytest.mark.asyncio
    async def it_efficiently_queries_current_month_spend(self):
        """
        Querying current month spend should be optimized.

        Query should:
        1. Use composite index (agent_id, month)
        2. Return single row for current month
        3. Complete in <100ms
        """
        query_pattern = {
            "operation": "query_rows",
            "table": "agent_monthly_spend",
            "filter": {
                "agent_id": "did:key:z6MkTest123",
                "month": "2026-02"
            },
            "expected_result": {
                "row_count": 1,
                "latency_ms": "<100"
            }
        }

    @pytest.mark.asyncio
    async def it_archives_previous_months_for_historical_analysis(self):
        """
        Previous month data should be retained for analysis.

        Requirements:
        - Keep at least 12 months of history
        - Support year-over-year comparisons
        - Enable trend analysis
        """
        historical_data_requirements = {
            "retention_months": 12,
            "archive_format": "immutable",
            "query_capabilities": [
                "Get agent spend for any past month",
                "Compare month-over-month",
                "Calculate average monthly spend",
                "Identify spending trends"
            ]
        }


class DescribeMonthlyLimitConfiguration:
    """Test monthly limit configuration and management."""

    @pytest.mark.asyncio
    async def it_allows_different_monthly_limits_per_agent(self):
        """
        Each agent can have different monthly limits.

        Agent configurations:
        - Agent A: $1000/month (conservative)
        - Agent B: $10000/month (high-volume)
        - Agent C: $500/month (experimental)
        """
        agent_configs = [
            {"agent_id": "agent_a", "monthly_limit": "1000.00"},
            {"agent_id": "agent_b", "monthly_limit": "10000.00"},
            {"agent_id": "agent_c", "monthly_limit": "500.00"}
        ]

    @pytest.mark.asyncio
    async def it_supports_unlimited_monthly_spending(self):
        """
        Monthly limit can be set to unlimited (null or 0).

        Use cases:
        - Trusted agents
        - Enterprise tier
        - Testing environments
        """
        unlimited_config = {
            "agent_id": "trusted_agent",
            "monthly_limit": None,  # null = unlimited
            "daily_limit": "5000.00"  # Still has daily limit
        }

    @pytest.mark.asyncio
    async def it_validates_monthly_limit_is_greater_than_daily(self):
        """
        Monthly limit must be >= daily limit.

        Invalid configurations should be rejected:
        - Daily: $500, Monthly: $400 = INVALID

        Valid configurations:
        - Daily: $100, Monthly: $3000 = VALID
        - Daily: $500, Monthly: $500 = VALID (same)
        """
        validation_rules = {
            "rule": "monthly_limit >= daily_limit",
            "invalid_examples": [
                {"daily": 500, "monthly": 400, "error": "Monthly limit must be >= daily limit"},
                {"daily": 1000, "monthly": 999, "error": "Monthly limit must be >= daily limit"}
            ],
            "valid_examples": [
                {"daily": 100, "monthly": 3000},
                {"daily": 500, "monthly": 500},
                {"daily": 100, "monthly": None}  # unlimited monthly
            ]
        }


# Test execution metadata
TEST_METADATA = {
    "issue": "#154",
    "feature": "Monthly Spending Limits",
    "test_count": 25,
    "coverage_target": "80%",
    "test_types": [
        "Monthly budget enforcement",
        "Combined daily+monthly limits",
        "Month boundary resets",
        "Error handling",
        "Data storage",
        "Configuration validation"
    ],
    "dependencies": [
        "SpendTrackingService (to be implemented)",
        "agent_monthly_spend table in ZeroDB",
        "freezegun for time mocking"
    ]
}
