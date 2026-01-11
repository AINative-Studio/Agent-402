"""
Unit tests for project limit validation and error handling.

Tests GitHub issue #59: PROJECT_LIMIT_EXCEEDED error handling
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import Tier, get_project_limit
from app.core.exceptions import ProjectLimitExceededException
from app.main import create_app
from app.models.project import ProjectCreate
from app.services.project_service import ProjectService


class TestProjectLimitConfiguration:
    """Test tier-based project limit configuration."""

    def test_get_project_limit_free(self):
        """Free tier should have 3 project limit."""
        assert get_project_limit(Tier.FREE) == 3

    def test_get_project_limit_starter(self):
        """Starter tier should have 10 project limit."""
        assert get_project_limit(Tier.STARTER) == 10

    def test_get_project_limit_pro(self):
        """Pro tier should have 50 project limit."""
        assert get_project_limit(Tier.PRO) == 50

    def test_get_project_limit_enterprise(self):
        """Enterprise tier should have effectively unlimited projects."""
        assert get_project_limit(Tier.ENTERPRISE) == 999999

    def test_get_project_limit_case_insensitive(self):
        """Project limit lookup should be case-insensitive."""
        assert get_project_limit("FREE") == 3
        assert get_project_limit("free") == 3
        assert get_project_limit("Free") == 3

    def test_get_project_limit_invalid_tier(self):
        """Invalid tier should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid tier"):
            get_project_limit("invalid-tier")


class TestProjectLimitException:
    """Test ProjectLimitExceededException behavior."""

    def test_exception_attributes(self):
        """Exception should contain all required attributes."""
        exc = ProjectLimitExceededException(
            current_tier="free",
            project_limit=3,
            current_count=3,
            upgrade_tier="starter"
        )

        assert exc.error_code == "PROJECT_LIMIT_EXCEEDED"
        assert exc.status_code == 429  # Too Many Requests
        assert exc.current_tier == "free"
        assert exc.project_limit == 3
        assert exc.current_count == 3
        assert exc.upgrade_tier == "starter"

    def test_exception_detail_with_upgrade(self):
        """Exception detail should include upgrade suggestion."""
        exc = ProjectLimitExceededException(
            current_tier="free",
            project_limit=3,
            current_count=3,
            upgrade_tier="starter"
        )

        assert "Project limit exceeded" in exc.detail
        assert "tier 'free'" in exc.detail
        assert "3/3" in exc.detail
        assert "upgrade to 'starter'" in exc.detail
        assert "support@ainative.studio" in exc.detail

    def test_exception_detail_without_upgrade(self):
        """Exception detail should suggest support when no upgrade available."""
        exc = ProjectLimitExceededException(
            current_tier="enterprise",
            project_limit=999999,
            current_count=999999,
            upgrade_tier=None
        )

        assert "Project limit exceeded" in exc.detail
        assert "contact support" in exc.detail
        assert "support@ainative.studio" in exc.detail


