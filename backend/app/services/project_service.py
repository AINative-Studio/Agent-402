"""
Project service layer.
Implements business logic for project operations.

Issue #123: Enhanced Projects API with agent associations,
task tracking, and payment linking.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from app.models.project import Project, ProjectStatus
from app.services.project_store import project_store
from app.core.errors import (
    ProjectNotFoundError,
    UnauthorizedError,
    AgentAlreadyAssociatedError,
    AgentNotAssociatedError,
    InvalidProjectStatusError
)


class ProjectService:
    """
    Project service for business logic.
    Separates business logic from HTTP layer.

    Issue #123: Extended with agent associations, task tracking,
    and payment linking.
    """

    def __init__(self):
        self.store = project_store
        # In-memory stores for demo (would be ZeroDB in production)
        self._agent_associations: Dict[str, List[Dict[str, Any]]] = {}
        self._project_tasks: Dict[str, List[Dict[str, Any]]] = {}
        self._project_payments: Dict[str, List[Dict[str, Any]]] = {}

    def list_user_projects(self, user_id: str) -> List[Project]:
        """
        List all projects for a user.
        Per Epic 1 Story 2: Return empty array if no projects exist.

        Args:
            user_id: Authenticated user ID

        Returns:
            List of projects owned by the user (empty list if none)
        """
        projects = self.store.get_by_user_id(user_id)
        return projects

    def get_project(self, project_id: str, user_id: str) -> Project:
        """
        Get a single project by ID.
        Validates that user owns the project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID

        Returns:
            Project if found and owned by user

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        project = self.store.get_by_id(project_id)

        if not project:
            raise ProjectNotFoundError(project_id)

        if project.user_id != user_id:
            raise UnauthorizedError(
                f"Not authorized to access project: {project_id}"
            )

        return project

    def count_user_projects(self, user_id: str) -> int:
        """Count total projects for a user."""
        return self.store.count_by_user_id(user_id)

    # Issue #123: Agent association methods

    def associate_agent(
        self,
        project_id: str,
        user_id: str,
        agent_did: str,
        role: str = "member"
    ) -> Dict[str, Any]:
        """
        Associate an agent with a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            agent_did: Agent DID to associate
            role: Agent role (executor, observer, admin, member)

        Returns:
            Dict with association details

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
            AgentAlreadyAssociatedError: If agent is already associated
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        # Initialize project's agent list if needed
        if project_id not in self._agent_associations:
            self._agent_associations[project_id] = []

        # Check for duplicate
        for assoc in self._agent_associations[project_id]:
            if assoc["agent_did"] == agent_did:
                raise AgentAlreadyAssociatedError(agent_did, project_id)

        # Create association
        association = {
            "project_id": project_id,
            "agent_did": agent_did,
            "role": role,
            "associated_at": datetime.now(timezone.utc)
        }

        self._agent_associations[project_id].append(association)
        return association

    def disassociate_agent(
        self,
        project_id: str,
        user_id: str,
        agent_did: str
    ) -> bool:
        """
        Remove an agent from a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            agent_did: Agent DID to disassociate

        Returns:
            True if successfully disassociated

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
            AgentNotAssociatedError: If agent is not associated
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        if project_id not in self._agent_associations:
            raise AgentNotAssociatedError(agent_did, project_id)

        # Find and remove the association
        for i, assoc in enumerate(self._agent_associations[project_id]):
            if assoc["agent_did"] == agent_did:
                self._agent_associations[project_id].pop(i)
                return True

        raise AgentNotAssociatedError(agent_did, project_id)

    def list_project_agents(
        self,
        project_id: str,
        user_id: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all agents associated with a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID

        Returns:
            Tuple of (list of associations, total count)

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        agents = self._agent_associations.get(project_id, [])
        return agents, len(agents)

    # Issue #123: Task tracking methods

    def track_task(
        self,
        project_id: str,
        user_id: str,
        task_id: str,
        status: str = "pending",
        agent_did: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track a task under a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            task_id: Task identifier
            status: Task status (pending, in_progress, completed, failed)
            agent_did: Optional agent DID
            result: Optional task result

        Returns:
            Dict with task tracking details

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        # Initialize project's task list if needed
        if project_id not in self._project_tasks:
            self._project_tasks[project_id] = []

        # Create or update task tracking
        task_record = {
            "project_id": project_id,
            "task_id": task_id,
            "status": status,
            "agent_did": agent_did,
            "result": result,
            "tracked_at": datetime.now(timezone.utc)
        }

        # Update if task_id exists, otherwise add new
        for i, existing in enumerate(self._project_tasks[project_id]):
            if existing["task_id"] == task_id:
                self._project_tasks[project_id][i] = task_record
                return task_record

        self._project_tasks[project_id].append(task_record)
        return task_record

    def get_project_tasks(
        self,
        project_id: str,
        user_id: str,
        status_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get all tasks tracked under a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            status_filter: Optional status to filter by

        Returns:
            Tuple of (list of tasks, total count)

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        tasks = self._project_tasks.get(project_id, [])

        if status_filter:
            tasks = [t for t in tasks if t["status"] == status_filter]

        return tasks, len(tasks)

    # Issue #123: Payment linking methods

    def link_payment(
        self,
        project_id: str,
        user_id: str,
        payment_receipt_id: str,
        amount: float,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Link a payment receipt to a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            payment_receipt_id: X402 payment receipt ID
            amount: Payment amount
            currency: Currency code

        Returns:
            Dict with payment link details

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        # Initialize project's payment list if needed
        if project_id not in self._project_payments:
            self._project_payments[project_id] = []

        # Create payment link
        payment = {
            "project_id": project_id,
            "payment_receipt_id": payment_receipt_id,
            "amount": amount,
            "currency": currency,
            "linked_at": datetime.now(timezone.utc)
        }

        self._project_payments[project_id].append(payment)
        return payment

    def get_payment_summary(
        self,
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get payment summary for a project.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID

        Returns:
            Dict with total_spent, payment_count, and payments list

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
        """
        # Verify project ownership
        self.get_project(project_id, user_id)

        payments = self._project_payments.get(project_id, [])
        total_spent = sum(p["amount"] for p in payments)

        return {
            "total_spent": total_spent,
            "payment_count": len(payments),
            "payments": payments
        }

    # Issue #123: Status workflow methods

    def update_status(
        self,
        project_id: str,
        user_id: str,
        new_status: str
    ) -> Project:
        """
        Update project status.

        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            new_status: New status value

        Returns:
            Updated project

        Raises:
            ProjectNotFoundError: If project doesn't exist
            UnauthorizedError: If user doesn't own the project
            InvalidProjectStatusError: If status is invalid
        """
        # Verify project ownership
        project = self.get_project(project_id, user_id)

        # Validate status
        valid_statuses = [s.value for s in ProjectStatus]
        normalized_status = new_status.upper()

        if normalized_status not in valid_statuses:
            raise InvalidProjectStatusError(new_status, valid_statuses)

        # Update project status
        project.status = ProjectStatus(normalized_status)
        project.updated_at = datetime.now(timezone.utc)

        # Update in store
        self.store.update(project)

        return project


# Global service instance
project_service = ProjectService()
