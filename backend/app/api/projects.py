"""
Projects API endpoints.
Implements GET /v1/public/projects per Epic 1 Story 2.

Issue #123: Enhanced with agent associations, task tracking,
payment linking, and status workflow endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from app.core.auth import get_current_user
from app.schemas.project import (
    ProjectResponse,
    ProjectListResponse,
    ErrorResponse,
    ProjectAgentAssociationRequest,
    ProjectAgentAssociationResponse,
    ProjectAgentListResponse,
    ProjectTaskTrackRequest,
    ProjectTaskResponse,
    ProjectTaskListResponse,
    ProjectPaymentLinkRequest,
    ProjectPaymentResponse,
    ProjectPaymentSummaryResponse,
    ProjectStatusUpdateRequest,
    AgentRole
)
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

    **Per PRD SS9:** Demo setup is deterministic with predefined projects.

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


# Issue #123: Agent association endpoints


@router.post(
    "/projects/{project_id}/agents",
    response_model=ProjectAgentAssociationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Agent successfully associated with project",
            "model": ProjectAgentAssociationResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        },
        409: {
            "description": "Agent already associated",
            "model": ErrorResponse
        },
        422: {
            "description": "Invalid role value",
            "model": ErrorResponse
        }
    },
    summary="Associate agent with project",
    description="""
    Associate an agent with a project.

    **Issue #123:** Project-agent associations for task management.

    **Roles:** executor, observer, admin, member (default)
    """
)
async def associate_agent(
    project_id: str,
    request: ProjectAgentAssociationRequest,
    current_user: str = Depends(get_current_user)
) -> ProjectAgentAssociationResponse:
    """
    Associate an agent with a project.

    Args:
        project_id: Project identifier
        request: Agent association request
        current_user: Authenticated user ID

    Returns:
        ProjectAgentAssociationResponse with association details
    """
    association = project_service.associate_agent(
        project_id=project_id,
        user_id=current_user,
        agent_did=request.agent_did,
        role=request.role.value if isinstance(request.role, AgentRole) else request.role
    )

    return ProjectAgentAssociationResponse(
        project_id=association["project_id"],
        agent_did=association["agent_did"],
        role=association["role"],
        associated_at=association["associated_at"]
    )


@router.delete(
    "/projects/{project_id}/agents/{agent_did:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Agent successfully disassociated"
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project or agent not found",
            "model": ErrorResponse
        }
    },
    summary="Disassociate agent from project",
    description="""
    Remove an agent's association with a project.

    **Issue #123:** Project-agent associations for task management.
    """
)
async def disassociate_agent(
    project_id: str,
    agent_did: str,
    current_user: str = Depends(get_current_user)
):
    """
    Disassociate an agent from a project.

    Args:
        project_id: Project identifier
        agent_did: Agent DID to disassociate
        current_user: Authenticated user ID

    Returns:
        No content on success
    """
    project_service.disassociate_agent(
        project_id=project_id,
        user_id=current_user,
        agent_did=agent_did
    )
    return None


@router.get(
    "/projects/{project_id}/agents",
    response_model=ProjectAgentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved agents list",
            "model": ProjectAgentListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="List project agents",
    description="""
    List all agents associated with a project.

    **Issue #123:** Project-agent associations for task management.
    """
)
async def list_project_agents(
    project_id: str,
    current_user: str = Depends(get_current_user)
) -> ProjectAgentListResponse:
    """
    List all agents associated with a project.

    Args:
        project_id: Project identifier
        current_user: Authenticated user ID

    Returns:
        ProjectAgentListResponse with list of agents
    """
    agents, total = project_service.list_project_agents(
        project_id=project_id,
        user_id=current_user
    )

    agent_responses = [
        ProjectAgentAssociationResponse(
            project_id=a["project_id"],
            agent_did=a["agent_did"],
            role=a["role"],
            associated_at=a["associated_at"]
        )
        for a in agents
    ]

    return ProjectAgentListResponse(
        agents=agent_responses,
        total=total
    )


# Issue #123: Task tracking endpoints


@router.post(
    "/projects/{project_id}/tasks",
    response_model=ProjectTaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Task successfully tracked",
            "model": ProjectTaskResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="Track task under project",
    description="""
    Track a task under a project.

    **Issue #123:** Task tracking per project.

    **Statuses:** pending, in_progress, completed, failed
    """
)
async def track_task(
    project_id: str,
    request: ProjectTaskTrackRequest,
    current_user: str = Depends(get_current_user)
) -> ProjectTaskResponse:
    """
    Track a task under a project.

    Args:
        project_id: Project identifier
        request: Task tracking request
        current_user: Authenticated user ID

    Returns:
        ProjectTaskResponse with task details
    """
    task = project_service.track_task(
        project_id=project_id,
        user_id=current_user,
        task_id=request.task_id,
        status=request.status.value if hasattr(request.status, 'value') else request.status,
        agent_did=request.agent_did,
        result=request.result
    )

    return ProjectTaskResponse(
        project_id=task["project_id"],
        task_id=task["task_id"],
        status=task["status"],
        agent_did=task["agent_did"],
        result=task["result"],
        tracked_at=task["tracked_at"]
    )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=ProjectTaskListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved tasks list",
            "model": ProjectTaskListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="List project tasks",
    description="""
    List all tasks tracked under a project.

    **Issue #123:** Task tracking per project.

    **Filtering:** Use ?status=completed to filter by status.
    """
)
async def list_project_tasks(
    project_id: str,
    status_param: Optional[str] = Query(None, alias="status"),
    current_user: str = Depends(get_current_user)
) -> ProjectTaskListResponse:
    """
    List all tasks tracked under a project.

    Args:
        project_id: Project identifier
        status_param: Optional status filter
        current_user: Authenticated user ID

    Returns:
        ProjectTaskListResponse with list of tasks
    """
    tasks, total = project_service.get_project_tasks(
        project_id=project_id,
        user_id=current_user,
        status_filter=status_param
    )

    task_responses = [
        ProjectTaskResponse(
            project_id=t["project_id"],
            task_id=t["task_id"],
            status=t["status"],
            agent_did=t["agent_did"],
            result=t["result"],
            tracked_at=t["tracked_at"]
        )
        for t in tasks
    ]

    return ProjectTaskListResponse(
        tasks=task_responses,
        total=total
    )


# Issue #123: Payment linking endpoints


@router.post(
    "/projects/{project_id}/payments",
    response_model=ProjectPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Payment successfully linked",
            "model": ProjectPaymentResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="Link payment to project",
    description="""
    Link a payment receipt to a project.

    **Issue #123:** Payment tracking per project.
    """
)
async def link_payment(
    project_id: str,
    request: ProjectPaymentLinkRequest,
    current_user: str = Depends(get_current_user)
) -> ProjectPaymentResponse:
    """
    Link a payment receipt to a project.

    Args:
        project_id: Project identifier
        request: Payment link request
        current_user: Authenticated user ID

    Returns:
        ProjectPaymentResponse with payment details
    """
    payment = project_service.link_payment(
        project_id=project_id,
        user_id=current_user,
        payment_receipt_id=request.payment_receipt_id,
        amount=request.amount,
        currency=request.currency
    )

    return ProjectPaymentResponse(
        project_id=payment["project_id"],
        payment_receipt_id=payment["payment_receipt_id"],
        amount=payment["amount"],
        currency=payment["currency"],
        linked_at=payment["linked_at"]
    )


@router.get(
    "/projects/{project_id}/payments",
    response_model=ProjectPaymentSummaryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved payment summary",
            "model": ProjectPaymentSummaryResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="Get project payment summary",
    description="""
    Get payment summary for a project.

    **Issue #123:** Payment tracking per project.

    Returns total spent, payment count, and list of payments.
    """
)
async def get_payment_summary(
    project_id: str,
    current_user: str = Depends(get_current_user)
) -> ProjectPaymentSummaryResponse:
    """
    Get payment summary for a project.

    Args:
        project_id: Project identifier
        current_user: Authenticated user ID

    Returns:
        ProjectPaymentSummaryResponse with payment summary
    """
    summary = project_service.get_payment_summary(
        project_id=project_id,
        user_id=current_user
    )

    payment_responses = [
        ProjectPaymentResponse(
            project_id=p["project_id"],
            payment_receipt_id=p["payment_receipt_id"],
            amount=p["amount"],
            currency=p["currency"],
            linked_at=p["linked_at"]
        )
        for p in summary["payments"]
    ]

    return ProjectPaymentSummaryResponse(
        total_spent=summary["total_spent"],
        payment_count=summary["payment_count"],
        payments=payment_responses
    )


# Issue #123: Status workflow endpoint


@router.patch(
    "/projects/{project_id}/status",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Project status successfully updated",
            "model": ProjectResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Invalid status value",
            "model": ErrorResponse
        }
    },
    summary="Update project status",
    description="""
    Update project status.

    **Issue #123:** Status workflow management.

    **Valid statuses:** DRAFT, ACTIVE, INACTIVE, SUSPENDED, COMPLETED, ARCHIVED
    """
)
async def update_project_status(
    project_id: str,
    request: ProjectStatusUpdateRequest,
    current_user: str = Depends(get_current_user)
) -> ProjectResponse:
    """
    Update project status.

    Args:
        project_id: Project identifier
        request: Status update request
        current_user: Authenticated user ID

    Returns:
        ProjectResponse with updated project
    """
    project = project_service.update_status(
        project_id=project_id,
        user_id=current_user,
        new_status=request.status.value if hasattr(request.status, 'value') else request.status
    )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        tier=project.tier
    )
