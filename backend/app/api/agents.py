"""
Agents API endpoints.
Implements agent profile management per Epic 12, Issue 1.
Per PRD Section 5 (Agent Personas): CrewAI agent profiles with did, role.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user
from app.schemas.agents import (
    AgentCreateRequest,
    UpdateAgentRequest,
    AgentResponse,
    AgentListResponse,
    ErrorResponse
)
from app.services.agent_service import agent_service
from app.services.project_service import project_service


router = APIRouter(
    prefix="/v1/public",
    tags=["agents"]
)


def validate_project_access(project_id: str, user_id: str) -> None:
    """
    Validate that the user has access to the project.

    Args:
        project_id: Project identifier
        user_id: Authenticated user ID

    Raises:
        ProjectNotFoundError: If project not found
        UnauthorizedError: If user doesn't have access
    """
    # This will raise ProjectNotFoundError or UnauthorizedError
    # Both are APIError subclasses with proper error_code
    project_service.get_project(project_id, user_id)


@router.post(
    "/{project_id}/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Agent created successfully",
            "model": AgentResponse
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
            "description": "Agent with DID already exists in project",
            "model": ErrorResponse
        }
    },
    summary="Create agent profile",
    description="""
    Create a new agent profile within a project.

    **Authentication:** Requires X-API-Key header

    **Per PRD Section 5 (Agent Personas):**
    - Agents represent CrewAI agent profiles
    - Each agent has a unique DID (Decentralized Identifier)
    - Agents are scoped to a project

    **Required fields:**
    - did: Decentralized Identifier (unique within project)
    - role: Agent role (e.g., researcher, analyst, executor)
    - name: Human-readable agent name

    **Optional fields:**
    - description: Agent description and purpose
    - scope: Operational scope (PROJECT, GLOBAL, RESTRICTED)
    """
)
async def create_agent(
    project_id: str,
    request: AgentCreateRequest,
    current_user: str = Depends(get_current_user)
) -> AgentResponse:
    """
    Create a new agent profile in a project.

    Args:
        project_id: Project identifier from URL
        request: Agent creation request body
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentResponse with created agent details
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Create agent - DuplicateAgentDIDError is an APIError and will be
    # handled by the exception handler with proper error_code
    agent = await agent_service.create_agent(
        project_id=project_id,
        did=request.did,
        role=request.role.value,  # Convert enum to string
        name=request.name,
        description=request.description,
        scope=request.scope
    )

    return AgentResponse(
        id=agent.id,
        agent_id=agent.id,
        did=agent.did,
        role=agent.role,
        name=agent.name,
        description=agent.description,
        scope=agent.scope,
        project_id=agent.project_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.get(
    "/{project_id}/agents",
    response_model=AgentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved agents list",
            "model": AgentListResponse
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
    summary="List agents in project",
    description="""
    List all agent profiles for a project.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Array of agents with id, did, role, name, description, scope
    - Empty array if no agents exist

    **Per PRD Section 5:** Lists all CrewAI agent personas registered to project.
    """
)
async def list_agents(
    project_id: str,
    current_user: str = Depends(get_current_user)
) -> AgentListResponse:
    """
    List all agents for a project.

    Args:
        project_id: Project identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentListResponse with list of agents and total count
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Get agents for project
    agents = await agent_service.list_project_agents(project_id)

    # Convert to response models
    agent_responses: List[AgentResponse] = [
        AgentResponse(
            id=agent.id,
            agent_id=agent.id,
            did=agent.did,
            role=agent.role,
            name=agent.name,
            description=agent.description,
            scope=agent.scope,
            project_id=agent.project_id,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
        for agent in agents
    ]

    return AgentListResponse(
        agents=agent_responses,
        total=len(agent_responses)
    )


@router.get(
    "/{project_id}/agents/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved agent",
            "model": AgentResponse
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
    summary="Get agent by ID",
    description="""
    Get a single agent profile by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Agent details with id, did, role, name, description, scope
    - 404 if agent not found or doesn't belong to project
    """
)
async def get_agent(
    project_id: str,
    agent_id: str,
    current_user: str = Depends(get_current_user)
) -> AgentResponse:
    """
    Get a single agent by ID.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentResponse with agent details
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Get agent - AgentNotFoundError is an APIError and will be
    # handled by the exception handler with proper error_code
    agent = await agent_service.get_agent(agent_id, project_id)

    return AgentResponse(
        id=agent.id,
        agent_id=agent.id,
        did=agent.did,
        role=agent.role,
        name=agent.name,
        description=agent.description,
        scope=agent.scope,
        project_id=agent.project_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.patch(
    "/{project_id}/agents/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Agent updated successfully",
            "model": AgentResponse
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
    summary="Update agent profile",
    description="""
    Update an existing agent profile within a project.

    **Authentication:** Requires X-API-Key header

    **Updatable fields:**
    - role: Agent role (optional)
    - name: Human-readable agent name (optional)
    - description: Agent description and purpose (optional)
    - scope: Operational scope (optional)

    **Note:** DID cannot be updated after creation.
    All fields are optional - only provide fields you want to update.
    """
)
async def update_agent(
    project_id: str,
    agent_id: str,
    request: UpdateAgentRequest,
    current_user: str = Depends(get_current_user)
) -> AgentResponse:
    """
    Update an existing agent profile.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL
        request: Agent update request body
        current_user: User ID from X-API-Key authentication

    Returns:
        AgentResponse with updated agent details
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Update agent
    agent = await agent_service.update_agent(
        agent_id=agent_id,
        project_id=project_id,
        name=request.name,
        role=request.role.value if request.role else None,  # Convert enum to string
        description=request.description,
        scope=request.scope
    )

    return AgentResponse(
        id=agent.id,
        agent_id=agent.id,
        did=agent.did,
        role=agent.role,
        name=agent.name,
        description=agent.description,
        scope=agent.scope,
        project_id=agent.project_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


@router.delete(
    "/{project_id}/agents/{agent_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Agent deleted successfully"
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
    summary="Delete agent profile",
    description="""
    Delete an agent profile from a project.

    **Authentication:** Requires X-API-Key header

    **Warning:** This action is permanent and cannot be undone.
    """
)
async def delete_agent(
    project_id: str,
    agent_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete an agent profile from a project.

    Args:
        project_id: Project identifier from URL
        agent_id: Agent identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        Success confirmation message
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Delete agent
    await agent_service.delete_agent(agent_id, project_id)

    return {
        "message": "Agent deleted successfully",
        "agent_id": agent_id
    }
