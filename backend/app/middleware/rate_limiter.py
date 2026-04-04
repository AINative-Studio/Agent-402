"""
Rate limiter middleware for FastAPI.
Issue #239: Agent Spend Limits — per-DID request throttling at the HTTP layer.
Issue #241: DID-Based Rate Limiting Enforcement.

DID resolution priority (highest to lowest):
1. x402 POST body 'did' field (parsed for /x402 POST requests).
2. ``X-Agent-DID`` request header.
3. ``sub`` claim from a JWT ``Authorization: Bearer …`` header.

Delegates to ``RateLimiterService.check_rate_limit()``.
Returns HTTP 429 with a ``Retry-After`` header when the limit is exceeded.
Logs rate-limit events to ZeroDB for analytics via
``RateLimiterService.log_rate_limit_event()`` (if available).

Built by AINative Dev Team
Refs #239, #241
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import RateLimitExceededError, format_error_response
from app.services.rate_limiter_service import RateLimiterService

logger = logging.getLogger(__name__)


def decode_access_token_sub(token: str) -> Optional[str]:
    """
    Decode a JWT and return the ``sub`` claim as the DID.

    This thin wrapper around the existing ``decode_access_token`` helper
    is a module-level function so tests can patch it cleanly.

    Args:
        token: Raw JWT string (without "Bearer " prefix).

    Returns:
        The ``sub`` / ``user_id`` claim, or None if decoding fails.
    """
    try:
        from app.core.jwt import decode_access_token
        token_data = decode_access_token(token)
        if token_data and token_data.user_id:
            return token_data.user_id
    except Exception:
        pass
    return None

# Default rate-limit parameters — may be overridden per-deployment via env/config
DEFAULT_MAX_REQUESTS: int = 100
DEFAULT_WINDOW_SECONDS: int = 60

# Paths that bypass rate limiting (health-checks, docs, etc.)
# Note: /x402 is NOT exempt — Issue #241 adds DID extraction from the x402
# POST body so signed requests can be rate-limited per DID.
# /x402 requests without a DID still pass through (no DID = no limiting).
_EXEMPT_PATHS = frozenset(
    {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/.well-known/x402",
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

        Uses the three-source DID resolution priority:
        1. x402 POST body 'did' field.
        2. X-Agent-DID header.
        3. JWT sub claim.

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

        did = await self._resolve_did(request)

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
            # Log analytics event to ZeroDB if the service supports it
            if hasattr(self._rate_limiter, "log_rate_limit_event"):
                try:
                    await self._rate_limiter.log_rate_limit_event(
                        did=did,
                        path=path,
                        retry_after_seconds=exc.retry_after_seconds,
                    )
                except Exception as log_exc:
                    logger.debug(f"Rate limit event logging failed (non-fatal): {log_exc}")

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

    async def _resolve_did(self, request: Request) -> Optional[str]:
        """
        Resolve the agent DID using a three-source priority chain.

        Priority (highest to lowest):
        1. ``did`` field in x402 POST JSON body (Issue #241).
        2. ``X-Agent-DID`` request header.
        3. ``sub`` claim from a JWT Bearer token.

        Args:
            request: Incoming HTTP request.

        Returns:
            DID string or None if no DID can be resolved from any source.
        """
        # Priority 1: x402 POST body DID
        x402_did = await self._extract_did_from_x402_payload(request)
        if x402_did:
            return x402_did

        # Priority 2: explicit header DID
        header_did = request.headers.get("X-Agent-DID")
        if header_did:
            return header_did.strip()

        # Priority 3: JWT sub claim
        jwt_did = self._extract_did_from_jwt(request)
        if jwt_did:
            return jwt_did

        return None

    async def _extract_did_from_x402_payload(
        self, request: Request
    ) -> Optional[str]:
        """
        Extract the DID from the ``did`` field of an x402 POST JSON body.

        Issue #241: parse the signed x402 POST body for the DID field.
        Only applicable to POST requests; non-POST methods return None.

        Args:
            request: Incoming HTTP request.

        Returns:
            DID string (stripped), or None if not present or parseable.
        """
        if request.method.upper() != "POST":
            return None

        try:
            body = await request.json()
        except Exception:
            return None

        did = body.get("did")
        if did and isinstance(did, str):
            return did.strip() or None
        return None

    def _extract_did_from_jwt(self, request: Request) -> Optional[str]:
        """
        Extract the DID from the ``sub`` claim of a JWT Bearer token.

        Issue #241: decode the JWT sub claim as a fallback DID source.
        Uses the module-level ``decode_access_token_sub`` wrapper so tests
        can patch it without touching the inner jwt module.

        Args:
            request: Incoming HTTP request.

        Returns:
            DID string from JWT sub claim, or None if unavailable.
        """
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None

        token = authorization[len("Bearer "):]
        try:
            return decode_access_token_sub(token)
        except Exception:
            return None

    @staticmethod
    def _extract_did(request: Request) -> Optional[str]:
        """
        Legacy synchronous DID extractor (Sprint 2 compatibility).

        Checks ``X-Agent-DID`` header first, then falls back to the ``sub``
        claim of a JWT Bearer token.  New code should use ``_resolve_did``
        which also handles x402 POST body parsing.

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
                return decode_access_token_sub(token)
            except Exception:
                pass

        return None
