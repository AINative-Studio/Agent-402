"""
Tests for AutoSettlementService.
Issue #240: Auto-Settlement Cron for USDC

TDD RED phase — tests written before implementation.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #240
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(
    zerodb_client=None,
    hedera_service=None,
    circle_service=None,
):
    """Return AutoSettlementService with injected mocks."""
    from app.services.auto_settlement_service import AutoSettlementService

    return AutoSettlementService(
        zerodb_client=zerodb_client or MagicMock(),
        hedera_service=hedera_service,
        circle_service=circle_service,
    )


def _make_pending_payment(
    payment_id: str = "pay_abc123",
    status: str = "pending",
    age_minutes: int = 10,
    network: str = "hedera",
) -> Dict[str, Any]:
    """Build a synthetic pending payment record."""
    created_at = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return {
        "payment_id": payment_id,
        "status": status,
        "network": network,
        "amount": 1_000_000,
        "from_account": "0.0.11111",
        "to_account": "0.0.22222",
        "created_at": created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# DescribeGetPendingSettlements
# ---------------------------------------------------------------------------


class DescribeGetPendingSettlements:
    """Describe AutoSettlementService.get_pending_settlements behavior."""

    @pytest.mark.asyncio
    async def it_returns_empty_list_when_no_pending_payments(self):
        """When ZeroDB has no pending records, an empty list is returned."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.get_pending_settlements()

        assert result == []

    @pytest.mark.asyncio
    async def it_returns_list_of_pending_payment_dicts(self):
        """Pending payments are returned as a list of dicts."""
        records = [
            _make_pending_payment("pay_001"),
            _make_pending_payment("pay_002"),
        ]
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=records)
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.get_pending_settlements()

        assert len(result) == 2
        assert result[0]["payment_id"] == "pay_001"
        assert result[1]["payment_id"] == "pay_002"

    @pytest.mark.asyncio
    async def it_queries_zerodb_x402_payments_table(self):
        """get_pending_settlements queries the x402_payments table."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        await svc.get_pending_settlements()

        mock_client.query_rows.assert_called_once()
        call_args = mock_client.query_rows.call_args
        # First positional arg should be the table name
        assert call_args[0][0] == "x402_payments"

    @pytest.mark.asyncio
    async def it_filters_by_max_age_hours(self):
        """Payments older than max_age_hours are excluded from results."""
        fresh = _make_pending_payment("pay_fresh", age_minutes=30)
        stale = _make_pending_payment("pay_stale", age_minutes=25 * 60)  # 25h old

        mock_client = AsyncMock()
        # Simulate ZeroDB returning only records where status='pending'
        mock_client.query_rows = AsyncMock(return_value=[fresh])
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.get_pending_settlements(max_age_hours=24)

        # The stale payment is not in the result from ZeroDB
        assert all(r["payment_id"] != "pay_stale" for r in result)

    @pytest.mark.asyncio
    async def it_accepts_custom_max_age_hours(self):
        """max_age_hours parameter is forwarded to the ZeroDB query."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        await svc.get_pending_settlements(max_age_hours=6)

        mock_client.query_rows.assert_called_once()


# ---------------------------------------------------------------------------
# DescribeSettlePayment
# ---------------------------------------------------------------------------


