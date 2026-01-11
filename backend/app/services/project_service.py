"""
Project service layer.
Implements business logic for project operations.
"""
from typing import List
from app.models.project import Project
from app.services.project_store import project_store
from app.core.errors import ProjectNotFoundError, UnauthorizedError


class ProjectService:
    """
    Project service for business logic.
    Separates business logic from HTTP layer.
    """

    def __init__(self):
        self.store = project_store

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


# Global service instance
project_service = ProjectService()