class TestProjectServiceLimitValidation:
    """Test project service limit validation logic."""

    def setup_method(self):
        """Create a fresh service instance for each test."""
        self.service = ProjectService()
        self.user_id = "test-user-123"

    def test_validate_limit_within_free_tier(self):
        """Should allow creating projects within free tier limit."""
        # Create 2 projects (under limit of 3)
        for i in range(2):
            project_data = ProjectCreate(
                name=f"test-project-{i}",
                tier=Tier.FREE
            )
            self.service.create_project(self.user_id, project_data)

        # Should not raise exception
        self.service.validate_project_limit(self.user_id, Tier.FREE)

    def test_validate_limit_at_free_tier_boundary(self):
        """Should raise exception when creating 4th project on free tier."""
        # Create 3 projects (at limit)
        for i in range(3):
            project_data = ProjectCreate(
                name=f"test-project-{i}",
                tier=Tier.FREE
            )
            self.service.create_project(self.user_id, project_data)

        # Should raise exception for 4th project
        with pytest.raises(ProjectLimitExceededException) as exc_info:
            self.service.validate_project_limit(self.user_id, Tier.FREE)

        assert exc_info.value.current_tier == Tier.FREE
        assert exc_info.value.project_limit == 3
        assert exc_info.value.current_count == 3
        assert exc_info.value.upgrade_tier == Tier.STARTER

    def test_validate_limit_starter_tier(self):
        """Should allow up to 10 projects on starter tier."""
        # Create 9 projects
        for i in range(9):
            project_data = ProjectCreate(
                name=f"test-project-{i}",
                tier=Tier.STARTER
            )
            self.service.create_project(self.user_id, project_data)

        # 10th should still work
        self.service.validate_project_limit(self.user_id, Tier.STARTER)

        # Create 10th project
        project_data = ProjectCreate(name="test-project-9", tier=Tier.STARTER)
        self.service.create_project(self.user_id, project_data)

        # 11th should fail
        with pytest.raises(ProjectLimitExceededException) as exc_info:
            self.service.validate_project_limit(self.user_id, Tier.STARTER)

        assert exc_info.value.current_count == 10
        assert exc_info.value.upgrade_tier == Tier.PRO

    def test_validate_limit_enterprise_tier(self):
        """Enterprise tier should have effectively unlimited projects."""
        # Create many projects
        for i in range(100):
            project_data = ProjectCreate(
                name=f"test-project-{i}",
                tier=Tier.ENTERPRISE
            )
            self.service.create_project(self.user_id, project_data)

        # Should not raise exception
        self.service.validate_project_limit(self.user_id, Tier.ENTERPRISE)

    def test_suggest_upgrade_tier_progression(self):
        """Should suggest correct upgrade path."""
        assert self.service.suggest_upgrade_tier(Tier.FREE) == "starter"
        assert self.service.suggest_upgrade_tier(Tier.STARTER) == "pro"
        assert self.service.suggest_upgrade_tier(Tier.PRO) == "enterprise"
        assert self.service.suggest_upgrade_tier(Tier.ENTERPRISE) is None


