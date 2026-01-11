"""
Integration tests for GET /v1/public/projects endpoint.
Tests Epic 1 Story 2 requirements.
"""
import pytest
from fastapi import status


class TestListProjectsEndpoint:
    """Test suite for GET /v1/public/projects endpoint."""

    def test_list_projects_success_user1(self, client, auth_headers_user1):
        """
        Test successful project listing for user 1.
        Epic 1 Story 2: List projects with id, name, status, tier.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert isinstance(data["projects"], list)
        assert isinstance(data["total"], int)

        # User 1 has 2 projects
        assert data["total"] == 2
        assert len(data["projects"]) == 2

        # Verify project structure
        for project in data["projects"]:
            assert "id" in project
            assert "name" in project
            assert "status" in project
            assert "tier" in project

            # Verify no extra fields leaked
            assert set(project.keys()) == {"id", "name", "status", "tier"}

    def test_list_projects_success_user2(self, client, auth_headers_user2):
        """
        Test successful project listing for user 2.
        User 2 has 3 projects in demo data.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user2)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3
        assert len(data["projects"]) == 3

    def test_list_projects_returns_only_user_projects(
        self, client, auth_headers_user1, auth_headers_user2
    ):
        """
        Test that users only see their own projects.
        Epic 1 Story 2: Filter projects by user's API key.
        """
        response1 = client.get("/v1/public/projects", headers=auth_headers_user1)
        response2 = client.get("/v1/public/projects", headers=auth_headers_user2)

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Different users should see different projects
        project_ids_1 = {p["id"] for p in data1["projects"]}
        project_ids_2 = {p["id"] for p in data2["projects"]}

        # No overlap between user projects
        assert len(project_ids_1.intersection(project_ids_2)) == 0

    def test_list_projects_missing_api_key(self, client):
        """
        Test missing X-API-Key header returns 401.
        Epic 2 Story 1: Authenticate using X-API-Key.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_list_projects_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test invalid API key returns 401.
        Epic 2 Story 2: Invalid API keys return 401 INVALID_API_KEY.
        """
        response = client.get("/v1/public/projects", headers=invalid_auth_headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert "detail" in data

    def test_list_projects_error_response_format(self, client):
        """
        Test error response follows DX Contract format.
        Epic 2 Story 3: All errors include detail field.
        DX Contract: All errors return { detail, error_code }.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        # Must have exactly these fields per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_list_projects_status_values(self, client, auth_headers_user1):
        """
        Test project status values are valid.
        Epic 1 Story 5: Project responses consistently show status: ACTIVE.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for project in data["projects"]:
            # Status must be a valid enum value
            assert project["status"] in ["ACTIVE", "INACTIVE", "SUSPENDED"]

    def test_list_projects_tier_values(self, client, auth_headers_user1):
        """
        Test project tier values are valid.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for project in data["projects"]:
            # Tier must be a valid enum value
            assert project["tier"] in ["FREE", "STARTER", "PRO", "ENTERPRISE"]

    def test_list_projects_response_schema(self, client, auth_headers_user1):
        """
        Test response schema matches documented contract.
        Ensures API stability per DX Contract.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Top-level schema
        assert isinstance(data, dict)
        assert set(data.keys()) == {"projects", "total"}

        # Projects array
        assert isinstance(data["projects"], list)

        # Each project schema
        for project in data["projects"]:
            assert isinstance(project, dict)
            assert "id" in project
            assert "name" in project
            assert "status" in project
            assert "tier" in project

            assert isinstance(project["id"], str)
            assert isinstance(project["name"], str)
            assert isinstance(project["status"], str)
            assert isinstance(project["tier"], str)

    def test_list_projects_deterministic_demo_data(
        self, client, auth_headers_user1
    ):
        """
        Test that demo data is deterministic per PRD §9.
        Multiple calls should return identical results.
        """
        response1 = client.get("/v1/public/projects", headers=auth_headers_user1)
        response2 = client.get("/v1/public/projects", headers=auth_headers_user1)

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Should be identical
        assert data1 == data2
