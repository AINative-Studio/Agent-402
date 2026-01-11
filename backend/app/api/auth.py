"""
Authentication API endpoints.
Implements Epic 2 Story 4: JWT authentication via POST /v1/public/auth/login.

Provides:
- POST /v1/public/auth/login - Exchange API key for JWT tokens
- POST /v1/public/auth/refresh - Refresh expired access tokens
- GET /v1/public/auth/me - Get current authenticated user info
"""
from fastapi import APIRouter, Header, status
from typing import Optional
from app.core.config import settings
from app.core.errors import InvalidAPIKeyError
from app.core.jwt import extract_token_from_header
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserInfoResponse
)
from app.schemas.project import ErrorResponse
from app.services.auth_service import get_auth_service


router = APIRouter(
    prefix="/v1/public/auth",
    tags=["authentication"]
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully authenticated, JWT tokens returned",
            "model": TokenResponse
        },
        401: {
            "description": "Invalid API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error - missing or invalid request body"
        }
    },
    summary="Login with API key to receive JWT tokens",
    description="""
    Exchange an API key for JWT access and refresh tokens.

    **Epic 2 Story 4:** Optional JWT authentication as alternative to X-API-Key

    **Authentication:** None required for this endpoint (public login endpoint)

    **Request:**
    - `api_key`: Valid API key to exchange for JWT tokens

    **Response:**
    - `access_token`: JWT token for subsequent API requests
    - `refresh_token`: Long-lived token for refreshing access tokens
    - `token_type`: Always "bearer"
    - `expires_in`: Access token expiration time in seconds (default: 3600)
    - `user_id`: User ID associated with the API key

    **Usage:**
    After receiving the JWT token, include it in subsequent requests:
    ```
    Authorization: Bearer <access_token>
    ```

    **DX Contract:**
    - JWT tokens include user context in claims
    - JWT can be used as alternative to X-API-Key
    - Invalid API keys return 401 INVALID_API_KEY
    - Token expiration is configurable (default: 1 hour)

    **Security:**
    - Tokens are signed with HMAC-SHA256
    - Expired tokens are rejected automatically
    - Each token includes issued-at and expiration timestamps
    - Refresh tokens have longer expiration (7 days)
    """
)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Login endpoint to exchange API key for JWT tokens.

    Args:
        request: LoginRequest containing API key

    Returns:
        TokenResponse with JWT access token, refresh token, and metadata

    Raises:
        InvalidAPIKeyError: If API key is invalid (401)
    """
    auth_service = get_auth_service()

    # Authenticate and get tokens
    access_token, refresh_token, expires_in = auth_service.login_with_api_key(
        request.api_key
    )

    # Get user ID for response
    user_id = settings.get_user_id_from_api_key(request.api_key)

    # Return token response
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user_id,
        refresh_token=refresh_token
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully refreshed access token",
            "model": RefreshTokenResponse
        },
        401: {
            "description": "Invalid or expired refresh token",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error - missing or invalid request body"
        }
    },
    summary="Refresh access token using refresh token",
    description="""
    Obtain a new access token using a valid refresh token.

    **Epic 2 Story 4:** JWT token refresh for long-lived sessions

    **Authentication:** None required (refresh token is used for authentication)

    **Request:**
    - `refresh_token`: Valid refresh token from login response

    **Response:**
    - `access_token`: New JWT access token
    - `token_type`: Always "bearer"
    - `expires_in`: Token expiration time in seconds

    **Usage:**
    When the access token expires, use the refresh token to get a new one:
    ```json
    POST /v1/public/auth/refresh
    { "refresh_token": "<refresh_token>" }
    ```

    **Security:**
    - Refresh tokens are validated before issuing new access tokens
    - Expired refresh tokens return 401 TOKEN_EXPIRED
    - Invalid refresh tokens return 401 INVALID_TOKEN
    """
)
async def refresh_token(request: RefreshTokenRequest) -> RefreshTokenResponse:
    """
    Refresh access token endpoint.

    Args:
        request: RefreshTokenRequest containing refresh token

    Returns:
        RefreshTokenResponse with new access token

    Raises:
        TokenExpiredAPIError: If refresh token has expired (401)
        InvalidTokenAPIError: If refresh token is invalid (401)
    """
    auth_service = get_auth_service()

    # Refresh and get new access token
    access_token, expires_in = auth_service.refresh_access_token(
        request.refresh_token
    )

    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Current user information",
            "model": UserInfoResponse
        },
        401: {
            "description": "Invalid or missing authentication",
            "model": ErrorResponse
        }
    },
    summary="Get current authenticated user info",
    description="""
    Retrieve information about the currently authenticated user.

    **Epic 2 Story 4:** User info endpoint for JWT authentication

    **Authentication:** Requires valid JWT Bearer token

    **Headers:**
    - `Authorization: Bearer <access_token>` - JWT access token (required)

    **Response:**
    - `user_id`: User ID from the JWT token
    - `issued_at`: Token issued timestamp (ISO 8601)
    - `expires_at`: Token expiration timestamp (ISO 8601)
    - `token_type`: Type of token (always "access")

    **Usage:**
    Use this endpoint to verify authentication and get user context:
    ```
    GET /v1/public/auth/me
    Authorization: Bearer <access_token>
    ```

    **Security:**
    - Requires valid JWT access token
    - Returns user info from token claims
    - Expired tokens return 401 TOKEN_EXPIRED
    """
)
async def get_current_user_info(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> UserInfoResponse:
    """
    Get current user info endpoint.

    Requires JWT Bearer token in Authorization header.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        UserInfoResponse with authenticated user details

    Raises:
        InvalidAPIKeyError: If no authorization header provided (401)
        TokenExpiredAPIError: If token has expired (401)
        InvalidTokenAPIError: If token is invalid (401)
    """
    # Check for Authorization header
    if not authorization:
        raise InvalidAPIKeyError(
            "Authentication required. Provide Authorization Bearer token."
        )

    # Extract token from header
    token = extract_token_from_header(authorization)
    if not token:
        raise InvalidAPIKeyError(
            "Invalid Authorization header format. Expected: Bearer <token>"
        )

    # Get user info from token
    auth_service = get_auth_service()
    user_info = auth_service.get_user_info(token)

    return UserInfoResponse(
        user_id=user_info.user_id,
        issued_at=user_info.issued_at,
        expires_at=user_info.expires_at,
        token_type=user_info.token_type
    )
