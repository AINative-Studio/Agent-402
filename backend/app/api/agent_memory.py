"""
Agent Memory API endpoints for persisting agent decisions.
Implements Epic 12 Issue 2: Agent memory persistence.

Endpoints:
- POST /v1/public/{project_id}/agent-memory (Create memory entry)
- GET /v1/public/{project_id}/agent-memory (List memories with filters)
- GET /v1/public/{project_id}/agent-memory/{memory_id} (Get single memory)

Per PRD Section 6 (ZeroDB Integration):
- Agent memory storage for decisions and context
- Namespace scoping for multi-agent isolation
- Support for various memory types (decisions, context, state)

Per DX Contract Section 4 (Endpoint Prefixing):
- All public endpoints use /v1/public/ prefix
- Requires X-API-Key authentication
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Path, Query
from app.core.auth import get_current_user
from app.core.errors import APIError
from app.schemas.agent_memory import (
    AgentMemoryCreateRequest,
    AgentMemoryCreateResponse,
    AgentMemoryResponse,
    AgentMemoryListResponse,
    MemoryType
)
from app.schemas.project import ErrorResponse
from app.services.agent_memory_service import agent_memory_service


router = APIRouter(
    prefix="/v1/public",
    tags=["agent-memory"]
)


@router.post(
    "/{project_id}/agent-memory",
    response_model=AgentMemoryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Successfully created agent memory entry",
            "model": AgentMemoryCreateResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error (invalid input)",
            "model": ErrorResponse
        }
    },
    summary="Create agent memory entry",
    description="""
    Persist an agent decision or memory to the agent_memory store.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 2:** Agent memory persistence

    **Memory Types:**
    - decision: Agent decisions and choices
    - context: Contextual information for agent reasoning
    - state: Agent state snapshots
    - observation: Observations from the environment
    - goal: Agent goals and objectives
    - plan: Planned actions and strategies
    - result: Results of agent actions
    - error: Error conditions and recovery

    **Namespace Isolation:**
    - Memories are scoped to a namespace for multi-agent isolation
    - Default namespace is 'default' if not specified
    - Agents in different namespaces cannot access each other's memories

    **Per PRD Section 6:**
    - Stores agent_id, run_id, memory_type, content, metadata, timestamp
    - Supports filtering and retrieval by various criteria
    - Enables agent recall and audit trail
    """
)
async def create_agent_memory(
    project_id: str = Path(
        ...,
        description="Project identifier"
    ),
    request: AgentMemoryCreateRequest = ...,
    current_user: str = Depends(get_current_user)
) -> AgentMemoryCreateResponse:
    """
    Create a new agent memory entry.

    Stores the agent's decision, context, or state information
    for later retrieval and analysis.

    Args:
        project_id: Project identifier
        request: Memory creation request
        current_user: Authenticated user ID

    Returns:
        AgentMemoryCreateResponse with created memory details
    """
    # Determine namespace (default if not provided)
    namespace = request.namespace or "default"

    # Store memory using the service
    memory_record = agent_memory_service.store_memory(
        project_id=project_id,
        agent_id=request.agent_id,
        run_id=request.run_id,
        memory_type=request.memory_type.value,
        content=request.content,
        namespace=namespace,
        metadata=request.metadata
    )

    return AgentMemoryCreateResponse(
        memory_id=memory_record["memory_id"],
        agent_id=memory_record["agent_id"],
        run_id=memory_record["run_id"],
        memory_type=MemoryType(memory_record["memory_type"]),
        namespace=memory_record["namespace"],
        timestamp=memory_record["timestamp"],
        created=True
    )


@router.get(
    "/{project_id}/agent-memory",
    response_model=AgentMemoryListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved agent memories",
            "model": AgentMemoryListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List agent memories",
    description="""
    List agent memory entries with optional filtering.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 2:** Agent memory persistence

    **Filters:**
    - agent_id: Filter by specific agent
    - run_id: Filter by specific execution run
    - memory_type: Filter by memory type
    - namespace: Filter by namespace

    **Pagination:**
    - limit: Maximum number of results (default 100, max 1000)
    - offset: Offset for pagination (default 0)

    **Ordering:**
    - Results are ordered by timestamp descending (most recent first)

    **Per PRD Section 6:**
    - Enable agent recall and decision history
    - Support audit trail and compliance
    """
)
async def list_agent_memories(
    project_id: str = Path(
        ...,
        description="Project identifier"
    ),
    agent_id: Optional[str] = Query(
        None,
        description="Filter by agent ID"
    ),
    run_id: Optional[str] = Query(
        None,
        description="Filter by run ID"
    ),
    memory_type: Optional[MemoryType] = Query(
        None,
        description="Filter by memory type"
    ),
    namespace: Optional[str] = Query(
        None,
        description="Filter by namespace"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of results (1-1000)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset"
    ),
    current_user: str = Depends(get_current_user)
) -> AgentMemoryListResponse:
    """
    List agent memories with filtering and pagination.

    Args:
        project_id: Project identifier
        agent_id: Optional agent ID filter
        run_id: Optional run ID filter
        memory_type: Optional memory type filter
        namespace: Optional namespace filter
        limit: Maximum results to return
        offset: Pagination offset
        current_user: Authenticated user ID

    Returns:
        AgentMemoryListResponse with list of memories
    """
    # Convert memory_type enum to string if provided
    memory_type_str = memory_type.value if memory_type else None

    # Get memories from service
    memories, total, filters_applied = agent_memory_service.list_memories(
        project_id=project_id,
        agent_id=agent_id,
        run_id=run_id,
        memory_type=memory_type_str,
        namespace=namespace,
        limit=limit,
        offset=offset
    )

    # Convert to response models
    memory_responses = [
        AgentMemoryResponse(
            memory_id=m["memory_id"],
            agent_id=m["agent_id"],
            run_id=m["run_id"],
            memory_type=MemoryType(m["memory_type"]),
            content=m["content"],
            metadata=m["metadata"],
            namespace=m["namespace"],
            timestamp=m["timestamp"],
            project_id=m["project_id"]
        )
        for m in memories
    ]

    return AgentMemoryListResponse(
        memories=memory_responses,
        total=total,
        limit=limit,
        offset=offset,
        filters_applied=filters_applied
    )


@router.get(
    "/{project_id}/agent-memory/{memory_id}",
    response_model=AgentMemoryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved agent memory",
            "model": AgentMemoryResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Memory not found",
            "model": ErrorResponse
        }
    },
    summary="Get single agent memory",
    description="""
    Retrieve a single agent memory entry by ID.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 2:** Agent memory persistence

    **Per PRD Section 6:**
    - Support retrieval of specific memory entries
    - Enable audit trail and decision review
    """
)
async def get_agent_memory(
    project_id: str = Path(
        ...,
        description="Project identifier"
    ),
    memory_id: str = Path(
        ...,
        description="Memory entry identifier"
    ),
    namespace: Optional[str] = Query(
        None,
        description="Optional namespace filter for faster lookup"
    ),
    current_user: str = Depends(get_current_user)
) -> AgentMemoryResponse:
    """
    Get a single agent memory entry by ID.

    Args:
        project_id: Project identifier
        memory_id: Memory entry identifier
        namespace: Optional namespace for faster lookup
        current_user: Authenticated user ID

    Returns:
        AgentMemoryResponse with memory details

    Raises:
        APIError: If memory not found (404)
    """
    # Get memory from service
    memory = agent_memory_service.get_memory(
        project_id=project_id,
        memory_id=memory_id,
        namespace=namespace
    )

    if not memory:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="MEMORY_NOT_FOUND",
            detail=f"Agent memory not found: {memory_id}"
        )

    return AgentMemoryResponse(
        memory_id=memory["memory_id"],
        agent_id=memory["agent_id"],
        run_id=memory["run_id"],
        memory_type=MemoryType(memory["memory_type"]),
        content=memory["content"],
        metadata=memory["metadata"],
        namespace=memory["namespace"],
        timestamp=memory["timestamp"],
        project_id=memory["project_id"]
    )
