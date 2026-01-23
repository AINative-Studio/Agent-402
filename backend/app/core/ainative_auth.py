"""
AINative JWT Token Validation.

Validates JWT tokens by calling AINative's auth API.
This allows the backend to accept tokens issued by AINative Studio.
"""
import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# AINative Auth API endpoint
AINATIVE_AUTH_URL = "https://api.ainative.studio/v1/public/auth"

# Cache TTL for token validation (5 minutes)
TOKEN_CACHE_TTL = timedelta(minutes=5)


class AINativeUser(BaseModel):
    """User info from AINative auth."""
    user_id: str
    email: str
    is_active: bool = True
    role: str = "user"
    full_name: Optional[str] = None
    username: Optional[str] = None


class TokenValidationCache:
    """Simple in-memory cache for token validation results."""

    def __init__(self):
        self._cache: dict[str, tuple[AINativeUser, datetime]] = {}

    def get(self, token: str) -> Optional[AINativeUser]:
        """Get cached user if token is still valid."""
        if token in self._cache:
            user, cached_at = self._cache[token]
            if datetime.utcnow() - cached_at < TOKEN_CACHE_TTL:
                return user
            # Cache expired, remove it
            del self._cache[token]
        return None

    def set(self, token: str, user: AINativeUser) -> None:
        """Cache token validation result."""
        self._cache[token] = (user, datetime.utcnow())

    def invalidate(self, token: str) -> None:
        """Remove token from cache."""
        self._cache.pop(token, None)


# Global cache instance
_token_cache = TokenValidationCache()


async def validate_ainative_token(token: str) -> Optional[AINativeUser]:
    """
    Validate a JWT token against AINative's auth API.

    Args:
        token: JWT token string (without 'Bearer ' prefix)

    Returns:
        AINativeUser if token is valid, None otherwise
    """
    # Check cache first
    cached_user = _token_cache.get(token)
    if cached_user:
        logger.debug(f"Token validation cache hit for user {cached_user.user_id}")
        return cached_user

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call AINative's /me endpoint to validate token and get user info
            response = await client.get(
                f"{AINATIVE_AUTH_URL}/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                user = AINativeUser(
                    user_id=data.get("id", ""),
                    email=data.get("email", ""),
                    is_active=data.get("is_active", True),
                    role=data.get("role", "user"),
                    full_name=data.get("full_name"),
                    username=data.get("username"),
                )

                # Cache the result
                _token_cache.set(token, user)

                logger.info(f"AINative token validated for user {user.user_id}")
                return user

            elif response.status_code == 401:
                logger.warning("AINative token validation failed: unauthorized")
                return None

            else:
                logger.error(f"AINative auth API error: {response.status_code}")
                return None

    except httpx.TimeoutException:
        logger.error("AINative auth API timeout")
        return None
    except httpx.RequestError as e:
        logger.error(f"AINative auth API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"AINative token validation error: {e}")
        return None


def validate_ainative_token_sync(token: str) -> Optional[AINativeUser]:
    """
    Synchronous version of validate_ainative_token.
    Used for contexts where async is not available.
    """
    # Check cache first
    cached_user = _token_cache.get(token)
    if cached_user:
        return cached_user

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{AINATIVE_AUTH_URL}/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                user = AINativeUser(
                    user_id=data.get("id", ""),
                    email=data.get("email", ""),
                    is_active=data.get("is_active", True),
                    role=data.get("role", "user"),
                    full_name=data.get("full_name"),
                    username=data.get("username"),
                )
                _token_cache.set(token, user)
                return user

            return None

    except Exception as e:
        logger.error(f"AINative token validation error: {e}")
        return None


def clear_token_cache() -> None:
    """Clear the entire token validation cache."""
    global _token_cache
    _token_cache = TokenValidationCache()
