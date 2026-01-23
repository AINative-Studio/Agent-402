"""
Unit tests for ProjectService.
Tests business logic layer.
"""
import pytest
from app.services.project_service import ProjectService
from app.services.project_store import ProjectStore
from app.core.errors import ProjectNotFoundError, UnauthorizedError


class TestProjectService:
    """Test suite for ProjectService class."""

    @pytest.fixture
    def service(self):
        """Create a fresh ProjectService instance for each test."""
        return ProjectService()

    def test_list_user_projects_returns_correct_projects(self, service):
        """
        Test that list_user_projects returns only projects owned by user.
        Epic 1 Story 2: Filter projects by user's API key.
        """
        user1_projects = service.list_user_projects("user_1")
        user2_projects = service.list_user_projects("user_2")

        # User 1 has 3 projects (UUID project, legacy proj_demo_u1_001, proj_demo_u1_002)
        assert len(user1_projects) == 3
        for project in user1_projects:
            assert project.user_id == "user_1"

        # User 2 should have 3 projects
        assert len(user2_projects) == 3
        for project in user2_projects:
            assert project.user_id == "user_2"

    def test_list_user_projects_returns_empty_for_unknown_user(self, service):
        """
        Test that list_user_projects returns empty list for user with no projects.
        Epic 1 Story 2: Return empty array if no projects exist.
        """
        unknown_projects = service.list_user_projects("unknown_user")

        assert isinstance(unknown_projects, list)
        assert len(unknown_projects) == 0

    def test_get_project_success(self, service):
        """
        Test successful project retrieval.
        """
        project = service.get_project("proj_demo_u1_001", "user_1")

        assert project is not None
        assert project.id == "proj_demo_u1_001"
        assert project.user_id == "user_1"

    def test_get_project_not_found(self, service):
        """
        Test get_project raises ProjectNotFoundError for non-existent project.
        """
        with pytest.raises(ProjectNotFoundError) as exc_info:
            service.get_project("nonexistent_project", "user_1")

        assert exc_info.value.error_code == "PROJECT_NOT_FOUND"
        assert "nonexistent_project" in exc_info.value.detail

    def test_get_project_unauthorized(self, service):
        """
        Test get_project raises UnauthorizedError when user doesn't own project.
        """
        # Try to access user_1's project as user_2
        with pytest.raises(UnauthorizedError) as exc_info:
            service.get_project("proj_demo_u1_001", "user_2")

        assert exc_info.value.error_code == "UNAUTHORIZED"

    def test_count_user_projects(self, service):
        """Test count_user_projects returns correct count."""
        # User 1 has 3 projects (UUID project, legacy proj_demo_u1_001, proj_demo_u1_002)
        assert service.count_user_projects("user_1") == 3
        assert service.count_user_projects("user_2") == 3
        assert service.count_user_projects("unknown_user") == 0
