"""
Rate limiter middleware for FastAPI.
Issue #239: Agent Spend Limits — per-DID request throttling at the HTTP layer.

Extracts the agent DID from the ``X-Agent-DID`` header (or falls back to the
``sub`` claim of a decoded JWT Bearer token), then delegates to
``RateLimiterService.check_rate_limit()``.  Returns HTTP 429 with a
``Retry-After`` header when the limit is exceeded.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import RateLimitExceededError, format_error_response
from app.services.rate_limiter_service import RateLimiterService

logger = logging.getLogger(__name__)

# Default rate-limit parameters — may be overridden per-deployment via env/config
DEFAULT_MAX_REQUESTS: int = 100
DEFAULT_WINDOW_SECONDS: int = 60

# Paths that bypass rate limiting (health-checks, docs, etc.)
_EXEMPT_PATHS = frozenset(
    {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/.well-known/x402",
        "/x402",
        "/v1/public/auth/login",
        "/v1/public/auth/refresh",
        "/v1/public/embeddings/models",
    }
)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-DID sliding-window rate limits.

    DID resolution order:
    1. ``X-Agent-DID`` request header (preferred — explicit agent identity)
    2. ``sub`` claim extracted from a JWT ``Authorization: Bearer …`` header
    3. If no DID can be resolved the request passes through without limiting
       (authentication middleware handles missing identity separately).

    On limit exceeded the middleware short-circuits with:
    - HTTP 429 Too Many Requests
    - ``Retry-After`` header set to the number of seconds until the window resets
    - JSON body: ``{ detail, error_code, retry_after_seconds }``
    """

    def __init__(
        self,
        app,
        rate_limiter: Optional[RateLimiterService] = None,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter or RateLimiterService()
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercept the request, extract the DID, and apply rate limiting.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            429 JSONResponse on limit exceeded, otherwise the downstream response.
        """
        path = request.url.path

        # Exempt paths bypass rate limiting
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        did = self._extract_did(request)

        if did is None:
            # No DID available — pass through; auth middleware handles identity
            return await call_next(request)

        try:
            await self._rate_limiter.check_rate_limit(
                did=did,
                max_requests=self._max_requests,
                window_seconds=self._window_seconds,
            )
        except RateLimitExceededError as exc:
            logger.warning(
                f"Rate limit triggered for DID '{did}' on path '{path}'.",
                extra={"did": did, "path": path, "retry_after": exc.retry_after_seconds},
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    **format_error_response(
                        error_code=exc.error_code,
                        detail=exc.detail,
                    ),
                    "retry_after_seconds": exc.retry_after_seconds,
                },
                headers={"Retry-After": str(exc.retry_after_seconds)},
            )

        return await call_next(request)

    @staticmethod
    def _extract_did(request: Request) -> Optional[str]:
        """
        Extract the agent DID from the request.

        Checks ``X-Agent-DID`` header first, then falls back to the ``sub``
        claim of a JWT Bearer token in the ``Authorization`` header.

        Args:
            request: Incoming HTTP request.

        Returns:
            DID string or None if no DID can be resolved.
        """
        # Preferred: explicit DID header
        did = request.headers.get("X-Agent-DID")
        if did:
            return did.strip()

        # Fallback: decode JWT and use the ``sub`` claim
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):]
            try:
                # Lazy import to avoid circular dependencies
                from app.core.jwt import decode_access_token
                token_data = decode_access_token(token)
                if token_data and token_data.user_id:
                    return token_data.user_id
            except Exception:
                # Non-fatal — token may be invalid; auth middleware handles that
                pass

        return None
