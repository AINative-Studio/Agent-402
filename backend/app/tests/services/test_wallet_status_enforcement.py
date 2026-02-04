"""
BDD tests for wallet status enforcement in Gateway payment verification.

Issue #156: Add wallet freeze and revoke controls
Task: Implement wallet status enforcement in Gateway payment verification

Test Coverage:
- Active wallets: payments allowed
- Paused wallets: payments blocked
- Frozen wallets: payments blocked (security hold)
- Revoked wallets: payments blocked (permanently disabled)

Built by AINative Dev Team
Powered by AINative Cloud
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from app.services.gateway_service import gateway_service
from app.core.errors import WalletNotActiveError


class TestWalletStatusEnforcement:
    """BDD tests for wallet status enforcement in payment verification."""

    class TestActiveWallet:
        """Scenario: Active wallet - payments allowed"""

        @pytest.mark.asyncio
        async def test_allows_payment_from_active_wallet(self):
            """
            Given a wallet with status 'active'
            When verifying payment header
            Then payment should be allowed
            """
            # Arrange
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = (
                "payer=0x1234567890123456789012345678901234567890,"
                "amount=10.00,"
                "signature=0xabcdef123456"
            )

            mock_wallet = {
                "wallet_id": "wallet_123",
                "agent_did": "did:key:z6MkTest",
                "status": "active",  # Active wallet
                "balance": "100.00"
            }

            # Mock dependencies
            with patch.object(
                gateway_service, '_verify_signature', new_callable=AsyncMock
            ) as mock_verify:
                mock_verify.return_value = True

                with patch.object(
                    gateway_service, '_get_wallet_by_payer', new_callable=AsyncMock
                ) as mock_get_wallet:
                    mock_get_wallet.return_value = mock_wallet

                    # Act - should NOT raise exception
                    result = await gateway_service.verify_payment_header(
                        request=mock_request,
                        required_amount=10.0
                    )

                    # Assert
                    assert result is not None
                    assert result["amount"] == "10.00"

    class TestPausedWallet:
        """Scenario: Paused wallet - all payments blocked"""

        @pytest.mark.asyncio
        async def test_blocks_payment_from_paused_wallet(self):
            """
            Given a wallet with status 'paused'
            When verifying payment header
            Then payment should be blocked with WalletNotActiveError
            And error should indicate wallet is temporarily paused
            """
            # Arrange
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = (
                "payer=0x1234567890123456789012345678901234567890,"
                "amount=10.00,"
                "signature=0xabcdef123456"
            )

            mock_wallet = {
                "wallet_id": "wallet_456",
                "agent_did": "did:key:z6MkTest",
                "status": "paused",  # Paused wallet
                "status_reason": "Agent requested temporary pause",
                "balance": "100.00"
            }

            # Mock dependencies
            with patch.object(
                gateway_service, '_get_wallet_by_payer', new_callable=AsyncMock
            ) as mock_get_wallet:
                mock_get_wallet.return_value = mock_wallet

                # Act & Assert
                with pytest.raises(WalletNotActiveError) as exc_info:
                    await gateway_service.verify_payment_header(
                        request=mock_request,
                        required_amount=10.0
                    )

                # Verify error details
                assert exc_info.value.status_code == 403
                assert "paused" in str(exc_info.value.detail).lower()

    class TestFrozenWallet:
        """Scenario: Frozen wallet - all payments blocked (security hold)"""

        @pytest.mark.asyncio
        async def test_blocks_payment_from_frozen_wallet(self):
            """
            Given a wallet with status 'frozen'
            When verifying payment header
            Then payment should be blocked with WalletNotActiveError
            And error should indicate wallet is frozen for security review
            """
            # Arrange
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = (
                "payer=0x1234567890123456789012345678901234567890,"
                "amount=10.00,"
                "signature=0xabcdef123456"
            )

            mock_wallet = {
                "wallet_id": "wallet_789",
                "agent_did": "did:key:z6MkTest",
                "status": "frozen",  # Frozen wallet
                "status_reason": "Suspicious activity detected",
                "balance": "100.00"
            }

            # Mock dependencies
            with patch.object(
                gateway_service, '_get_wallet_by_payer', new_callable=AsyncMock
            ) as mock_get_wallet:
                mock_get_wallet.return_value = mock_wallet

                # Act & Assert
                with pytest.raises(WalletNotActiveError) as exc_info:
                    await gateway_service.verify_payment_header(
                        request=mock_request,
                        required_amount=10.0
                    )

                # Verify error details
                assert exc_info.value.status_code == 403
                assert "frozen" in str(exc_info.value.detail).lower()

    class TestRevokedWallet:
        """Scenario: Revoked wallet - permanently disabled"""

        @pytest.mark.asyncio
        async def test_blocks_payment_from_revoked_wallet(self):
            """
            Given a wallet with status 'revoked'
            When verifying payment header
            Then payment should be blocked with WalletNotActiveError
            And error should indicate wallet has been permanently revoked
            """
            # Arrange
            mock_request = MagicMock(spec=Request)
            mock_request.headers.get.return_value = (
                "payer=0x1234567890123456789012345678901234567890,"
                "amount=10.00,"
                "signature=0xabcdef123456"
            )

            mock_wallet = {
                "wallet_id": "wallet_999",
                "agent_did": "did:key:z6MkTest",
                "status": "revoked",  # Revoked wallet
                "status_reason": "Terms of service violation",
                "balance": "100.00"
            }

            # Mock dependencies
            with patch.object(
                gateway_service, '_get_wallet_by_payer', new_callable=AsyncMock
            ) as mock_get_wallet:
                mock_get_wallet.return_value = mock_wallet

                # Act & Assert
                with pytest.raises(WalletNotActiveError) as exc_info:
                    await gateway_service.verify_payment_header(
                        request=mock_request,
                        required_amount=10.0
                    )

                # Verify error details
                assert exc_info.value.status_code == 403
                assert "revoked" in str(exc_info.value.detail).lower()