class TestProjectAPILimitErrors:
    """Test project API endpoints return correct error responses."""

    def setup_method(self):
        """Create test client for each test."""
        # Import and reset the service for each test
        from app.services.project_service import project_service
        project_service._projects.clear()  # Clear state between tests

        app = create_app()
        self.client = TestClient(app)
        self.api_key = f"test-api-key-{id(self)}"  # Unique per test instance
        self.headers = {"X-API-Key": self.api_key}

    def test_create_project_success(self):
        """Should successfully create a project within limits."""
        response = self.client.post(
            "/v1/public/projects",
            json={
                "name": "test-project",
                "description": "Test project",
                "tier": "free",
                "database_enabled": True
            },
            headers=self.headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "test-project"
        assert data["tier"] == "free"
        assert data["status"] == "ACTIVE"

    def test_create_project_limit_exceeded_returns_429(self):
        """Should return HTTP 429 when project limit exceeded."""
        # Create 3 projects (free tier limit)
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={
                    "name": f"test-project-{i}",
                    "tier": "free",
                    "database_enabled": True
                },
                headers=self.headers
            )

        # 4th project should fail with 429
        response = self.client.post(
            "/v1/public/projects",
            json={
                "name": "test-project-4",
                "tier": "free",
                "database_enabled": True
            },
            headers=self.headers
        )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_limit_exceeded_error_has_error_code(self):
        """Error response should include error_code field."""
        # Create 3 projects to hit limit
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=self.headers
            )

        # Attempt 4th project
        response = self.client.post(
            "/v1/public/projects",
            json={"name": "project-4", "tier": "free"},
            headers=self.headers
        )

        assert response.status_code == 429
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "PROJECT_LIMIT_EXCEEDED"

    def test_limit_exceeded_error_has_detail(self):
        """Error response should include detailed error message."""
        # Create 3 projects to hit limit
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=self.headers
            )

        # Attempt 4th project
        response = self.client.post(
            "/v1/public/projects",
            json={"name": "project-4", "tier": "free"},
            headers=self.headers
        )

        data = response.json()
        assert "detail" in data

        detail = data["detail"]
        # Verify detail contains required information
        assert "Project limit exceeded" in detail
        assert "tier 'free'" in detail
        assert "3/3" in detail  # current_count/limit

    def test_limit_exceeded_suggests_upgrade(self):
        """Error message should suggest upgrade path."""
        # Create 3 free tier projects
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=self.headers
            )

        response = self.client.post(
            "/v1/public/projects",
            json={"name": "project-4", "tier": "free"},
            headers=self.headers
        )

        detail = response.json()["detail"]
        assert "upgrade to 'starter'" in detail

    def test_limit_exceeded_includes_support_contact(self):
        """Error message should include support contact information."""
        # Create 3 projects
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=self.headers
            )

        response = self.client.post(
            "/v1/public/projects",
            json={"name": "project-4", "tier": "free"},
            headers=self.headers
        )

        detail = response.json()["detail"]
        assert "support@ainative.studio" in detail

    def test_invalid_tier_returns_422(self):
        """Should return HTTP 422 for invalid tier."""
        response = self.client.post(
            "/v1/public/projects",
            json={
                "name": "test-project",
                "tier": "invalid-tier"
            },
            headers=self.headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["error_code"] == "INVALID_TIER"

    def test_missing_api_key_returns_401(self):
        """Should return HTTP 401 when API key is missing."""
        response = self.client.post(
            "/v1/public/projects",
            json={"name": "test-project", "tier": "free"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_different_tiers_have_different_limits(self):
        """Should enforce different limits for different tiers."""
        # Use a fresh API key to avoid state from other tests
        unique_headers = {"X-API-Key": f"tier-test-{id(self)}"}

        # Test free tier (limit: 3)
        for i in range(3):
            response = self.client.post(
                "/v1/public/projects",
                json={"name": f"free-project-{i}", "tier": "free"},
                headers=unique_headers
            )
            assert response.status_code == 201

        # 4th free tier project should fail
        response = self.client.post(
            "/v1/public/projects",
            json={"name": "free-project-4", "tier": "free"},
            headers=unique_headers
        )
        assert response.status_code == 429

    def test_list_projects_shows_all_created(self):
        """List endpoint should show all created projects."""
        # Use unique headers to isolate this test
        unique_headers = {"X-API-Key": f"list-test-{id(self)}"}

        # Create 2 projects
        for i in range(2):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=unique_headers
            )

        # List projects
        response = self.client.get(
            "/v1/public/projects",
            headers=unique_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


class TestErrorResponseContract:
    """Test that error responses follow the DX contract."""

    def setup_method(self):
        """Create test client for each test."""
        app = create_app()
        self.client = TestClient(app)

    def test_all_errors_have_detail_field(self):
        """All error responses must include a 'detail' field."""
        errors_to_test = [
            # Invalid API key
            (
                "POST",
                "/v1/public/projects",
                {},
                None
            ),
            # Invalid tier
            (
                "POST",
                "/v1/public/projects",
                {"name": "test", "tier": "invalid"},
                {"X-API-Key": "test-key"}
            ),
        ]

        for method, path, json_data, headers in errors_to_test:
            if method == "POST":
                response = self.client.post(path, json=json_data, headers=headers)
            else:
                response = self.client.get(path, headers=headers)

            # All errors should have detail field
            if response.status_code >= 400:
                data = response.json()
                assert "detail" in data, f"Missing 'detail' in error response for {path}"

    def test_domain_errors_have_error_code(self):
        """Domain-specific errors should include error_code field."""
        # Test PROJECT_LIMIT_EXCEEDED
        headers = {"X-API-Key": "test-key"}
        for i in range(3):
            self.client.post(
                "/v1/public/projects",
                json={"name": f"project-{i}", "tier": "free"},
                headers=headers
            )

        response = self.client.post(
            "/v1/public/projects",
            json={"name": "project-4", "tier": "free"},
            headers=headers
        )

        assert response.status_code == 429
        data = response.json()
        assert "error_code" in data
        assert isinstance(data["error_code"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
