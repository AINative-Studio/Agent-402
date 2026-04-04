"""
Tests for RateLimiterService — sliding window rate limiting.
Issue #239: Agent Spend Limits — rate limiting enforcement.

TDD: RED phase — tests written before implementation.
"""
from __future__ import annotations

import asyncio
import pytest
import time
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock


class DescribeRateLimiterServiceInit:
    """Describe RateLimiterService construction and defaults."""

    def it_can_be_instantiated_without_arguments(self):
        """RateLimiterService must be constructable with no args."""
        from app.services.rate_limiter_service import RateLimiterService
        svc = RateLimiterService()
        assert svc is not None

    def it_accepts_optional_zerodb_client(self):
        """Constructor accepts an optional client for testing."""
        from app.services.rate_limiter_service import RateLimiterService
        mock_client = MagicMock()
        svc = RateLimiterService(client=mock_client)
        assert svc is not None


class DescribeCheckRateLimit:
    """Describe RateLimiterService.check_rate_limit sliding-window behavior."""

    def _make_service(self):
        from app.services.rate_limiter_service import RateLimiterService
        return RateLimiterService(client=None)

    @pytest.mark.asyncio
    async def it_returns_true_for_first_request(self):
        """First request from a DID is always allowed."""
        svc = self._make_service()
        result = await svc.check_rate_limit(
            did="did:hedera:testnet:new-agent",
            max_requests=10,
            window_seconds=60,
        )
        assert result is True

    @pytest.mark.asyncio
    async def it_returns_true_within_the_request_limit(self):
        """Requests up to max_requests within window must all return True."""
        svc = self._make_service()
        did = "did:hedera:testnet:agent-within-limit"
        for _ in range(5):
            result = await svc.check_rate_limit(
                did=did,
                max_requests=10,
                window_seconds=60,
            )
            assert result is True

    @pytest.mark.asyncio
    async def it_raises_429_when_limit_exceeded(self):
        """Exceeding max_requests within window must raise RateLimitExceededError."""
        from app.services.rate_limiter_service import RateLimitExceededError
        svc = self._make_service()
        did = "did:hedera:testnet:agent-over-limit"
        # Exhaust the limit
        for _ in range(3):
            await svc.check_rate_limit(did=did, max_requests=3, window_seconds=60)
        # Next request must raise
        with pytest.raises(RateLimitExceededError):
            await svc.check_rate_limit(did=did, max_requests=3, window_seconds=60)

    @pytest.mark.asyncio
    async def it_raises_error_with_correct_http_status(self):
        """RateLimitExceededError must carry HTTP 429."""
        from app.services.rate_limiter_service import RateLimitExceededError
        from app.core.errors import APIError
        svc = self._make_service()
        did = "did:hedera:testnet:agent-429"
        for _ in range(2):
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=60)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=60)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def it_raises_error_with_rate_limit_exceeded_error_code(self):
        """RateLimitExceededError must carry RATE_LIMIT_EXCEEDED error_code."""
        from app.services.rate_limiter_service import RateLimitExceededError
        svc = self._make_service()
        did = "did:hedera:testnet:agent-code"
        for _ in range(2):
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=60)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=60)
        assert exc_info.value.error_code == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def it_exposes_retry_after_seconds_on_error(self):
        """RateLimitExceededError must expose retry_after_seconds attribute."""
        from app.services.rate_limiter_service import RateLimitExceededError
        svc = self._make_service()
        did = "did:hedera:testnet:agent-retry"
        for _ in range(2):
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=30)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await svc.check_rate_limit(did=did, max_requests=2, window_seconds=30)
        assert hasattr(exc_info.value, "retry_after_seconds")
        assert exc_info.value.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def it_tracks_different_dids_independently(self):
        """Requests for different DIDs must not share rate limit state."""
        svc = self._make_service()
        did_a = "did:hedera:testnet:agent-a"
        did_b = "did:hedera:testnet:agent-b"
        # Exhaust limit for agent-a
        for _ in range(2):
            await svc.check_rate_limit(did=did_a, max_requests=2, window_seconds=60)
        # agent-b still has quota
        result = await svc.check_rate_limit(did=did_b, max_requests=2, window_seconds=60)
        assert result is True

    @pytest.mark.asyncio
    async def it_prunes_expired_timestamps_from_sliding_window(self):
        """Timestamps older than window_seconds must be pruned, freeing quota."""
        from app.services.rate_limiter_service import RateLimiterService
        svc = RateLimiterService(client=None)
        did = "did:hedera:testnet:agent-expire"
        # Manually inject old timestamps to simulate a past window
        old_time = time.monotonic() - 120  # 2 minutes ago
        svc._store[did] = [old_time, old_time, old_time]
        # New request in a 60s window should succeed (old ones pruned)
        result = await svc.check_rate_limit(did=did, max_requests=2, window_seconds=60)
        assert result is True

    @pytest.mark.asyncio
    async def it_uses_default_max_requests_100_and_window_60(self):
        """Default parameters must be max_requests=100 and window_seconds=60."""
        svc = self._make_service()
        did = "did:hedera:testnet:agent-defaults"
        # Single call with no explicit params should not raise
        result = await svc.check_rate_limit(did=did)
        assert result is True


class DescribeRateLimiterConcurrency:
    """Describe RateLimiterService thread-safety with asyncio.Lock."""

    @pytest.mark.asyncio
    async def it_handles_concurrent_requests_safely(self):
        """Concurrent calls for the same DID must not exceed the limit."""
        from app.services.rate_limiter_service import RateLimiterService, RateLimitExceededError
        svc = RateLimiterService(client=None)
        did = "did:hedera:testnet:agent-concurrent"
        max_requests = 5

        results = []
        errors = []

        async def make_request():
            try:
                r = await svc.check_rate_limit(
                    did=did, max_requests=max_requests, window_seconds=60
                )
                results.append(r)
            except RateLimitExceededError:
                errors.append(True)

        # Fire 10 concurrent requests; only 5 should succeed
        await asyncio.gather(*[make_request() for _ in range(10)])
        assert len(results) == max_requests
        assert len(errors) == 10 - max_requests


class DescribeRateLimiterMiddlewareIntegration:
    """Describe the rate limiter middleware return shape for 429 responses."""

    @pytest.mark.asyncio
    async def it_raises_error_that_includes_did_in_detail(self):
        """Error detail must name the DID that was rate-limited."""
        from app.services.rate_limiter_service import RateLimiterService, RateLimitExceededError
        svc = RateLimiterService(client=None)
        did = "did:hedera:testnet:agent-detail"
        for _ in range(1):
            await svc.check_rate_limit(did=did, max_requests=1, window_seconds=60)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await svc.check_rate_limit(did=did, max_requests=1, window_seconds=60)
        assert did in exc_info.value.detail
