"""
JWT authentication schemas for request/response validation.
Implements Epic 2 Story 4: JWT authentication as alternative to X-API-Key.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """
    Login request schema for POST /v1/public/auth/login.

    Per Epic 2 Story 4: Accept credentials and return JWT token.
    """
    api_key: str = Field(
        ...,
        description="API key to exchange for JWT token",
        min_length=1,
        example="demo_key_user1_abc123"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "demo_key_user1_abc123"
            }
        }


class TokenResponse(BaseModel):
    """
    JWT token response schema.

    Returns access token and metadata for client use.
    Per DX Contract: JWT should include user/project context.
    """
    access_token: str = Field(
        ...,
        description="JWT access token for authentication"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds"
    )
    user_id: str = Field(
        ...,
        description="User ID associated with the token"
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="Refresh token for obtaining new access tokens"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "user_1",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request schema for POST /v1/public/auth/refresh.

    Per Epic 2 Story 4: Support token refresh for long-lived sessions.
    """
    refresh_token: str = Field(
        ...,
        description="Refresh token from login response",
        min_length=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """
    Response schema for token refresh endpoint.

    Returns new access token with same format as login.
    """
    access_token: str = Field(
        ...,
        description="New JWT access token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class UserInfoResponse(BaseModel):
    """
    User info response schema for GET /v1/public/auth/me.

    Returns authenticated user details from JWT token.
    Per Epic 2 Story 4: JWT should include user/project context.
    """
    user_id: str = Field(
        ...,
        description="User ID from the JWT token"
    )
    issued_at: Optional[datetime] = Field(
        default=None,
        description="Token issued at timestamp (ISO 8601)"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp (ISO 8601)"
    )
    token_type: str = Field(
        default="access",
        description="Type of token used for authentication"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_1",
                "issued_at": "2024-01-15T10:30:00Z",
                "expires_at": "2024-01-15T11:30:00Z",
                "token_type": "access"
            }
        }


class TokenPayload(BaseModel):
    """
    JWT token payload structure.

    Internal model for encoding/decoding JWT claims.
    Per Epic 2 Story 4: JWT should include user/project context.
    """
    sub: str = Field(..., description="Subject (user_id)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    user_id: str = Field(..., description="User ID")
    token_type: str = Field(default="access", description="Token type")
