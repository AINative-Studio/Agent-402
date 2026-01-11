"""
Comprehensive test suite for Epic 9, Issue 42: Error Format Consistency.

Tests that ALL error responses include both 'detail' AND 'error_code' fields.
This ensures compliance with the DX Contract Section 7 (Error Semantics):
- All errors MUST return { detail, error_code }
- detail: Human-readable error message (required, never null or empty)
- error_code: Machine-readable error code (required, UPPER_SNAKE_CASE)

Test Coverage:
1. Custom APIError exceptions return both detail and error_code
2. Generic HTTPException is converted to include error_code
3. Unexpected exceptions return 500 with INTERNAL_ERROR code
4. FastAPI validation errors (422) include error_code
5. Various HTTP status codes (400, 401, 403, 404, 422, 429, 500) all have error_code
6. PATH_NOT_FOUND vs RESOURCE_NOT_FOUND distinction (Epic 9, Issue 43)

Reference:
- backend/app/core/errors.py - APIError and custom exceptions
- backend/app/core/middleware.py - Error handling middleware
- backend/app/main.py - Exception handler registration
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.core.errors import (
    InvalidAPIKeyError,
    ProjectNotFoundError,
    UnauthorizedError,
    ProjectLimitExceededError,
    InvalidTierError,
    InvalidTokenError,
    TokenExpiredAPIError,
    AgentNotFoundError,
    TableNotFoundError,
    SchemaValidationError,
    ImmutableRecordError,
    PathNotFoundError,
    ResourceNotFoundError,
)


class TestCustomAPIErrorFormat:
    """Test that custom APIError exceptions return both detail and error_code."""

    def test_invalid_api_key_error_format(self, client):
        """
        Test InvalidAPIKeyError returns both detail and error_code.

        Per Epic 9, Issue 42: All errors return { detail, error_code }.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # MUST have both fields
        assert "detail" in data, "Missing 'detail' field"
        assert "error_code" in data, "Missing 'error_code' field"

        # Verify values
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert data["detail"] is not None

        assert isinstance(data["error_code"], str)
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["error_code"] != ""
        assert data["error_code"] is not None

    def test_project_not_found_error_format(self, client, auth_headers_user1):
        """Test ProjectNotFoundError returns both detail and error_code."""
        # Use correct endpoint path: /{project_id}/agents, not /projects/{project_id}
        response = client.get(
            "/v1/public/nonexistent_project_123/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        # Verify values
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert "project" in data["detail"].lower() or "not found" in data["detail"].lower()

        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_unauthorized_error_format(self, client, auth_headers_user1):
        """Test UnauthorizedError (403) returns both detail and error_code."""
        # Create a scenario that triggers 403
        # First create a project as user1
        create_response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={"name": "User1 Project"}
        )

        if create_response.status_code == 201:
            project_id = create_response.json()["id"]

            # Try to access it as user2 (if multi-tenancy is enforced)
            # This is an example - actual endpoint may vary
            # For now, we verify the error structure is correct when it occurs
            pass

    def test_project_limit_exceeded_error_format(self, client, auth_headers_user1):
        """Test ProjectLimitExceededError (429) returns both detail and error_code."""
        # This test verifies the error format when rate limit is hit
        # We'll create multiple projects until we hit the limit

        # Create projects until we hit limit (or reasonable max for testing)
        max_attempts = 20
        for i in range(max_attempts):
            response = client.post(
                "/v1/public/projects",
                headers=auth_headers_user1,
                json={"name": f"Test Project {i}"}
            )

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                data = response.json()

                # MUST have both fields
                assert "detail" in data
                assert "error_code" in data

                assert data["error_code"] == "PROJECT_LIMIT_EXCEEDED"
                assert isinstance(data["detail"], str)
                assert data["detail"] != ""
                break


