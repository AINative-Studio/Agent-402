"""
Unit Tests for Tier Validation (GitHub Issue #58)

Tests the following requirements:
- Invalid tier values must return HTTP 422
- Error response must include error_code: "INVALID_TIER"
- Error response must include "detail" field with clear message
- Error message should list valid tier options
- Response format must be consistent with API error contract
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app, projects_db, user_api_keys


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Return a valid API key for testing"""
    return "test_api_key_123"


@pytest.fixture(autouse=True)
def clear_projects_db():
    """Clear projects database before each test"""
    projects_db.clear()
    yield
    projects_db.clear()


class TestTierValidation:
    """Test suite for tier validation functionality"""

    def test_valid_tier_free(self, client, valid_api_key):
        """Test that 'free' tier is accepted"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "free",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "free"
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_valid_tier_starter(self, client, valid_api_key):
        """Test that 'starter' tier is accepted"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "starter",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "starter"

    def test_valid_tier_professional(self, client, valid_api_key):
        """Test that 'professional' tier is accepted"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "professional",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "professional"

    def test_valid_tier_enterprise(self, client, valid_api_key):
        """Test that 'enterprise' tier is accepted"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "enterprise",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "enterprise"

    def test_invalid_tier_returns_422(self, client, valid_api_key):
        """
        Requirement: Invalid tier values must return HTTP 422
        """
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "invalid_tier",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422

    def test_invalid_tier_has_error_code(self, client, valid_api_key):
        """
        Requirement: Error response must include error_code: "INVALID_TIER"
        """
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "premium",  # Not a valid tier
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "INVALID_TIER"

    def test_invalid_tier_has_detail_field(self, client, valid_api_key):
        """
        Requirement: Error response must include "detail" field with clear message
        """
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "basic",  # Not a valid tier
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_error_message_lists_valid_tiers(self, client, valid_api_key):
        """
        Requirement: Error message should list valid tier options
        """
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "gold",  # Not a valid tier
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        data = response.json()
        detail = data["detail"].lower()

        # Check that all valid tiers are mentioned in the error message
        assert "free" in detail
        assert "starter" in detail
        assert "professional" in detail
        assert "enterprise" in detail

    def test_error_response_format_consistency(self, client, valid_api_key):
        """
        Requirement: Response format must be consistent with API error contract
        As per DX Contract §6: All errors return { detail, error_code }
        """
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "platinum",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        data = response.json()

        # Must have both detail and error_code
        assert "detail" in data
        assert "error_code" in data

        # Detail must be a string
        assert isinstance(data["detail"], str)

        # error_code must be INVALID_TIER
        assert data["error_code"] == "INVALID_TIER"

    def test_tier_case_insensitive(self, client, valid_api_key):
        """Test that tier validation is case-insensitive"""
        # Test uppercase
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project 1",
                "tier": "FREE",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 201
        assert response.json()["tier"] == "free"  # Should be normalized to lowercase

        # Test mixed case
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project 2",
                "tier": "Starter",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 201
        assert response.json()["tier"] == "starter"

    def test_tier_with_whitespace(self, client, valid_api_key):
        """Test that tier validation handles whitespace"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "  free  ",  # Whitespace around valid tier
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        assert response.json()["tier"] == "free"

    def test_empty_tier_value(self, client, valid_api_key):
        """Test that empty tier value is rejected"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        data = response.json()
        assert "error_code" in data

    def test_missing_tier_field(self, client, valid_api_key):
        """Test that missing tier field is rejected"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "database_enabled": True
                # tier is missing
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422

    def test_numeric_tier_value(self, client, valid_api_key):
        """Test that numeric tier values are rejected"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": 123,  # Invalid type
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422

    def test_multiple_invalid_tiers(self, client, valid_api_key):
        """Test various invalid tier values"""
        invalid_tiers = [
            "basic",
            "premium",
            "gold",
            "silver",
            "platinum",
            "trial",
            "pro",
            "business",
            "unlimited"
        ]

        for invalid_tier in invalid_tiers:
            response = client.post(
                "/v1/public/projects",
                json={
                    "name": f"Test Project {invalid_tier}",
                    "tier": invalid_tier,
                    "database_enabled": True
                },
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 422, f"Tier '{invalid_tier}' should be rejected"
            data = response.json()
            assert data["error_code"] == "INVALID_TIER", f"Tier '{invalid_tier}' should return INVALID_TIER"


class TestProjectCreation:
    """Additional tests for project creation functionality"""

    def test_successful_project_creation_response_structure(self, client, valid_api_key):
        """Test that successful project creation returns proper structure"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "description": "A test project",
                "tier": "free",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify required fields
        assert "id" in data
        assert "name" in data
        assert "tier" in data
        assert "status" in data
        assert "database_enabled" in data
        assert "created_at" in data

        # Verify values
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert data["tier"] == "free"
        assert data["status"] == "ACTIVE"
        assert data["database_enabled"] is True

    def test_project_list_shows_tier(self, client, valid_api_key):
        """
        Test that listing projects shows tier information
        As per Epic 1: list projects should show id, name, status, tier
        """
        # Create a project first
        client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "starter",
                "database_enabled": True
            },
            headers={"X-API-Key": valid_api_key}
        )

        # List projects
        response = client.get(
            "/v1/public/projects",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["tier"] == "starter"
        assert "id" in projects[0]
        assert "name" in projects[0]
        assert "status" in projects[0]


class TestAuthentication:
    """Test authentication requirements"""

    def test_missing_api_key_returns_401(self, client):
        """Test that missing API key returns 401"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "free",
                "database_enabled": True
            }
        )

        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        """Test that invalid API key returns 401"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "free",
                "database_enabled": True
            },
            headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_invalid_api_key_has_detail_field(self, client):
        """Test that invalid API key error has detail field"""
        response = client.post(
            "/v1/public/projects",
            json={
                "name": "Test Project",
                "tier": "free",
                "database_enabled": True
            },
            headers={"X-API-Key": "wrong_key"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
