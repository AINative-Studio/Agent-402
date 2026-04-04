"""
Nonce Replay Guard Service.
Issue #242: Replay Prevention via Nonces

Validates nonces for uniqueness per DID and timestamp freshness to prevent
replay attacks on x402 signed requests.

ZeroDB table: x402_nonces

Validation rules:
- Nonce must be a valid UUID v4 string.
- Nonce must be unique per DID (reject duplicates = replay attack).
- Timestamp must be within 5 minutes of server time (reject stale requests).

Built by AINative Dev Team
Refs #242
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ZeroDB table that stores used nonces
NONCES_TABLE = "x402_nonces"

# Maximum allowed age/skew for request timestamps (in minutes)
MAX_TIMESTAMP_DRIFT_MINUTES = 5


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ReplayAttackError(Exception):
    """
    Raised when a nonce has already been used by the same DID.

    This indicates a replay attack — the same signed request is being
    resubmitted.  The middleware returns HTTP 409 Conflict.
    """

    def __init__(self, nonce: str, did: str) -> None:
        self.nonce = nonce
        self.did = did
        super().__init__(
            f"Replay attack detected: nonce '{nonce}' already used by DID '{did}'."
        )


class StaleRequestError(Exception):
    """
    Raised when the request timestamp is outside the acceptable window.

    The middleware returns HTTP 400 Bad Request.
    """

    def __init__(self, timestamp: str) -> None:
        self.timestamp = timestamp
        super().__init__(
            f"Request timestamp '{timestamp}' is outside the "
            f"{MAX_TIMESTAMP_DRIFT_MINUTES}-minute acceptance window."
        )


class InvalidNonceError(Exception):
    """
    Raised when the nonce is not a valid UUID v4 string.

    The middleware returns HTTP 400 Bad Request.
    """

    def __init__(self, nonce: str) -> None:
        self.nonce = nonce
        super().__init__(
            f"Invalid nonce format '{nonce}'. "
            f"Nonce must be a UUID v4 string (e.g., '550e8400-e29b-41d4-a716-446655440000')."
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class NonceReplayGuard:
    """
    Guards against replayed x402 requests by tracking used nonces in ZeroDB.

    Per-DID nonce uniqueness ensures that even if a signed request is
    intercepted it cannot be replayed.  Timestamp freshness prevents
    pre-recorded requests from being submitted later.
    """

    def __init__(self, zerodb_client: Optional[Any] = None) -> None:
        """
        Initialise the guard.

        Args:
            zerodb_client: Injected ZeroDB client (for testing / DI).
        """
        self._zerodb_client = zerodb_client

    @property
    def zerodb_client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._zerodb_client is None:
            from app.services.zerodb_client import get_zerodb_client
            self._zerodb_client = get_zerodb_client()
        return self._zerodb_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def validate_request(
        self,
        nonce: str,
        timestamp: str,
        did: str,
    ) -> bool:
        """
        Validate that a request nonce is unique and its timestamp is fresh.

        Steps performed:
        1. Validate nonce is a UUID v4 string.
        2. Validate timestamp is within ±5 minutes of now.
        3. Query ZeroDB for existing nonce+did combination.
        4. Reject if a matching record exists (replay).

        Args:
            nonce: UUID v4 nonce string from the request.
            timestamp: ISO 8601 timestamp string from the request.
            did: DID of the agent making the request.

        Returns:
            True when the request is valid.

        Raises:
            InvalidNonceError: Nonce is not a valid UUID v4.
            StaleRequestError: Timestamp is outside the 5-minute window.
            ReplayAttackError: This nonce has already been used by this DID.
        """
        self._validate_nonce_format(nonce)
        self._validate_timestamp(timestamp)
        await self._check_uniqueness(nonce, did)
        return True

    async def record_nonce(
        self,
        nonce: str,
        did: str,
        timestamp: str,
    ) -> None:
        """
        Persist a used nonce to ZeroDB to prevent future replays.

        Should be called after a request has passed validation and been
        processed.

        Args:
            nonce: The UUID v4 nonce that was used.
            did: The DID of the agent.
            timestamp: The ISO 8601 timestamp from the request.
        """
        record = {
            "nonce": nonce,
            "did": did,
            "timestamp": timestamp,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.zerodb_client.insert_row(NONCES_TABLE, record)
        logger.debug(f"Recorded nonce for DID {did}: {nonce}")

    async def cleanup_expired_nonces(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """
        Prune nonces older than max_age_hours from ZeroDB.

        Args:
            max_age_hours: Age threshold in hours. Nonces older than this
                           are deleted. Defaults to 24 hours.

        Returns:
            Count of deleted nonce records.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cutoff_iso = cutoff.isoformat()

        logger.info(
            f"Cleaning up nonces older than {max_age_hours}h (cutoff={cutoff_iso})."
        )

        expired = await self.zerodb_client.query_rows(
            NONCES_TABLE,
            {"timestamp_before": cutoff_iso},
        )

        deleted = 0
        for record in expired:
            record_id = record.get("id")
            if record_id:
                await self.zerodb_client.delete_row(NONCES_TABLE, {"id": record_id})
                deleted += 1

        logger.info(f"Deleted {deleted} expired nonce record(s).")
        return deleted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_nonce_format(nonce: str) -> None:
        """Ensure the nonce is a valid UUID v4 string."""
        try:
            parsed = uuid.UUID(nonce, version=4)
            # uuid.UUID is lenient about version; verify explicitly
            if str(parsed) != nonce.lower():
                raise ValueError("Not a canonical UUID v4")
        except (ValueError, AttributeError):
            raise InvalidNonceError(nonce)

    @staticmethod
    def _validate_timestamp(timestamp: str) -> None:
        """Ensure the timestamp is within the acceptable drift window."""
        try:
            # Parse ISO 8601 — handle both offset-aware and naive forms
            if timestamp.endswith("Z"):
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                ts = datetime.fromisoformat(timestamp)

            # Ensure timezone-aware for comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

        except (ValueError, TypeError):
            raise StaleRequestError(timestamp)

        now = datetime.now(timezone.utc)
        delta = abs((now - ts).total_seconds())
        max_seconds = MAX_TIMESTAMP_DRIFT_MINUTES * 60

        if delta > max_seconds:
            raise StaleRequestError(timestamp)

    async def _check_uniqueness(self, nonce: str, did: str) -> None:
        """Query ZeroDB to detect duplicate nonce use by this DID."""
        existing = await self.zerodb_client.query_rows(
            NONCES_TABLE,
            {"nonce": nonce, "did": did},
        )
        if existing:
            raise ReplayAttackError(nonce=nonce, did=did)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

nonce_replay_guard = NonceReplayGuard()


def get_nonce_replay_guard() -> NonceReplayGuard:
    """Return the module-level NonceReplayGuard singleton."""
    return nonce_replay_guard
