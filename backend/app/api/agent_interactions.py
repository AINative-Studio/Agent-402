"""
Agent Interactions API endpoints.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 5 (Agent Personas):
- Agents can be hired for tasks
- Tasks are submitted and tracked
- Results are returned upon completion

Per PRD Section 8 (X402 Protocol):
- All agent interactions require X402 payment header
- Payments tracked and linked to tasks
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Header, status, HTTPException
from app.core.auth import get_current_user
from app.schemas.agent_interactions import (
    HireAgentRequest,
    HireAgentResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
    AgentStatusResponse,
    TaskResult,
    ErrorResponse,
    AgentInteractionStatus,
    TaskStatus
)
from app.schemas.payment_tracking import PaymentReceiptCreate
from app.services.agent_interactions_service import (
    agent_interactions_service,
    HireNotFoundError,
    TaskNotFoundError,
    AgentNotAvailableError
)
from app.services.x402_payment_tracker import (
    x402_payment_tracker,
    PaymentReceiptNotFoundError
)
from app.services.project_service import project_service
from app.core.errors import AgentNotFoundError


router = APIRouter(
    prefix="/v1/public",
    tags=["agent-interactions"]
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
    project_service.get_project(project_id, user_id)


# ============================================================================
# POST /agents/hire - Hire an agent for a task
# ============================================================================

@router.post(
    "/agents/hire",
    response_model=HireAgentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Agent hired successfully",
            "model": HireAgentResponse
        },
        400: {
            "description": "Invalid request or missing payment header",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        402: {
            "description": "Payment required - X-X402-Payment header missing",
            "model": ErrorResponse
        },
        404: {
            "description": "Agent not found",
            "model": ErrorResponse
        },
        409: {
            "description": "Agent not available",
            "model": ErrorResponse
        }
    },
    summary="Hire an agent for a task",
    description="""
    Hire an agent to perform a task.

    **Authentication:** Requires X-API-Key header
    **Payment:** Requires X-X402-Payment header with valid payment token

    Per PRD Section 5 (Agent Personas):
    - Agents can be hired for specific tasks
    - Payment is processed before task begins
    - Hire creates a task record for tracking

    **Returns:**
    - hire_id: Unique hire transaction ID
    - task_id: ID of created task
    - payment_receipt_id: Payment receipt for tracking
    - status: Current hire status
    """
)
async def hire_agent(
    request: HireAgentRequest,
    current_user: str = Depends(get_current_user),
    x_x402_payment: Optional[str] = Header(None, alias="X-X402-Payment")
):
    """
    Hire an agent for a task.

    Args:
        request: Hire request body
        current_user: User ID from authentication
        x_x402_payment: X402 payment header

    Returns:
        HireAgentResponse with hire details
    """
    # Require X402 payment header
    if not x_x402_payment:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="X-X402-Payment header required for agent hire"
        )

    # Use a default project for now (in production, this would be from request or auth)
    project_id = f"proj_{current_user}"

    # Create payment receipt for the hire
    try:
        receipt_data = PaymentReceiptCreate(
            x402_request_id=f"x402_hire_{x_x402_payment[:16]}",
            from_agent_id=current_user,
            to_agent_id=request.agent_id,
            amount_usdc=request.payment_amount_usdc,
            purpose="agent-hire",
            metadata={"task_description": request.task_description[:100]}
        )

        payment_receipt = await x402_payment_tracker.create_payment_receipt(
            project_id=project_id,
            receipt_data=receipt_data
        )

        payment_receipt_id = payment_receipt["receipt_id"]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process payment: {str(e)}"
        )

    # Hire the agent
    try:
        result = await agent_interactions_service.hire_agent(
            project_id=project_id,
            request=request,
            payment_receipt_id=payment_receipt_id
        )

        return HireAgentResponse(
            hire_id=result["hire_id"],
            agent_id=result["agent_id"],
            task_id=result["task_id"],
            status=AgentInteractionStatus(result["status"]),
            payment_receipt_id=result["payment_receipt_id"],
            estimated_completion=datetime.fromisoformat(
                result["estimated_completion"].replace("Z", "+00:00")
            ) if result.get("estimated_completion") else None,
            created_at=datetime.fromisoformat(
                result["created_at"].replace("Z", "+00:00")
            )
        )

    except AgentNotAvailableError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to hire agent: {str(e)}"
        )


# ============================================================================
# POST /agents/tasks - Submit task to hired agent
# ============================================================================

@router.post(
    "/agents/tasks",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Task submitted successfully",
            "model": TaskSubmitResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Hire not found",
            "model": ErrorResponse
        }
    },
    summary="Submit task to hired agent",
    description="""
    Submit a task to a previously hired agent.

    **Authentication:** Requires X-API-Key header

    Per PRD Section 5:
    - Task input data is associated with the hire
    - Task execution begins after submission
    - Callback URL can be provided for completion notification
    """
)
async def submit_task(
    request: TaskSubmitRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Submit a task to a hired agent.

    Args:
        request: Task submission request
        current_user: User ID from authentication

    Returns:
        TaskSubmitResponse with task details
    """
    project_id = f"proj_{current_user}"

    try:
        result = await agent_interactions_service.submit_task(
            project_id=project_id,
            request=request
        )

        return TaskSubmitResponse(
            task_id=result["task_id"],
            hire_id=result["hire_id"],
            status=TaskStatus(result["status"]),
            estimated_completion=datetime.fromisoformat(
                result["estimated_completion"].replace("Z", "+00:00")
            ) if result.get("estimated_completion") else None,
            created_at=datetime.fromisoformat(
                result["created_at"].replace("Z", "+00:00")
            )
        )

    except HireNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hire not found: {request.hire_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}"
        )


