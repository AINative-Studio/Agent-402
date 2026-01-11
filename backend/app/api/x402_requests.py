"""
X402 Requests API endpoints.
Implements Epic 12 Issue 4: X402 requests linked to agent + task.

Per PRD Section 6 (ZeroDB Integration):
- X402 signed requests are logged with agent and task linkage
- Supports linking to agent_memory and compliance_events records
- Enables audit trail for X402 protocol transactions

Per PRD Section 8 (X402 Protocol):
- X402 requests contain signed payment authorizations
- Requests must be traceable to originating agent and task
- Supports compliance and audit requirements

Endpoints:
- POST /v1/public/{project_id}/x402-requests - Create X402 request
- GET /v1/public/{project_id}/x402-requests - List X402 requests (with filters)
- GET /v1/public/{project_id}/x402-requests/{request_id} - Get single request with links
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Path, Query
from app.core.auth import get_current_user
from app.schemas.x402_requests import (
    X402RequestCreate,
    X402RequestResponse,
    X402RequestWithLinks,
    X402RequestListResponse,
    X402RequestStatus
)
from app.schemas.project import ErrorResponse
from app.services.x402_service import x402_service


router = APIRouter(
    prefix="/v1/public",
    tags=["x402-requests"]
)


@router.post(
    "/{project_id}/x402-requests",
    response_model=X402RequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Successfully created X402 request",
            "model": X402RequestResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse
        }
    },
    summary="Create X402 signed request (Epic 12 Issue 4)",
    description="""
    Create a new X402 signed request record linked to agent and task.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 4 Requirements:**
    - Links X402 requests to the agent + task that produced them
    - Stores request_payload with cryptographic signature
    - Supports linking to agent_memory records
    - Supports linking to compliance_events records
    - Enables audit trail for X402 protocol transactions

    **Per PRD Section 6 (ZeroDB Integration):**
    - All X402 requests are persisted for audit
    - Linked records provide decision provenance
    - Supports compliance and regulatory requirements

    **Per PRD Section 8 (X402 Protocol):**
    - X402 requests contain signed payment authorizations
    - Signature ensures authenticity and non-repudiation
    - Request payloads follow X402 protocol specification

    **Request Fields:**
    - agent_id: DID or identifier of originating agent
    - task_id: Identifier of task that produced the request
    - run_id: Execution context identifier
    - request_payload: X402 protocol payload (payment details)
    - signature: Cryptographic signature of the request
    - linked_memory_ids: Optional links to agent memory
    - linked_compliance_ids: Optional links to compliance events
    """
)
async def create_x402_request(
    project_id: str = Path(..., description="Project ID"),
    request: X402RequestCreate = ...,
    current_user: str = Depends(get_current_user)
) -> X402RequestResponse:
    """
    Create a new X402 signed request.

    Args:
        project_id: Project identifier
        request: X402 request creation data
        current_user: Authenticated user ID

    Returns:
        X402RequestResponse with created request details
    """
    # Create the X402 request
    created_request = x402_service.create_request(
        project_id=project_id,
        agent_id=request.agent_id,
        task_id=request.task_id,
        run_id=request.run_id,
        request_payload=request.request_payload,
        signature=request.signature,
        status=request.status or X402RequestStatus.PENDING,
        linked_memory_ids=request.linked_memory_ids,
        linked_compliance_ids=request.linked_compliance_ids,
        metadata=request.metadata
    )

    return X402RequestResponse(
        request_id=created_request["request_id"],
        project_id=created_request["project_id"],
        agent_id=created_request["agent_id"],
        task_id=created_request["task_id"],
        run_id=created_request["run_id"],
        request_payload=created_request["request_payload"],
        signature=created_request["signature"],
        status=X402RequestStatus(created_request["status"]),
        timestamp=created_request["timestamp"],
        linked_memory_ids=created_request["linked_memory_ids"],
        linked_compliance_ids=created_request["linked_compliance_ids"],
        metadata=created_request.get("metadata")
    )


@router.get(
    "/{project_id}/x402-requests",
    response_model=X402RequestListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved X402 requests",
            "model": X402RequestListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List X402 requests with filters (Epic 12 Issue 4)",
    description="""
    List X402 signed requests with optional filters.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 4 Requirements:**
    - Filter by agent_id to get all requests from a specific agent
    - Filter by task_id to get all requests from a specific task
    - Filter by run_id to get all requests from a specific run
    - Filter by status to get requests in a specific state
    - Supports pagination with limit and offset

    **Per PRD Section 6 (ZeroDB Integration):**
    - Enables audit and compliance queries
    - Supports agent activity analysis
    - Provides transaction history by agent/task/run

    **Query Parameters:**
    - agent_id: Filter by agent identifier
    - task_id: Filter by task identifier
    - run_id: Filter by run identifier
    - status: Filter by request status (PENDING, APPROVED, REJECTED, etc.)
    - limit: Maximum number of results (1-1000, default 100)
    - offset: Pagination offset (default 0)

    **Returns:**
    - Array of X402 requests matching filters
    - Total count of matching requests
    - Pagination metadata
    """
)
async def list_x402_requests(
    project_id: str = Path(..., description="Project ID"),
    agent_id: Optional[str] = Query(
        None,
        description="Filter by agent identifier"
    ),
    task_id: Optional[str] = Query(
        None,
        description="Filter by task identifier"
    ),
    run_id: Optional[str] = Query(
        None,
        description="Filter by run identifier"
    ),
    status: Optional[X402RequestStatus] = Query(
        None,
        description="Filter by request status"
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
) -> X402RequestListResponse:
    """
    List X402 requests with optional filters.

    Args:
        project_id: Project identifier
        agent_id: Optional filter by agent
        task_id: Optional filter by task
        run_id: Optional filter by run
        status: Optional filter by status
        limit: Maximum results to return
        offset: Pagination offset
        current_user: Authenticated user ID

    Returns:
        X402RequestListResponse with paginated results
    """
    # Get filtered requests
    requests, total = x402_service.list_requests(
        project_id=project_id,
        agent_id=agent_id,
        task_id=task_id,
        run_id=run_id,
        status=status,
        limit=limit,
        offset=offset
    )

    # Convert to response models
    request_responses = [
        X402RequestResponse(
            request_id=req["request_id"],
            project_id=req["project_id"],
            agent_id=req["agent_id"],
            task_id=req["task_id"],
            run_id=req["run_id"],
            request_payload=req["request_payload"],
            signature=req["signature"],
            status=X402RequestStatus(req["status"]),
            timestamp=req["timestamp"],
            linked_memory_ids=req.get("linked_memory_ids", []),
            linked_compliance_ids=req.get("linked_compliance_ids", []),
            metadata=req.get("metadata")
        )
        for req in requests
    ]

    return X402RequestListResponse(
        requests=request_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{project_id}/x402-requests/{request_id}",
    response_model=X402RequestWithLinks,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved X402 request with linked records",
            "model": X402RequestWithLinks
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "X402 request not found",
            "model": ErrorResponse
        }
    },
    summary="Get X402 request with linked records (Epic 12 Issue 4)",
    description="""
    Get a single X402 request by ID with all linked records.

    **Authentication:** Requires X-API-Key header

    **Epic 12 Issue 4 Requirements:**
    - Returns full X402 request details
    - Includes linked agent_memory records
    - Includes linked compliance_events records
    - Provides complete audit trail for the request

    **Per PRD Section 6 (ZeroDB Integration):**
    - Enables detailed audit and compliance review
    - Provides decision provenance through linked memories
    - Supports regulatory requirements with compliance events

    **Per PRD Section 8 (X402 Protocol):**
    - Returns complete X402 request payload
    - Includes signature for verification
    - Provides status and processing history

    **Returns:**
    - Complete X402 request record
    - Full linked_memories array with memory content
    - Full linked_compliance_events array with event details
    """
)
async def get_x402_request(
    project_id: str = Path(..., description="Project ID"),
    request_id: str = Path(..., description="X402 request ID"),
    current_user: str = Depends(get_current_user)
) -> X402RequestWithLinks:
    """
    Get a single X402 request with all linked records.

    Args:
        project_id: Project identifier
        request_id: X402 request identifier
        current_user: Authenticated user ID

    Returns:
        X402RequestWithLinks with full request and linked records

    Raises:
        X402RequestNotFoundError: If request not found
    """
    # Get request with linked records
    request_data = x402_service.get_request(
        project_id=project_id,
        request_id=request_id,
        include_links=True
    )

    return X402RequestWithLinks(
        request_id=request_data["request_id"],
        project_id=request_data["project_id"],
        agent_id=request_data["agent_id"],
        task_id=request_data["task_id"],
        run_id=request_data["run_id"],
        request_payload=request_data["request_payload"],
        signature=request_data["signature"],
        status=X402RequestStatus(request_data["status"]),
        timestamp=request_data["timestamp"],
        linked_memory_ids=request_data.get("linked_memory_ids", []),
        linked_compliance_ids=request_data.get("linked_compliance_ids", []),
        metadata=request_data.get("metadata"),
        linked_memories=request_data.get("linked_memories", []),
        linked_compliance_events=request_data.get("linked_compliance_events", [])
    )
