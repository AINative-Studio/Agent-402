"""
Project API Models - Contract-First Design

These models define the exact API contract for project creation
and management, aligned with PRD §6 and backlog Epic 1.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator


class ProjectTier(str, Enum):
    """
    Valid project tiers.
    Following ZeroDB DX Contract - these are stable values.
    As per GitHub Issue #58: free, starter, professional, enterprise
    """
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ProjectStatus(str, Enum):
    """
    Project status values.
    ACTIVE is the default and only MVP status.
    """
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class ProjectCreate(BaseModel):
    """
    Request model for POST /v1/public/projects

    Following DX Contract requirements:
    - name: required, 1-255 chars
    - description: optional, max 1000 chars
    - tier: required, must be valid ProjectTier
    - database_enabled: boolean, default True
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Project name (required)",
        example="My Fintech Agent Project"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Project description (optional)",
        example="Autonomous fintech agent crew with X402 signing"
    )
    tier: str = Field(
        ...,
        description="Project tier (required): free, starter, professional, enterprise",
        example="free"
    )
    database_enabled: bool = Field(
        True,
        description="Enable database features (vectors, tables, events)",
        example=True
    )

    @validator('name')
    def validate_name(cls, v):
        """Ensure name is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        """Trim description if provided"""
        if v is not None:
            return v.strip() if v.strip() else None
        return v

    @validator('tier')
    def validate_tier(cls, v):
        """
        Validate tier against allowed values.
        This ensures we return INVALID_TIER error for invalid tiers.
        GitHub Issue #58 requirement.
        """
        if not v:
            raise ValueError("tier cannot be empty")

        # Normalize to lowercase for comparison
        tier_lower = v.lower().strip()

        # Check against valid tier values
        valid_tiers = [tier.value for tier in ProjectTier]

        if tier_lower not in valid_tiers:
            # Raise ValueError with the exact format expected by our error handler
            raise ValueError(
                f"Invalid tier '{v}'. Valid options are: {', '.join(valid_tiers)}"
            )

        return tier_lower

    class Config:
        use_enum_values = True


class ProjectResponse(BaseModel):
    """
    Response model for project operations.

    Following PRD §6 and backlog Epic 1:
    - Returns id, name, status, tier, created_at
    - Status always ACTIVE for MVP
    """
    id: str = Field(
        ...,
        description="Unique project ID (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    name: str = Field(
        ...,
        description="Project name",
        example="My Fintech Agent Project"
    )
    description: Optional[str] = Field(
        None,
        description="Project description",
        example="Autonomous fintech agent crew"
    )
    status: ProjectStatus = Field(
        ...,
        description="Project status",
        example="ACTIVE"
    )
    tier: ProjectTier = Field(
        ...,
        description="Project tier",
        example="free"
    )
    database_enabled: bool = Field(
        ...,
        description="Database features enabled",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="Project creation timestamp (ISO 8601)",
        example="2025-12-13T22:41:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp (ISO 8601)",
        example="2025-12-13T22:41:00Z"
    )

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectListResponse(BaseModel):
    """
    Response model for GET /v1/public/projects

    Returns paginated list of projects.
    """
    projects: list[ProjectResponse] = Field(
        ...,
        description="List of projects"
    )
    total: int = Field(
        ...,
        description="Total number of projects",
        example=5
    )
    limit: int = Field(
        ...,
        description="Page size limit",
        example=100
    )
    offset: int = Field(
        ...,
        description="Pagination offset",
        example=0
    )

    class Config:
        use_enum_values = True
