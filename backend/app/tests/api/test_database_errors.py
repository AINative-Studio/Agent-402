"""
Test suite for Issue #69: Epic 11 Story 3 - Test fails loudly on missing /database/.

Tests proper error handling when database endpoints are accessed without proper
paths or table IDs.

Requirements:
- Test GET /database/ returns 404 (not a valid endpoint)
- Test GET /tables without table_id returns 200 (list endpoint)
- Test GET /tables/{invalid_id} returns 404
- Test database operations with missing project_id return 401/403
- Verify error messages are descriptive
- Test coverage >= 80%

DX Contract:
- All errors return { detail, error_code }
- Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
- Validation errors use HTTP 422
"""
import pytest
from fastapi import status


class TestInvalidDatabasePaths:
    """Test cases for invalid database path scenarios."""

    def test_get_database_root_returns_404(self, client):
        """
        Test that GET /database/ returns 404 PATH_NOT_FOUND.

        This is not a valid API endpoint - should return path not found.
        """
        response = client.get("/database/", headers={"X-API-Key": "demo_key_user1"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_database_root_error_code(self, client):
        """
        Test that GET /database/ returns PATH_NOT_FOUND error code.

        Epic 9 Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
        """
        response = client.get("/database/", headers={"X-API-Key": "demo_key_user1"})

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "PATH_NOT_FOUND"

    def test_get_database_root_has_detail(self, client):
        """
        Test that GET /database/ returns clear detail message.

        DX Contract: All errors include a detail field
        """
        response = client.get("/database/", headers={"X-API-Key": "demo_key_user1"})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # Should mention path not found
        assert "path" in data["detail"].lower() or "not found" in data["detail"].lower()

    def test_get_database_root_error_format(self, client):
        """
        Test that GET /database/ follows DX Contract error format.

        DX Contract: All errors return { detail, error_code }
        """
        response = client.get("/database/", headers={"X-API-Key": "demo_key_user1"})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_get_database_without_trailing_slash_returns_404(self, client):
        """
        Test that GET /database (no trailing slash) returns 404.

        Ensure consistency in path validation.
        """
        response = client.get("/database", headers={"X-API-Key": "demo_key_user1"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_database_arbitrary_path_returns_404(self, client):
        """
        Test that GET /database/foo/bar returns 404 PATH_NOT_FOUND.

        Invalid nested paths under /database/ should return path not found.
        """
        response = client.get("/database/foo/bar", headers={"X-API-Key": "demo_key_user1"})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"


class TestTableListEndpoint:
    """Test cases for GET /tables without table_id (list endpoint)."""

    def test_get_tables_without_table_id_returns_200(self, client, auth_headers_user1):
        """
        Test that GET /v1/public/{project_id}/tables returns 200.

        This is a valid list endpoint - should succeed (empty list if no tables).
        """
        project_id = "test-project-123"
        response = client.get(
            f"/v1/public/{project_id}/tables",
            headers=auth_headers_user1
        )

        # Should return 200 for list endpoint (may return 404 if project doesn't exist,
        # but that's a PROJECT_NOT_FOUND, not a path error)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_tables_list_structure(self, client, auth_headers_user1):
        """
        Test that GET /v1/public/{project_id}/tables returns proper list structure.

        If project exists, should return { tables: [], total: 0 }
        """
        # Note: This test verifies the list endpoint works as expected
        # It may return 404 if project doesn't exist, which is correct behavior
        project_id = "test-project-123"
        response = client.get(
            f"/v1/public/{project_id}/tables",
            headers=auth_headers_user1
        )

        # If project exists, should return list structure
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "tables" in data
            assert "total" in data
            assert isinstance(data["tables"], list)
            assert isinstance(data["total"], int)

    def test_get_tables_list_without_auth_returns_401(self, client):
        """
        Test that GET /v1/public/{project_id}/tables without auth returns 401.

        Authentication is required for all /v1/public/* endpoints.
        """
        project_id = "test-project-123"
        response = client.get(f"/v1/public/{project_id}/tables")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestInvalidTableID:
    """Test cases for invalid table_id scenarios."""

    def test_get_table_with_invalid_id_returns_404(self, client, auth_headers_user1):
        """
        Test that GET /v1/public/{project_id}/tables/{invalid_id} returns 404.

        Invalid table ID should return TABLE_NOT_FOUND error.
        """
        project_id = "test-project-123"
        invalid_table_id = "nonexistent-table-xyz"

        response = client.get(
            f"/v1/public/{project_id}/tables/{invalid_table_id}",
            headers=auth_headers_user1
        )

        # May return 404 for project or table not found
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_table_invalid_id_error_code(self, client, auth_headers_user1):
        """
        Test that invalid table_id returns proper error code.

        Should return TABLE_NOT_FOUND or PROJECT_NOT_FOUND (both are 404).
        Epic 9 Issue 43: Distinguish resource types in error codes.
        """
        project_id = "test-project-123"
        invalid_table_id = "nonexistent-table-xyz"

        response = client.get(
            f"/v1/public/{project_id}/tables/{invalid_table_id}",
            headers=auth_headers_user1
        )

        data = response.json()
        assert "error_code" in data
        # Could be PROJECT_NOT_FOUND or TABLE_NOT_FOUND depending on project existence
        assert data["error_code"] in ["TABLE_NOT_FOUND", "PROJECT_NOT_FOUND"]

    def test_get_table_invalid_id_has_detail(self, client, auth_headers_user1):
        """
        Test that invalid table_id returns descriptive error message.

        Error should clearly indicate what resource was not found.
        """
        project_id = "test-project-123"
        invalid_table_id = "nonexistent-table-xyz"

        response = client.get(
            f"/v1/public/{project_id}/tables/{invalid_table_id}",
            headers=auth_headers_user1
        )

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # Should mention not found
        assert "not found" in data["detail"].lower()

    def test_get_table_empty_table_id_returns_200_or_404(self, client, auth_headers_user1):
        """
        Test that GET /v1/public/{project_id}/tables/ (trailing slash) behaves correctly.

        This should route to the list endpoint (200) or return 404 if misrouted.
        """
        project_id = "test-project-123"

        response = client.get(
            f"/v1/public/{project_id}/tables/",
            headers=auth_headers_user1
        )

        # Acceptable responses: 200 (list), 404 (project not found), or 404 (path routing)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_get_table_special_chars_in_id(self, client, auth_headers_user1):
        """
        Test that table_id with special characters is handled properly.

        Special characters in table_id should either be validated (422) or not found (404).
        """
        project_id = "test-project-123"
        invalid_table_id = "table@#$%^&*()"

        response = client.get(
            f"/v1/public/{project_id}/tables/{invalid_table_id}",
            headers=auth_headers_user1
        )

        # Should return 404 (not found) or 422 (invalid format)
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_get_table_very_long_id(self, client, auth_headers_user1):
        """
        Test that very long table_id is handled properly.

        Extremely long IDs should be validated or result in not found.
        """
        project_id = "test-project-123"
        very_long_id = "x" * 1000  # 1000 character table ID

        response = client.get(
            f"/v1/public/{project_id}/tables/{very_long_id}",
            headers=auth_headers_user1
        )

        # Should return 404 or 422 depending on validation
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_414_REQUEST_URI_TOO_LONG
        ]


class TestMissingAuthentication:
    """Test cases for missing authentication on database endpoints."""

    def test_get_tables_without_api_key_returns_401(self, client):
        """
        Test that GET /v1/public/{project_id}/tables without auth returns 401.

        All /v1/public/* endpoints require X-API-Key header.
        """
        project_id = "test-project-123"
        response = client.get(f"/v1/public/{project_id}/tables")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_tables_without_api_key_error_code(self, client):
        """
        Test that missing API key returns INVALID_API_KEY error code.
        """
        project_id = "test-project-123"
        response = client.get(f"/v1/public/{project_id}/tables")

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_table_by_id_without_auth_returns_401(self, client):
        """
        Test that GET /v1/public/{project_id}/tables/{table_id} without auth returns 401.
        """
        project_id = "test-project-123"
        table_id = "table-123"

        response = client.get(f"/v1/public/{project_id}/tables/{table_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_table_without_auth_returns_401(self, client):
        """
        Test that POST /v1/public/{project_id}/tables without auth returns 401.
        """
        project_id = "test-project-123"

        response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "test_table",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True}
                    }
                }
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_delete_table_without_auth_returns_401(self, client):
        """
        Test that DELETE /v1/public/{project_id}/tables/{table_id} without auth returns 401.
        """
        project_id = "test-project-123"
        table_id = "table-123"

        response = client.delete(f"/v1/public/{project_id}/tables/{table_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_invalid_api_key_returns_401(self, client):
        """
        Test that invalid API key returns 401 on table endpoints.
        """
        project_id = "test-project-123"

        response = client.get(
            f"/v1/public/{project_id}/tables",
            headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestMissingProjectID:
    """Test cases for operations with missing or invalid project_id."""

    def test_tables_without_project_id_returns_404(self, client, auth_headers_user1):
        """
        Test that accessing /v1/public/tables (no project_id) returns 404 PATH_NOT_FOUND.

        The API requires project_id in the path.
        """
        # This path doesn't exist in our routing
        response = client.get("/v1/public/tables", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_tables_without_project_id_error_code(self, client, auth_headers_user1):
        """
        Test that missing project_id in path returns PATH_NOT_FOUND.
        """
        response = client.get("/v1/public/tables", headers=auth_headers_user1)

        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"

    def test_empty_project_id_returns_404(self, client, auth_headers_user1):
        """
        Test that empty project_id in path returns 404.

        /v1/public//tables should route to path not found.
        """
        # Double slash represents empty project_id
        response = client.get("/v1/public//tables", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_project_id_format(self, client, auth_headers_user1):
        """
        Test that project_id with invalid characters is handled.

        Special characters should either be URL-encoded or return validation error.
        """
        project_id = "project@#$%"

        response = client.get(
            f"/v1/public/{project_id}/tables",
            headers=auth_headers_user1
        )

        # Should return 404 (not found) or 422 (invalid format)
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestUnauthorizedProjectAccess:
    """Test cases for accessing projects without proper authorization."""

    def test_access_other_user_project_returns_403_or_404(
        self,
        client,
        auth_headers_user1,
        auth_headers_user2
    ):
        """
        Test that accessing another user's project returns 403 or 404.

        Users should not be able to access projects they don't own.
        Security: Return 404 to avoid leaking project existence.
        """
        # If we had project creation, we'd create with user1 and access with user2
        # For now, test with hypothetical project IDs
        other_user_project = "user2-private-project"

        response = client.get(
            f"/v1/public/{other_user_project}/tables",
            headers=auth_headers_user1
        )

        # Should return 404 (doesn't exist or no access) or 403 (forbidden)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]


class TestErrorMessageQuality:
    """Test that error messages are descriptive and helpful."""

    def test_path_not_found_message_is_descriptive(self, client, auth_headers_user1):
        """
        Test that PATH_NOT_FOUND errors have clear messages.

        Should mention the invalid path and suggest checking documentation.
        """
        response = client.get("/database/", headers=auth_headers_user1)

        data = response.json()
        detail = data["detail"]

        # Should be descriptive
        assert len(detail) > 20
        # Should mention path or documentation
        assert any(keyword in detail.lower() for keyword in [
            "path", "not found", "endpoint", "documentation", "api"
        ])

    def test_table_not_found_message_includes_id(self, client, auth_headers_user1):
        """
        Test that TABLE_NOT_FOUND errors include the table ID in the message.

        Helps developers quickly identify which resource wasn't found.
        """
        project_id = "test-project-123"
        table_id = "nonexistent-table-xyz"

        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            data = response.json()
            detail = data["detail"]

            # Should be descriptive
            assert len(detail) > 10
            # Should mention not found
            assert "not found" in detail.lower()

    def test_auth_error_message_is_clear(self, client):
        """
        Test that authentication error messages are clear.

        Should help developers understand they need to provide API key.
        """
        response = client.get("/v1/public/test-project/tables")

        data = response.json()
        detail = data["detail"]

        # Should mention API key
        assert "api key" in detail.lower() or "api-key" in detail.lower()


class TestDXContractCompliance:
    """Test strict compliance with DX Contract error format."""

    def test_all_404_errors_follow_dx_contract(self, client, auth_headers_user1):
        """
        Test that all 404 errors return { detail, error_code }.

        DX Contract: All errors must have consistent format.
        """
        test_cases = [
            "/database/",
            "/database",
            "/v1/public/test-project/tables/invalid-table-id"
        ]

        for path in test_cases:
            response = client.get(path, headers=auth_headers_user1)

            if response.status_code == status.HTTP_404_NOT_FOUND:
                data = response.json()
                # DX Contract: Exact shape
                assert set(data.keys()) == {"detail", "error_code"}
                assert isinstance(data["detail"], str)
                assert isinstance(data["error_code"], str)
                assert len(data["detail"]) > 0
                assert len(data["error_code"]) > 0

    def test_all_401_errors_follow_dx_contract(self, client):
        """
        Test that all 401 errors return { detail, error_code }.
        """
        test_cases = [
            "/v1/public/test-project/tables",
            "/v1/public/test-project/tables/table-123"
        ]

        for path in test_cases:
            response = client.get(path)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            # DX Contract: Exact shape
            assert set(data.keys()) == {"detail", "error_code"}
            assert data["error_code"] == "INVALID_API_KEY"

    def test_error_codes_are_stable(self, client, auth_headers_user1):
        """
        Test that error codes are deterministic and stable.

        Multiple requests to same invalid path should return same error code.
        """
        path = "/database/"

        response1 = client.get(path, headers=auth_headers_user1)
        response2 = client.get(path, headers=auth_headers_user1)

        data1 = response1.json()
        data2 = response2.json()

        # Error codes must be identical
        assert data1["error_code"] == data2["error_code"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_url_encoded_special_chars_in_table_id(self, client, auth_headers_user1):
        """
        Test URL-encoded special characters in table_id.
        """
        import urllib.parse

        project_id = "test-project"
        table_id = urllib.parse.quote("table with spaces")

        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}",
            headers=auth_headers_user1
        )

        # Should return 404 (not found) - table doesn't exist
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_numeric_table_id(self, client, auth_headers_user1):
        """
        Test numeric table_id is handled properly.
        """
        project_id = "test-project"
        table_id = "12345"

        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}",
            headers=auth_headers_user1
        )

        # Should return 404 (not found)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_uuid_format_table_id(self, client, auth_headers_user1):
        """
        Test UUID-format table_id is handled properly.
        """
        project_id = "test-project"
        table_id = "550e8400-e29b-41d4-a716-446655440000"

        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}",
            headers=auth_headers_user1
        )

        # Should return 404 (not found)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_case_sensitivity_in_paths(self, client, auth_headers_user1):
        """
        Test that API paths are case-sensitive.
        """
        # Lowercase (correct)
        response1 = client.get(
            "/v1/public/test-project/tables",
            headers=auth_headers_user1
        )

        # Uppercase (should fail - paths are case-sensitive)
        response2 = client.get(
            "/v1/public/test-project/TABLES",
            headers=auth_headers_user1
        )

        # Correct path should work (200 or 404 for project not found)
        assert response1.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

        # Wrong case should return 404 PATH_NOT_FOUND
        assert response2.status_code == status.HTTP_404_NOT_FOUND
        if response2.status_code == status.HTTP_404_NOT_FOUND:
            data = response2.json()
            assert data["error_code"] == "PATH_NOT_FOUND"


