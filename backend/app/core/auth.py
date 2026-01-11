"""
Authentication and authorization using X-API-Key header or JWT Bearer token.
Per PRD §9 and Epic 2, all public endpoints require authentication.
Epic 2 Story 4: Support both X-API-Key and JWT Bearer token authentication.
"""
from typing import Optional
from fastapi import Header, Depends
from app.core.config import settings
from app.core.errors import InvalidAPIKeyError, InvalidTokenError, TokenExpiredAPIError
from app.core.jwt import (
    extract_token_from_header,
    decode_access_token,
    TokenExpiredError,
    InvalidJWTError
)


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="API key for authentication")
) -> str:
    """
    Verify X-API-Key header and return user_id.

    Handles multiple invalid API key scenarios:
    - Missing API key (None or empty)
    - Malformed API key (whitespace, too short, invalid characters)
    - Expired API key (special prefix for demo)
    - Unauthorized API key (not found in system)

    Per DX Contract Section 2: All invalid keys return 401 INVALID_API_KEY
    Per Epic 2 Story 2: Error response includes error_code and clear detail message

    Raises:
        InvalidAPIKeyError: If API key is missing, malformed, expired, or unauthorized.

    Returns:
        str: User ID associated with the API key.
    """
    # Case 1: Missing API key
    if not x_api_key:
        raise InvalidAPIKeyError("Missing X-API-Key header")

    # Case 2: Malformed API key - empty string or whitespace only
    if not x_api_key.strip():
        raise InvalidAPIKeyError("API key cannot be empty or whitespace")

    # Case 3: Malformed API key - too short (minimum length validation)
    # Valid API keys should be at least 10 characters for security
    if len(x_api_key.strip()) < 10:
        raise InvalidAPIKeyError("API key format is invalid")

    # Case 4: Malformed API key - contains invalid characters
    # API keys should only contain alphanumeric characters, underscores, and hyphens
    cleaned_key = x_api_key.strip()
    if not all(c.isalnum() or c in ('_', '-') for c in cleaned_key):
        raise InvalidAPIKeyError("API key contains invalid characters")

    # Case 5: Expired API key (demo simulation with prefix)
    # In production, this would check expiration timestamp in database
    if cleaned_key.startswith("expired_"):
        raise InvalidAPIKeyError("API key has expired")

    # Case 6: Unauthorized API key - not found in system
    user_id = settings.get_user_id_from_api_key(cleaned_key)

    if not user_id:
        # Generic message for security (don't reveal if key exists but is invalid)
        raise InvalidAPIKeyError("Invalid API key")

    return user_id


# Dependency for routes that require authentication
async def get_current_user(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Get current authenticated user ID from either X-API-Key or JWT Bearer token.

    Per Epic 2 Story 4: Support both X-API-Key and Bearer JWT token authentication.

    Args:
        x_api_key: Optional X-API-Key header
        authorization: Optional Authorization Bearer header

    Returns:
        str: Authenticated user ID

    Raises:
        InvalidAPIKeyError: If neither auth method provided or both invalid
    """
    # Try X-API-Key first (with all validation)
    if x_api_key:
        try:
            return await verify_api_key(x_api_key)
        except InvalidAPIKeyError:
            # If API key is provided but invalid, and no JWT, raise error
            if not authorization:
                raise

    # Try JWT Bearer token
    if authorization:
        token = extract_token_from_header(authorization)
        if token:
            try:
                token_data = decode_access_token(token)
                return token_data.user_id
            except TokenExpiredError:
                # Only raise TokenExpiredAPIError if no valid API key
                if not x_api_key:
                    raise TokenExpiredAPIError("JWT token has expired")
            except InvalidJWTError as e:
                # Only raise InvalidTokenError if no valid API key
                if not x_api_key:
                    raise InvalidTokenError(f"Invalid JWT token: {str(e)}")

    # No valid authentication found
    raise InvalidAPIKeyError(
        "Authentication required. Provide X-API-Key or Authorization Bearer token."
    )