# ============================================================================
# GET /agents/{agent_id}/status - Get agent status
# ============================================================================

@router.get(
    "/agents/{agent_id}/status",
    response_model=AgentStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Agent status retrieved successfully",
            "model": AgentStatusResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Agent not found",
            "model": ErrorResponse
        }
    },
    summary="Get agent status",
    description="""
    Get current status of an agent including availability and reputation.

    **Authentication:** Requires X-API-Key header

    Per PRD Section 5:
    - Returns current agent status (available, hired, working, etc.)
    - Includes reputation score from Arc blockchain
    - Shows total tasks completed
    """
)
async def get_agent_status(
    agent_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get agent status.

    Args:
        agent_id: Agent identifier
        current_user: User ID from authentication

    Returns:
        AgentStatusResponse with status details
    """
    project_id = f"proj_{current_user}"

    try:
        result = await agent_interactions_service.get_agent_status(
            project_id=project_id,
            agent_id=agent_id
        )

        return AgentStatusResponse(
            agent_id=result["agent_id"],
            status=AgentInteractionStatus(result["status"]),
            current_task_id=result.get("current_task_id"),
            current_hire_id=result.get("current_hire_id"),
            reputation_score=result.get("reputation_score"),
            trust_tier=result.get("trust_tier"),
            total_tasks_completed=result.get("total_tasks_completed", 0),
            availability=result.get("availability", {})
        )

    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent status: {str(e)}"
        )


# ============================================================================
# GET /tasks/{task_id}/result - Get task result
# ============================================================================

@router.get(
    "/tasks/{task_id}/result",
    response_model=TaskResult,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Task result retrieved successfully",
            "model": TaskResult
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Task not found",
            "model": ErrorResponse
        }
    },
    summary="Get task result",
    description="""
    Get result of a completed task.

    **Authentication:** Requires X-API-Key header

    Per PRD Section 5:
    - Returns task output data for completed tasks
    - Includes execution time and status
    - Returns error message if task failed
    """
)
async def get_task_result(
    task_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get task result.

    Args:
        task_id: Task identifier
        current_user: User ID from authentication

    Returns:
        TaskResult with task output
    """
    project_id = f"proj_{current_user}"

    try:
        result = await agent_interactions_service.get_task_result(
            project_id=project_id,
            task_id=task_id
        )

        return TaskResult(
            task_id=result["task_id"],
            hire_id=result["hire_id"],
            agent_id=result["agent_id"],
            status=TaskStatus(result["status"]),
            output_data=result.get("output_data"),
            error_message=result.get("error_message"),
            execution_time_seconds=result.get("execution_time_seconds"),
            payment_receipt_id=result["payment_receipt_id"],
            started_at=datetime.fromisoformat(
                result["started_at"].replace("Z", "+00:00")
            ) if result.get("started_at") else None,
            completed_at=datetime.fromisoformat(
                result["completed_at"].replace("Z", "+00:00")
            ) if result.get("completed_at") else None,
            metadata=result.get("metadata")
        )

    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task result: {str(e)}"
        )
