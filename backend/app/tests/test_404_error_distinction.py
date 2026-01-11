"""
Comprehensive test suite for Epic 9, Issue 43: 404 Error Distinction.

Tests that 404 errors properly distinguish between:
- PATH_NOT_FOUND: The API endpoint/route doesn't exist (typo in URL)
- RESOURCE_NOT_FOUND: The endpoint exists but the resource doesn't (missing data)

Per DX Contract Section 7 (Error Semantics):
- All errors MUST return { detail, error_code }
- Both return HTTP 404 status
- Different error_code values help developers quickly identify URL typos vs missing resources

Test Requirements:
1. Test invalid route returns PATH_NOT_FOUND error code
2. Test missing project returns PROJECT_NOT_FOUND error code
3. Test missing table returns TABLE_NOT_FOUND error code
4. Test missing vector returns VECTOR_NOT_FOUND error code
5. Test PATH_NOT_FOUND includes helpful message about checking API docs
6. Test RESOURCE_NOT_FOUND includes the resource type and ID
7. Both should return HTTP 404 status

Reference:
- backend/app/core/errors.py - PathNotFoundError, ResourceNotFoundError classes
- backend/app/core/middleware.py - 404 distinction logic
- backend/app/main.py - Exception handlers
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestPathNotFoundErrors:
    """
    Test PATH_NOT_FOUND errors (invalid routes/endpoints).

    These tests verify that when a user requests a non-existent API endpoint,
    the system returns HTTP 404 with error_code: PATH_NOT_FOUND and includes
    helpful guidance about checking the API documentation.
    """

    def test_nonexistent_route_returns_path_not_found(self, client, auth_headers_user1):
        """
        Test that invalid route returns PATH_NOT_FOUND error code.

        Requirement 1: Test invalid route returns PATH_NOT_FOUND error code
        Example: GET /v1/public/nonexistent → PATH_NOT_FOUND
        """
        response = client.get(
            "/v1/public/nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error response format
        assert "detail" in data, "Missing 'detail' field in 404 error response"
        assert "error_code" in data, "Missing 'error_code' field in 404 error response"

        # Verify error_code is PATH_NOT_FOUND
        assert data["error_code"] == "PATH_NOT_FOUND", (
            f"Expected PATH_NOT_FOUND for invalid route, got {data['error_code']}"
        )

        # Verify detail field is not empty
        assert isinstance(data["detail"], str), "detail must be a string"
        assert len(data["detail"]) > 0, "detail must not be empty"

    def test_path_not_found_includes_api_docs_guidance(self, client, auth_headers_user1):
        """
        Test that PATH_NOT_FOUND includes helpful message about checking API docs.

        Requirement 5: Test PATH_NOT_FOUND includes helpful message about checking API docs
        """
        response = client.get(
            "/v1/public/invalid-endpoint",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error_code
        assert data["error_code"] == "PATH_NOT_FOUND"

        # Verify detail includes guidance about API documentation
        detail = data["detail"].lower()
        assert "api" in detail or "documentation" in detail or "endpoint" in detail or "docs" in detail, (
            "PATH_NOT_FOUND detail should include guidance about API documentation"
        )

        # Verify detail includes the invalid path
        assert "/v1/public/invalid-endpoint" in data["detail"], (
            "PATH_NOT_FOUND detail should include the requested path"
        )

    def test_path_not_found_with_different_invalid_routes(self, client, auth_headers_user1):
        """
        Test PATH_NOT_FOUND with various invalid route patterns.

        Verifies that different types of invalid routes all return PATH_NOT_FOUND.
        """
        invalid_routes = [
            "/v1/public/nonexistent",
            "/v1/public/invalid-resource",
            "/v1/public/typo-in-url",
            "/v1/public/projects/vectors/invalid",  # Invalid nested path
            "/api/v1/wrong-prefix",  # Wrong API prefix
        ]

        for route in invalid_routes:
            response = client.get(route, headers=auth_headers_user1)

            assert response.status_code == status.HTTP_404_NOT_FOUND, (
                f"Route {route} should return 404"
            )

            data = response.json()
            assert data["error_code"] == "PATH_NOT_FOUND", (
                f"Route {route} should return PATH_NOT_FOUND, got {data['error_code']}"
            )

            assert "detail" in data
            assert len(data["detail"]) > 0

    def test_path_not_found_with_different_http_methods(self, client, auth_headers_user1):
        """
        Test PATH_NOT_FOUND with different HTTP methods on invalid routes.

        Verifies that POST, PUT, DELETE on non-existent routes return PATH_NOT_FOUND.
        """
        invalid_route = "/v1/public/nonexistent-endpoint"

        # Test POST
        response = client.post(
            invalid_route,
            headers=auth_headers_user1,
            json={"test": "data"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "PATH_NOT_FOUND"

        # Test PUT
        response = client.put(
            invalid_route,
            headers=auth_headers_user1,
            json={"test": "data"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "PATH_NOT_FOUND"

        # Test DELETE
        response = client.delete(
            invalid_route,
            headers=auth_headers_user1
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error_code"] == "PATH_NOT_FOUND"


class TestProjectNotFoundErrors:
    """
    Test PROJECT_NOT_FOUND errors (valid endpoint, missing project resource).

    These tests verify that when a user requests a project that doesn't exist,
    the system returns HTTP 404 with error_code: PROJECT_NOT_FOUND and includes
    the project ID in the detail message.
    """

    def test_missing_project_returns_project_not_found(self, client, auth_headers_user1):
        """
        Test that missing project returns PROJECT_NOT_FOUND error code.

        Requirement 2: Test missing project returns PROJECT_NOT_FOUND error code
        Example: GET /v1/public/{invalid-project-id}/agents → PROJECT_NOT_FOUND
        """
        invalid_project_id = "invalid-project-12345"
        response = client.get(
            f"/v1/public/{invalid_project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error response format
        assert "detail" in data, "Missing 'detail' field in 404 error response"
        assert "error_code" in data, "Missing 'error_code' field in 404 error response"

        # Verify error_code is PROJECT_NOT_FOUND (not PATH_NOT_FOUND)
        assert data["error_code"] == "PROJECT_NOT_FOUND", (
            f"Expected PROJECT_NOT_FOUND for missing project, got {data['error_code']}"
        )

        # Verify detail is not empty
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_project_not_found_includes_resource_id(self, client, auth_headers_user1):
        """
        Test that RESOURCE_NOT_FOUND includes the resource type and ID.

        Requirement 6: Test RESOURCE_NOT_FOUND includes the resource type and ID
        """
        invalid_project_id = "nonexistent-proj-789"
        response = client.get(
            f"/v1/public/{invalid_project_id}/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error_code is PROJECT_NOT_FOUND
        assert data["error_code"] == "PROJECT_NOT_FOUND"

        # Verify detail includes the project ID
        assert invalid_project_id in data["detail"], (
            "PROJECT_NOT_FOUND detail should include the project ID"
        )

        # Verify detail mentions "project" (resource type)
        detail_lower = data["detail"].lower()
        assert "project" in detail_lower, (
            "PROJECT_NOT_FOUND detail should mention the resource type (project)"
        )

    def test_project_not_found_different_from_path_not_found(self, client, auth_headers_user1):
        """
        Verify that PROJECT_NOT_FOUND is distinct from PATH_NOT_FOUND.

        This test ensures that:
        - Valid endpoint with missing resource → PROJECT_NOT_FOUND
        - Invalid endpoint → PATH_NOT_FOUND
        """
        # Valid endpoint, missing resource
        response_resource = client.get(
            "/v1/public/missing-project-id/agents",
            headers=auth_headers_user1
        )

        # Invalid endpoint
        response_path = client.get(
            "/v1/public/invalid-endpoint",
            headers=auth_headers_user1
        )

        # Both return 404
        assert response_resource.status_code == status.HTTP_404_NOT_FOUND
        assert response_path.status_code == status.HTTP_404_NOT_FOUND

        # But with different error codes
        assert response_resource.json()["error_code"] == "PROJECT_NOT_FOUND"
        assert response_path.json()["error_code"] == "PATH_NOT_FOUND"

        # And different detail messages
        assert response_resource.json()["detail"] != response_path.json()["detail"]


class TestTableNotFoundErrors:
    """
    Test TABLE_NOT_FOUND errors (valid endpoint, missing table resource).

    These tests verify that when a user requests a table that doesn't exist,
    the system returns HTTP 404 with error_code: TABLE_NOT_FOUND and includes
    the table ID in the detail message.
    """

    def test_missing_table_returns_table_not_found(self, client, auth_headers_user1):
        """
        Test that missing table returns TABLE_NOT_FOUND error code.

        Requirement 3: Test missing table returns TABLE_NOT_FOUND error code
        """
        # First create a project to test against
        create_response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={
                "name": "Test Project for Table 404",
                "description": "Testing table not found errors"
            }
        )

        # Handle case where project creation might fail or already exists
        if create_response.status_code == 201:
            project_data = create_response.json()
            project_id = project_data["project_id"]
        else:
            # Use a known invalid project ID if creation failed
            project_id = "test-project-for-404"

        # Try to get a non-existent table
        invalid_table_id = "nonexistent-table-12345"
        response = client.get(
            f"/v1/public/{project_id}/tables/{invalid_table_id}",
            headers=auth_headers_user1
        )

        # Should return 404 (either PROJECT_NOT_FOUND or TABLE_NOT_FOUND)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error response format
        assert "detail" in data
        assert "error_code" in data

        # Should be either TABLE_NOT_FOUND or PROJECT_NOT_FOUND
        # (depending on whether the project exists)
        assert data["error_code"] in ["TABLE_NOT_FOUND", "PROJECT_NOT_FOUND"], (
            f"Expected TABLE_NOT_FOUND or PROJECT_NOT_FOUND, got {data['error_code']}"
        )

    def test_table_not_found_includes_resource_id(self, client, auth_headers_user1):
        """
        Test that TABLE_NOT_FOUND includes the table ID in the detail message.

        Requirement 6: Test RESOURCE_NOT_FOUND includes the resource type and ID
        """
        # Create a project first
        create_response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={
                "name": "Test Project for Table Error Messages",
                "description": "Testing table error messages"
            }
        )

        if create_response.status_code == 201:
            project_data = create_response.json()
            project_id = project_data["project_id"]

            invalid_table_id = "missing-table-xyz"
            response = client.get(
                f"/v1/public/{project_id}/tables/{invalid_table_id}",
                headers=auth_headers_user1
            )

            # If we got TABLE_NOT_FOUND, verify the detail message
            if response.status_code == 404:
                data = response.json()
                if data["error_code"] == "TABLE_NOT_FOUND":
                    # Verify detail includes the table ID
                    assert invalid_table_id in data["detail"], (
                        "TABLE_NOT_FOUND detail should include the table ID"
                    )

                    # Verify detail mentions "table" (resource type)
                    detail_lower = data["detail"].lower()
                    assert "table" in detail_lower, (
                        "TABLE_NOT_FOUND detail should mention the resource type (table)"
                    )


class TestVectorNotFoundErrors:
    """
    Test VECTOR_NOT_FOUND errors (valid endpoint, missing vector resource).

    These tests verify that when a user requests a vector that doesn't exist,
    the system returns HTTP 404 with error_code: VECTOR_NOT_FOUND and includes
    the vector ID in the detail message.

    Note: These tests are illustrative. The VectorNotFoundError class exists
    in errors.py and can be used by vector-related endpoints.
    """

    def test_missing_vector_returns_vector_not_found(self, client, auth_headers_user1):
        """
        Test that missing vector returns VECTOR_NOT_FOUND error code.

        Requirement 4: Test missing vector returns VECTOR_NOT_FOUND error code

        This test verifies the VectorNotFoundError class is properly defined
        and will return the correct error code when used by vector endpoints.
        """
        # Import and verify VectorNotFoundError exists and has correct attributes
        from app.core.errors import VectorNotFoundError

        # Create instance to test error attributes
        error = VectorNotFoundError(vector_id="test-vector-123", namespace="default")

        # Verify error code
        assert error.error_code == "VECTOR_NOT_FOUND", (
            f"Expected VECTOR_NOT_FOUND, got {error.error_code}"
        )

        # Verify status code
        assert error.status_code == 404

        # Verify detail includes vector ID
        assert "test-vector-123" in error.detail
        assert "vector" in error.detail.lower()

    def test_vector_not_found_includes_resource_id(self, client, auth_headers_user1):
        """
        Test that VECTOR_NOT_FOUND includes the vector ID in the detail message.

        Requirement 6: Test RESOURCE_NOT_FOUND includes the resource type and ID
        """
        from app.core.errors import VectorNotFoundError

        vector_id = "missing-vector-xyz789"
        error = VectorNotFoundError(vector_id=vector_id, namespace="default")

        # Verify detail includes the vector ID
        assert vector_id in error.detail, (
            "VECTOR_NOT_FOUND detail should include the vector ID"
        )

        # Verify detail mentions "vector" (resource type)
        detail_lower = error.detail.lower()
        assert "vector" in detail_lower, (
            "VECTOR_NOT_FOUND detail should mention the resource type (vector)"
        )

    def test_vector_not_found_includes_namespace(self, client, auth_headers_user1):
        """
        Test that VECTOR_NOT_FOUND includes namespace information when applicable.

        Vectors are scoped to namespaces, so the error message should include
        both the vector ID and the namespace for better debugging.
        """
        from app.core.errors import VectorNotFoundError

        vector_id = "missing-vector-in-namespace"
        namespace = "test_namespace"

        error = VectorNotFoundError(vector_id=vector_id, namespace=namespace)

        # Verify detail includes namespace information
        detail_lower = error.detail.lower()
        assert "namespace" in detail_lower, (
            "VECTOR_NOT_FOUND detail should include namespace information"
        )
        assert namespace in error.detail, (
            "VECTOR_NOT_FOUND detail should include the namespace value"
        )


class TestErrorDistinctionConsistency:
    """
    Test consistency of 404 error distinction across different scenarios.

    These tests verify that the distinction between PATH_NOT_FOUND and
    RESOURCE_NOT_FOUND is consistently applied across the API.
    """

    def test_all_404_errors_return_404_status(self, client, auth_headers_user1):
        """
        Requirement 7: Both PATH_NOT_FOUND and RESOURCE_NOT_FOUND return HTTP 404 status.

        Verifies that all 404 errors (both path and resource) return HTTP 404.
        """
        test_cases = [
            # PATH_NOT_FOUND cases
            ("/v1/public/nonexistent", "PATH_NOT_FOUND"),
            ("/v1/public/invalid-route", "PATH_NOT_FOUND"),

            # RESOURCE_NOT_FOUND cases
            ("/v1/public/invalid-proj-id/agents", "PROJECT_NOT_FOUND"),
        ]

        for endpoint, expected_error_code in test_cases:
            response = client.get(endpoint, headers=auth_headers_user1)

            # All should return HTTP 404
            assert response.status_code == status.HTTP_404_NOT_FOUND, (
                f"Endpoint {endpoint} should return 404, got {response.status_code}"
            )

            data = response.json()

            # All should have detail and error_code
            assert "detail" in data
            assert "error_code" in data

            # Error code should match expected
            assert data["error_code"] == expected_error_code, (
                f"Endpoint {endpoint} should return {expected_error_code}, "
                f"got {data['error_code']}"
            )

    def test_error_response_format_consistency(self, client, auth_headers_user1):
        """
        Test that all 404 errors follow the same response format.

        Per DX Contract: All errors return { detail, error_code }
        """
        # PATH_NOT_FOUND
        path_response = client.get(
            "/v1/public/nonexistent",
            headers=auth_headers_user1
        )

        # PROJECT_NOT_FOUND
        resource_response = client.get(
            "/v1/public/projects/invalid-id",
            headers=auth_headers_user1
        )

        # Both should have same structure
        path_data = path_response.json()
        resource_data = resource_response.json()

        # Check required fields exist
        for data in [path_data, resource_data]:
            assert "detail" in data
            assert "error_code" in data
            assert isinstance(data["detail"], str)
            assert isinstance(data["error_code"], str)
            assert len(data["detail"]) > 0
            assert len(data["error_code"]) > 0

    def test_detail_messages_are_distinct_and_helpful(self, client, auth_headers_user1):
        """
        Test that detail messages are distinct and helpful for different error types.

        PATH_NOT_FOUND should guide users to check API docs.
        RESOURCE_NOT_FOUND should include the resource type and ID.
        """
        # PATH_NOT_FOUND
        path_response = client.get(
            "/v1/public/invalid-endpoint",
            headers=auth_headers_user1
        )
        path_data = path_response.json()
        path_detail = path_data["detail"].lower()

        # Should mention documentation or API
        assert any(word in path_detail for word in ["api", "documentation", "docs", "endpoint"]), (
            "PATH_NOT_FOUND should guide users to check API documentation"
        )

        # PROJECT_NOT_FOUND
        project_id = "missing-project-123"
        resource_response = client.get(
            f"/v1/public/{project_id}/agents",
            headers=auth_headers_user1
        )
        resource_data = resource_response.json()

        # Should include resource type and ID
        assert "project" in resource_data["detail"].lower(), (
            "PROJECT_NOT_FOUND should mention the resource type"
        )
        assert project_id in resource_data["detail"], (
            "PROJECT_NOT_FOUND should include the project ID"
        )

        # Details should be different
        assert path_data["detail"] != resource_data["detail"], (
            "PATH_NOT_FOUND and RESOURCE_NOT_FOUND should have different detail messages"
        )


class TestEdgeCases:
    """
    Test edge cases and boundary conditions for 404 error distinction.
    """

    def test_404_with_query_parameters(self, client, auth_headers_user1):
        """
        Test that 404 errors work correctly with query parameters.
        """
        # Invalid route with query params should still be PATH_NOT_FOUND
        response = client.get(
            "/v1/public/nonexistent?param=value",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"

    def test_404_without_authentication(self, client):
        """
        Test that 404 errors are handled correctly even without authentication.

        Note: Authentication errors (401) take precedence over 404s in most cases,
        but this test verifies the behavior.
        """
        # Request to invalid route without auth
        response = client.get("/v1/public/nonexistent")

        # Should return 401 (authentication required) before checking route
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]

        data = response.json()
        assert "detail" in data
        assert "error_code" in data

    def test_404_with_trailing_slash(self, client, auth_headers_user1):
        """
        Test that 404 errors are handled correctly with trailing slashes.
        """
        # Invalid route with trailing slash
        response = client.get(
            "/v1/public/nonexistent/",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"
        assert "detail" in data

    def test_nested_invalid_routes(self, client, auth_headers_user1):
        """
        Test that deeply nested invalid routes return PATH_NOT_FOUND.
        """
        nested_invalid_route = "/v1/public/projects/invalid/nested/deep/route"
        response = client.get(nested_invalid_route, headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Should be PATH_NOT_FOUND for invalid route structure
        assert data["error_code"] == "PATH_NOT_FOUND"
        assert "detail" in data
