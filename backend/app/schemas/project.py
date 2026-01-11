"""
Project API schemas for request/response validation.
These schemas define the contract with API consumers per DX Contract.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.project import ProjectStatus, ProjectTier


class ProjectResponse(BaseModel):
    """
    Project response schema for GET /v1/public/projects.
    Per Epic 1 Story 2: id, name, status, tier.
    """
    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(..., description="Project status (ACTIVE, INACTIVE, SUSPENDED)")
    tier: ProjectTier = Field(..., description="Project tier (FREE, STARTER, PRO, ENTERPRISE)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "proj_abc123",
                "name": "My Agent Project",
                "status": "ACTIVE",
                "tier": "FREE"
            }
        }


class ProjectListResponse(BaseModel):
    """
    Response schema for listing projects.
    Returns array of projects for authenticated user.
    """
    projects: List[ProjectResponse] = Field(
        default_factory=list,
        description="List of projects owned by the authenticated user"
    )
    total: int = Field(..., description="Total number of projects")

    class Config:
        json_schema_extra = {
            "example": {
                "projects": [
                    {
                        "id": "proj_abc123",
                        "name": "My Agent Project",
                        "status": "ACTIVE",
                        "tier": "FREE"
                    },
                    {
                        "id": "proj_xyz789",
                        "name": "Production Project",
                        "status": "ACTIVE",
                        "tier": "PRO"
                    }
                ],
                "total": 2
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response per DX Contract.
    All errors return { detail, error_code }.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid or missing API key",
                "error_code": "INVALID_API_KEY"
            }
        }
