"""
Projects API endpoints.
Implements GET /v1/public/projects per Epic 1 Story 2.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user
from app.schemas.project import ProjectResponse, ProjectListResponse, ErrorResponse
from app.services.project_service import project_service


router = APIRouter(
    prefix="/v1/public",
    tags=["projects"]
)


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved projects list",
            "model": ProjectListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List user projects",
    description="""
    List all projects for the authenticated user.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Array of projects with id, name, status, tier
    - Empty array if no projects exist

    **Per PRD §9:** Demo setup is deterministic with predefined projects.

    **Per Epic 1 Story 2:**
    - Filters projects by user's API key
    - Returns empty array if no projects exist
    - Consistently shows status: ACTIVE for demo projects
    """
)
async def list_projects(
    current_user: str = Depends(get_current_user)
) -> ProjectListResponse:
    """
    List all projects for authenticated user.

    Args:
        current_user: User ID from X-API-Key authentication

    Returns:
        ProjectListResponse with list of projects and total count
    """
    # Get projects for user
    projects = project_service.list_user_projects(current_user)

    # Convert to response models
    project_responses: List[ProjectResponse] = [
        ProjectResponse(
            id=project.id,
            name=project.name,
            status=project.status,
            tier=project.tier
        )
        for project in projects
    ]

    return ProjectListResponse(
        projects=project_responses,
        total=len(project_responses)
    )
