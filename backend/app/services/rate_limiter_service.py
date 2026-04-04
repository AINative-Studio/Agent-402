"""
Sliding-window rate limiter service for per-DID request throttling.
Issue #239: Agent Spend Limits — rate limiting enforcement.

Implements an in-memory sliding window rate limiter with asyncio.Lock
for thread safety and optional ZeroDB fallback for distributed state.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from app.core.errors import RateLimitExceededError

logger = logging.getLogger(__name__)


class RateLimiterService:
    """
    In-memory sliding-window rate limiter keyed by agent DID.

    Each DID maintains a list of request timestamps (monotonic clock).
    On every call the list is pruned to discard entries older than
    ``window_seconds``, then the remaining count is compared to
    ``max_requests``.

    Thread safety is guaranteed by a per-instance ``asyncio.Lock``.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        """
        Initialise the rate limiter.

        Args:
            client: Optional ZeroDB client (reserved for future distributed
                    state fallback; not used in the current in-memory impl).
        """
        self._client = client
        # Mapping of DID -> list of monotonic timestamps
        self._store: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        did: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check whether a DID is within its allowed request rate.

        Prunes timestamps outside the sliding window, counts remaining
        entries, and either records a new timestamp (allowed) or raises
        ``RateLimitExceededError`` (denied).

        Args:
            did: Agent DID — the rate-limit key.
            max_requests: Maximum number of requests permitted within the window.
            window_seconds: Length of the sliding window in seconds.

        Returns:
            True when the request is within the allowed rate.

        Raises:
            RateLimitExceededError: When the DID has exceeded ``max_requests``
                within the current ``window_seconds`` window.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._lock:
            # Initialise entry for new DIDs
            if did not in self._store:
                self._store[did] = []

            timestamps = self._store[did]

            # Prune expired timestamps (sliding window)
            pruned = [ts for ts in timestamps if ts > cutoff]
            self._store[did] = pruned

            if len(pruned) >= max_requests:
                # Calculate earliest expiry so callers know when to retry
                oldest = min(pruned)
                retry_after = max(1, int(oldest + window_seconds - now) + 1)
                logger.warning(
                    f"Rate limit exceeded for DID '{did}': "
                    f"{len(pruned)}/{max_requests} requests in {window_seconds}s window.",
                    extra={"did": did, "count": len(pruned), "limit": max_requests},
                )
                raise RateLimitExceededError(did=did, retry_after_seconds=retry_after)

            # Record this request
            self._store[did].append(now)

        logger.debug(
            f"Rate limit check passed for DID '{did}': "
            f"{len(self._store[did])}/{max_requests} requests.",
            extra={"did": did, "limit": max_requests},
        )
        return True


# Global singleton — tests inject a fresh instance via constructor
rate_limiter_service = RateLimiterService()
