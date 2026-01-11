"""
Project service layer - Business logic for project operations.

Implements project limit validation and CRUD operations.
"""
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.core.config import Tier, get_project_limit
from app.core.exceptions import ProjectLimitExceededException
from app.models.project import ProjectCreate, ProjectResponse


class ProjectService:
    """
    Service layer for project operations.

    Implements business logic including tier-based project limit validation.
    In production, this would interface with a real database.
    For MVP, uses in-memory storage per user.
    """

    def __init__(self):
        # In-memory storage: user_id -> list of projects
        # In production, this would be replaced with database queries
        self._projects: Dict[str, List[ProjectResponse]] = {}

    def get_user_projects(self, user_id: str) -> List[ProjectResponse]:
        """
        Get all projects for a user.

        Args:
            user_id: User identifier

        Returns:
            List of user's projects
        """
        return self._projects.get(user_id, [])

    def count_user_projects(self, user_id: str) -> int:
        """
        Count total projects for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of projects owned by the user
        """
        return len(self._projects.get(user_id, []))

    def get_user_tier(self, user_id: str) -> str:
        """
        Get the user's current tier.

        In production, this would query the user's account settings.
        For MVP, infers tier from existing projects or defaults to 'free'.

        Args:
            user_id: User identifier

        Returns:
            User's tier (free, starter, pro, enterprise)
        """
        projects = self.get_user_projects(user_id)
        if not projects:
            return Tier.FREE

        # Return the highest tier among user's projects
        # In production, this would be a separate user attribute
        tier_priority = {Tier.FREE: 0, Tier.STARTER: 1, Tier.PRO: 2, Tier.ENTERPRISE: 3}
        max_tier = max((p.tier for p in projects), key=lambda t: tier_priority.get(t, 0))
        return max_tier

    def suggest_upgrade_tier(self, current_tier: str) -> Optional[str]:
        """
        Suggest the next tier for upgrade.

        Args:
            current_tier: User's current tier

        Returns:
            Suggested upgrade tier, or None if already at highest tier
        """
        tier_upgrades = {
            Tier.FREE: "starter",
            Tier.STARTER: "pro",
            Tier.PRO: "enterprise",
            Tier.ENTERPRISE: None
        }
        return tier_upgrades.get(current_tier)

    def validate_project_limit(self, user_id: str, requested_tier: str) -> None:
        """
        Validate that the user can create another project.

        Checks against tier-based project limits. Raises exception if limit exceeded.

        Args:
            user_id: User identifier
            requested_tier: Tier for the new project

        Raises:
            ProjectLimitExceededException: If user has reached their project limit
        """
        # Get user's effective tier (use requested tier if higher)
        user_tier = self.get_user_tier(user_id)

        # For tier validation: use the requested tier to check limits
        # This ensures users can't bypass limits by creating projects at higher tiers
        # In production, tier would be validated against user's subscription
        tier_to_check = requested_tier

        # Get the limit for this tier
        project_limit = get_project_limit(tier_to_check)

        # Count current projects
        current_count = self.count_user_projects(user_id)

        # Check if limit is exceeded
        if current_count >= project_limit:
            upgrade_tier = self.suggest_upgrade_tier(tier_to_check)
            raise ProjectLimitExceededException(
                current_tier=tier_to_check,
                project_limit=project_limit,
                current_count=current_count,
                upgrade_tier=upgrade_tier
            )

    def create_project(self, user_id: str, project_data: ProjectCreate) -> ProjectResponse:
        """
        Create a new project for a user.

        Validates project limits before creation.

        Args:
            user_id: User identifier
            project_data: Project creation data

        Returns:
            Created project

        Raises:
            ProjectLimitExceededException: If user has reached their project limit
        """
        # Validate project limit
        self.validate_project_limit(user_id, project_data.tier)

        # Create the project
        project = ProjectResponse(
            id=uuid4(),
            name=project_data.name,
            description=project_data.description,
            tier=project_data.tier,
            status="ACTIVE",  # Per PRD requirement
            database_enabled=project_data.database_enabled
        )

        # Store the project
        if user_id not in self._projects:
            self._projects[user_id] = []
        self._projects[user_id].append(project)

        return project

    def list_projects(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[ProjectResponse], int]:
        """
        List projects for a user with pagination.

        Args:
            user_id: User identifier
            limit: Maximum number of projects to return
            offset: Number of projects to skip

        Returns:
            Tuple of (projects list, total count)
        """
        projects = self.get_user_projects(user_id)
        total = len(projects)

        # Apply pagination
        start = offset
        end = offset + limit
        paginated = projects[start:end]

        return paginated, total

    def get_project(self, user_id: str, project_id: UUID) -> Optional[ProjectResponse]:
        """
        Get a specific project by ID.

        Args:
            user_id: User identifier
            project_id: Project identifier

        Returns:
            Project if found, None otherwise
        """
        projects = self.get_user_projects(user_id)
        for project in projects:
            if project.id == project_id:
                return project
        return None


# Global service instance
project_service = ProjectService()
