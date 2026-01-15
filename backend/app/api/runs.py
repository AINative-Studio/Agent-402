"""
Runs API endpoints for agent run replay.
Implements Epic 12, Issue 5: Replay agent runs from ZeroDB records.

Per PRD Section 10 (Success Criteria):
- Enable deterministic replay of agent runs
- Complete audit trail and replayability

Per PRD Section 11 (Deterministic Replay):
- GET /v1/public/{project_id}/runs - List all runs
- GET /v1/public/{project_id}/runs/{run_id} - Get run details
- GET /v1/public/{project_id}/runs/{run_id}/replay - Get complete replay data

Endpoints aggregate:
- agent_profile: Agent configuration
- agent_memory: All memory records
- compliance_events: All compliance events
- x402_requests: All X402 payment requests

All data is ordered chronologically by timestamp for deterministic replay.
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Path, Query, HTTPException
from app.core.auth import get_current_user
from app.core.errors import RunNotFoundError
from app.schemas.runs import (
    RunStatus,
    RunListResponse,
    RunDetail,
    RunReplayData,
    ProjectStatsResponse,
    ErrorResponse
)
from app.services.replay_service import replay_service


router = APIRouter(
    prefix="/v1/public",
    tags=["runs"]
)


@router.get(
    "/{project_id}/runs",
    response_model=RunListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved runs list",
            "model": RunListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="List project runs",
    description="""
    List all agent runs for a project with pagination.

    **Authentication:** Requires X-API-Key header

    **Epic 12, Issue 5:**
    - Returns list of run summaries with counts
    - Supports pagination via page and page_size
    - Optional status filter
    - Sorted by started_at descending (newest first)

    **Returns:**
    - Array of run summaries
    - Each summary includes: run_id, status, counts for memory/events/requests
    - Pagination info: total count, page, page_size

    **Per PRD Section 10:** Complete audit trail for all runs.
    """
)
async def list_runs(
    project_id: str = Path(
        ...,
        description="Project ID to list runs for"
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-based)"
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)"
    ),
    status_filter: Optional[RunStatus] = Query(
        default=None,
        description="Filter by run status"
    ),
    current_user: str = Depends(get_current_user)
) -> RunListResponse:
    """
    List all runs for a project.

    Args:
        project_id: Project identifier
        page: Page number (1-based)
        page_size: Items per page
        status_filter: Optional status filter
        current_user: Authenticated user ID

    Returns:
        RunListResponse with list of run summaries and pagination info
    """
    runs, total = replay_service.list_runs(
        project_id=project_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter
    )

    return RunListResponse(
        runs=runs,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{project_id}/stats",
    response_model=ProjectStatsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved project statistics",
            "model": ProjectStatsResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    },
    summary="Get project statistics",
    description="""
    Get aggregate statistics for a project.

    **Authentication:** Requires X-API-Key header

    **Per PRD Section 5.1 (Overview):**
    - KPI strip with latest run status
    - Number of X402 ledger entries
    - Number of memory items
    - Number of compliance events

    **Returns:**
    - total_runs: Total number of runs in the project
    - latest_run: Info about the most recent run (run_id, status, started_at)
    - total_x402_requests: Total X402 requests across all runs
    - total_memory_entries: Total memory entries across all runs
    - total_compliance_events: Total compliance events across all runs
    """
)
async def get_project_stats(
    project_id: str = Path(
        ...,
        description="Project ID to get statistics for"
    ),
    current_user: str = Depends(get_current_user)
) -> ProjectStatsResponse:
    """
    Get aggregate statistics for a project.

    Args:
        project_id: Project identifier
        current_user: Authenticated user ID

    Returns:
        ProjectStatsResponse with aggregate counts
    """
    return replay_service.get_project_stats(project_id)


@router.get(
    "/{project_id}/runs/{run_id}",
    response_model=RunDetail,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved run details",
            "model": RunDetail
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Run not found",
            "model": ErrorResponse
        }
    },
    summary="Get run details",
    description="""
    Get detailed information for a specific agent run.

    **Authentication:** Requires X-API-Key header

    **Epic 12, Issue 5:**
    - Returns run metadata and agent profile
    - Includes counts for memory records, events, requests
    - Calculates run duration if completed

    **Returns:**
    - Run ID, project ID, status
    - Agent profile configuration
    - Start/completion timestamps
    - Duration in milliseconds (if completed)
    - Counts for all record types

    **Per PRD Section 10:** Complete audit information for the run.
    """
)
async def get_run(
    project_id: str = Path(
        ...,
        description="Project ID"
    ),
    run_id: str = Path(
        ...,
        description="Run ID to retrieve"
    ),
    current_user: str = Depends(get_current_user)
) -> RunDetail:
    """
    Get detailed information for a specific run.

    Args:
        project_id: Project identifier
        run_id: Run identifier
        current_user: Authenticated user ID

    Returns:
        RunDetail with full run information

    Raises:
        RunNotFoundError: If run is not found
    """
    run_detail = replay_service.get_run_detail(
        project_id=project_id,
        run_id=run_id
    )

    if not run_detail:
        raise RunNotFoundError(run_id=run_id, project_id=project_id)

    return run_detail


@router.get(
    "/{project_id}/runs/{run_id}/replay",
    response_model=RunReplayData,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved replay data",
            "model": RunReplayData
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Run not found",
            "model": ErrorResponse
        }
    },
    summary="Get run replay data",
    description="""
    Get complete replay data for deterministic agent run replay.

    **Authentication:** Requires X-API-Key header

    **Epic 12, Issue 5 - Core Implementation:**
    - Aggregates all ZeroDB records for the run
    - Orders all records chronologically by timestamp
    - Validates all linked records exist
    - Returns complete data for deterministic replay

    **Aggregated Data:**
    - agent_profile: Agent configuration at run time
    - agent_memory: All memory records in chronological order
    - compliance_events: All compliance events in chronological order
    - x402_requests: All X402 payment requests in chronological order

    **Validation:**
    - Validates agent profile exists
    - Validates all records have matching run_id
    - Verifies chronological order
    - Reports any missing or inconsistent records

    **Per PRD Section 11 (Deterministic Replay):**
    - Complete data set for reproducing agent execution
    - All timestamps preserved for accurate sequencing
    - Validation ensures data integrity

    **Use Cases:**
    - Audit and compliance review
    - Debugging and troubleshooting
    - Training and improvement analysis
    - Regulatory reporting
    """
)
async def get_run_replay(
    project_id: str = Path(
        ...,
        description="Project ID"
    ),
    run_id: str = Path(
        ...,
        description="Run ID to get replay data for"
    ),
    current_user: str = Depends(get_current_user)
) -> RunReplayData:
    """
    Get complete replay data for a run.

    Per PRD Section 11 (Deterministic Replay):
    - Aggregates agent profile, memory, events, requests
    - Orders chronologically by timestamp
    - Validates all linked records exist

    Args:
        project_id: Project identifier
        run_id: Run identifier
        current_user: Authenticated user ID

    Returns:
        RunReplayData with complete replay information

    Raises:
        RunNotFoundError: If run is not found
    """
    replay_data = replay_service.get_replay_data(
        project_id=project_id,
        run_id=run_id
    )

    if not replay_data:
        raise RunNotFoundError(run_id=run_id, project_id=project_id)

    return replay_data
