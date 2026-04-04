"""
BDD tests for wallet status management API.
Issue #156: Add wallet freeze and revoke controls.

Tests verify:
- PATCH /v1/public/{project_id}/wallets/{wallet_id}/status
- Status transitions (active, paused, frozen, inactive)
- Audit logging to compliance_events
- Status transition validation rules
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from datetime import datetime

from app.schemas.circle import WalletStatus


class TestWalletStatusAPI:
    """Test suite for wallet status management API"""

    class TestUpdateStatus:
        """Test status update endpoint"""

        @pytest.mark.asyncio
        async def test_updates_wallet_status_to_paused(self):
            """PATCH /wallets/{id}/status → paused"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate

            # Given: A mock wallet service and compliance service
            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service, \
                 patch('app.api.wallet_status.compliance_service') as mock_compliance_service:

                # Mock wallet data
                mock_wallet = {
                    "wallet_id": "wallet_test123",
                    "agent_did": "did:key:z6MkTest",
                    "status": "active",
                    "wallet_type": "transaction"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)
                mock_wallet_service.update_wallet_status = AsyncMock(return_value={
                    **mock_wallet,
                    "status": "paused"
                })
                mock_compliance_service.create_event = AsyncMock()

                # When: Updating wallet status to paused
                status_update = WalletStatusUpdate(
                    status=WalletStatus.PAUSED,
                    reason="Temporary maintenance"
                )

                result = await update_wallet_status(
                    project_id="proj_test",
                    wallet_id="wallet_test123",
                    status_update=status_update,
                    user_id="user_test"
                )

                # Then: Status updated and audit log created
                assert result.wallet_id == "wallet_test123"
                assert result.status == WalletStatus.PAUSED
                assert result.previous_status == WalletStatus.ACTIVE
                assert result.reason == "Temporary maintenance"
                assert result.updated_by == "user_test"

                # Verify compliance event created
                mock_compliance_service.create_event.assert_called_once()
                call_args = mock_compliance_service.create_event.call_args
                assert call_args[1]["project_id"] == "proj_test"
                event_data = call_args[1]["event_data"]
                assert event_data.details["action"] == "wallet_status_change"

        @pytest.mark.asyncio
        async def test_updates_wallet_status_to_frozen(self):
            """PATCH /wallets/{id}/status → frozen with reason"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service, \
                 patch('app.api.wallet_status.compliance_service') as mock_compliance_service:

                mock_wallet = {
                    "wallet_id": "wallet_test456",
                    "agent_did": "did:key:z6MkTest",
                    "status": "active",
                    "wallet_type": "analyst"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)
                mock_wallet_service.update_wallet_status = AsyncMock(return_value={
                    **mock_wallet,
                    "status": "frozen"
                })
                mock_compliance_service.create_event = AsyncMock()

                # When: Freezing wallet with reason
                status_update = WalletStatusUpdate(
                    status=WalletStatus.FROZEN,
                    reason="Suspicious activity detected",
                    frozen_until="2026-02-10T00:00:00Z"
                )

                result = await update_wallet_status(
                    project_id="proj_test",
                    wallet_id="wallet_test456",
                    status_update=status_update,
                    user_id="admin_user"
                )

                # Then: Wallet frozen with audit trail
                assert result.status == WalletStatus.FROZEN
                assert result.reason == "Suspicious activity detected"
                assert result.frozen_until == "2026-02-10T00:00:00Z"

                # Verify audit log includes freeze details
                mock_compliance_service.create_event.assert_called_once()
                event_data = mock_compliance_service.create_event.call_args[1]["event_data"]
                assert event_data.details["new_status"] == "frozen"
                assert event_data.details["reason"] == "Suspicious activity detected"

        @pytest.mark.asyncio
        async def test_updates_wallet_status_to_inactive(self):
            """PATCH /wallets/{id}/status → inactive"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service, \
                 patch('app.api.wallet_status.compliance_service') as mock_compliance_service:

                mock_wallet = {
                    "wallet_id": "wallet_test789",
                    "agent_did": "did:key:z6MkTest",
                    "status": "active",
                    "wallet_type": "compliance"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)
                mock_wallet_service.update_wallet_status = AsyncMock(return_value={
                    **mock_wallet,
                    "status": "inactive"
                })
                mock_compliance_service.create_event = AsyncMock()

                # When: Setting wallet to inactive
                status_update = WalletStatusUpdate(
                    status=WalletStatus.INACTIVE,
                    reason="Agent decommissioned"
                )

                result = await update_wallet_status(
                    project_id="proj_test",
                    wallet_id="wallet_test789",
                    status_update=status_update,
                    user_id="admin_user"
                )

                # Then: Status transitioned to inactive
                assert result.status == WalletStatus.INACTIVE
                assert result.previous_status == WalletStatus.ACTIVE
                assert result.reason == "Agent decommissioned"

        @pytest.mark.asyncio
        async def test_logs_status_change_to_compliance_events(self):
            """Should create detailed audit log entry"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate
            from app.schemas.compliance_events import ComplianceEventType, ComplianceOutcome

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service, \
                 patch('app.api.wallet_status.compliance_service') as mock_compliance_service:

                mock_wallet = {
                    "wallet_id": "wallet_audit",
                    "agent_did": "did:key:z6MkAuditTest",
                    "status": "active",
                    "wallet_type": "transaction"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)
                mock_wallet_service.update_wallet_status = AsyncMock(return_value={
                    **mock_wallet,
                    "status": "frozen"
                })
                mock_compliance_service.create_event = AsyncMock()

                # When: Updating status
                status_update = WalletStatusUpdate(
                    status=WalletStatus.FROZEN,
                    reason="Security review"
                )

                await update_wallet_status(
                    project_id="proj_audit",
                    wallet_id="wallet_audit",
                    status_update=status_update,
                    user_id="security_admin"
                )

                # Then: Compliance event created with full details
                mock_compliance_service.create_event.assert_called_once()
                call_kwargs = mock_compliance_service.create_event.call_args[1]

                assert call_kwargs["project_id"] == "proj_audit"
                event_data = call_kwargs["event_data"]
                assert event_data.agent_id == "did:key:z6MkAuditTest"
                assert event_data.event_type == ComplianceEventType.AUDIT_LOG
                assert event_data.outcome == ComplianceOutcome.PASS
                assert event_data.risk_score == 0.0

                details = event_data.details
                assert details["action"] == "wallet_status_change"
                assert details["wallet_id"] == "wallet_audit"
                assert details["previous_status"] == "active"
                assert details["new_status"] == "frozen"
                assert details["reason"] == "Security review"
                assert details["updated_by"] == "security_admin"

        @pytest.mark.asyncio
        async def test_requires_reason_for_frozen_status(self):
            """Should reject frozen status without reason"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service:

                mock_wallet = {
                    "wallet_id": "wallet_noreason",
                    "agent_did": "did:key:z6MkTest",
                    "status": "active",
                    "wallet_type": "transaction"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

                # When: Freezing without reason
                status_update = WalletStatusUpdate(
                    status=WalletStatus.FROZEN,
                    reason=None
                )

                # Then: Should raise validation error
                with pytest.raises(HTTPException) as exc_info:
                    await update_wallet_status(
                        project_id="proj_test",
                        wallet_id="wallet_noreason",
                        status_update=status_update,
                        user_id="user_test"
                    )

                assert exc_info.value.status_code == 400
                assert "reason required" in exc_info.value.detail.lower()

        @pytest.mark.asyncio
        async def test_prevents_status_change_from_inactive(self):
            """Should reject status changes from inactive wallets"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service:

                mock_wallet = {
                    "wallet_id": "wallet_inactive",
                    "agent_did": "did:key:z6MkTest",
                    "status": "inactive",
                    "wallet_type": "transaction"
                }
                mock_wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

                # When: Trying to change status from inactive
                status_update = WalletStatusUpdate(
                    status=WalletStatus.ACTIVE,
                    reason="Attempting to reactivate"
                )

                # Then: Should raise error
                with pytest.raises(HTTPException) as exc_info:
                    await update_wallet_status(
                        project_id="proj_test",
                        wallet_id="wallet_inactive",
                        status_update=status_update,
                        user_id="user_test"
                    )

                assert exc_info.value.status_code == 400
                assert "inactive" in exc_info.value.detail.lower()

        @pytest.mark.asyncio
        async def test_handles_wallet_not_found(self):
            """Should return 404 when wallet does not exist"""
            from app.api.wallet_status import update_wallet_status
            from app.schemas.wallet_status import WalletStatusUpdate
            from app.services.circle_service import WalletNotFoundError

            with patch('app.api.wallet_status.circle_wallet_service') as mock_wallet_service:

                mock_wallet_service.get_wallet = AsyncMock(
                    side_effect=WalletNotFoundError("wallet_missing")
                )

                # When: Updating status of non-existent wallet
                status_update = WalletStatusUpdate(
                    status=WalletStatus.PAUSED,
                    reason="Test"
                )

                # Then: Should raise 404 error
                with pytest.raises(WalletNotFoundError):
                    await update_wallet_status(
                        project_id="proj_test",
                        wallet_id="wallet_missing",
                        status_update=status_update,
                        user_id="user_test"
                    )
