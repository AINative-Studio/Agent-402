"""
JWT token generation and validation utilities.
Implements Epic 2 Story 4: JWT authentication as alternative to X-API-Key.
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from app.core.config import settings
from app.schemas.auth import TokenPayload


class JWTTokenError(Exception):
    """Base exception for JWT token errors."""
    pass


class TokenExpiredError(JWTTokenError):
    """Raised when JWT token has expired."""
    pass


class InvalidJWTError(JWTTokenError):
    """Raised when JWT token is invalid."""
    pass


def create_access_token(user_id: str) -> tuple[str, int]:
    """
    Create a new JWT access token for the given user.

    Args:
        user_id: User ID to encode in the token

    Returns:
        Tuple of (token_string, expires_in_seconds)

    Raises:
        ValueError: If user_id is empty or None
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")

    # Calculate expiration time
    now = datetime.utcnow()
    expires_delta = timedelta(seconds=settings.jwt_expiration_seconds)
    expire = now + expires_delta

    # Create token payload
    payload = {
        "sub": user_id,  # Subject claim
        "user_id": user_id,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "token_type": "access"
    }

    # Encode JWT token
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return token, settings.jwt_expiration_seconds


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        TokenPayload with decoded claims

    Raises:
        TokenExpiredError: If token has expired
        InvalidJWTError: If token is invalid or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Validate required claims
        if "sub" not in payload or "user_id" not in payload:
            raise InvalidJWTError("Token missing required claims")

        # Create TokenPayload from decoded data
        token_data = TokenPayload(
            sub=payload["sub"],
            user_id=payload["user_id"],
            exp=payload["exp"],
            iat=payload["iat"],
            token_type=payload.get("token_type", "access")
        )

        return token_data

    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")

    except InvalidTokenError as e:
        raise InvalidJWTError(f"Invalid token: {str(e)}")


def verify_token(token: str) -> Optional[str]:
    """
    Verify a JWT token and return the user_id if valid.

    Args:
        token: JWT token string to verify

    Returns:
        User ID if token is valid, None if invalid

    This is a convenience method for authentication middleware.
    """
    try:
        token_data = decode_access_token(token)
        return token_data.user_id
    except (TokenExpiredError, InvalidJWTError):
        return None


def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization_header: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string if valid format, None otherwise

    The header must be in format: "Bearer <token>"
    """
    if not authorization_header:
        return None

    parts = authorization_header.split()

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer":
        return None

    return token
