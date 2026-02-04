"""
BDD tests for Gateway budget enforcement.
Issue #153: Implement per-agent daily spending limits.

Test coverage:
- Budget check allows payment within daily limit
- Budget check blocks payment exceeding daily limit
- Budget check includes current spend and remaining in error
- Budget check handles agents without wallets (no enforcement)
- Budget check handles agents without daily limits (no enforcement)
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request

from app.services.gateway_service import gateway_service
from app.core.errors import APIError


class TestGatewayBudgetEnforcement:
    """BDD tests for Gateway budget enforcement."""

    @pytest.mark.asyncio
    async def test_allows_payment_within_daily_budget(self):
        """
        Should allow payment when agent is under daily spending limit.

        Given: An agent with max_daily_spend of 100 USDC
        And: Current daily spend is 50 USDC
        When: Agent attempts payment of 30 USDC
        Then: Payment is allowed (50 + 30 = 80 < 100)
        """
        # Create mock request with valid payment header
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = (
            "payer=0x1234567890abcdef1234567890abcdef12345678,"
            "amount=30.00,signature=0xvalidsignature123,network=arc-testnet"
        )

        # Mock wallet with daily limit
        mock_wallet = {
            "wallet_id": "wallet_test_123",
            "agent_did": "did:agent:test123",
            "wallet_type": "transaction",
            "max_daily_spend": "100.00",
            "balance": "200.00"
        }

        # Mock budget check result (allowed)
        mock_budget_check = {
            "allowed": True,
            "current_spend": Decimal("50.00"),
            "limit": Decimal("100.00"),
            "remaining": Decimal("50.00")
        }

        # Mock the lazy-loaded properties
        mock_wallet_service = MagicMock()
        mock_wallet_service.get_wallet_by_agent = AsyncMock(return_value=mock_wallet)

        mock_spend_tracking = MagicMock()
        mock_spend_tracking.check_daily_budget = AsyncMock(return_value=mock_budget_check)

        with patch.object(
            gateway_service,
            'circle_wallet_service',
            mock_wallet_service
        ), patch.object(
            gateway_service,
            'spend_tracking',
            mock_spend_tracking
        ):
            # Should not raise exception
            result = await gateway_service.verify_payment_header(
                request=mock_request,
                required_amount=30.00,
                agent_id="did:agent:test123",
                project_id="proj_test_001"
            )

            # Verify payment data was returned
            assert result["amount"] == "30.00"
            assert result["payer"] == "0x1234567890abcdef1234567890abcdef12345678"

            # Verify budget check was called
            mock_spend_tracking.check_daily_budget.assert_called_once_with(
                agent_id="did:agent:test123",
                project_id="proj_test_001",
                amount=Decimal("30.00"),
                daily_limit=Decimal("100.00")
            )

    @pytest.mark.asyncio
    async def test_blocks_payment_exceeding_daily_budget(self):
        """
        Should raise BudgetExceededError when payment exceeds daily limit.

        Given: An agent with max_daily_spend of 100 USDC
        And: Current daily spend is 80 USDC
        When: Agent attempts payment of 30 USDC
        Then: Payment is blocked (80 + 30 = 110 > 100)
        And: BudgetExceededError is raised with HTTP 402
        """
        # Create mock request with valid payment header
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = (
            "payer=0x1234567890abcdef1234567890abcdef12345678,"
            "amount=30.00,signature=0xvalidsignature123,network=arc-testnet"
        )

        # Mock wallet with daily limit
        mock_wallet = {
            "wallet_id": "wallet_test_123",
            "agent_did": "did:agent:test123",
            "wallet_type": "transaction",
            "max_daily_spend": "100.00",
            "balance": "200.00"
        }

        # Mock budget check result (not allowed)
        mock_budget_check = {
            "allowed": False,
            "current_spend": Decimal("80.00"),
            "limit": Decimal("100.00"),
            "remaining": Decimal("20.00")
        }

        # Mock the lazy-loaded properties
        mock_wallet_service = MagicMock()
        mock_wallet_service.get_wallet_by_agent = AsyncMock(return_value=mock_wallet)

        mock_spend_tracking = MagicMock()
        mock_spend_tracking.check_daily_budget = AsyncMock(return_value=mock_budget_check)

        with patch.object(
            gateway_service,
            'circle_wallet_service',
            mock_wallet_service
        ), patch.object(
            gateway_service,
            'spend_tracking',
            mock_spend_tracking
        ):
            # Should raise BudgetExceededError
            with pytest.raises(APIError) as exc_info:
                await gateway_service.verify_payment_header(
                    request=mock_request,
                    required_amount=30.00,
                    agent_id="did:agent:test123",
                    project_id="proj_test_001"
                )

            # Verify error details
            error = exc_info.value
            assert error.status_code == 402
            assert error.error_code == "BUDGET_EXCEEDED"

    @pytest.mark.asyncio
    async def test_includes_current_spend_in_error(self):
        """
        Should include current spend, limit, and remaining in error detail.

        Given: An agent exceeding budget
        When: BudgetExceededError is raised
        Then: Error detail includes current_spend, daily_limit, and remaining
        """
        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = (
            "payer=0x1234567890abcdef1234567890abcdef12345678,"
            "amount=50.00,signature=0xvalidsignature123,network=arc-testnet"
        )

        # Mock wallet with daily limit
        mock_wallet = {
            "wallet_id": "wallet_test_123",
            "agent_did": "did:agent:test123",
            "wallet_type": "transaction",
            "max_daily_spend": "100.00",
            "balance": "200.00"
        }

        # Mock budget check result (not allowed)
        mock_budget_check = {
            "allowed": False,
            "current_spend": Decimal("90.00"),
            "limit": Decimal("100.00"),
            "remaining": Decimal("10.00")
        }

        # Mock the lazy-loaded properties
        mock_wallet_service = MagicMock()
        mock_wallet_service.get_wallet_by_agent = AsyncMock(return_value=mock_wallet)

        mock_spend_tracking = MagicMock()
        mock_spend_tracking.check_daily_budget = AsyncMock(return_value=mock_budget_check)

        with patch.object(
            gateway_service,
            'circle_wallet_service',
            mock_wallet_service
        ), patch.object(
            gateway_service,
            'spend_tracking',
            mock_spend_tracking
        ):
            # Should raise BudgetExceededError
            with pytest.raises(APIError) as exc_info:
                await gateway_service.verify_payment_header(
                    request=mock_request,
                    required_amount=50.00,
                    agent_id="did:agent:test123",
                    project_id="proj_test_001"
                )

            # Verify error includes budget details
            error = exc_info.value
            assert error.status_code == 402
            assert hasattr(error, "detail")

            # Detail should be a dict with budget information
            detail = error.detail if isinstance(error.detail, dict) else {}
            assert detail.get("error") == "budget_exceeded"
            assert detail.get("current_spend") == "90.00"
            assert detail.get("daily_limit") == "100.00"
            assert detail.get("remaining") == "10.00"

    @pytest.mark.asyncio
    async def test_allows_payment_when_no_wallet_exists(self):
        """
        Should allow payment when agent has no wallet (no budget enforcement).

        Given: An agent without a transaction wallet
        When: Agent attempts payment
        Then: Payment is allowed (no budget enforcement)
        """
        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = (
            "payer=0x1234567890abcdef1234567890abcdef12345678,"
            "amount=30.00,signature=0xvalidsignature123,network=arc-testnet"
        )

        # Mock wallet lookup raises WalletNotFoundError
        from app.services.circle_service import WalletNotFoundError

        mock_wallet_service = MagicMock()
        mock_wallet_service.get_wallet_by_agent = AsyncMock(
            side_effect=WalletNotFoundError("wallet not found")
        )

        with patch.object(
            gateway_service,
            'circle_wallet_service',
            mock_wallet_service
        ):
            # Should not raise exception (no enforcement)
            result = await gateway_service.verify_payment_header(
                request=mock_request,
                required_amount=30.00,
                agent_id="did:agent:test123",
                project_id="proj_test_001"
            )

            # Verify payment was allowed
            assert result["amount"] == "30.00"

    @pytest.mark.asyncio
    async def test_allows_payment_when_no_daily_limit_set(self):
        """
        Should allow payment when wallet has no max_daily_spend set.

        Given: An agent with a wallet but no max_daily_spend configured
        When: Agent attempts payment
        Then: Payment is allowed (no budget enforcement)
        """
        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = (
            "payer=0x1234567890abcdef1234567890abcdef12345678,"
            "amount=30.00,signature=0xvalidsignature123,network=arc-testnet"
        )

        # Mock wallet without daily limit
        mock_wallet = {
            "wallet_id": "wallet_test_123",
            "agent_did": "did:agent:test123",
            "wallet_type": "transaction",
            "balance": "200.00"
            # No max_daily_spend field
        }

        mock_wallet_service = MagicMock()
        mock_wallet_service.get_wallet_by_agent = AsyncMock(return_value=mock_wallet)

        with patch.object(
            gateway_service,
            'circle_wallet_service',
            mock_wallet_service
        ):
            # Should not raise exception (no enforcement)
            result = await gateway_service.verify_payment_header(
                request=mock_request,
                required_amount=30.00,
                agent_id="did:agent:test123",
                project_id="proj_test_001"
            )

            # Verify payment was allowed
            assert result["amount"] == "30.00"


class TestSpendTrackingService:
    """BDD tests for SpendTrackingService."""

    @pytest.mark.asyncio
    async def test_allows_spend_within_limit(self):
        """
        Should allow spend when total is within daily limit.

        Given: Agent has spent 50 USDC today
        And: Daily limit is 100 USDC
        When: Checking budget for 30 USDC spend
        Then: allowed=True, current_spend=50, remaining=50
        """
        from app.services.spend_tracking_service import SpendTrackingService

        # Create a new service instance for testing
        service = SpendTrackingService()

        # Mock the ZeroDB client
        mock_client = MagicMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [{"total_spend": "50.00"}]
        })
        service._client = mock_client

        result = await service.check_daily_budget(
            agent_id="did:agent:test123",
            project_id="proj_test_001",
            amount=Decimal("30.00"),
            daily_limit=Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["current_spend"] == Decimal("50.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_blocks_spend_exceeding_limit(self):
        """
        Should block spend when total would exceed daily limit.

        Given: Agent has spent 80 USDC today
        And: Daily limit is 100 USDC
        When: Checking budget for 30 USDC spend
        Then: allowed=False, current_spend=80, remaining=20
        """
        from app.services.spend_tracking_service import SpendTrackingService

        service = SpendTrackingService()

        # Mock the ZeroDB client
        mock_client = MagicMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [{"total_spend": "80.00"}]
        })
        service._client = mock_client

        result = await service.check_daily_budget(
            agent_id="did:agent:test123",
            project_id="proj_test_001",
            amount=Decimal("30.00"),
            daily_limit=Decimal("100.00")
        )

        assert result["allowed"] is False
        assert result["current_spend"] == Decimal("80.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_allows_spend_exactly_at_limit(self):
        """
        Should allow spend when total exactly reaches daily limit.

        Given: Agent has spent 70 USDC today
        And: Daily limit is 100 USDC
        When: Checking budget for 30 USDC spend
        Then: allowed=True (70 + 30 = 100, exactly at limit)
        """
        from app.services.spend_tracking_service import SpendTrackingService

        service = SpendTrackingService()

        # Mock the ZeroDB client
        mock_client = MagicMock()
        mock_client.query_rows = AsyncMock(return_value={
            "rows": [{"total_spend": "70.00"}]
        })
        service._client = mock_client

        result = await service.check_daily_budget(
            agent_id="did:agent:test123",
            project_id="proj_test_001",
            amount=Decimal("30.00"),
            daily_limit=Decimal("100.00")
        )

        assert result["allowed"] is True
        assert result["current_spend"] == Decimal("70.00")
        assert result["limit"] == Decimal("100.00")
        assert result["remaining"] == Decimal("30.00")
