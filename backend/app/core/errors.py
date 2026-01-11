"""
Custom error classes and error handling.
Implements deterministic error responses per DX Contract.

DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422

Epic 2, Story 3: As a developer, all errors include a detail field.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class APIError(HTTPException):
    """
    Base API error with consistent error_code and detail.

    All custom exceptions should inherit from this class to ensure
    consistent error format across the API.

    Attributes:
        status_code: HTTP status code
        error_code: Machine-readable error code (required)
        detail: Human-readable error message (required)
        headers: Optional HTTP headers
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        # Ensure detail is always a string (never None)
        if not detail:
            detail = "An error occurred"

        # Ensure error_code is always provided
        if not error_code:
            error_code = "ERROR"

        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class InvalidAPIKeyError(APIError):
    """
    Raised when API key is invalid or missing.

    Per DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY
    Per Epic 2 Story 2 (Issue #7): Handle all invalid API key scenarios

    Scenarios handled:
    - Missing API key (no X-API-Key header)
    - Malformed API key (empty, whitespace, too short, invalid characters)
    - Expired API key (in production: timestamp check; in demo: prefix check)
    - Unauthorized API key (valid format but not found in system)

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: INVALID_API_KEY
        - detail: Human-readable message about the specific invalidity

    All scenarios use the same error_code for security (don't reveal system internals)
    """

    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_API_KEY",
            detail=detail or "Invalid or missing API key"  # Ensure detail never None
        )


class ProjectNotFoundError(APIError):
    """
    Raised when project is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: PROJECT_NOT_FOUND
        - detail: Message including project ID
    """

    def __init__(self, project_id: str):
        detail = f"Project not found: {project_id}" if project_id else "Project not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PROJECT_NOT_FOUND",
            detail=detail
        )


class UnauthorizedError(APIError):
    """
    Raised when user is not authorized to access resource.

    Returns:
        - HTTP 403 (Forbidden)
        - error_code: UNAUTHORIZED
        - detail: Message about unauthorized access
    """

    def __init__(self, detail: str = "Not authorized to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="UNAUTHORIZED",
            detail=detail or "Not authorized to access this resource"
        )


class ProjectLimitExceededError(APIError):
    """
    Raised when user exceeds project creation limit for their tier.

    Returns:
        - HTTP 429 (Too Many Requests)
        - error_code: PROJECT_LIMIT_EXCEEDED
        - detail: Message with current count and limit
    """

    def __init__(self, current_count: int, limit: int, tier: str = ""):
        tier_info = f" for tier '{tier}'" if tier else ""
        detail = (
            f"Project limit exceeded{tier_info}. "
            f"Current projects: {current_count}/{limit}."
        )
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="PROJECT_LIMIT_EXCEEDED",
            detail=detail
        )


class InvalidTierError(APIError):
    """
    Raised when an invalid tier is specified.

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_TIER
        - detail: Message with valid tier options
    """

    def __init__(self, tier: str, valid_tiers: list):
        valid_tiers_str = ", ".join(valid_tiers) if valid_tiers else "unknown"
        detail = (
            f"Invalid tier '{tier}'. "
            f"Valid tiers are: {valid_tiers_str}."
        )
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_TIER",
            detail=detail
        )


class InvalidTokenError(APIError):
    """
    Raised when JWT token is invalid.

    Epic 2 Story 4: JWT authentication support

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: INVALID_TOKEN
        - detail: Message about invalid token
    """

    def __init__(self, detail: str = "Invalid JWT token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            detail=detail or "Invalid JWT token"
        )


class TokenExpiredAPIError(APIError):
    """
    Raised when JWT token has expired.

    Epic 2 Story 4: JWT authentication support

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: TOKEN_EXPIRED
        - detail: Message about expired token
    """

    def __init__(self, detail: str = "JWT token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            detail=detail or "JWT token has expired"
        )


def format_error_response(error_code: str, detail: str) -> Dict[str, str]:
    """
    Format error response per DX Contract.

    All errors MUST return { detail, error_code }.

    Args:
        error_code: Machine-readable error code
        detail: Human-readable error message

    Returns:
        Dictionary with detail and error_code fields
    """
    # Ensure detail is never empty or None
    if not detail:
        detail = "An error occurred"

    # Ensure error_code is never empty or None
    if not error_code:
        error_code = "ERROR"

    return {
        "detail": detail,
        "error_code": error_code
    }
