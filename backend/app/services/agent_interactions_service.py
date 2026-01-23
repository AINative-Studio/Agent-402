"""
Agent Interactions Service.
Issues #119 + #122: X402 Payment Tracking and Agent Interaction APIs.

Per PRD Section 5 (Agent Personas):
- Agents can be hired for tasks
- Tasks are submitted and tracked
- Results are returned upon completion

Per PRD Section 8 (X402 Protocol):
- All agent interactions require X402 payment
- Payments tracked and linked to tasks
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from app.schemas.agent_interactions import (
    AgentInteractionStatus,
    TaskStatus,
    HireAgentRequest,
    TaskSubmitRequest
)
from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client
from app.services.arc_blockchain_service import arc_blockchain_service

logger = logging.getLogger(__name__)

# Table names for ZeroDB
HIRES_TABLE = "agent_hires"
TASKS_TABLE = "agent_tasks"


class HireNotFoundError(APIError):
    """
    Raised when a hire record is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: HIRE_NOT_FOUND
        - detail: Message including hire ID
    """

    def __init__(self, hire_id: str):
        detail = f"Hire not found: {hire_id}" if hire_id else "Hire not found"
        super().__init__(
            status_code=404,
            error_code="HIRE_NOT_FOUND",
            detail=detail
        )


class TaskNotFoundError(APIError):
    """
    Raised when a task is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: TASK_NOT_FOUND
        - detail: Message including task ID
    """

    def __init__(self, task_id: str):
        detail = f"Task not found: {task_id}" if task_id else "Task not found"
        super().__init__(
            status_code=404,
            error_code="TASK_NOT_FOUND",
            detail=detail
        )


class AgentNotAvailableError(APIError):
    """
    Raised when agent is not available for hire.

    Returns:
        - HTTP 409 (Conflict)
        - error_code: AGENT_NOT_AVAILABLE
        - detail: Message about agent unavailability
    """

    def __init__(self, agent_id: str, reason: str = "Agent is currently busy"):
        detail = f"Agent {agent_id} not available: {reason}"
        super().__init__(
            status_code=409,
            error_code="AGENT_NOT_AVAILABLE",
            detail=detail
        )


class AgentInteractionsService:
    """
    Service for managing agent interactions (hire, task, status).

    Handles the full lifecycle of agent hiring and task execution:
    1. Hire agent (creates hire record, links payment)
    2. Submit task (associates input data with hire)
    3. Track status (monitor task progress)
    4. Get result (retrieve completed task output)
    """

    def __init__(self, client=None):
        """
        Initialize the Agent Interactions service.

        Args:
            client: Optional ZeroDB client instance (for testing)
        """
        self._client = client

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    def generate_hire_id(self) -> str:
        """Generate a unique hire ID."""
        return f"hire_{uuid.uuid4().hex[:16]}"

    def generate_task_id(self) -> str:
        """Generate a unique task ID."""
        return f"task_{uuid.uuid4().hex[:16]}"

    # =========================================================================
    # Hire Agent
    # =========================================================================

    async def hire_agent(
        self,
        project_id: str,
        request: HireAgentRequest,
        payment_receipt_id: str
    ) -> Dict[str, Any]:
        """
        Hire an agent for a task.

        Args:
            project_id: Project identifier
            request: Hire request data
            payment_receipt_id: Payment receipt ID from X402 payment

        Returns:
            Dict containing hire record with hire_id, task_id, status

        Raises:
            AgentNotAvailableError: If agent is not available
        """
        hire_id = self.generate_hire_id()
        task_id = self.generate_task_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Calculate estimated completion based on max_duration
        max_duration = request.max_duration_seconds or 3600
        estimated_completion = (
            datetime.utcnow() + timedelta(seconds=max_duration)
        ).isoformat() + "Z"

        # Build hire record
        hire_data = {
            "id": str(uuid.uuid4()),
            "hire_id": hire_id,
            "project_id": project_id,
            "agent_id": request.agent_id,
            "task_id": task_id,
            "task_description": request.task_description,
            "payment_amount_usdc": request.payment_amount_usdc,
            "payment_receipt_id": payment_receipt_id,
            "max_duration_seconds": max_duration,
            "priority": request.priority or "normal",
            "status": AgentInteractionStatus.HIRED.value,
            "estimated_completion": estimated_completion,
            "created_at": timestamp,
            "started_at": None,
            "completed_at": None,
            "metadata": request.metadata or {}
        }

        try:
            await self.client.insert_row(HIRES_TABLE, hire_data)
            logger.info(f"Created hire record: {hire_id} for agent {request.agent_id}")

            # Also create initial task record
            task_data = {
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "project_id": project_id,
                "hire_id": hire_id,
                "agent_id": request.agent_id,
                "status": TaskStatus.PENDING.value,
                "input_data": None,  # Set when task is submitted
                "output_data": None,
                "error_message": None,
                "execution_time_seconds": None,
                "payment_receipt_id": payment_receipt_id,
                "created_at": timestamp,
                "started_at": None,
                "completed_at": None,
                "metadata": {}
            }

            await self.client.insert_row(TASKS_TABLE, task_data)
            logger.info(f"Created task record: {task_id}")

            return {
                "hire_id": hire_id,
                "agent_id": request.agent_id,
                "task_id": task_id,
                "status": AgentInteractionStatus.HIRED.value,
                "payment_receipt_id": payment_receipt_id,
                "estimated_completion": estimated_completion,
                "created_at": timestamp
            }

        except Exception as e:
            logger.error(f"Failed to create hire record: {e}")
            raise

    # =========================================================================
    # Submit Task
    # =========================================================================

    async def submit_task(
        self,
        project_id: str,
        request: TaskSubmitRequest
    ) -> Dict[str, Any]:
        """
        Submit a task to a hired agent.

        Args:
            project_id: Project identifier
            request: Task submission data

        Returns:
            Dict containing task submission result

        Raises:
            HireNotFoundError: If hire record not found
        """
        try:
            # Find the hire record
            hire_result = await self.client.query_rows(
                HIRES_TABLE,
                filter={"hire_id": request.hire_id, "project_id": project_id},
                limit=1
            )

            rows = hire_result.get("rows", [])
            if not rows:
                raise HireNotFoundError(request.hire_id)

            hire = rows[0]
            task_id = hire.get("task_id")

            # Find and update the task record
            task_result = await self.client.query_rows(
                TASKS_TABLE,
                filter={"task_id": task_id, "project_id": project_id},
                limit=1
            )

            task_rows = task_result.get("rows", [])
            if not task_rows:
                raise TaskNotFoundError(task_id)

            task = task_rows[0]
            task_row_id = task.get("id") or task.get("row_id")

            timestamp = datetime.utcnow().isoformat() + "Z"

            # Calculate estimated completion
            max_duration = hire.get("max_duration_seconds", 3600)
            estimated_completion = (
                datetime.utcnow() + timedelta(seconds=max_duration)
            ).isoformat() + "Z"

            # Update task with input data
            updated_task = {
                **task,
                "status": TaskStatus.PENDING.value,
                "input_data": request.input_data,
                "callback_url": request.callback_url,
                "started_at": timestamp
            }

            await self.client.update_row(TASKS_TABLE, task_row_id, updated_task)
            logger.info(f"Submitted task: {task_id}")

            return {
                "task_id": task_id,
                "hire_id": request.hire_id,
                "status": TaskStatus.PENDING.value,
                "estimated_completion": estimated_completion,
                "created_at": timestamp
            }

        except HireNotFoundError:
            raise
        except TaskNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            raise HireNotFoundError(request.hire_id)

    # =========================================================================
    # Get Agent Status
    # =========================================================================

    async def get_agent_status(
        self,
        project_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Get current status of an agent.

        Args:
            project_id: Project identifier
            agent_id: Agent identifier

        Returns:
            Dict containing agent status information
        """
        try:
            # Check for active hires
            hire_result = await self.client.query_rows(
                HIRES_TABLE,
                filter={
                    "agent_id": agent_id,
                    "project_id": project_id,
                    "status": AgentInteractionStatus.HIRED.value
                },
                limit=1
            )

            active_hire = hire_result.get("rows", [])

            # Count completed tasks
            completed_result = await self.client.query_rows(
                TASKS_TABLE,
                filter={
                    "agent_id": agent_id,
                    "project_id": project_id,
                    "status": TaskStatus.COMPLETED.value
                },
                limit=10000
            )

            total_completed = len(completed_result.get("rows", []))

            # Determine status
            if active_hire:
                hire = active_hire[0]
                status = AgentInteractionStatus.WORKING
                current_task_id = hire.get("task_id")
                current_hire_id = hire.get("hire_id")
            else:
                status = AgentInteractionStatus.AVAILABLE
                current_task_id = None
                current_hire_id = None

            # Get reputation from Arc blockchain (mock for now)
            # In production: Map agent_id to agent_token_id
            agent_token_id = hash(agent_id) % 100  # Mock token ID
            reputation = await arc_blockchain_service.get_agent_reputation(agent_token_id)

            return {
                "agent_id": agent_id,
                "status": status.value,
                "current_task_id": current_task_id,
                "current_hire_id": current_hire_id,
                "reputation_score": reputation.get("total_score", 0),
                "trust_tier": reputation.get("trust_tier", 0),
                "total_tasks_completed": total_completed,
                "availability": {
                    "is_available": status == AgentInteractionStatus.AVAILABLE,
                    "next_available": None if status == AgentInteractionStatus.AVAILABLE else "unknown"
                }
            }

        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            # Return default status
            return {
                "agent_id": agent_id,
                "status": AgentInteractionStatus.AVAILABLE.value,
                "current_task_id": None,
                "current_hire_id": None,
                "reputation_score": 0,
                "trust_tier": 0,
                "total_tasks_completed": 0,
                "availability": {
                    "is_available": True,
                    "next_available": None
                }
            }

    # =========================================================================
    # Complete Task
    # =========================================================================

    async def complete_task(
        self,
        project_id: str,
        task_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        status: TaskStatus = TaskStatus.COMPLETED,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a task as completed.

        Args:
            project_id: Project identifier
            task_id: Task identifier
            output_data: Task output data
            status: Final task status
            error_message: Error message if failed

        Returns:
            Updated task record

        Raises:
            TaskNotFoundError: If task not found
        """
        try:
            # Find the task
            task_result = await self.client.query_rows(
                TASKS_TABLE,
                filter={"task_id": task_id, "project_id": project_id},
                limit=1
            )

            rows = task_result.get("rows", [])
            if not rows:
                raise TaskNotFoundError(task_id)

            task = rows[0]
            task_row_id = task.get("id") or task.get("row_id")

            timestamp = datetime.utcnow().isoformat() + "Z"

            # Calculate execution time
            started_at = task.get("started_at")
            execution_time = None
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    end_dt = datetime.utcnow()
                    execution_time = (end_dt - start_dt.replace(tzinfo=None)).total_seconds()
                except Exception:
                    pass

            # Update task
            status_value = status.value if isinstance(status, TaskStatus) else status
            updated_task = {
                **task,
                "status": status_value,
                "output_data": output_data,
                "error_message": error_message,
                "execution_time_seconds": execution_time,
                "completed_at": timestamp
            }

            await self.client.update_row(TASKS_TABLE, task_row_id, updated_task)
            logger.info(f"Completed task: {task_id} with status {status_value}")

            # Also update hire record status
            hire_id = task.get("hire_id")
            if hire_id:
                hire_result = await self.client.query_rows(
                    HIRES_TABLE,
                    filter={"hire_id": hire_id, "project_id": project_id},
                    limit=1
                )

                hire_rows = hire_result.get("rows", [])
                if hire_rows:
                    hire = hire_rows[0]
                    hire_row_id = hire.get("id") or hire.get("row_id")
                    hire_status = (
                        AgentInteractionStatus.COMPLETED
                        if status == TaskStatus.COMPLETED
                        else AgentInteractionStatus.FAILED
                    )
                    updated_hire = {
                        **hire,
                        "status": hire_status.value,
                        "completed_at": timestamp
                    }
                    await self.client.update_row(HIRES_TABLE, hire_row_id, updated_hire)

            return self._row_to_task_result(updated_task)

        except TaskNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            raise TaskNotFoundError(task_id)

    # =========================================================================
    # Get Task Result
    # =========================================================================

    async def get_task_result(
        self,
        project_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Get task result.

        Args:
            project_id: Project identifier
            task_id: Task identifier

        Returns:
            Dict containing task result

        Raises:
            TaskNotFoundError: If task not found
        """
        try:
            task_result = await self.client.query_rows(
                TASKS_TABLE,
                filter={"task_id": task_id, "project_id": project_id},
                limit=1
            )

            rows = task_result.get("rows", [])
            if not rows:
                raise TaskNotFoundError(task_id)

            return self._row_to_task_result(rows[0])

        except TaskNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get task result: {e}")
            raise TaskNotFoundError(task_id)

    def _row_to_task_result(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a ZeroDB row to task result format."""
        return {
            "task_id": row.get("task_id"),
            "hire_id": row.get("hire_id"),
            "agent_id": row.get("agent_id"),
            "status": row.get("status"),
            "output_data": row.get("output_data"),
            "error_message": row.get("error_message"),
            "execution_time_seconds": row.get("execution_time_seconds"),
            "payment_receipt_id": row.get("payment_receipt_id"),
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "metadata": row.get("metadata", {})
        }


# Global service instance
agent_interactions_service = AgentInteractionsService()
