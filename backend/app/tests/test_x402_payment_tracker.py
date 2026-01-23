"""
Tests for X402 Payment Tracker Service.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

TDD: These tests are written FIRST, implementation follows.

Per PRD Section 8 (X402 Protocol):
- Payment receipts stored in ZeroDB
- Linked to Arc blockchain transactions
- USDC transaction tracking

Per Testing Requirements:
- BDD-style tests (describe/it pattern)
- 80%+ test coverage required
- All tests must pass before merge
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.schemas.payment_tracking import (
    PaymentStatus,
    PaymentReceipt,
    PaymentReceiptCreate
)


# ============================================================================
# Describe: X402PaymentTracker Service
# ============================================================================

class TestX402PaymentTrackerService:
    """Test suite for X402PaymentTracker service."""

    # ------------------------------------------------------------------------
    # Describe: create_payment_receipt
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_create_payment_receipt_with_valid_data(
        self,
        mock_zerodb_client
    ):
        """It should create a payment receipt with valid input data."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_abc123",
            from_agent_id="agent_001",
            to_agent_id="agent_002",
            amount_usdc="10.000000",
            purpose="x402-api-call",
            metadata={"task_id": "task_xyz"}
        )

        result = await tracker.create_payment_receipt(
            project_id="test_project",
            receipt_data=receipt_data
        )

        # Verify receipt was created
        assert result is not None
        assert result["receipt_id"].startswith("pay_rcpt_")
        assert result["x402_request_id"] == "x402_req_abc123"
        assert result["from_agent_id"] == "agent_001"
        assert result["to_agent_id"] == "agent_002"
        assert result["amount_usdc"] == "10.000000"
        assert result["status"] == PaymentStatus.PENDING.value
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_it_should_generate_unique_receipt_ids(
        self,
        mock_zerodb_client
    ):
        """It should generate unique receipt IDs for each payment."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_abc123",
            from_agent_id="agent_001",
            to_agent_id="agent_002",
            amount_usdc="5.000000",
            purpose="task-completion"
        )

        # Create multiple receipts
        receipt1 = await tracker.create_payment_receipt("proj1", receipt_data)
        receipt2 = await tracker.create_payment_receipt("proj1", receipt_data)

        # Receipt IDs should be unique
        assert receipt1["receipt_id"] != receipt2["receipt_id"]

    # ------------------------------------------------------------------------
    # Describe: get_payment_receipt
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_get_payment_receipt_by_id(
        self,
        mock_zerodb_client
    ):
        """It should retrieve a payment receipt by its ID."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # First create a receipt
        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_get_test",
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            amount_usdc="25.000000",
            purpose="hire-agent"
        )

        created = await tracker.create_payment_receipt("test_proj", receipt_data)
        receipt_id = created["receipt_id"]

        # Now retrieve it
        retrieved = await tracker.get_payment_receipt(
            project_id="test_proj",
            receipt_id=receipt_id
        )

        assert retrieved is not None
        assert retrieved["receipt_id"] == receipt_id
        assert retrieved["amount_usdc"] == "25.000000"

    @pytest.mark.asyncio
    async def test_it_should_raise_error_for_nonexistent_receipt(
        self,
        mock_zerodb_client
    ):
        """It should raise PaymentReceiptNotFoundError for missing receipt."""
        from app.services.x402_payment_tracker import (
            X402PaymentTracker,
            PaymentReceiptNotFoundError
        )

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        with pytest.raises(PaymentReceiptNotFoundError):
            await tracker.get_payment_receipt(
                project_id="test_proj",
                receipt_id="nonexistent_receipt_id"
            )

    # ------------------------------------------------------------------------
    # Describe: update_payment_status
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_update_payment_status_to_confirmed(
        self,
        mock_zerodb_client
    ):
        """It should update payment status from pending to confirmed."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # Create a receipt first
        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_status_test",
            from_agent_id="agent_x",
            to_agent_id="agent_y",
            amount_usdc="100.000000",
            purpose="large-task"
        )

        created = await tracker.create_payment_receipt("proj_status", receipt_data)

        # Update status
        updated = await tracker.update_payment_status(
            project_id="proj_status",
            receipt_id=created["receipt_id"],
            status=PaymentStatus.CONFIRMED,
            transaction_hash="0xabc123def456789",
            arc_payment_id=42
        )

        assert updated["status"] == PaymentStatus.CONFIRMED.value
        assert updated["transaction_hash"] == "0xabc123def456789"
        assert updated["arc_payment_id"] == 42
        assert updated["confirmed_at"] is not None

    @pytest.mark.asyncio
    async def test_it_should_update_payment_status_to_failed(
        self,
        mock_zerodb_client
    ):
        """It should update payment status to failed with error info."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_fail_test",
            from_agent_id="agent_1",
            to_agent_id="agent_2",
            amount_usdc="50.000000",
            purpose="test-task"
        )

        created = await tracker.create_payment_receipt("proj_fail", receipt_data)

        updated = await tracker.update_payment_status(
            project_id="proj_fail",
            receipt_id=created["receipt_id"],
            status=PaymentStatus.FAILED,
            error_message="Insufficient balance in treasury"
        )

        assert updated["status"] == PaymentStatus.FAILED.value
        assert updated["metadata"]["error_message"] == "Insufficient balance in treasury"

    # ------------------------------------------------------------------------
    # Describe: list_payment_receipts
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_list_receipts_for_project(
        self,
        mock_zerodb_client
    ):
        """It should list all payment receipts for a project."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # Create multiple receipts
        for i in range(3):
            receipt_data = PaymentReceiptCreate(
                x402_request_id=f"x402_req_list_{i}",
                from_agent_id="agent_sender",
                to_agent_id=f"agent_receiver_{i}",
                amount_usdc=f"{(i + 1) * 10}.000000",
                purpose="list-test"
            )
            await tracker.create_payment_receipt("proj_list", receipt_data)

        # List receipts
        receipts, total = await tracker.list_payment_receipts(
            project_id="proj_list"
        )

        assert total == 3
        assert len(receipts) == 3

    @pytest.mark.asyncio
    async def test_it_should_filter_receipts_by_agent_id(
        self,
        mock_zerodb_client
    ):
        """It should filter receipts by from_agent_id or to_agent_id."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # Create receipts with different agents
        receipt1 = PaymentReceiptCreate(
            x402_request_id="x402_req_filter_1",
            from_agent_id="agent_alpha",
            to_agent_id="agent_beta",
            amount_usdc="20.000000",
            purpose="filter-test"
        )
        receipt2 = PaymentReceiptCreate(
            x402_request_id="x402_req_filter_2",
            from_agent_id="agent_gamma",
            to_agent_id="agent_beta",
            amount_usdc="30.000000",
            purpose="filter-test"
        )

        await tracker.create_payment_receipt("proj_filter", receipt1)
        await tracker.create_payment_receipt("proj_filter", receipt2)

        # Filter by from_agent_id
        receipts, _ = await tracker.list_payment_receipts(
            project_id="proj_filter",
            from_agent_id="agent_alpha"
        )

        assert len(receipts) == 1
        assert receipts[0]["from_agent_id"] == "agent_alpha"

    @pytest.mark.asyncio
    async def test_it_should_filter_receipts_by_status(
        self,
        mock_zerodb_client
    ):
        """It should filter receipts by payment status."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # Create and update receipts with different statuses
        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_status_filter",
            from_agent_id="agent_1",
            to_agent_id="agent_2",
            amount_usdc="15.000000",
            purpose="status-filter-test"
        )

        created = await tracker.create_payment_receipt("proj_status_filter", receipt_data)

        # Update one to confirmed
        await tracker.update_payment_status(
            project_id="proj_status_filter",
            receipt_id=created["receipt_id"],
            status=PaymentStatus.CONFIRMED
        )

        # Create another pending receipt
        receipt_data2 = PaymentReceiptCreate(
            x402_request_id="x402_req_status_filter_2",
            from_agent_id="agent_3",
            to_agent_id="agent_4",
            amount_usdc="25.000000",
            purpose="status-filter-test-2"
        )
        await tracker.create_payment_receipt("proj_status_filter", receipt_data2)

        # Filter by status
        confirmed_receipts, _ = await tracker.list_payment_receipts(
            project_id="proj_status_filter",
            status=PaymentStatus.CONFIRMED
        )

        assert len(confirmed_receipts) == 1
        assert confirmed_receipts[0]["status"] == PaymentStatus.CONFIRMED.value

    # ------------------------------------------------------------------------
    # Describe: link_to_arc_blockchain
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_link_receipt_to_arc_payment(
        self,
        mock_zerodb_client
    ):
        """It should link payment receipt to Arc blockchain payment ID."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        receipt_data = PaymentReceiptCreate(
            x402_request_id="x402_req_arc_link",
            from_agent_id="agent_arc_1",
            to_agent_id="agent_arc_2",
            amount_usdc="75.000000",
            purpose="arc-link-test"
        )

        created = await tracker.create_payment_receipt("proj_arc", receipt_data)

        # Link to Arc payment
        linked = await tracker.link_to_arc_payment(
            project_id="proj_arc",
            receipt_id=created["receipt_id"],
            arc_payment_id=123,
            treasury_from_id=1,
            treasury_to_id=2
        )

        assert linked["arc_payment_id"] == 123
        assert linked["treasury_from_id"] == 1
        assert linked["treasury_to_id"] == 2

    # ------------------------------------------------------------------------
    # Describe: get_receipts_by_x402_request
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_it_should_get_receipts_by_x402_request_id(
        self,
        mock_zerodb_client
    ):
        """It should retrieve all receipts linked to an X402 request."""
        from app.services.x402_payment_tracker import X402PaymentTracker

        tracker = X402PaymentTracker(client=mock_zerodb_client)

        # Create receipts linked to same X402 request
        x402_id = "x402_req_linked_multi"

        for i in range(2):
            receipt_data = PaymentReceiptCreate(
                x402_request_id=x402_id,
                from_agent_id=f"agent_from_{i}",
                to_agent_id=f"agent_to_{i}",
                amount_usdc=f"{(i + 1) * 5}.000000",
                purpose="x402-link-test"
            )
            await tracker.create_payment_receipt("proj_x402_link", receipt_data)

        # Get receipts by X402 request ID
        receipts = await tracker.get_receipts_by_x402_request(
            project_id="proj_x402_link",
            x402_request_id=x402_id
        )

        assert len(receipts) == 2
        for receipt in receipts:
            assert receipt["x402_request_id"] == x402_id


# ============================================================================
# Describe: Payment Receipt Schema Validation
# ============================================================================

class TestPaymentReceiptSchemas:
    """Test suite for payment receipt schema validation."""

    def test_it_should_validate_payment_receipt_create_schema(self):
        """It should validate PaymentReceiptCreate with required fields."""
        receipt = PaymentReceiptCreate(
            x402_request_id="x402_req_schema_test",
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            amount_usdc="100.000000",
            purpose="schema-validation"
        )

        assert receipt.x402_request_id == "x402_req_schema_test"
        assert receipt.amount_usdc == "100.000000"
        assert receipt.metadata is None

    def test_it_should_include_optional_metadata(self):
        """It should include optional metadata in receipt."""
        receipt = PaymentReceiptCreate(
            x402_request_id="x402_req_metadata_test",
            from_agent_id="agent_1",
            to_agent_id="agent_2",
            amount_usdc="50.000000",
            purpose="metadata-test",
            metadata={"custom_field": "custom_value"}
        )

        assert receipt.metadata == {"custom_field": "custom_value"}

    def test_it_should_validate_payment_status_enum(self):
        """It should validate PaymentStatus enumeration values."""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.CONFIRMED.value == "confirmed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.REFUNDED.value == "refunded"
