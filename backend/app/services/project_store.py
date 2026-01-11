"""
Project data store.
For MVP demo (PRD §9), we use deterministic in-memory storage.
In production, this would connect to ZeroDB or a database.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.models.project import Project, ProjectStatus, ProjectTier


class ProjectStore:
    """
    In-memory project store for deterministic demo.
    Per PRD §9: Demo setup must be deterministic.
    """

    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._initialize_demo_projects()

    def _initialize_demo_projects(self):
        """
        Initialize deterministic demo projects per PRD §9.
        Creates predefined projects for demo API key users.
        """
        demo_projects = [
            # User 1 projects
            Project(
                id="proj_demo_u1_001",
                name="Agent Finance Demo",
                status=ProjectStatus.ACTIVE,
                tier=ProjectTier.FREE,
                user_id="user_1",
                description="Demo project for autonomous fintech agents",
                database_enabled=True,
                created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Project(
                id="proj_demo_u1_002",
                name="X402 Integration",
                status=ProjectStatus.ACTIVE,
                tier=ProjectTier.STARTER,
                user_id="user_1",
                description="X402 protocol integration and testing",
                database_enabled=True,
                created_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # User 2 projects
            Project(
                id="proj_demo_u2_001",
                name="CrewAI Workflow",
                status=ProjectStatus.ACTIVE,
                tier=ProjectTier.PRO,
                user_id="user_2",
                description="Multi-agent CrewAI orchestration",
                database_enabled=True,
                created_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Project(
                id="proj_demo_u2_002",
                name="Compliance Audit System",
                status=ProjectStatus.ACTIVE,
                tier=ProjectTier.ENTERPRISE,
                user_id="user_2",
                description="Agent-based compliance and KYC verification",
                database_enabled=True,
                created_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Project(
                id="proj_demo_u2_003",
                name="Testing Sandbox",
                status=ProjectStatus.INACTIVE,
                tier=ProjectTier.FREE,
                user_id="user_2",
                description="Experimental testing environment",
                database_enabled=False,
                created_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for project in demo_projects:
            self._projects[project.id] = project

    def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self._projects.get(project_id)

    def get_by_user_id(self, user_id: str) -> List[Project]:
        """
        Get all projects for a user.
        Returns empty list if no projects exist (per Epic 1 Story 2).
        """
        return [
            project for project in self._projects.values()
            if project.user_id == user_id
        ]

    def create(self, project: Project) -> Project:
        """
        Create a new project.
        For production, this would insert into ZeroDB.
        """
        self._projects[project.id] = project
        return project

    def update(self, project: Project) -> Project:
        """Update an existing project."""
        if project.id not in self._projects:
            raise ValueError(f"Project not found: {project.id}")
        self._projects[project.id] = project
        return project

    def delete(self, project_id: str) -> bool:
        """Delete a project by ID."""
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    def count_by_user_id(self, user_id: str) -> int:
        """Count projects owned by a user."""
        return len(self.get_by_user_id(user_id))


# Global singleton instance for demo
project_store = ProjectStore()
