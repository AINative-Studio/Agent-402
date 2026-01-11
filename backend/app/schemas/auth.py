"""
JWT authentication schemas for request/response validation.
Implements Epic 2 Story 4: JWT authentication as alternative to X-API-Key.
"""
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

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "user_1"
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
