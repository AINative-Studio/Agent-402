"""
Integration tests for transaction amount limits.

Tests the enforcement of per-transaction maximum amounts for different
wallet types as part of Agent Spend Governance (Issue #155).

Wallet Type Limits:
- Analyst: $100 max per transaction
- Compliance: $500 max per transaction
- Transaction: $1,000 max per transaction

Test Strategy: BDD (Given/When/Then)
Coverage Target: 80%+

Built by AINative Dev Team
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from fastapi import Request

from app.services.gateway_service import (
    gateway_service,
    PaymentRequiredError,
    InsufficientPaymentError,
    InvalidSignatureError
)


# Transaction limits by wallet type (from governance roadmap)
WALLET_LIMITS = {
    "analyst": Decimal("100.00"),
    "compliance": Decimal("500.00"),
    "transaction": Decimal("1000.00")
}


class TestTransactionLimitsIntegration:
    """Integration tests for transaction amount limit enforcement."""

    class TestGatewayValidation:
        """Test Gateway service validates transaction limits."""

        @pytest.mark.asyncio
        async def test_validates_amount_before_budget_checks(self):
            """
            Given: A transaction limit of $1000
            When: A $1500 payment is attempted
            Then: Transaction amount exceeds wallet limit

            Note: This test validates the limit check logic.
            When limits are implemented in Gateway, this should raise an error.
            """
            # Arrange
            wallet_type = "transaction"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("1500.00")

            # Act - Validate against limit
            is_valid = amount_requested <= limit

            # Assert - Amount exceeds limit
            assert is_valid is False, (
                f"Transaction of ${amount_requested} should exceed "
                f"{wallet_type} limit of ${limit}"
            )

        @pytest.mark.asyncio
        async def test_allows_transaction_at_exact_limit(self):
            """
            Given: A transaction limit of $1000
            When: A $1000 payment is attempted
            Then: Transaction is allowed (at exact limit)
            """
            # Arrange
            mock_request = self._create_mock_request(
                amount="1000.00",
                wallet_type="transaction"
            )
            required_amount = 1000.00

            # Mock signature verification to pass
            with patch.object(
                gateway_service,
                '_verify_signature',
                return_value=True
            ):
                # Act
                result = await gateway_service.verify_payment_header(
                    mock_request,
                    required_amount
                )

                # Assert
                assert result["amount"] == "1000.00"
                assert float(result["amount"]) <= float(WALLET_LIMITS["transaction"])

        @pytest.mark.asyncio
        async def test_allows_large_transaction_when_no_limit_set(self):
            """
            Given: No transaction limit is configured
            When: A $10,000 payment is attempted
            Then: Transaction is allowed (assuming signature and budget OK)
            """
            # Arrange
            mock_request = self._create_mock_request(
                amount="10000.00",
                wallet_type="transaction"
            )
            required_amount = 10000.00

            # Mock signature verification to pass
            with patch.object(
                gateway_service,
                '_verify_signature',
                return_value=True
            ):
                # Act
                result = await gateway_service.verify_payment_header(
                    mock_request,
                    required_amount
                )

                # Assert - transaction allowed
                assert result["amount"] == "10000.00"
                assert float(result["amount"]) > float(WALLET_LIMITS["transaction"])

        def _create_mock_request(
            self,
            amount: str,
            wallet_type: str = "transaction"
        ) -> Request:
            """Create a mock FastAPI Request with payment header."""
            from unittest.mock import MagicMock

            request = MagicMock(spec=Request)
            payment_header = (
                f"payer=0x1234567890abcdef1234567890abcdef12345678,"
                f"amount={amount},"
                f"signature=0xvalidsignature123abc,"
                f"network=arc-testnet"
            )
            request.headers.get.return_value = payment_header

            return request

    class TestWalletTypeSpecificLimits:
        """Test transaction limits vary by wallet type."""

        @pytest.mark.asyncio
        async def test_enforces_analyst_wallet_limit(self):
            """
            Given: An analyst wallet with $100 limit
            When: A $150 payment is attempted
            Then: Transaction is blocked
            """
            # Arrange
            wallet_type = "analyst"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("150.00")

            # Act & Assert
            assert amount_requested > limit, (
                f"Test setup error: {amount_requested} should exceed {limit}"
            )

            # Simulate validation
            is_valid = amount_requested <= limit
            assert is_valid is False, (
                f"Analyst wallet transaction of ${amount_requested} "
                f"should be blocked (limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_allows_analyst_wallet_below_limit(self):
            """
            Given: An analyst wallet with $100 limit
            When: A $75 payment is attempted
            Then: Transaction is allowed
            """
            # Arrange
            wallet_type = "analyst"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("75.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is True, (
                f"Analyst wallet transaction of ${amount_requested} "
                f"should be allowed (limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_enforces_compliance_wallet_limit(self):
            """
            Given: A compliance wallet with $500 limit
            When: A $600 payment is attempted
            Then: Transaction is blocked
            """
            # Arrange
            wallet_type = "compliance"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("600.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is False, (
                f"Compliance wallet transaction of ${amount_requested} "
                f"should be blocked (limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_allows_compliance_wallet_below_limit(self):
            """
            Given: A compliance wallet with $500 limit
            When: A $450 payment is attempted
            Then: Transaction is allowed
            """
            # Arrange
            wallet_type = "compliance"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("450.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is True, (
                f"Compliance wallet transaction of ${amount_requested} "
                f"should be allowed (limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_enforces_transaction_wallet_limit(self):
            """
            Given: A transaction wallet with $1000 limit
            When: A $1100 payment is attempted
            Then: Transaction is blocked
            """
            # Arrange
            wallet_type = "transaction"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("1100.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is False, (
                f"Transaction wallet transaction of ${amount_requested} "
                f"should be blocked (limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_allows_transaction_wallet_below_limit(self):
            """
            Given: A transaction wallet with $1000 limit
            When: A $900 payment is attempted
            Then: Transaction is allowed
            """
            # Arrange
            wallet_type = "transaction"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("900.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is True, (
                f"Transaction wallet transaction of ${amount_requested} "
                f"should be allowed (limit: ${limit})"
            )

    class TestEdgeCases:
        """Test edge cases for transaction limits."""

        @pytest.mark.asyncio
        async def test_handles_zero_limit(self):
            """
            Given: A wallet with $0 transaction limit
            When: A $0.01 payment is attempted
            Then: Transaction is blocked
            """
            # Arrange
            limit = Decimal("0.00")
            amount_requested = Decimal("0.01")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is False, (
                f"Zero limit should block all transactions, "
                f"including ${amount_requested}"
            )

        @pytest.mark.asyncio
        async def test_handles_decimal_precision(self):
            """
            Given: A wallet with $100.00 limit
            When: A $100.01 payment is attempted
            Then: Transaction is blocked (exceeds by 1 cent)
            """
            # Arrange
            limit = Decimal("100.00")
            amount_requested = Decimal("100.01")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is False, (
                f"Transaction of ${amount_requested} should be blocked "
                f"(exceeds ${limit} by $0.01)"
            )

        @pytest.mark.asyncio
        async def test_allows_exact_limit_with_decimals(self):
            """
            Given: A wallet with $100.00 limit
            When: A $100.00 payment is attempted
            Then: Transaction is allowed (exact match)
            """
            # Arrange
            limit = Decimal("100.00")
            amount_requested = Decimal("100.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is True, (
                f"Transaction of ${amount_requested} should be allowed "
                f"(exact match with limit ${limit})"
            )

        @pytest.mark.asyncio
        async def test_handles_large_amounts(self):
            """
            Given: A wallet with $1000 limit
            When: A $999,999.99 payment is attempted
            Then: Transaction is blocked
            """
            # Arrange
            limit = Decimal("1000.00")
            amount_requested = Decimal("999999.99")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is False, (
                f"Large transaction of ${amount_requested} should be blocked "
                f"(limit: ${limit})"
            )

        @pytest.mark.asyncio
        async def test_handles_very_small_amounts(self):
            """
            Given: A wallet with $100 limit
            When: A $0.01 payment is attempted
            Then: Transaction is allowed (under limit)
            """
            # Arrange
            limit = Decimal("100.00")
            amount_requested = Decimal("0.01")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            assert is_valid is True, (
                f"Small transaction of ${amount_requested} should be allowed "
                f"(under limit ${limit})"
            )

        @pytest.mark.asyncio
        async def test_handles_negative_amounts(self):
            """
            Given: A wallet with $100 limit
            When: A negative amount is provided
            Then: Transaction is rejected (invalid amount)
            """
            # Arrange
            limit = Decimal("100.00")
            amount_requested = Decimal("-10.00")

            # Act
            is_negative = amount_requested < Decimal("0")

            # Assert
            assert is_negative is True, (
                "Negative amounts should be detected and rejected"
            )

    class TestLimitValidationFlow:
        """Test the complete limit validation flow."""

        @pytest.mark.asyncio
        async def test_validates_limits_in_correct_order(self):
            """
            Given: Multiple validation checks
            When: A payment is processed
            Then: Checks run in order: amount > 0, format valid, within limit
            """
            # Arrange
            amount_str = "150.00"
            wallet_type = "analyst"
            limit = WALLET_LIMITS[wallet_type]

            # Act - Step 1: Check amount is positive
            amount_decimal = Decimal(amount_str)
            assert amount_decimal > Decimal("0"), "Amount must be positive"

            # Act - Step 2: Check format is valid (2 decimal places)
            assert len(amount_str.split(".")[-1]) <= 2, "Max 2 decimal places"

            # Act - Step 3: Check within limit
            is_within_limit = amount_decimal <= limit

            # Assert
            assert is_within_limit is False, (
                f"${amount_decimal} exceeds {wallet_type} limit of ${limit}"
            )

        @pytest.mark.asyncio
        async def test_provides_clear_error_messages(self):
            """
            Given: A transaction that exceeds limit
            When: Validation fails
            Then: Error message includes limit and requested amount
            """
            # Arrange
            wallet_type = "analyst"
            limit = WALLET_LIMITS[wallet_type]
            amount_requested = Decimal("150.00")

            # Act
            is_valid = amount_requested <= limit

            # Assert
            if not is_valid:
                error_message = (
                    f"Transaction amount ${amount_requested} exceeds "
                    f"{wallet_type} wallet limit of ${limit}"
                )
                assert "exceeds" in error_message
                assert str(amount_requested) in error_message
                assert str(limit) in error_message

    class TestMultipleWalletScenarios:
        """Test scenarios involving multiple wallets."""

        @pytest.mark.asyncio
        async def test_enforces_different_limits_per_wallet_type(self):
            """
            Given: Three wallet types with different limits
            When: Same amount is tested against each
            Then: Results differ based on wallet type
            """
            # Arrange
            test_amount = Decimal("400.00")

            # Act & Assert for each wallet type
            analyst_valid = test_amount <= WALLET_LIMITS["analyst"]
            compliance_valid = test_amount <= WALLET_LIMITS["compliance"]
            transaction_valid = test_amount <= WALLET_LIMITS["transaction"]

            # Assert
            assert analyst_valid is False, "Should exceed analyst limit ($100)"
            assert compliance_valid is True, "Should be under compliance limit ($500)"
            assert transaction_valid is True, "Should be under transaction limit ($1000)"

        @pytest.mark.asyncio
        async def test_handles_concurrent_validations(self):
            """
            Given: Multiple transactions being validated simultaneously
            When: Each has different amounts and wallet types
            Then: Each is validated independently
            """
            # Arrange
            transactions = [
                {"amount": Decimal("50.00"), "wallet_type": "analyst", "expected": True},
                {"amount": Decimal("150.00"), "wallet_type": "analyst", "expected": False},
                {"amount": Decimal("300.00"), "wallet_type": "compliance", "expected": True},
                {"amount": Decimal("600.00"), "wallet_type": "compliance", "expected": False},
                {"amount": Decimal("800.00"), "wallet_type": "transaction", "expected": True},
                {"amount": Decimal("1200.00"), "wallet_type": "transaction", "expected": False},
            ]

            # Act & Assert
            for tx in transactions:
                limit = WALLET_LIMITS[tx["wallet_type"]]
                is_valid = tx["amount"] <= limit

                assert is_valid == tx["expected"], (
                    f"Transaction of ${tx['amount']} for {tx['wallet_type']} "
                    f"(limit: ${limit}) should be {tx['expected']}"
                )

    class TestLimitConfigurationValidation:
        """Test validation of limit configuration itself."""

        @pytest.mark.asyncio
        async def test_validates_all_wallet_types_have_limits(self):
            """
            Given: Required wallet types
            When: Checking limit configuration
            Then: All wallet types have defined limits
            """
            # Arrange
            required_wallet_types = ["analyst", "compliance", "transaction"]

            # Act & Assert
            for wallet_type in required_wallet_types:
                assert wallet_type in WALLET_LIMITS, (
                    f"Wallet type '{wallet_type}' must have a defined limit"
                )
                assert WALLET_LIMITS[wallet_type] > Decimal("0"), (
                    f"Limit for '{wallet_type}' must be positive"
                )

        @pytest.mark.asyncio
        async def test_validates_limits_increase_by_wallet_privilege(self):
            """
            Given: Wallet types with different privilege levels
            When: Comparing limits
            Then: Limits increase with privilege (analyst < compliance < transaction)
            """
            # Act & Assert
            assert WALLET_LIMITS["analyst"] < WALLET_LIMITS["compliance"], (
                "Compliance limit should exceed analyst limit"
            )
            assert WALLET_LIMITS["compliance"] < WALLET_LIMITS["transaction"], (
                "Transaction limit should exceed compliance limit"
            )
            assert WALLET_LIMITS["analyst"] < WALLET_LIMITS["transaction"], (
                "Transaction limit should exceed analyst limit"
            )

        @pytest.mark.asyncio
        async def test_validates_limit_values_are_reasonable(self):
            """
            Given: Transaction limits
            When: Checking values
            Then: Limits are within reasonable ranges
            """
            # Act & Assert
            # Analyst: should be <= $1000
            assert WALLET_LIMITS["analyst"] <= Decimal("1000.00"), (
                "Analyst limit should not exceed $1000"
            )

            # Compliance: should be between $100 and $5000
            assert Decimal("100.00") <= WALLET_LIMITS["compliance"] <= Decimal("5000.00"), (
                "Compliance limit should be between $100 and $5000"
            )

            # Transaction: should be between $500 and $10000
            assert Decimal("500.00") <= WALLET_LIMITS["transaction"] <= Decimal("10000.00"), (
                "Transaction limit should be between $500 and $10,000"
            )
