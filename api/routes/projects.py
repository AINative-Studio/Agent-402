"""
Projects API Routes

Implements POST /v1/public/projects endpoint.
Following GitHub issue #56 requirements.

PRD Alignment:
- §6 ZeroDB Integration
- §10 Success Criteria (deterministic errors, auditability)

Backlog Alignment:
- Epic 1: Public Projects API
- Story 1: Create project endpoint (2 pts)
"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from api.models import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
)
from api.middleware import verify_api_key
from api.services import ZeroDBService


router = APIRouter(prefix="/v1/public", tags=["Projects"])


class ProjectError(HTTPException):
    """Custom project error with error_code"""
    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        error_code: str = "PROJECT_ERROR"
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


def get_zerodb_service() -> ZeroDBService:
    """Dependency to get ZeroDB service instance"""
    return ZeroDBService()


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="""
    Create a new project with the specified configuration.

    **Authentication:** Requires X-API-Key header

    **Request Body:**
    - name: Project name (required, 1-255 chars)
    - description: Project description (optional, max 1000 chars)
    - tier: Project tier - FREE, STARTER, PRO, or ENTERPRISE (required)
    - database_enabled: Enable database features (default: true)

    **Response:**
    Returns the created project with:
    - id: Unique project UUID
    - name: Project name
    - status: Always "ACTIVE" for newly created projects
    - tier: Project tier
    - created_at: ISO 8601 timestamp

    **Error Codes:**
    - 401 INVALID_API_KEY: Missing or invalid API key
    - 422 Validation Error: Invalid input data
    - 400 INVALID_TIER: Invalid tier specified
    - 429 PROJECT_LIMIT_EXCEEDED: Project limit for tier exceeded
    - 500 ZERODB_ERROR: Internal ZeroDB error
    """,
    responses={
        201: {
            "description": "Project created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "My Fintech Agent Project",
                        "status": "ACTIVE",
                        "tier": "FREE",
                        "created_at": "2025-12-13T22:41:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid tier",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid tier: INVALID. Must be one of: FREE, STARTER, PRO, ENTERPRISE",
                        "error_code": "INVALID_TIER"
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key",
                        "error_code": "INVALID_API_KEY"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        },
        429: {
            "description": "Project limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Project limit exceeded for tier FREE (max: 3)",
                        "error_code": "PROJECT_LIMIT_EXCEEDED"
                    }
                }
            }
        }
    }
)
async def create_project(
    project: ProjectCreate,
    api_key: str = Depends(verify_api_key),
    db: ZeroDBService = Depends(get_zerodb_service)
) -> ProjectResponse:
    """
    Create a new project.

    This endpoint creates a project with the specified configuration.
    The project is persisted to ZeroDB and can be used to scope
    all subsequent API operations.

    Following DX Contract:
    - Deterministic error responses
    - Append-only data model
    - Clear error codes

    Args:
        project: Project creation request
        api_key: Validated API key from header
        db: ZeroDB service instance

    Returns:
        ProjectResponse: Created project details

    Raises:
        ProjectError: On validation or creation failure
    """
    try:
        # For MVP: Use ZeroDB MCP tool to create the actual project
        # This calls the ZeroDB project creation API
        project_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        # Create the project using MCP tool
        # This is a placeholder - in production this would call ZeroDB's create project API
        # For now we'll use environment variable for project ID
        storage_project_id = os.getenv("ZERODB_PROJECT_ID", "").strip()

        if not storage_project_id:
            raise ProjectError(
                detail="Server configuration error: ZERODB_PROJECT_ID not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="CONFIGURATION_ERROR"
            )

        # Ensure projects table exists in the storage project
        try:
            db.ensure_projects_table(storage_project_id)
        except Exception as e:
            # Non-fatal - table might already exist
            pass

        # Insert project record
        project_data = {
            "id": project_id,
            "name": project.name,
            "description": project.description,
            "tier": project.tier.value,
            "status": ProjectStatus.ACTIVE.value,
            "database_enabled": project.database_enabled,
            "created_at": created_at.isoformat()
        }

        try:
            db.insert_project_record(storage_project_id, project_data)
        except Exception as e:
            error_msg = str(e)
            if "limit" in error_msg.lower() or "quota" in error_msg.lower():
                raise ProjectError(
                    detail=f"Project limit exceeded for tier {project.tier.value}",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    error_code="PROJECT_LIMIT_EXCEEDED"
                )
            raise ProjectError(
                detail=f"Failed to create project: {error_msg}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="ZERODB_ERROR"
            )

        # Return successful response
        return ProjectResponse(
            id=project_id,
            name=project.name,
            status=ProjectStatus.ACTIVE,
            tier=project.tier,
            created_at=created_at
        )

    except ProjectError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise ProjectError(
            detail=f"Unexpected error creating project: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR"
        )
