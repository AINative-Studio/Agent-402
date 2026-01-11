"""
Project API endpoints.

Implements project creation and listing with tier-based limits.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import verify_api_key
from app.core.exceptions import ProjectNotFoundError, UnauthorizedError
from app.models.project import ProjectCreate, ProjectListResponse, ProjectResponse
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="""
Create a new ZeroDB project.

**Project Limits by Tier:**
- Free: 3 projects
- Starter: 10 projects
- Pro: 50 projects
- Enterprise: Unlimited

**Error Codes:**
- `INVALID_TIER`: Invalid tier specified
- `PROJECT_LIMIT_EXCEEDED`: User has reached their project limit for the tier
- `INVALID_API_KEY`: Missing or invalid API key

**Example Request:**
```json
{
  "name": "my-agent-project",
  "description": "Agent memory and compliance tracking",
  "tier": "free",
  "database_enabled": true
}
```

**Example Error Response (HTTP 429):**
```json
{
  "detail": "Project limit exceeded for tier 'free'. Current projects: 3/3. Please upgrade to 'starter' tier for higher limits, or contact support at support@ainative.studio.",
  "error_code": "PROJECT_LIMIT_EXCEEDED"
}
```
""",
    responses={
        201: {
            "description": "Project created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "my-agent-project",
                        "description": "Agent memory and compliance tracking",
                        "tier": "free",
                        "status": "ACTIVE",
                        "database_enabled": True,
                        "created_at": "2025-12-13T22:41:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or missing API key. Please provide a valid X-API-Key header.",
                        "error_code": "INVALID_API_KEY"
                    }
                }
            }
        },
        422: {
            "description": "Invalid tier",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid tier 'premium'. Valid tiers are: free, starter, pro, enterprise.",
                        "error_code": "INVALID_TIER"
                    }
                }
            }
        },
        429: {
            "description": "Project limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Project limit exceeded for tier 'free'. Current projects: 3/3. Please upgrade to 'starter' tier for higher limits, or contact support at support@ainative.studio.",
                        "error_code": "PROJECT_LIMIT_EXCEEDED"
                    }
                }
            }
        }
    }
)
async def create_project(
    project_data: ProjectCreate,
    user_id: Annotated[str, Depends(verify_api_key)]
) -> ProjectResponse:
    """
    Create a new project.

    Validates project limits based on the requested tier.
    Raises PROJECT_LIMIT_EXCEEDED if the user has reached their limit.
    """
    return project_service.create_project(user_id, project_data)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects",
    description="""
List all projects for the authenticated user.

Supports pagination via `limit` and `offset` query parameters.

**Example Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "my-agent-project",
      "tier": "free",
      "status": "ACTIVE",
      "database_enabled": true,
      "created_at": "2025-12-13T22:41:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```
""",
    responses={
        200: {"description": "List of projects"},
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or missing API key. Please provide a valid X-API-Key header.",
                        "error_code": "INVALID_API_KEY"
                    }
                }
            }
        }
    }
)
async def list_projects(
    user_id: Annotated[str, Depends(verify_api_key)],
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of projects to return"),
    offset: int = Query(default=0, ge=0, description="Number of projects to skip")
) -> ProjectListResponse:
    """
    List projects for the authenticated user.
    """
    projects, total = project_service.list_projects(user_id, limit=limit, offset=offset)

    return ProjectListResponse(
        items=projects,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by ID",
    description="""
Get a single project by its unique identifier.

The authenticated user must be the owner of the project to access it.

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-agent-project",
  "description": "Agent memory and compliance tracking",
  "tier": "free",
  "status": "ACTIVE",
  "database_enabled": true,
  "created_at": "2025-12-13T22:41:00Z"
}
```
""",
    responses={
        200: {
            "description": "Project details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "my-agent-project",
                        "description": "Agent memory and compliance tracking",
                        "tier": "free",
                        "status": "ACTIVE",
                        "database_enabled": True,
                        "created_at": "2025-12-13T22:41:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or missing API key. Please provide a valid X-API-Key header.",
                        "error_code": "INVALID_API_KEY"
                    }
                }
            }
        },
        403: {
            "description": "Not authorized to access this project",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authorized to access this resource",
                        "error_code": "UNAUTHORIZED"
                    }
                }
            }
        },
        404: {
            "description": "Project not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Project not found: 550e8400-e29b-41d4-a716-446655440000",
                        "error_code": "PROJECT_NOT_FOUND"
                    }
                }
            }
        },
        422: {
            "description": "Invalid project ID format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid UUID format",
                        "error_code": "VALIDATION_ERROR"
                    }
                }
            }
        }
    }
)
async def get_project_by_id(
    project_id: UUID,
    user_id: Annotated[str, Depends(verify_api_key)]
) -> ProjectResponse:
    """
    Get a single project by ID.

    Args:
        project_id: UUID of the project to retrieve
        user_id: User ID from API key (injected by dependency)

    Returns:
        ProjectResponse with project details

    Raises:
        ProjectNotFoundError: Project doesn't exist (404)
        UnauthorizedError: User doesn't own project (403)
    """
    project = project_service.get_project(user_id, project_id)

    if project is None:
        raise ProjectNotFoundError(project_id=str(project_id))

    return project
