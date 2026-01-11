"""
Custom exceptions for ZeroDB Public API.

Implements domain-specific exceptions with clear error codes and messages.
"""
from typing import Optional


class ZeroDBException(Exception):
    """Base exception for all ZeroDB errors."""

    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int = 400,
        headers: Optional[dict] = None
    ):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.headers = headers
        super().__init__(self.detail)


class ProjectLimitExceededException(ZeroDBException):
    """
    Raised when a user attempts to create a project but has reached their tier limit.

    Per PRD §12 (Infrastructure Credibility):
    - Returns HTTP 429 (Too Many Requests)
    - Includes error_code: PROJECT_LIMIT_EXCEEDED
    - Provides clear detail message with current tier and limit
    - Suggests upgrade path or support contact
    """

    def __init__(
        self,
        current_tier: str,
        project_limit: int,
        current_count: int,
        upgrade_tier: Optional[str] = None
    ):
        # Build detailed error message
        detail_parts = [
            f"Project limit exceeded for tier '{current_tier}'.",
            f"Current projects: {current_count}/{project_limit}.",
        ]

        if upgrade_tier:
            detail_parts.append(
                f"Please upgrade to '{upgrade_tier}' tier for higher limits, "
                "or contact support at support@ainative.studio."
            )
        else:
            detail_parts.append(
                "Please contact support at support@ainative.studio to increase your limit."
            )

        detail = " ".join(detail_parts)

        super().__init__(
            detail=detail,
            error_code="PROJECT_LIMIT_EXCEEDED",
            status_code=429  # HTTP 429 Too Many Requests
        )

        self.current_tier = current_tier
        self.project_limit = project_limit
        self.current_count = current_count
        self.upgrade_tier = upgrade_tier


class InvalidTierException(ZeroDBException):
    """
    Raised when an invalid tier is specified.

    Per backlog item #3 (INVALID_TIER error handling).
    """

    def __init__(self, tier: str, valid_tiers: list[str]):
        detail = (
            f"Invalid tier '{tier}'. "
            f"Valid tiers are: {', '.join(valid_tiers)}."
        )

        super().__init__(
            detail=detail,
            error_code="INVALID_TIER",
            status_code=422  # Unprocessable Entity
        )

        self.tier = tier
        self.valid_tiers = valid_tiers


class InvalidAPIKeyException(ZeroDBException):
    """Raised when API key is invalid or missing."""

    def __init__(self):
        super().__init__(
            detail="Invalid or missing API key. Please provide a valid X-API-Key header.",
            error_code="INVALID_API_KEY",
            status_code=401  # Unauthorized
        )


class InvalidTimestampException(ZeroDBException):
    """
    Raised when an invalid timestamp format is provided.

    Per backlog Epic 8 (Events API) - clear error handling for invalid timestamps.
    """

    def __init__(self, timestamp: str, reason: str):
        detail = (
            f"Invalid timestamp '{timestamp}'. "
            f"Expected ISO8601 format (e.g., '2025-01-11T22:00:00Z' or '2025-01-11T22:00:00+00:00'). "
            f"Error: {reason}"
        )

        super().__init__(
            detail=detail,
            error_code="INVALID_TIMESTAMP",
            status_code=422  # Unprocessable Entity
        )

        self.timestamp = timestamp
        self.reason = reason
