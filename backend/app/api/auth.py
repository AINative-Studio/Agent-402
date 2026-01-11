"""
Authentication API endpoints.
Implements Epic 2 Story 4: JWT authentication via POST /v1/public/auth/login.
"""
from fastapi import APIRouter, status
from app.core.config import settings
from app.core.errors import InvalidAPIKeyError
from app.core.jwt import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.project import ErrorResponse


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
            "description": "Successfully authenticated, JWT token returned",
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
    summary="Login with API key to receive JWT token",
    description="""
    Exchange an API key for a JWT access token.

    **Epic 2 Story 4:** Optional JWT authentication as alternative to X-API-Key

    **Authentication:** None required for this endpoint (public login endpoint)

    **Request:**
    - `api_key`: Valid API key to exchange for JWT token

    **Response:**
    - `access_token`: JWT token for subsequent API requests
    - `token_type`: Always "bearer"
    - `expires_in`: Token expiration time in seconds (default: 3600)
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
    """
)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Login endpoint to exchange API key for JWT token.

    Args:
        request: LoginRequest containing API key

    Returns:
        TokenResponse with JWT access token and metadata

    Raises:
        InvalidAPIKeyError: If API key is invalid (401)
    """
    # Validate API key and get user ID
    user_id = settings.get_user_id_from_api_key(request.api_key)

    if not user_id:
        raise InvalidAPIKeyError("Invalid API key")

    # Generate JWT access token
    access_token, expires_in = create_access_token(user_id)

    # Return token response
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user_id
    )
