"""
Tests for NonceReplayGuard and NonceMiddleware.
Issue #242: Replay Prevention via Nonces

TDD RED phase — tests written before implementation.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #242
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_guard(zerodb_client=None):
    """Return NonceReplayGuard with injected mocks."""
    from app.services.nonce_replay_guard import NonceReplayGuard

    return NonceReplayGuard(zerodb_client=zerodb_client or AsyncMock())


def _fresh_nonce() -> str:
    """Return a valid UUID v4 nonce string."""
    return str(uuid.uuid4())


def _now_ts() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _stale_ts(minutes: int = 10) -> str:
    """Return a timestamp that is `minutes` old."""
    stale = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return stale.isoformat()


def _future_ts(minutes: int = 10) -> str:
    """Return a timestamp `minutes` in the future."""
    future = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return future.isoformat()


# ---------------------------------------------------------------------------
# DescribeValidateRequest
# ---------------------------------------------------------------------------


class DescribeValidateRequest:
    """Describe NonceReplayGuard.validate_request behavior."""

    @pytest.mark.asyncio
    async def it_accepts_a_fresh_unique_nonce(self):
        """A valid UUID nonce with a current timestamp passes validation."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])  # no existing nonce
        guard = _make_guard(zerodb_client=mock_client)

        result = await guard.validate_request(
            nonce=_fresh_nonce(),
            timestamp=_now_ts(),
            did="did:hedera:testnet:agent-1",
        )

        assert result is True

    @pytest.mark.asyncio
    async def it_raises_on_duplicate_nonce_for_same_did(self):
        """A nonce already used by the same DID is rejected as replay."""
        from app.services.nonce_replay_guard import ReplayAttackError

        existing_nonce = _fresh_nonce()
        existing_record = {
            "nonce": existing_nonce,
            "did": "did:hedera:testnet:agent-1",
            "timestamp": _now_ts(),
        }
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[existing_record])
        guard = _make_guard(zerodb_client=mock_client)

        with pytest.raises(ReplayAttackError):
            await guard.validate_request(
                nonce=existing_nonce,
                timestamp=_now_ts(),
                did="did:hedera:testnet:agent-1",
            )

    @pytest.mark.asyncio
    async def it_raises_on_stale_timestamp_older_than_5_minutes(self):
        """A timestamp older than 5 minutes is rejected."""
        from app.services.nonce_replay_guard import StaleRequestError

        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        with pytest.raises(StaleRequestError):
            await guard.validate_request(
                nonce=_fresh_nonce(),
                timestamp=_stale_ts(minutes=6),
                did="did:hedera:testnet:agent-1",
            )

    @pytest.mark.asyncio
    async def it_accepts_timestamp_exactly_at_5_minute_boundary(self):
        """A timestamp exactly 5 minutes old is accepted (boundary inclusive)."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        # 4m59s ago — just inside the window
        ts = (datetime.now(timezone.utc) - timedelta(minutes=4, seconds=59)).isoformat()

        result = await guard.validate_request(
            nonce=_fresh_nonce(),
            timestamp=ts,
            did="did:hedera:testnet:agent-1",
        )

        assert result is True

    @pytest.mark.asyncio
    async def it_raises_on_non_uuid_nonce_format(self):
        """A nonce that is not a UUID v4 string is rejected with InvalidNonceError."""
        from app.services.nonce_replay_guard import InvalidNonceError

        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        with pytest.raises(InvalidNonceError):
            await guard.validate_request(
                nonce="not-a-uuid",
                timestamp=_now_ts(),
                did="did:hedera:testnet:agent-1",
            )

    @pytest.mark.asyncio
    async def it_allows_same_nonce_for_different_dids(self):
        """The same nonce used by a different DID is accepted (per-DID uniqueness)."""
        nonce = _fresh_nonce()
        existing_record = {
            "nonce": nonce,
            "did": "did:hedera:testnet:agent-OTHER",
            "timestamp": _now_ts(),
        }
        mock_client = AsyncMock()
        # ZeroDB returns no match for the requesting DID's nonce
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        result = await guard.validate_request(
            nonce=nonce,
            timestamp=_now_ts(),
            did="did:hedera:testnet:agent-1",
        )

        assert result is True

    @pytest.mark.asyncio
    async def it_raises_on_future_timestamp_beyond_5_minutes(self):
        """A timestamp more than 5 minutes in the future is rejected."""
        from app.services.nonce_replay_guard import StaleRequestError

        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        with pytest.raises(StaleRequestError):
            await guard.validate_request(
                nonce=_fresh_nonce(),
                timestamp=_future_ts(minutes=6),
                did="did:hedera:testnet:agent-1",
            )


# ---------------------------------------------------------------------------
# DescribeRecordNonce
# ---------------------------------------------------------------------------


class DescribeRecordNonce:
    """Describe NonceReplayGuard.record_nonce behavior."""

    @pytest.mark.asyncio
    async def it_inserts_nonce_into_zerodb(self):
        """record_nonce stores the nonce, DID, and timestamp in ZeroDB."""
        mock_client = AsyncMock()
        mock_client.insert_row = AsyncMock(return_value={"id": "row_001"})
        guard = _make_guard(zerodb_client=mock_client)

        nonce = _fresh_nonce()
        did = "did:hedera:testnet:agent-1"
        ts = _now_ts()

        await guard.record_nonce(nonce=nonce, did=did, timestamp=ts)

        mock_client.insert_row.assert_called_once()
        call_args = mock_client.insert_row.call_args
        table = call_args[0][0]
        record = call_args[0][1]
        assert table == "x402_nonces"
        assert record["nonce"] == nonce
        assert record["did"] == did

    @pytest.mark.asyncio
    async def it_stores_nonce_in_x402_nonces_table(self):
        """record_nonce always writes to the x402_nonces table."""
        mock_client = AsyncMock()
        mock_client.insert_row = AsyncMock(return_value={"id": "row_002"})
        guard = _make_guard(zerodb_client=mock_client)

        await guard.record_nonce(
            nonce=_fresh_nonce(),
            did="did:hedera:testnet:agent-x",
            timestamp=_now_ts(),
        )

        call_args = mock_client.insert_row.call_args
        assert call_args[0][0] == "x402_nonces"

    @pytest.mark.asyncio
    async def it_includes_timestamp_in_stored_record(self):
        """The stored record includes the provided timestamp."""
        mock_client = AsyncMock()
        mock_client.insert_row = AsyncMock(return_value={"id": "row_003"})
        guard = _make_guard(zerodb_client=mock_client)

        ts = _now_ts()
        await guard.record_nonce(
            nonce=_fresh_nonce(),
            did="did:hedera:testnet:agent-1",
            timestamp=ts,
        )

        call_args = mock_client.insert_row.call_args
        record = call_args[0][1]
        assert record["timestamp"] == ts


# ---------------------------------------------------------------------------
# DescribeCleanupExpiredNonces
# ---------------------------------------------------------------------------


class DescribeCleanupExpiredNonces:
    """Describe NonceReplayGuard.cleanup_expired_nonces behavior."""

    @pytest.mark.asyncio
    async def it_returns_count_of_deleted_nonces(self):
        """cleanup_expired_nonces returns an integer count of removed records."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[
            {"id": "n1", "nonce": "aaa", "timestamp": _stale_ts(25 * 60)},
            {"id": "n2", "nonce": "bbb", "timestamp": _stale_ts(26 * 60)},
        ])
        mock_client.delete_row = AsyncMock(return_value=True)
        guard = _make_guard(zerodb_client=mock_client)

        count = await guard.cleanup_expired_nonces(max_age_hours=24)

        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def it_deletes_nonces_older_than_max_age_hours(self):
        """Nonces older than max_age_hours are pruned from ZeroDB."""
        stale_records = [
            {"id": "old1", "nonce": "aaa", "timestamp": _stale_ts(25 * 60)},
        ]
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=stale_records)
        mock_client.delete_row = AsyncMock(return_value=True)
        guard = _make_guard(zerodb_client=mock_client)

        count = await guard.cleanup_expired_nonces(max_age_hours=24)

        assert count == 1
        mock_client.delete_row.assert_called_once()

    @pytest.mark.asyncio
    async def it_returns_zero_when_no_expired_nonces(self):
        """Returns 0 when all nonces are within max_age_hours."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        mock_client.delete_row = AsyncMock(return_value=True)
        guard = _make_guard(zerodb_client=mock_client)

        count = await guard.cleanup_expired_nonces(max_age_hours=24)

        assert count == 0

    @pytest.mark.asyncio
    async def it_accepts_custom_max_age_hours(self):
        """cleanup_expired_nonces works with non-default max_age_hours values."""
        mock_client = AsyncMock()
        mock_client.query_rows = AsyncMock(return_value=[])
        guard = _make_guard(zerodb_client=mock_client)

        count = await guard.cleanup_expired_nonces(max_age_hours=48)

        assert count == 0


# ---------------------------------------------------------------------------
# DescribeNonceMiddleware
# ---------------------------------------------------------------------------


class DescribeNonceMiddleware:
    """Describe NonceMiddleware HTTP middleware behavior."""

    def _make_request(
        self,
        path: str = "/x402",
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ):
        """Build a minimal mock Request object."""
        mock_request = MagicMock()
        mock_request.url.path = path
        mock_request.method = method
        mock_request.headers = headers or {}

        async def _json():
            return body or {}

        mock_request.json = _json
        return mock_request

    @pytest.mark.asyncio
    async def it_passes_through_non_x402_paths(self):
        """Non-x402 paths bypass nonce validation entirely."""
        from app.middleware.nonce_middleware import NonceMiddleware

        mock_guard = AsyncMock()
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(path="/health")

        await middleware.dispatch(request, mock_call_next)

        mock_guard.validate_request.assert_not_called()
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def it_passes_through_get_requests_on_x402_path(self):
        """GET requests to /x402 are not nonce-checked (nonces apply to POST only)."""
        from app.middleware.nonce_middleware import NonceMiddleware

        mock_guard = AsyncMock()
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(path="/x402", method="GET")

        await middleware.dispatch(request, mock_call_next)

        mock_guard.validate_request.assert_not_called()

    @pytest.mark.asyncio
    async def it_calls_validate_request_for_x402_post(self):
        """POST to /x402 with a valid nonce calls validate_request."""
        from app.middleware.nonce_middleware import NonceMiddleware

        nonce = _fresh_nonce()
        ts = _now_ts()
        did = "did:hedera:testnet:agent-1"

        mock_guard = AsyncMock()
        mock_guard.validate_request = AsyncMock(return_value=True)
        mock_guard.record_nonce = AsyncMock(return_value=None)
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(
            path="/x402",
            method="POST",
            body={"nonce": nonce, "timestamp": ts, "did": did},
        )

        await middleware.dispatch(request, mock_call_next)

        mock_guard.validate_request.assert_called_once_with(
            nonce=nonce, timestamp=ts, did=did
        )

    @pytest.mark.asyncio
    async def it_returns_409_on_replay_attack(self):
        """Replayed nonces produce a 409 Conflict response."""
        from app.middleware.nonce_middleware import NonceMiddleware
        from app.services.nonce_replay_guard import ReplayAttackError
        from fastapi.responses import JSONResponse

        nonce = _fresh_nonce()
        mock_guard = AsyncMock()
        mock_guard.validate_request = AsyncMock(
            side_effect=ReplayAttackError(nonce=nonce, did="did:hedera:testnet:agent-1")
        )
        mock_call_next = AsyncMock()

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(
            path="/x402",
            method="POST",
            body={"nonce": nonce, "timestamp": _now_ts(), "did": "did:hedera:testnet:agent-1"},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 409
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def it_returns_400_on_stale_timestamp(self):
        """A stale timestamp produces a 400 Bad Request response."""
        from app.middleware.nonce_middleware import NonceMiddleware
        from app.services.nonce_replay_guard import StaleRequestError
        from fastapi.responses import JSONResponse

        nonce = _fresh_nonce()
        mock_guard = AsyncMock()
        mock_guard.validate_request = AsyncMock(
            side_effect=StaleRequestError(timestamp=_stale_ts(10))
        )
        mock_call_next = AsyncMock()

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(
            path="/x402",
            method="POST",
            body={"nonce": nonce, "timestamp": _stale_ts(10), "did": "did:hedera:testnet:agent-1"},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 400
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def it_records_nonce_after_successful_validation(self):
        """After a request passes validation, record_nonce is called."""
        from app.middleware.nonce_middleware import NonceMiddleware

        nonce = _fresh_nonce()
        ts = _now_ts()
        did = "did:hedera:testnet:agent-1"

        mock_guard = AsyncMock()
        mock_guard.validate_request = AsyncMock(return_value=True)
        mock_guard.record_nonce = AsyncMock(return_value=None)
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(
            path="/x402",
            method="POST",
            body={"nonce": nonce, "timestamp": ts, "did": did},
        )

        await middleware.dispatch(request, mock_call_next)

        mock_guard.record_nonce.assert_called_once_with(
            nonce=nonce, did=did, timestamp=ts
        )

    @pytest.mark.asyncio
    async def it_passes_through_when_nonce_field_absent(self):
        """Requests without a nonce field bypass nonce validation gracefully."""
        from app.middleware.nonce_middleware import NonceMiddleware

        mock_guard = AsyncMock()
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = NonceMiddleware(app=MagicMock(), guard=mock_guard)
        request = self._make_request(
            path="/x402",
            method="POST",
            body={"did": "did:hedera:testnet:agent-1"},  # no nonce
        )

        await middleware.dispatch(request, mock_call_next)

        mock_guard.validate_request.assert_not_called()
        mock_call_next.assert_called_once()
