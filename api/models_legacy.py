"""
API Models and Schemas
Defines Pydantic models for request/response validation
"""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectTier(str, Enum):
    """
    Valid project tier values.
    As per DX Contract, these are the only allowed values.
    """
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ProjectStatus(str, Enum):
    """Project status values"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    tier: str = Field(..., description="Project tier (free, starter, professional, enterprise)")
    database_enabled: bool = Field(default=True, description="Enable database features")

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """
        Validate tier against allowed values.
        This ensures we return INVALID_TIER error for invalid tiers.
        """
        # Normalize to lowercase for comparison
        tier_lower = v.lower().strip()

        # Check against valid tier values
        valid_tiers = [tier.value for tier in ProjectTier]

        if tier_lower not in valid_tiers:
            # Raise ValueError which will be caught and converted to 422 with INVALID_TIER
            raise ValueError(
                f"Invalid tier '{v}'. Valid options are: {', '.join(valid_tiers)}"
            )

        return tier_lower


class ProjectResponse(BaseModel):
    """Response model for project data"""
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    tier: str = Field(..., description="Project tier")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="Project status")
    database_enabled: bool = Field(..., description="Database features enabled")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    As per DX Contract §6, all errors must return { detail, error_code }
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")


class ValidationErrorDetail(BaseModel):
    """Validation error detail structure (Pydantic format)"""
    loc: list = Field(..., description="Location of the error (field path)")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """
    Response for validation errors (HTTP 422).
    Includes both standard error format and validation details.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    validation_errors: Optional[list[ValidationErrorDetail]] = Field(
        None,
        description="Detailed validation errors"
    )
