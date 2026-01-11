"""
API Key and JWT Authentication Middleware.

Enforces authentication on all /v1/public/* endpoints using either:
1. X-API-Key header authentication (Epic 2, Story 1)
2. JWT Bearer token authentication (Epic 2, Story 4)

Per PRD §10 (Signed requests + auditability) and DX Contract §2.

This middleware:
1. Intercepts all requests to /v1/public/* endpoints
2. Validates X-API-Key header OR Authorization Bearer token
3. Returns 401 with appropriate error code if authentication fails
4. Attaches user_id to request state for downstream use
5. Allows health check, docs, and login endpoints to pass through
"""
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.errors import format_error_response
from app.core.jwt import (
    extract_token_from_header,
    decode_access_token,
    TokenExpiredError,
    InvalidJWTError
)
import logging

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication on all public endpoints.

    This middleware implements the security requirements from:
    - PRD §10: Signed requests + auditability
    - Epic 2, Story 1: X-API-Key authentication for all public endpoints
    - Epic 2, Story 4: JWT Bearer token authentication as alternative
    - DX-Contract.md §2: All public endpoints accept X-API-Key or JWT Bearer token

    The middleware:
    1. Checks if the request path starts with /v1/public/
    2. Exempts health check, documentation, and login endpoints
    3. Validates X-API-Key header OR Authorization Bearer token
    4. Returns 401 with specific error code if authentication fails
    5. Attaches authenticated user_id to request.state for route handlers
    """

    # Paths that don't require authentication
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/public/auth/login",  # Login endpoint doesn't require auth
    }

    # Prefix for public API endpoints that require authentication
    PUBLIC_API_PREFIX = "/v1/public/"

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Intercept and validate authentication for public endpoints.

        Supports both X-API-Key and JWT Bearer token authentication.
        Per Epic 2 Story 4: JWT should be usable as alternative to X-API-Key.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: Either a 401 error or the result of call_next
        """
        path = request.url.path

        # Skip authentication for exempt paths
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Only authenticate public API endpoints
        if not path.startswith(self.PUBLIC_API_PREFIX):
            return await call_next(request)

        # Try to authenticate using either X-API-Key or JWT
        user_id = await self._authenticate_request(request, path)

        if not user_id:
            # Check if there's a specific auth error (e.g., expired token)
            if hasattr(request.state, "auth_error"):
                error_info = request.state.auth_error
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=format_error_response(
                        error_code=error_info["error_code"],
                        detail=error_info["detail"]
                    )
                )

            # Generic authentication failure
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=format_error_response(
                    error_code="UNAUTHORIZED",
                    detail="Authentication required. Provide X-API-Key or Authorization Bearer token."
                )
            )

        # Attach user_id to request state for use in route handlers
        # This allows routes to access the authenticated user without re-validating
        request.state.user_id = user_id

        logger.info(
            f"Authenticated request to {path}",
            extra={"path": path, "user_id": user_id}
        )

        # Continue to route handler
        return await call_next(request)

    async def _authenticate_request(
        self, request: Request, path: str
    ) -> Optional[str]:
        """
        Authenticate the request using X-API-Key or JWT Bearer token.

        Per Epic 2 Story 4: Support both X-API-Key and Bearer JWT token authentication.

        Args:
            request: The incoming HTTP request
            path: Request path for logging

        Returns:
            User ID if authentication succeeds, None otherwise
        """
        # Try X-API-Key authentication first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user_id = settings.get_user_id_from_api_key(api_key)
            if user_id:
                logger.debug(
                    f"Authenticated via X-API-Key: {path}",
                    extra={"path": path, "user_id": user_id, "auth_method": "api_key"}
                )
                return user_id
            else:
                logger.warning(
                    f"Invalid X-API-Key for request to {path}",
                    extra={"path": path, "api_key_prefix": api_key[:8]}
                )

        # Try JWT Bearer token authentication
        authorization = request.headers.get("Authorization")
        if authorization:
            token = extract_token_from_header(authorization)
            if token:
                try:
                    token_data = decode_access_token(token)
                    logger.debug(
                        f"Authenticated via JWT: {path}",
                        extra={"path": path, "user_id": token_data.user_id, "auth_method": "jwt"}
                    )
                    return token_data.user_id
                except TokenExpiredError:
                    logger.warning(
                        f"Expired JWT token for request to {path}",
                        extra={"path": path}
                    )
                    # Return a more specific error for expired tokens
                    request.state.auth_error = {
                        "error_code": "TOKEN_EXPIRED",
                        "detail": "JWT token has expired"
                    }
                except InvalidJWTError as e:
                    logger.warning(
                        f"Invalid JWT token for request to {path}: {str(e)}",
                        extra={"path": path}
                    )
                    # Return a more specific error for invalid tokens
                    request.state.auth_error = {
                        "error_code": "INVALID_TOKEN",
                        "detail": "Invalid JWT token"
                    }

        # No valid authentication found
        logger.warning(
            f"No valid authentication for request to {path}",
            extra={"path": path, "has_api_key": bool(api_key), "has_auth_header": bool(authorization)}
        )
        return None
