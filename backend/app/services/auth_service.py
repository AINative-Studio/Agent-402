"""
Authentication service for JWT token management.

Implements Epic 2 Story 4: JWT authentication as alternative to X-API-Key.

This service provides:
- JWT access token generation
- Refresh token generation and validation
- User info retrieval from JWT tokens
- Token claims validation
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.core.config import settings
from app.core.jwt import (
    create_access_token,
    decode_access_token,
    TokenExpiredError,
    InvalidJWTError
)
from app.core.errors import (
    InvalidAPIKeyError,
    InvalidTokenError as InvalidTokenAPIError,
    TokenExpiredAPIError
)
from app.schemas.auth import TokenPayload


# Refresh token expiration is typically longer than access token
# Default: 7 days (604800 seconds)
REFRESH_TOKEN_EXPIRATION_SECONDS = 604800


@dataclass
class UserInfo:
    """User information extracted from authentication."""
    user_id: str
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    token_type: str = "access"


class AuthService:
    """
    Authentication service for JWT token operations.

    Provides centralized authentication logic for:
    - Token generation (access and refresh)
    - Token validation and refresh
    - User info extraction
    """

    def __init__(self):
        """Initialize auth service with settings."""
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm
        self.access_token_expiration = settings.jwt_expiration_seconds
        self.refresh_token_expiration = REFRESH_TOKEN_EXPIRATION_SECONDS

    def login_with_api_key(self, api_key: str) -> Tuple[str, str, int]:
        """
        Authenticate with API key and return access and refresh tokens.

        Args:
            api_key: API key to validate

        Returns:
            Tuple of (access_token, refresh_token, expires_in)

        Raises:
            InvalidAPIKeyError: If API key is invalid
        """
        # Validate API key and get user ID
        user_id = settings.get_user_id_from_api_key(api_key)

        if not user_id:
            raise InvalidAPIKeyError("Invalid API key")

        # Generate tokens
        access_token, expires_in = create_access_token(user_id)
        refresh_token = self._create_refresh_token(user_id)

        return access_token, refresh_token, expires_in

    def refresh_access_token(self, refresh_token: str) -> Tuple[str, int]:
        """
        Refresh an access token using a valid refresh token.

        Args:
            refresh_token: Refresh token to validate

        Returns:
            Tuple of (new_access_token, expires_in)

        Raises:
            TokenExpiredAPIError: If refresh token has expired
            InvalidTokenAPIError: If refresh token is invalid
        """
        try:
            # Decode the refresh token
            payload = jwt.decode(
                refresh_token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                leeway=10,  # Allow 10 seconds clock skew
                options={"verify_iat": False}  # Don't verify iat to avoid timing issues
            )

            # Verify this is a refresh token
            if payload.get("token_type") != "refresh":
                raise InvalidTokenAPIError("Invalid token type: expected refresh token")

            # Extract user ID
            user_id = payload.get("user_id")
            if not user_id:
                raise InvalidTokenAPIError("Token missing user_id claim")

            # Generate new access token
            access_token, expires_in = create_access_token(user_id)

            return access_token, expires_in

        except ExpiredSignatureError:
            raise TokenExpiredAPIError("Refresh token has expired")
        except InvalidTokenError as e:
            raise InvalidTokenAPIError(f"Invalid refresh token: {str(e)}")

    def get_user_info(self, token: str) -> UserInfo:
        """
        Extract user information from a valid access token.

        Args:
            token: JWT access token

        Returns:
            UserInfo with user details

        Raises:
            TokenExpiredAPIError: If token has expired
            InvalidTokenAPIError: If token is invalid
        """
        try:
            token_data = decode_access_token(token)

            return UserInfo(
                user_id=token_data.user_id,
                issued_at=datetime.utcfromtimestamp(token_data.iat),
                expires_at=datetime.utcfromtimestamp(token_data.exp),
                token_type=token_data.token_type
            )

        except TokenExpiredError:
            raise TokenExpiredAPIError("JWT token has expired")
        except InvalidJWTError as e:
            raise InvalidTokenAPIError(f"Invalid JWT token: {str(e)}")

    def _create_refresh_token(self, user_id: str) -> str:
        """
        Create a refresh token for the given user.

        Refresh tokens have longer expiration and are used to obtain
        new access tokens without re-authenticating.

        Args:
            user_id: User ID to encode in the token

        Returns:
            JWT refresh token string
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")

        # Calculate timestamps using time.time() for proper UTC timestamp
        import time
        now_timestamp = int(time.time())
        expire_timestamp = now_timestamp + self.refresh_token_expiration

        # Create refresh token payload
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "exp": expire_timestamp,
            "iat": now_timestamp,
            "token_type": "refresh"
        }

        # Encode JWT token
        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )

        return token


# Singleton instance for dependency injection
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Get the auth service instance."""
    return auth_service