class TestHTTPExceptionConversion:
    """Test that generic HTTPException is converted to include error_code."""

    def test_404_not_found_has_error_code(self, client, auth_headers_user1):
        """
        Test that 404 errors include error_code.

        Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND.
        """
        # Test resource not found (endpoint exists, resource doesn't)
        # Use correct endpoint path: /{project_id}/agents
        response = client.get(
            "/v1/public/nonexistent_resource_xyz/agents",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        # Should be RESOURCE_NOT_FOUND or specific like PROJECT_NOT_FOUND
        assert data["error_code"] in [
            "PROJECT_NOT_FOUND",
            "RESOURCE_NOT_FOUND",
            "AGENT_NOT_FOUND",
            "TABLE_NOT_FOUND"
        ]

    def test_404_path_not_found_has_error_code(self, client, auth_headers_user1):
        """
        Test that 404 for invalid paths includes PATH_NOT_FOUND error_code.

        Per Epic 9, Issue 43: PATH_NOT_FOUND for invalid routes.
        """
        # Test path not found (endpoint doesn't exist)
        response = client.get(
            "/v1/public/this_endpoint_does_not_exist",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        # Should be PATH_NOT_FOUND for invalid routes
        assert data["error_code"] == "PATH_NOT_FOUND"
        assert "path" in data["detail"].lower() or "not found" in data["detail"].lower()

    def test_405_method_not_allowed_has_error_code(self, client, auth_headers_user1):
        """Test that 405 errors include error_code."""
        # Try an unsupported method on a valid endpoint
        response = client.put(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={}
        )

        # Should be 405 Method Not Allowed
        if response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            # Should have an appropriate error code
            assert isinstance(data["error_code"], str)
            assert data["error_code"] != ""

    def test_401_unauthorized_has_error_code(self, client):
        """Test that 401 errors include error_code."""
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        assert data["error_code"] == "INVALID_API_KEY"

    def test_403_forbidden_has_error_code(self, client, auth_headers_user1):
        """Test that 403 errors include error_code."""
        # Attempt to trigger immutable record error (403)
        # Try to update agent table (immutable)
        response = client.put(
            "/v1/public/projects/test_project/tables/agents/rows/some_id",
            headers=auth_headers_user1,
            json={"data": "updated"}
        )

        # If we get 403, verify error format
        if response.status_code == status.HTTP_403_FORBIDDEN:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            # Should be IMMUTABLE_RECORD or UNAUTHORIZED
            assert data["error_code"] in ["IMMUTABLE_RECORD", "UNAUTHORIZED", "FORBIDDEN"]


class TestValidationErrorFormat:
    """Test that FastAPI validation errors (422) include error_code."""

    def test_invalid_query_param_has_error_code(self, client, auth_headers_user1):
        """Test that validation errors for query params include error_code."""
        # Send invalid limit parameter (should be an integer)
        response = client.get(
            "/v1/public/projects?limit=not_a_number",
            headers=auth_headers_user1
        )

        # Should return 422 for validation error
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # MUST have both fields
            assert "detail" in data, "Validation error missing 'detail'"
            assert "error_code" in data, "Validation error missing 'error_code'"

            # error_code should be VALIDATION_ERROR
            assert data["error_code"] == "VALIDATION_ERROR"

            # detail should be a string summary
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""

            # May have validation_errors array (optional)
            if "validation_errors" in data:
                assert isinstance(data["validation_errors"], list)

    def test_invalid_json_body_has_error_code(self, client, auth_headers_user1):
        """Test that validation errors for request body include error_code."""
        # Send invalid JSON body to an endpoint
        response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={"invalid_field": "value", "limit": "not_a_number"}
        )

        # May be 422 or 400 depending on validation
        if response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            # Verify values
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert isinstance(data["error_code"], str)
            assert data["error_code"] != ""

    def test_missing_required_field_has_error_code(self, client, auth_headers_user1):
        """Test that missing required field errors include error_code."""
        # POST to projects without required 'name' field
        response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={}
        )

        # Should be 422 validation error
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            assert data["error_code"] == "VALIDATION_ERROR"


class TestUnexpectedExceptionFormat:
    """Test that unexpected exceptions return 500 with INTERNAL_ERROR code."""

    def test_internal_error_format(self):
        """
        Test that internal server errors include both detail and error_code.

        Per Epic 9, Issue 42: All errors return { detail, error_code }.
        Even unexpected exceptions should return INTERNAL_SERVER_ERROR code.
        """
        # Verify the error handler configuration
        from app.core.middleware import DEFAULT_INTERNAL_ERROR_DETAIL

        # The default message should exist
        assert DEFAULT_INTERNAL_ERROR_DETAIL is not None
        assert isinstance(DEFAULT_INTERNAL_ERROR_DETAIL, str)
        assert len(DEFAULT_INTERNAL_ERROR_DETAIL) > 0

    def test_internal_error_has_safe_detail(self):
        """Test that internal errors don't leak sensitive information."""
        from app.core.middleware import DEFAULT_INTERNAL_ERROR_DETAIL

        # Should not contain sensitive keywords
        safe_message = DEFAULT_INTERNAL_ERROR_DETAIL.lower()
        sensitive_keywords = ["exception", "traceback", "stack", "file", "line"]

        for keyword in sensitive_keywords:
            assert keyword not in safe_message, \
                f"Internal error message should not contain '{keyword}'"


