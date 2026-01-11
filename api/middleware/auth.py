"""
Authentication Middleware

Following DX Contract and PRD §10:
- X-API-Key header authentication
- Returns 401 INVALID_API_KEY on failure
- Deterministic error responses
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import os


class AuthError(HTTPException):
    """Custom authentication error with error_code"""
    def __init__(self, detail: str, error_code: str = "INVALID_API_KEY"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "X-API-Key"}
        )
        self.error_code = error_code


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="API Key for authentication")
) -> str:
    """
    Verify X-API-Key header.

    For MVP, validates against ZERODB_API_KEY environment variable.
    In production, this would check against a database of valid API keys.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        str: Validated API key

    Raises:
        AuthError: If API key is missing or invalid (401)
    """
    # Check if header is present
    if not x_api_key:
        raise AuthError(
            detail="Missing X-API-Key header",
            error_code="MISSING_API_KEY"
        )

    # Validate against environment variable (MVP only)
    valid_key = os.getenv("ZERODB_API_KEY", "").strip()

    if not valid_key:
        # Configuration error - should not happen in production
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: API key validation unavailable"
        )

    if x_api_key != valid_key:
        raise AuthError(
            detail="Invalid API key",
            error_code="INVALID_API_KEY"
        )

    return x_api_key


def get_project_limit_for_tier(tier: str) -> int:
    """
    Get the project creation limit for a given tier.

    Following backlog Epic 1, story 4:
    - Different tiers have different project limits
    """
    limits = {
        "FREE": 3,
        "STARTER": 10,
        "PRO": 50,
        "ENTERPRISE": 999999  # Effectively unlimited
    }
    return limits.get(tier, 1)
