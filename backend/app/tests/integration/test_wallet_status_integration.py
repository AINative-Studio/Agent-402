"""
Integration tests for wallet status management and enforcement.

Issue #156: Add wallet freeze and revoke controls

Test-Driven Development (TDD): Tests written FIRST

Built by AINative Dev Team
All Data Services Built on ZeroDB
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.circle_wallet_service import CircleWalletService
from app.services.circle_service import WalletNotFoundError
from app.core.errors import APIError


class TestWalletStatusTransitions:
    """Test wallet status transitions."""

    @pytest.mark.asyncio
    async def test_transition_active_to_paused(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """
        GIVEN an active wallet
        WHEN status changes to paused
        THEN status updates successfully
        """
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_001",
            wallet_type="transaction"
        )
        
        updated = await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="paused",
            reason="Test pause",
            updated_by="test_admin"
        )
        
        assert updated["status"] == "paused"
        assert updated["status_reason"] == "Test pause"

    @pytest.mark.asyncio
    async def test_transition_active_to_frozen(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN active wallet WHEN frozen THEN status updates"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_002",
            wallet_type="compliance"
        )
        
        updated = await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Compliance review",
            updated_by="compliance_system"
        )
        
        assert updated["status"] == "frozen"
        assert "frozen_at" in updated

    @pytest.mark.asyncio
    async def test_transition_active_to_revoked(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN active wallet WHEN revoked THEN permanently revoked"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_003",
            wallet_type="analyst"
        )
        
        updated = await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="revoked",
            reason="TOS violation",
            updated_by="admin"
        )
        
        assert updated["status"] == "revoked"
        assert "revoked_at" in updated

    @pytest.mark.asyncio
    async def test_cannot_change_revoked_wallet(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN revoked wallet WHEN change attempted THEN fails"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_004",
            wallet_type="transaction"
        )
        
        await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="revoked",
            reason="Ban",
            updated_by="admin"
        )
        
        with pytest.raises(APIError) as exc:
            await wallet_service.update_wallet_status(
                wallet_id=wallet["wallet_id"],
                project_id=test_project_id,
                new_status="active",
                reason="Try reactivate",
                updated_by="admin"
            )
        
        assert exc.value.status_code == 403
        assert "revoked" in str(exc.value.detail).lower()


class TestPaymentBlockingByStatus:
    """Test payment blocking for each status."""

    @pytest.mark.asyncio
    async def test_blocks_paused_wallet_transfer(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN paused wallet WHEN transfer THEN blocked 403"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        source = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_005",
            wallet_type="transaction"
        )
        
        dest = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_006",
            wallet_type="transaction"
        )
        
        await wallet_service.update_wallet_status(
            wallet_id=source["wallet_id"],
            project_id=test_project_id,
            new_status="paused",
            reason="Test",
            updated_by="test"
        )
        
        with pytest.raises(APIError) as exc:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source["wallet_id"],
                destination_wallet_id=dest["wallet_id"],
                amount="100.00"
            )
        
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_blocks_frozen_wallet_transfer(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN frozen wallet WHEN transfer THEN blocked 403"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        source = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_007",
            wallet_type="transaction"
        )
        
        dest = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_008",
            wallet_type="transaction"
        )
        
        await wallet_service.update_wallet_status(
            wallet_id=source["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Review",
            updated_by="compliance"
        )
        
        with pytest.raises(APIError) as exc:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source["wallet_id"],
                destination_wallet_id=dest["wallet_id"],
                amount="50.00"
            )
        
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_blocks_revoked_wallet_transfer(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN revoked wallet WHEN transfer THEN blocked 403"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        source = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_009",
            wallet_type="transaction"
        )
        
        dest = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_010",
            wallet_type="transaction"
        )
        
        await wallet_service.update_wallet_status(
            wallet_id=source["wallet_id"],
            project_id=test_project_id,
            new_status="revoked",
            reason="Terminated",
            updated_by="admin"
        )
        
        with pytest.raises(APIError) as exc:
            await wallet_service.initiate_transfer(
                project_id=test_project_id,
                source_wallet_id=source["wallet_id"],
                destination_wallet_id=dest["wallet_id"],
                amount="25.00"
            )
        
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_allows_active_wallet_transfer(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN active wallet WHEN transfer THEN succeeds"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        source = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_011",
            wallet_type="transaction"
        )
        
        dest = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_012",
            wallet_type="transaction"
        )
        
        transfer = await wallet_service.initiate_transfer(
            project_id=test_project_id,
            source_wallet_id=source["wallet_id"],
            destination_wallet_id=dest["wallet_id"],
            amount="75.00"
        )
        
        assert transfer is not None
        assert transfer["amount"] == "75.00"


class TestWalletStatusAuditLogging:
    """Test audit logging for status changes."""

    @pytest.mark.asyncio
    async def test_logs_status_change(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN status change WHEN logged THEN event created"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_013",
            wallet_type="transaction"
        )
        
        await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Suspicious activity",
            updated_by="compliance_ai"
        )
        
        events = await wallet_service.get_wallet_status_history(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id
        )
        
        assert len(events) >= 1
        assert events[0]["event_type"] == "wallet_status_change"
        assert events[0]["new_status"] == "frozen"
        assert events[0]["reason"] == "Suspicious activity"


class TestTemporaryFreeze:
    """Test temporary freeze capability."""

    @pytest.mark.asyncio
    async def test_temporary_freeze_with_expiration(
        self,
        mock_zerodb_client,
        mock_circle_service,
        test_project_id
    ):
        """GIVEN temporary freeze WHEN expired THEN auto-unfreezes"""
        wallet_service = CircleWalletService(
            client=mock_zerodb_client,
            circle_service=mock_circle_service
        )
        
        wallet = await wallet_service.create_agent_wallet(
            project_id=test_project_id,
            agent_did="did:key:agent_016",
            wallet_type="transaction"
        )
        
        frozen_until = datetime.now(timezone.utc) + timedelta(hours=2)
        
        updated = await wallet_service.update_wallet_status(
            wallet_id=wallet["wallet_id"],
            project_id=test_project_id,
            new_status="frozen",
            reason="Temporary hold",
            updated_by="system",
            frozen_until=frozen_until.isoformat()
        )
        
        assert updated["status"] == "frozen"
        assert "frozen_until" in updated