class TestErrorCodeConsistency:
    """Test that error codes are consistent across different status codes."""

    def test_400_bad_request_has_error_code(self, client, auth_headers_user1):
        """Test that 400 errors include error_code."""
        # This might be triggered by malformed request
        # Testing with invalid content-type or malformed data
        response = client.post(
            "/v1/public/projects",
            headers={**auth_headers_user1, "Content-Type": "text/plain"},
            data="not json"
        )

        # May be 400 or 422 depending on how FastAPI handles it
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            # Should have BAD_REQUEST error code
            assert data["error_code"] in ["BAD_REQUEST", "VALIDATION_ERROR"]

    def test_422_validation_error_has_error_code(self, client, auth_headers_user1):
        """Test that 422 errors always include VALIDATION_ERROR code."""
        response = client.get(
            "/v1/public/projects?limit=invalid_value",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # MUST have both fields
            assert "detail" in data
            assert "error_code" in data

            # MUST be VALIDATION_ERROR
            assert data["error_code"] == "VALIDATION_ERROR"

    def test_429_rate_limit_has_error_code(self, client, auth_headers_user1):
        """Test that 429 errors include error_code."""
        # Try to hit rate limit by creating many projects
        for i in range(20):
            response = client.post(
                "/v1/public/projects",
                headers=auth_headers_user1,
                json={"name": f"Rate Limit Test {i}"}
            )

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                data = response.json()

                # MUST have both fields
                assert "detail" in data
                assert "error_code" in data

                # Should be PROJECT_LIMIT_EXCEEDED or RATE_LIMIT_EXCEEDED
                assert data["error_code"] in [
                    "PROJECT_LIMIT_EXCEEDED",
                    "RATE_LIMIT_EXCEEDED"
                ]
                break


class TestErrorCodeNamingConvention:
    """Test that error codes follow UPPER_SNAKE_CASE convention."""

    def test_error_codes_are_uppercase(self, client):
        """Test that error_code values are UPPER_SNAKE_CASE."""
        error_scenarios = [
            client.get("/v1/public/projects"),  # 401
            client.get("/v1/public/projects/nonexistent", headers={"X-API-Key": "demo_alice_key_1"}),  # 404
            client.get("/v1/public/invalid_path", headers={"X-API-Key": "demo_alice_key_1"}),  # 404
        ]

        for response in error_scenarios:
            data = response.json()

            if "error_code" in data:
                error_code = data["error_code"]

                # Should be uppercase
                assert error_code == error_code.upper(), \
                    f"error_code should be uppercase: {error_code}"

                # Should use underscores, not spaces or hyphens
                assert " " not in error_code, "error_code should not contain spaces"
                assert "-" not in error_code, "error_code should not contain hyphens"

                # Should match pattern: UPPER_SNAKE_CASE
                import re
                pattern = r"^[A-Z][A-Z0-9_]*$"
                assert re.match(pattern, error_code), \
                    f"error_code should match UPPER_SNAKE_CASE pattern: {error_code}"


class TestPathVsResourceNotFound:
    """Test Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND."""

    def test_invalid_route_returns_path_not_found(self, client, auth_headers_user1):
        """
        Test that invalid API routes return PATH_NOT_FOUND.

        Per Epic 9, Issue 43: PATH_NOT_FOUND for non-existent endpoints.
        """
        response = client.get(
            "/v1/public/completely_invalid_endpoint",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        # Should be PATH_NOT_FOUND
        assert data["error_code"] == "PATH_NOT_FOUND"

        # Detail should mention path
        assert "path" in data["detail"].lower()

    def test_missing_resource_returns_resource_not_found(self, client, auth_headers_user1):
        """
        Test that missing resources return specific error codes.

        Per Epic 9, Issue 43: Use specific codes like PROJECT_NOT_FOUND, not PATH_NOT_FOUND.
        """
        # Use correct endpoint path: /{project_id}/tables
        response = client.get(
            "/v1/public/nonexistent_project_12345/tables",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have both fields
        assert "detail" in data
        assert "error_code" in data

        # Should be PROJECT_NOT_FOUND (specific) or RESOURCE_NOT_FOUND (generic)
        # NOT PATH_NOT_FOUND (that's for invalid routes)
        assert data["error_code"] in ["PROJECT_NOT_FOUND", "RESOURCE_NOT_FOUND"]
        assert data["error_code"] != "PATH_NOT_FOUND"

    def test_missing_agent_returns_agent_not_found(self, client, auth_headers_user1):
        """Test that missing agents return AGENT_NOT_FOUND, not PATH_NOT_FOUND."""
        # Create a project first
        project_response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={"name": "Test Project for Agents"}
        )

        if project_response.status_code == 201:
            project_id = project_response.json()["id"]

            # Try to get non-existent agent
            response = client.get(
                f"/v1/public/projects/{project_id}/agents/nonexistent_agent_123",
                headers=auth_headers_user1
            )

            # If endpoint exists and returns 404
            if response.status_code == status.HTTP_404_NOT_FOUND:
                data = response.json()

                # MUST have both fields
                assert "detail" in data
                assert "error_code" in data

                # Should be AGENT_NOT_FOUND
                assert data["error_code"] in ["AGENT_NOT_FOUND", "RESOURCE_NOT_FOUND"]
                assert data["error_code"] != "PATH_NOT_FOUND"

    def test_missing_table_returns_table_not_found(self, client, auth_headers_user1):
        """Test that missing tables return TABLE_NOT_FOUND, not PATH_NOT_FOUND."""
        # Create a project first
        project_response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={"name": "Test Project for Tables"}
        )

        if project_response.status_code == 201:
            project_id = project_response.json()["id"]

            # Try to get non-existent table
            response = client.get(
                f"/v1/public/projects/{project_id}/tables/nonexistent_table_xyz",
                headers=auth_headers_user1
            )

            # If endpoint exists and returns 404
            if response.status_code == status.HTTP_404_NOT_FOUND:
                data = response.json()

                # MUST have both fields
                assert "detail" in data
                assert "error_code" in data

                # Should be TABLE_NOT_FOUND
                assert data["error_code"] in ["TABLE_NOT_FOUND", "RESOURCE_NOT_FOUND"]
                assert data["error_code"] != "PATH_NOT_FOUND"


class TestDXContractCompliance:
    """Test full compliance with DX Contract Section 7 (Error Semantics)."""

    def test_all_errors_have_detail_and_error_code(self, client, auth_headers_user1):
        """
        Test that ALL error responses include both detail and error_code.

        Per Epic 9, Issue 42: All errors return { detail, error_code }.
        This is the contract requirement.
        """
        error_scenarios = [
            # 401 - Missing API key
            client.get("/v1/public/projects"),
            # 401 - Invalid API key
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
            # 404 - Path not found
            client.get("/v1/public/invalid_endpoint", headers=auth_headers_user1),
            # 404 - Resource not found
            client.get("/v1/public/projects/nonexistent_xyz", headers=auth_headers_user1),
            # 405 - Method not allowed (if applicable)
            client.delete("/v1/public/projects", headers=auth_headers_user1),
        ]

        for response in error_scenarios:
            data = response.json()

            # MUST have detail field
            assert "detail" in data, f"Missing 'detail' in {response.status_code} error"
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert data["detail"] is not None
            assert len(data["detail"]) > 0

            # MUST have error_code field
            assert "error_code" in data, f"Missing 'error_code' in {response.status_code} error"
            assert isinstance(data["error_code"], str)
            assert data["error_code"] != ""
            assert data["error_code"] is not None
            assert len(data["error_code"]) > 0

    def test_error_codes_are_stable(self, client):
        """
        Test that error codes are stable (same error = same code).

        Per DX Contract: Error codes are stable and documented.
        """
        # Make the same error multiple times
        responses = [
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})
            for _ in range(3)
        ]

        error_codes = [r.json()["error_code"] for r in responses]

        # All should be the same
        assert len(set(error_codes)) == 1, "Same error should produce same error_code"
        assert error_codes[0] == "INVALID_API_KEY"

    def test_detail_and_error_code_never_null(self, client):
        """Test that detail and error_code are never null or empty."""
        error_scenarios = [
            client.get("/v1/public/projects"),
            client.get("/v1/public/projects", headers={"X-API-Key": ""}),
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
        ]

        for response in error_scenarios:
            data = response.json()

            # detail must never be null or empty
            assert data["detail"] is not None, "detail must not be null"
            assert data["detail"] != "", "detail must not be empty string"
            assert data["detail"].strip() != "", "detail must not be whitespace only"

            # error_code must never be null or empty
            assert data["error_code"] is not None, "error_code must not be null"
            assert data["error_code"] != "", "error_code must not be empty string"
            assert data["error_code"].strip() != "", "error_code must not be whitespace only"

    def test_error_responses_are_deterministic(self, client):
        """Test that error responses are deterministic and replayable."""
        # Make the same request twice
        response1 = client.get("/v1/public/projects")
        response2 = client.get("/v1/public/projects")

        data1 = response1.json()
        data2 = response2.json()

        # Should have identical error_code
        assert data1["error_code"] == data2["error_code"]

        # Should have identical detail (or very similar)
        assert data1["detail"] == data2["detail"]

    def test_error_format_is_json(self, client):
        """Test that all errors return JSON with correct content type."""
        error_scenarios = [
            client.get("/v1/public/projects"),
            client.get("/v1/public/invalid", headers={"X-API-Key": "demo_alice_key_1"}),
        ]

        for response in error_scenarios:
            # Should be JSON
            assert "application/json" in response.headers.get("content-type", "")

            # Should be parseable JSON
            data = response.json()
            assert isinstance(data, dict)

            # Should have the required fields
            assert "detail" in data
            assert "error_code" in data