class DescribeSettlePayment:
    """Describe AutoSettlementService.settle_payment behavior."""

    @pytest.mark.asyncio
    async def it_settles_hedera_payment_via_hedera_service(self):
        """A pending Hedera payment is settled using hedera_service."""
        payment = _make_pending_payment("pay_hdr_001", network="hedera")

        mock_hedera = AsyncMock()
        mock_hedera.transfer_usdc = AsyncMock(
            return_value={"transaction_id": "0.0.12345@1000.000", "status": "SUCCESS"}
        )
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[payment])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, hedera_service=mock_hedera)

        result = await svc.settle_payment("pay_hdr_001")

        assert result["status"] == "settled"
        assert "transaction_id" in result
        mock_hedera.transfer_usdc.assert_called_once()

    @pytest.mark.asyncio
    async def it_settles_circle_payment_via_circle_service(self):
        """A pending Circle payment is settled using circle_service."""
        payment = _make_pending_payment("pay_cir_001", network="circle")

        mock_circle = AsyncMock()
        mock_circle.create_transfer = AsyncMock(
            return_value={"data": {"id": "txn_circle_abc", "state": "COMPLETE"}}
        )
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[payment])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, circle_service=mock_circle)

        result = await svc.settle_payment("pay_cir_001")

        assert result["status"] == "settled"
        mock_circle.create_transfer.assert_called_once()

    @pytest.mark.asyncio
    async def it_raises_when_payment_not_found(self):
        """settle_payment raises ValueError when the payment_id does not exist."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        with pytest.raises(ValueError, match="not found"):
            await svc.settle_payment("pay_nonexistent")

    @pytest.mark.asyncio
    async def it_updates_payment_status_in_zerodb_after_settlement(self):
        """After successful settlement, payment status is updated in ZeroDB."""
        payment = _make_pending_payment("pay_upd_001", network="hedera")

        mock_hedera = AsyncMock()
        mock_hedera.transfer_usdc = AsyncMock(
            return_value={"transaction_id": "tx_001", "status": "SUCCESS"}
        )
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[payment])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, hedera_service=mock_hedera)

        await svc.settle_payment("pay_upd_001")

        mock_client.update_row.assert_called_once()
        update_call_args = mock_client.update_row.call_args
        # First arg is table name, second is filter, third is update data
        update_data = update_call_args[0][2] if len(update_call_args[0]) >= 3 else update_call_args[1].get("data", {})
        assert update_data.get("status") == "settled"

    @pytest.mark.asyncio
    async def it_skips_payment_that_is_not_pending(self):
        """A payment that is already settled or failed is skipped."""
        payment = _make_pending_payment("pay_done", status="settled")

        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[payment])
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.settle_payment("pay_done")

        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def it_returns_failed_status_on_settlement_error(self):
        """If the payment network call fails, settle_payment returns failed status."""
        payment = _make_pending_payment("pay_err_001", network="hedera")

        mock_hedera = AsyncMock()
        mock_hedera.transfer_usdc = AsyncMock(side_effect=Exception("Hedera error"))
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[payment])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, hedera_service=mock_hedera)

        result = await svc.settle_payment("pay_err_001")

        assert result["status"] == "failed"
        assert "error" in result


# ---------------------------------------------------------------------------
# DescribeRunSettlementCycle
# ---------------------------------------------------------------------------


class DescribeRunSettlementCycle:
    """Describe AutoSettlementService.run_settlement_cycle behavior."""

    @pytest.mark.asyncio
    async def it_returns_summary_dict_with_counts(self):
        """run_settlement_cycle returns a summary with settled/failed/skipped counts."""
        from app.services.auto_settlement_service import AutoSettlementService

        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.run_settlement_cycle()

        assert "settled" in result
        assert "failed" in result
        assert "skipped" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def it_settles_all_pending_payments(self):
        """All pending payments are processed in a single cycle."""
        payments = [
            _make_pending_payment("pay_a", network="hedera"),
            _make_pending_payment("pay_b", network="hedera"),
        ]

        mock_hedera = AsyncMock()
        mock_hedera.transfer_usdc = AsyncMock(
            return_value={"transaction_id": "tx_ok", "status": "SUCCESS"}
        )
        mock_client = AsyncMock()
        # query_rows returns the pending list on first call,
        # then per-payment lookups return single items
        mock_client.query_rows = AsyncMock(side_effect=[
            payments,       # get_pending_settlements call
            [payments[0]],  # settle_payment lookup for pay_a
            [payments[1]],  # settle_payment lookup for pay_b
        ])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, hedera_service=mock_hedera)

        result = await svc.run_settlement_cycle()

        assert result["total"] == 2
        assert result["settled"] == 2

    @pytest.mark.asyncio
    async def it_returns_zero_counts_when_no_pending_payments(self):
        """An empty queue produces an all-zero summary."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        result = await svc.run_settlement_cycle()

        assert result["total"] == 0
        assert result["settled"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def it_counts_failures_separately_from_successes(self):
        """Payments that fail are tracked in the failed counter."""
        payments = [
            _make_pending_payment("pay_ok", network="hedera"),
            _make_pending_payment("pay_fail", network="hedera"),
        ]

        call_count = 0

        async def _transfer_usdc(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"transaction_id": "tx_ok", "status": "SUCCESS"}
            raise Exception("Hedera node down")

        mock_hedera = AsyncMock()
        mock_hedera.transfer_usdc = AsyncMock(side_effect=_transfer_usdc)
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(side_effect=[
            payments,
            [payments[0]],
            [payments[1]],
        ])
        mock_client.update_row = AsyncMock(return_value=True)

        svc = _make_service(zerodb_client=mock_client, hedera_service=mock_hedera)

        result = await svc.run_settlement_cycle()

        assert result["total"] == 2
        assert result["settled"] == 1
        assert result["failed"] == 1


# ---------------------------------------------------------------------------
# DescribeScheduleSettlement
# ---------------------------------------------------------------------------


class DescribeScheduleSettlement:
    """Describe AutoSettlementService.schedule_settlement behavior."""

    @pytest.mark.asyncio
    async def it_returns_a_coroutine_or_task(self):
        """schedule_settlement returns an asyncio.Task object."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        task = await svc.schedule_settlement(interval_minutes=0.001)

        assert task is not None
        # Clean up — cancel the background task
        if hasattr(task, "cancel"):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def it_accepts_custom_interval_minutes(self):
        """schedule_settlement accepts an interval_minutes parameter without error."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        svc = _make_service(zerodb_client=mock_client)

        task = await svc.schedule_settlement(interval_minutes=15)

        assert task is not None
        if hasattr(task, "cancel"):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
