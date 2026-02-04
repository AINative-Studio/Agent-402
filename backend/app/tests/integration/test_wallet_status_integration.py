"""
Integration tests for wallet status management and enforcement.

Issue #156: Add wallet freeze and revoke controls

This test suite validates:
1. Status transitions (active, paused, frozen, revoked)
2. Payment blocking enforcement for each status
3. Audit logging for status changes
4. Temporary freeze capabilities
5. Irreversibility of revoked status

Test-Driven Development (TDD):
- Written FIRST before implementation
- Uses BDD-style Given/When/Then pattern
- Follows AAA (Arrange-Act-Assert) pattern

Built by AINative Dev Team
All Data Services Built on ZeroDB
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from app.services.circle_wallet_service import (
    CircleWalletService,
    DuplicateWalletError
)
from app.services.circle_service import WalletNotFoundError
from app.core.errors import APIError


class TestWalletStatusTransitions:
    """Test all valid and invalid wallet status transitions."""

    @pytest.mark.asyncio
    async def test_transition_active_to_paused_and_back(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN an active wallet
        WHEN status is changed to paused and back to active
        THEN status updates successfully
        """
        # Arrange: Create active wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_001"
        wallet_type = "transaction"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type=wallet_type,
            description="Test transaction wallet"
        )

        assert wallet["status"] == "active"
        wallet_id = wallet["wallet_id"]

        # Act: Transition to paused
        updated_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="paused",
            reason="Testing pause functionality",
            updated_by="test_admin"
        )

        # Assert: Status is paused
        assert updated_wallet["status"] == "paused"
        assert updated_wallet["status_reason"] == "Testing pause functionality"
        assert updated_wallet["status_updated_by"] == "test_admin"

        # Act: Transition back to active
        reactivated_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="active",
            reason="Testing complete",
            updated_by="test_admin"
        )

        # Assert: Status is active again
        assert reactivated_wallet["status"] == "active"
        assert reactivated_wallet["status_reason"] == "Testing complete"

    @pytest.mark.asyncio
    async def test_transition_active_to_frozen_requires_review(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN an active wallet
        WHEN status is changed to frozen
        THEN status updates and requires review to reactivate
        """
        # Arrange: Create active wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_002"
        wallet_type = "compliance"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type=wallet_type,
            description="Test compliance wallet"
        )

        wallet_id = wallet["wallet_id"]

        # Act: Freeze wallet
        frozen_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="frozen",
            reason="Suspicious activity detected",
            updated_by="compliance_system"
        )

        # Assert: Wallet is frozen
        assert frozen_wallet["status"] == "frozen"
        assert frozen_wallet["status_reason"] == "Suspicious activity detected"
        assert frozen_wallet["status_updated_by"] == "compliance_system"
        assert "frozen_at" in frozen_wallet

        # Act: Unfreeze after review
        unfrozen_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="active",
            reason="Review complete - cleared",
            updated_by="compliance_officer"
        )

        # Assert: Successfully unfrozen after review
        assert unfrozen_wallet["status"] == "active"
        assert unfrozen_wallet["status_reason"] == "Review complete - cleared"

    @pytest.mark.asyncio
    async def test_transition_active_to_revoked_is_permanent(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN an active wallet
        WHEN status is changed to revoked
        THEN status updates permanently and cannot be changed
        """
        # Arrange: Create active wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_003"
        wallet_type = "analyst"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type=wallet_type,
            description="Test analyst wallet"
        )

        wallet_id = wallet["wallet_id"]

        # Act: Revoke wallet permanently
        revoked_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="revoked",
            reason="Terms of service violation",
            updated_by="admin_system"
        )

        # Assert: Wallet is revoked
        assert revoked_wallet["status"] == "revoked"
        assert revoked_wallet["status_reason"] == "Terms of service violation"
        assert revoked_wallet["status_updated_by"] == "admin_system"
        assert "revoked_at" in revoked_wallet

    @pytest.mark.asyncio
    async def test_cannot_change_revoked_wallet_status(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a revoked wallet
        WHEN attempting to change status
        THEN operation fails with appropriate error
        """
        # Arrange: Create and revoke wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_004"
        wallet_type = "transaction"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type=wallet_type
        )

        wallet_id = wallet["wallet_id"]

        await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="revoked",
            reason="Permanent ban",
            updated_by="admin"
        )

        # Act & Assert: Cannot change revoked wallet
        with pytest.raises(APIError) as exc_info:
            await wallet_service.update_wallet_status(
                wallet_id=wallet_id,
                project_id=test_project_id,
                new_status="active",
                reason="Attempted reactivation",
                updated_by="admin"
            )

        assert exc_info.value.status_code == 403
        assert "revoked" in str(exc_info.value.detail).lower()
        assert "cannot" in str(exc_info.value.detail).lower() or "permanent" in str(exc_info.value.detail).lower()


class TestPaymentBlockingByStatus:
    """Test payment blocking enforcement for each wallet status."""

    @pytest.mark.asyncio
    async def test_blocks_payment_from_paused_wallet(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a paused wallet
        WHEN attempting to initiate transfer
        THEN transfer is blocked with HTTP 403
        """
        # Arrange: Create and pause wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did_source = "did:key:test_agent_005"
        agent_did_dest = "did:key:test_agent_006"

        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_source,
            wallet_type="transaction"
        )

        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_dest,
            wallet_type="transaction"
        )

        # Pause source wallet
        await wallet_service.update_wallet_status(
            wallet_id=source_wallet["wallet_id"],
            project_id=test_project_id,
            new_status="paused",
            reason="Testing payment block",
            updated_by="test_system"
        )

        # Act & Assert: Transfer should be blocked
        with pytest.raises(APIError) as exc_info:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source_wallet["wallet_id"],
                destination_wallet_id=dest_wallet["wallet_id"],
                amount="100.00"
            )

        # Verify it's a 403 Forbidden error
        assert exc_info.value.status_code == 403
        assert "paused" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_blocks_payment_from_frozen_wallet(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a frozen wallet
        WHEN attempting to initiate transfer
        THEN transfer is blocked with HTTP 403
        """
        # Arrange: Create and freeze wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did_source = "did:key:test_agent_007"
        agent_did_dest = "did:key:test_agent_008"

        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_source,
            wallet_type="transaction"
        )

        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_dest,
            wallet_type="transaction"
        )

        # Freeze source wallet
        await wallet_service.update_wallet_status(
            wallet_id=source_wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Compliance review",
            updated_by="compliance_system"
        )

        # Act & Assert: Transfer should be blocked
        with pytest.raises(APIError) as exc_info:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source_wallet["wallet_id"],
                destination_wallet_id=dest_wallet["wallet_id"],
                amount="50.00"
            )

        # Verify it's a 403 Forbidden error
        assert exc_info.value.status_code == 403
        assert "frozen" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_blocks_payment_from_revoked_wallet(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a revoked wallet
        WHEN attempting to initiate transfer
        THEN transfer is blocked with HTTP 403
        """
        # Arrange: Create and revoke wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did_source = "did:key:test_agent_009"
        agent_did_dest = "did:key:test_agent_010"

        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_source,
            wallet_type="transaction"
        )

        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_dest,
            wallet_type="transaction"
        )

        # Revoke source wallet
        await wallet_service.update_wallet_status(
            wallet_id=source_wallet["wallet_id"],
            project_id=test_project_id,
            new_status="revoked",
            reason="Account terminated",
            updated_by="admin_system"
        )

        # Act & Assert: Transfer should be blocked
        with pytest.raises(APIError) as exc_info:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source_wallet["wallet_id"],
                destination_wallet_id=dest_wallet["wallet_id"],
                amount="25.00"
            )

        # Verify it's a 403 Forbidden error
        assert exc_info.value.status_code == 403
        assert "revoked" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_allows_payment_from_active_wallet(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN an active wallet
        WHEN attempting to initiate transfer
        THEN transfer succeeds with HTTP 200
        """
        # Arrange: Create active wallets
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did_source = "did:key:test_agent_011"
        agent_did_dest = "did:key:test_agent_012"

        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_source,
            wallet_type="transaction"
        )

        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_dest,
            wallet_type="transaction"
        )

        # Act: Initiate transfer from active wallet
        transfer = await wallet_service.initiate_transfer(
            project_id=test_project_id,
            source_wallet_id=source_wallet["wallet_id"],
            destination_wallet_id=dest_wallet["wallet_id"],
            amount="75.00"
        )

        # Assert: Transfer succeeds
        assert transfer is not None
        assert transfer["status"] in ["pending", "complete"]
        assert transfer["amount"] == "75.00"


class TestWalletStatusAuditLogging:
    """Test audit logging for wallet status changes."""

    @pytest.mark.asyncio
    async def test_logs_status_change_to_compliance_events(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a wallet status change
        WHEN status is updated
        THEN compliance event is created with full details
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_013"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="transaction"
        )

        # Act: Update status
        await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Suspicious activity pattern",
            updated_by="compliance_ai_agent"
        )

        # Assert: Compliance event logged
        events = await wallet_service.get_wallet_status_history(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id
        )

        assert len(events) >= 1
        latest_event = events[0]

        assert latest_event["event_type"] == "wallet_status_change"
        assert latest_event["wallet_id"] == wallet["wallet_id"]
        assert latest_event["previous_status"] == "active"
        assert latest_event["new_status"] == "frozen"
        assert latest_event["reason"] == "Suspicious activity pattern"
        assert latest_event["updated_by"] == "compliance_ai_agent"
        assert "timestamp" in latest_event

    @pytest.mark.asyncio
    async def test_includes_detailed_reason_in_audit_log(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a status change with detailed reason
        WHEN audit log is queried
        THEN reason is present and complete
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_014"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="analyst"
        )

        detailed_reason = (
            "Multiple failed authentication attempts detected. "
            "Pattern matches known attack vectors. "
            "Manual review required before reactivation."
        )

        # Act: Update with detailed reason
        await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason=detailed_reason,
            updated_by="security_system"
        )

        # Assert: Reason is captured in audit
        history = await wallet_service.get_wallet_status_history(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id
        )

        assert len(history) >= 1
        event = history[0]

        assert event["reason"] == detailed_reason
        assert "authentication" in event["reason"]
        assert "review required" in event["reason"]

    @pytest.mark.asyncio
    async def test_tracks_multiple_status_changes_in_order(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN multiple status changes
        WHEN audit log is queried
        THEN all changes are recorded in chronological order
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_015"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="compliance"
        )

        wallet_id = wallet["wallet_id"]

        # Act: Multiple status changes
        await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="paused",
            reason="Routine maintenance",
            updated_by="system"
        )

        await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="active",
            reason="Maintenance complete",
            updated_by="system"
        )

        await wallet_service.update_wallet_status(
            wallet_id=wallet_id,
            project_id=test_project_id,
            new_status="frozen",
            reason="Compliance review initiated",
            updated_by="compliance_officer"
        )

        # Assert: All changes logged
        history = await wallet_service.get_wallet_status_history(
            wallet_id=wallet_id,
            project_id=test_project_id
        )

        assert len(history) >= 3

        # Verify sequence (most recent first)
        assert history[0]["new_status"] == "frozen"
        assert history[1]["new_status"] == "active"
        assert history[2]["new_status"] == "paused"


class TestTemporaryFreezeCapability:
    """Test temporary freeze with automatic unfreezing."""

    @pytest.mark.asyncio
    async def test_supports_frozen_until_timestamp(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a wallet with temporary freeze
        WHEN frozen_until timestamp is set
        THEN wallet is frozen with expiration time
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_016"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="transaction"
        )

        # Set freeze for 2 hours from now
        frozen_until = datetime.now(timezone.utc) + timedelta(hours=2)

        # Act: Freeze temporarily
        frozen_wallet = await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Temporary compliance hold",
            updated_by="compliance_system",
            frozen_until=frozen_until.isoformat()
        )

        # Assert: Freeze is temporary
        assert frozen_wallet["status"] == "frozen"
        assert "frozen_until" in frozen_wallet
        assert frozen_wallet["frozen_until"] == frozen_until.isoformat()

        # Verify frozen_until is in the future
        frozen_until_dt = datetime.fromisoformat(
            frozen_wallet["frozen_until"].replace("Z", "+00:00")
        )
        assert frozen_until_dt > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_auto_unfreezes_when_expired(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a wallet with expired frozen_until
        WHEN wallet is retrieved
        THEN status automatically updates to active
        """
        # Arrange: Create wallet with past freeze time
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_017"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="analyst"
        )

        # Freeze with past timestamp (1 hour ago)
        frozen_until = datetime.now(timezone.utc) - timedelta(hours=1)

        await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Temporary 1-hour freeze",
            updated_by="test_system",
            frozen_until=frozen_until.isoformat()
        )

        # Act: Retrieve wallet (should trigger auto-unfreeze)
        current_wallet = await wallet_service.get_wallet(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id
        )

        # Assert: Wallet is automatically active
        assert current_wallet["status"] == "active"
        assert current_wallet.get("frozen_until") is None

    @pytest.mark.asyncio
    async def test_blocks_transfer_during_temporary_freeze(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a temporarily frozen wallet
        WHEN attempting transfer
        THEN transfer is blocked even with future unfreeze time
        """
        # Arrange: Create wallets
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did_source = "did:key:test_agent_018"
        agent_did_dest = "did:key:test_agent_019"

        source_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_source,
            wallet_type="transaction"
        )

        dest_wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did_dest,
            wallet_type="transaction"
        )

        # Temporarily freeze source
        frozen_until = datetime.now(timezone.utc) + timedelta(hours=24)

        await wallet_service.update_wallet_status(
            wallet_id=source_wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="24-hour compliance hold",
            updated_by="compliance_system",
            frozen_until=frozen_until.isoformat()
        )

        # Act & Assert: Transfer blocked during freeze
        with pytest.raises(APIError) as exc_info:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source_wallet["wallet_id"],
                destination_wallet_id=dest_wallet["wallet_id"],
                amount="100.00"
            )

        assert exc_info.value.status_code == 403
        assert "frozen" in str(exc_info.value.detail).lower()


class TestWalletStatusEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_status_values(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a wallet
        WHEN invalid status is provided
        THEN validation error is raised
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_020"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="transaction"
        )

        # Act & Assert: Invalid status rejected
        with pytest.raises(APIError) as exc_info:
            await wallet_service.update_wallet_status(
                wallet_id=wallet["wallet_id"],
                project_id=test_project_id,
                new_status="invalid_status",
                reason="Testing validation",
                updated_by="test_system"
            )

        assert exc_info.value.status_code in [400, 422]
        assert "invalid" in str(exc_info.value.detail).lower() or "status" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_requires_reason_for_status_changes(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a wallet
        WHEN status change without reason
        THEN validation error is raised
        """
        # Arrange: Create wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        agent_did = "did:key:test_agent_021"

        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did=agent_did,
            wallet_type="compliance"
        )

        # Act & Assert: Reason is required
        with pytest.raises(APIError) as exc_info:
            await wallet_service.update_wallet_status(
                wallet_id=wallet["wallet_id"],
                project_id=test_project_id,
                new_status="frozen",
                reason="",  # Empty reason
                updated_by="test_system"
            )

        assert exc_info.value.status_code in [400, 422]
        assert "reason" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_handles_nonexistent_wallet_gracefully(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN a nonexistent wallet ID
        WHEN attempting status update
        THEN WalletNotFoundError is raised
        """
        # Arrange: Non-existent wallet
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        fake_wallet_id = "wallet_nonexistent"

        # Act & Assert: Wallet not found
        with pytest.raises(WalletNotFoundError):
            await wallet_service.update_wallet_status(
                wallet_id=fake_wallet_id,
                project_id=test_project_id,
                new_status="frozen",
                reason="Testing error handling",
                updated_by="test_system"
            )
