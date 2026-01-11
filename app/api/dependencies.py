"""
FastAPI dependencies for authentication and common operations.
"""
from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import settings
from app.core.exceptions import InvalidAPIKeyException


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None
) -> str:
    """
    Verify the API key from X-API-Key header.

    In production, this would validate against a database of API keys.
    For MVP, implements basic validation to ensure the header is present.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        User ID extracted from the API key

    Raises:
        InvalidAPIKeyException: If API key is missing or invalid
    """
    if not x_api_key:
        raise InvalidAPIKeyException()

    # For MVP: Use API key as user identifier
    # In production, this would:
    # 1. Validate the key against a database
    # 2. Check expiration and rate limits
    # 3. Return the associated user ID

    # Basic validation: ensure it's not empty after stripping
    if not x_api_key.strip():
        raise InvalidAPIKeyException()

    # Return user_id (for MVP, just use the API key itself)
    return x_api_key.strip()


# Type alias for dependency injection
APIKeyDep = Annotated[str, Header()]