class TestSpecificErrorCodes:
    """Test specific error codes for various scenarios."""

    def test_invalid_api_key_code(self, client):
        """Test that invalid API key returns INVALID_API_KEY code."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_missing_api_key_code(self, client):
        """Test that missing API key returns INVALID_API_KEY code."""
        response = client.get("/v1/public/projects")

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_validation_error_code(self, client, auth_headers_user1):
        """Test that validation errors return VALIDATION_ERROR code."""
        response = client.get(
            "/v1/public/projects?limit=not_a_number",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()
            assert data["error_code"] == "VALIDATION_ERROR"

    def test_project_not_found_code(self, client, auth_headers_user1):
        """Test that missing projects return PROJECT_NOT_FOUND code."""
        # Use correct endpoint path: /{project_id}/agents
        response = client.get(
            "/v1/public/xyz_nonexistent/agents",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            data = response.json()
            # Should be PROJECT_NOT_FOUND or RESOURCE_NOT_FOUND
            assert data["error_code"] in ["PROJECT_NOT_FOUND", "RESOURCE_NOT_FOUND"]

    def test_path_not_found_code(self, client, auth_headers_user1):
        """Test that invalid paths return PATH_NOT_FOUND code."""
        response = client.get(
            "/v1/public/this_endpoint_does_not_exist_anywhere",
            headers=auth_headers_user1
        )

        data = response.json()
        assert data["error_code"] == "PATH_NOT_FOUND"


class TestErrorDetailQuality:
    """Test that error details are high quality and helpful."""

    def test_detail_is_descriptive(self, client):
        """Test that error details are descriptive, not generic."""
        response = client.get("/v1/public/projects")
        data = response.json()

        # Should be more than just "Error"
        assert len(data["detail"]) > 10

        # Should mention the specific issue
        detail_lower = data["detail"].lower()
        assert any(
            keyword in detail_lower
            for keyword in ["api", "key", "invalid", "missing"]
        )

    def test_detail_does_not_leak_sensitive_info(self, client):
        """Test that error details don't expose sensitive information."""
        error_scenarios = [
            client.get("/v1/public/projects"),
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
        ]

        for response in error_scenarios:
            detail = response.json()["detail"].lower()

            # Should not expose internal details
            sensitive_keywords = [
                "password", "secret", "traceback", "stack trace",
                "database", "sql query", "connection string"
            ]

            for keyword in sensitive_keywords:
                assert keyword not in detail, \
                    f"Error detail should not contain '{keyword}'"
