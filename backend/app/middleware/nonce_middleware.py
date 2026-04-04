"""
Nonce Middleware for FastAPI.
Issue #242: Replay Prevention via Nonces

Intercepts POST requests to /x402, extracts the nonce and timestamp from
the request body, and delegates to NonceReplayGuard for validation.

HTTP responses:
- 409 Conflict: Replay attack (duplicate nonce).
- 400 Bad Request: Stale timestamp or invalid nonce format.

Built by AINative Dev Team
Refs #242
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that require nonce validation (POST only)
_NONCE_PROTECTED_PATHS = frozenset({"/x402"})


class NonceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces nonce-based replay prevention on x402 POST requests.

    For each POST to a nonce-protected path:
    1. Parse the JSON body for 'nonce', 'timestamp', and 'did' fields.
    2. If 'nonce' is absent, pass through (graceful degradation).
    3. Call NonceReplayGuard.validate_request() — returns 409/400 on failure.
    4. On success, call NonceReplayGuard.record_nonce() to mark the nonce as used.
    5. Forward the request to the next handler.
    """

    def __init__(
        self,
        app: Any,
        guard: Optional[Any] = None,
    ) -> None:
        """
        Initialise the middleware.

        Args:
            app: The ASGI application.
            guard: Optional NonceReplayGuard instance (for testing / DI).
        """
        super().__init__(app)
        self._guard = guard

    @property
    def guard(self) -> Any:
        """Lazy-init NonceReplayGuard."""
        if self._guard is None:
            from app.services.nonce_replay_guard import get_nonce_replay_guard
            self._guard = get_nonce_replay_guard()
        return self._guard

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercept requests, validate nonces on protected POST paths.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            - 409 JSONResponse on replay attack.
            - 400 JSONResponse on stale/invalid nonce.
            - Downstream response on success or when nonce validation is skipped.
        """
        path = request.url.path
        method = request.method.upper()

        # Only POST requests to protected paths are nonce-checked
        if path not in _NONCE_PROTECTED_PATHS or method != "POST":
            return await call_next(request)

        # Parse JSON body — non-fatal if body is malformed
        try:
            body = await request.json()
        except Exception:
            body = {}

        nonce = body.get("nonce")
        timestamp = body.get("timestamp")
        did = body.get("did", "")

        # If no nonce present, bypass validation gracefully
        if not nonce:
            return await call_next(request)

        # Validate — catch known guard errors
        from app.services.nonce_replay_guard import (
            ReplayAttackError,
            StaleRequestError,
            InvalidNonceError,
        )

        try:
            await self.guard.validate_request(
                nonce=nonce,
                timestamp=timestamp or "",
                did=did,
            )
        except ReplayAttackError as exc:
            logger.warning(
                f"Replay attack blocked for DID '{did}', nonce='{nonce}': {exc}"
            )
            return JSONResponse(
                status_code=409,
                content={
                    "detail": str(exc),
                    "error_code": "REPLAY_ATTACK",
                },
            )
        except (StaleRequestError, InvalidNonceError) as exc:
            logger.warning(
                f"Invalid nonce request for DID '{did}': {exc}"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "detail": str(exc),
                    "error_code": "INVALID_NONCE",
                },
            )

        # Persist the used nonce before forwarding the request
        try:
            await self.guard.record_nonce(
                nonce=nonce,
                did=did,
                timestamp=timestamp or "",
            )
        except Exception as exc:
            # Non-fatal: log and continue — request already validated
            logger.error(f"Failed to record nonce for DID '{did}': {exc}")

        return await call_next(request)
