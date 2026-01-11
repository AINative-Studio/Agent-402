"""
Project data models for ZeroDB Public API.

Defines request/response schemas for project operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from app.core.config import Tier


class ProjectCreate(BaseModel):
    """Request schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    tier: str = Field(default=Tier.FREE, description="Project tier (free, starter, pro, enterprise)")
    database_enabled: bool = Field(default=True, description="Enable database features")

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """Ensure tier is lowercase and valid."""
        tier_lower = v.lower()
        valid_tiers = [t.value for t in Tier]
        if tier_lower not in valid_tiers:
            from app.core.exceptions import InvalidTierException
            raise InvalidTierException(tier=v, valid_tiers=valid_tiers)
        return tier_lower

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "my-agent-project",
                    "description": "Agent memory and compliance tracking",
                    "tier": "free",
                    "database_enabled": True
                }
            ]
        }
    }


class ProjectResponse(BaseModel):
    """Response schema for project operations."""

    id: UUID = Field(default_factory=uuid4, description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    tier: str = Field(..., description="Project tier")
    status: str = Field(default="ACTIVE", description="Project status")
    database_enabled: bool = Field(..., description="Database features enabled")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "my-agent-project",
                    "description": "Agent memory and compliance tracking",
                    "tier": "free",
                    "status": "ACTIVE",
                    "database_enabled": True,
                    "created_at": "2025-12-13T22:41:00Z"
                }
            ]
        }
    }


class ProjectListResponse(BaseModel):
    """Response schema for listing projects."""

    items: list[ProjectResponse] = Field(default_factory=list, description="List of projects")
    total: int = Field(..., description="Total number of projects")
    limit: int = Field(default=50, description="Maximum items per page")
    offset: int = Field(default=0, description="Pagination offset")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "my-agent-project",
                            "tier": "free",
                            "status": "ACTIVE",
                            "database_enabled": True,
                            "created_at": "2025-12-13T22:41:00Z"
                        }
                    ],
                    "total": 1,
                    "limit": 50,
                    "offset": 0
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str = Field(..., description="Human-readable error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Project limit exceeded for tier 'free'. Current projects: 3/3. Please upgrade to 'starter' tier for higher limits, or contact support at support@ainative.studio.",
                    "error_code": "PROJECT_LIMIT_EXCEEDED"
                }
            ]
        }
    }