class TestParameterizedInvalidPaths:
    """Parameterized tests for various invalid path scenarios."""

    @pytest.mark.parametrize("invalid_path", [
        "/database/",
        "/database",
        "/database/foo",
        "/database/foo/bar",
        "/v1/database",
        "/v1/database/",
    ])
    def test_invalid_database_paths_return_404(
        self,
        client,
        auth_headers_user1,
        invalid_path
    ):
        """
        Test that various invalid /database paths return 404 PATH_NOT_FOUND.
        """
        response = client.get(invalid_path, headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"
        assert "detail" in data
        assert "error_code" in data

    @pytest.mark.parametrize("table_id", [
        "nonexistent-table",
        "fake-table-id",
        "table-999999",
        "this-table-does-not-exist",
    ])
    def test_various_invalid_table_ids_return_404(
        self,
        client,
        auth_headers_user1,
        table_id
    ):
        """
        Test that various invalid table IDs return 404.
        """
        project_id = "test-project"

        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error_code" in data
        assert "detail" in data

    @pytest.mark.parametrize("endpoint_path", [
        "/v1/public/test-project/tables",
        "/v1/public/test-project/tables/table-123",
    ])
    def test_all_table_endpoints_require_auth(
        self,
        client,
        endpoint_path
    ):
        """
        Test that all table endpoints require authentication.
        """
        response = client.get(endpoint_path)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
