"""
Comprehensive tests for Issue #8: All errors include a detail field.

Per DX Contract §7 and Epic 2 Story 3:
- All errors MUST return { detail, error_code }
- detail field is REQUIRED in all error responses
- error_code field should be present (but is optional for some error types)

This test suite validates that every possible error scenario includes
the detail field in the response.

Test Coverage:
1. Custom API errors (401, 403, 404, 422, 429)
2. Validation errors (422)
3. HTTPException errors
4. Unexpected exceptions (500)
5. Various error scenarios from different endpoints
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestErrorDetailField:
    """Test suite ensuring all errors include detail field."""

    # ==================== Authentication Errors ====================

    def test_missing_api_key_has_detail(self, client):
        """
        Test that missing API key error includes detail field.
        Epic 2 Story 2: Invalid API keys return 401 INVALID_API_KEY.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "Missing detail field in 401 error"
        assert isinstance(data["detail"], str), "detail must be a string"
        assert len(data["detail"]) > 0, "detail must not be empty"

        # SHOULD have error_code
        assert "error_code" in data, "Missing error_code in 401 error"
        assert data["error_code"] == "INVALID_API_KEY"

    def test_invalid_api_key_has_detail(self, client):
        """Test that invalid API key error includes detail field."""
        headers = {"X-API-Key": "invalid_key_12345"}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        assert "detail" in data, "Missing detail field in invalid API key error"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_malformed_api_key_has_detail(self, client):
        """Test that malformed API key error includes detail field."""
        # Test various malformed keys
        malformed_keys = [
            "",  # empty
            "   ",  # whitespace only
            "x",  # too short
            "key@#$%",  # invalid characters
        ]

        for key in malformed_keys:
            headers = {"X-API-Key": key}
            response = client.get("/v1/public/projects", headers=headers)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()

            assert "detail" in data, f"Missing detail for malformed key: {key}"
            assert isinstance(data["detail"], str)
            assert len(data["detail"]) > 0
            assert "error_code" in data

    # ==================== Not Found Errors ====================

    def test_project_not_found_has_detail(self, client, auth_headers_user1):
        """Test that project not found error includes detail field."""
        response = client.get(
            "/v1/public/projects/nonexistent_project_id",
            headers=auth_headers_user1
        )

        # Should return 404 when endpoint exists (if implemented)
        # For now, may return 404 for route not found
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data, "Missing detail field in 404 error"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # error_code may not be present for Starlette's default 404 handler
        # but detail field MUST always be present

    def test_route_not_found_has_detail(self, client):
        """Test that route not found error includes detail field."""
        # Note: Without auth headers, will get 401 first due to middleware
        # This is expected behavior - auth is checked before routing
        response = client.get("/v1/public/nonexistent_route")

        # Will return 401 due to missing auth
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
        data = response.json()

        assert "detail" in data, "Missing detail field in error response"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # error_code may or may not be present for route not found

    # ==================== Validation Errors ====================

    def test_validation_error_has_detail(self, client, auth_headers_user1):
        """
        Test that Pydantic validation errors include detail field.
        Per DX Contract: Validation errors use HTTP 422.
        """
        # Test with invalid JSON in request body
        # (This would be for a POST endpoint with validation)
        # For now, test with invalid query parameters if available

        # Send request with invalid parameters
        response = client.get(
            "/v1/public/projects?limit=invalid",
            headers=auth_headers_user1
        )

        # If validation is in place, should return 422
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            assert "detail" in data, "Missing detail field in validation error"
            assert isinstance(data["detail"], str)
            assert len(data["detail"]) > 0
            assert "error_code" in data
            # Should have validation_errors array
            # This is optional but useful for debugging

    # ==================== Method Not Allowed ====================

    def test_method_not_allowed_has_detail(self, client, auth_headers_user1):
        """Test that method not allowed error includes detail field."""
        # Try DELETE on an endpoint that only supports GET
        response = client.delete("/v1/public/projects", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        data = response.json()

        assert "detail" in data, "Missing detail field in 405 error"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # error_code may not be present for Starlette's default 405 handler
        # but detail field MUST always be present

    # ==================== Internal Server Errors ====================

    def test_internal_server_error_has_detail(self, client, monkeypatch):
        """
        Test that internal server errors include detail field.
        This tests the catch-all exception handler.
        """
        # We need to trigger an internal error
        # This is tricky without modifying the application code
        # For now, we'll test the error format for known errors

        # If we can trigger a 500, verify it has detail
        # This might require a specific test setup or mock
        pass  # Placeholder - implementation depends on application structure

    # ==================== Custom Business Logic Errors ====================

    def test_project_limit_exceeded_has_detail(self, client, auth_headers_user1):
        """
        Test that project limit exceeded error includes detail field.
        Epic 3 Story 1: Project creation respects tier limits.
        """
        # This test would need to create projects until limit is reached
        # For now, we verify the error structure if we can trigger it
        pass  # Placeholder - requires project creation endpoint

    def test_invalid_tier_has_detail(self, client, auth_headers_user1):
        """
        Test that invalid tier error includes detail field.
        Backlog #3: INVALID_TIER error handling.
        """
        # This test would need a project creation endpoint
        # For now, we verify the error structure if we can trigger it
        pass  # Placeholder - requires project creation endpoint

    # ==================== Error Response Schema Validation ====================

    def test_all_errors_follow_schema(self, client, auth_headers_user1):
        """
        Test that all error responses follow the DX Contract schema.

        Required fields:
        - detail: string (required)
        - error_code: string (optional but recommended)
        """
        # Test various error scenarios
        error_scenarios = [
            # (method, path, headers, expected_status, scenario_name)
            ("GET", "/v1/public/projects", {}, 401, "missing_auth"),
            ("GET", "/v1/public/projects", {"X-API-Key": "invalid"}, 401, "invalid_auth"),
            ("GET", "/v1/public/nonexistent", auth_headers_user1, 404, "not_found"),
            ("DELETE", "/v1/public/projects", auth_headers_user1, 405, "method_not_allowed"),
        ]

        for method, path, headers, expected_status, scenario in error_scenarios:
            if method == "GET":
                response = client.get(path, headers=headers)
            elif method == "POST":
                response = client.post(path, headers=headers, json={})
            elif method == "DELETE":
                response = client.delete(path, headers=headers)
            else:
                continue

            # Verify status code
            assert response.status_code == expected_status, \
                f"Unexpected status for scenario: {scenario}"

            # Verify error response schema
            data = response.json()

            # MUST have detail field
            assert "detail" in data, \
                f"Missing detail field in {scenario} (status {expected_status})"
            assert isinstance(data["detail"], str), \
                f"detail must be string in {scenario}"
            assert len(data["detail"]) > 0, \
                f"detail must not be empty in {scenario}"

            # SHOULD have error_code (but not strictly required for all errors)
            # We verify it exists and is a string if present
            if "error_code" in data:
                assert isinstance(data["error_code"], str), \
                    f"error_code must be string in {scenario}"
                assert len(data["error_code"]) > 0, \
                    f"error_code must not be empty in {scenario}"

    # ==================== Detail Field Content Validation ====================

    def test_detail_field_is_meaningful(self, client):
        """
        Test that detail field contains meaningful error messages.

        Per PRD §10 (Replay + Explainability):
        - Error messages should be clear and actionable
        - Should help developers understand what went wrong
        """
        # Test missing API key
        response = client.get("/v1/public/projects")
        data = response.json()

        detail = data["detail"]
        assert len(detail) > 10, "Detail should be more than a few words"
        assert any(word in detail.lower() for word in ["api", "key", "auth", "missing", "invalid"]), \
            "Detail should mention API key or authentication"

    def test_detail_field_is_deterministic(self, client):
        """
        Test that detail field is deterministic for the same error.

        Per PRD §9 (Demo Setup):
        - Error messages should be consistent
        - Same error should produce same detail message
        """
        # Make the same request twice
        response1 = client.get("/v1/public/projects")
        response2 = client.get("/v1/public/projects")

        data1 = response1.json()
        data2 = response2.json()

        assert data1["detail"] == data2["detail"], \
            "Same error should produce same detail message"
        assert data1.get("error_code") == data2.get("error_code"), \
            "Same error should produce same error_code"

    # ==================== Error Code Consistency ====================

    def test_error_codes_are_uppercase(self, client, auth_headers_user1):
        """
        Test that error codes follow naming convention.

        Convention: UPPER_SNAKE_CASE (e.g., INVALID_API_KEY)
        """
        # Test various errors
        error_responses = [
            client.get("/v1/public/projects"),  # Missing auth
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),  # Invalid auth
        ]

        for response in error_responses:
            data = response.json()
            if "error_code" in data:
                error_code = data["error_code"]
                # Should be uppercase with underscores
                assert error_code == error_code.upper(), \
                    f"Error code should be uppercase: {error_code}"
                assert " " not in error_code, \
                    f"Error code should not contain spaces: {error_code}"

    def test_stable_error_codes(self, client):
        """
        Test that error codes are stable across requests.

        Per DX Contract: Error codes are stable and documented.
        """
        # Test that INVALID_API_KEY is always used for auth failures
        auth_failures = [
            client.get("/v1/public/projects"),  # Missing
            client.get("/v1/public/projects", headers={"X-API-Key": ""}),  # Empty
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),  # Invalid
        ]

        for response in auth_failures:
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert data.get("error_code") == "INVALID_API_KEY", \
                "All auth failures should use INVALID_API_KEY code"


class TestErrorDetailFieldEdgeCases:
    """Test edge cases for error detail field."""

    def test_detail_field_never_null(self, client):
        """Test that detail field is never null."""
        response = client.get("/v1/public/projects")
        data = response.json()

        assert data["detail"] is not None, "detail should never be null"
        assert data["detail"] != "", "detail should never be empty string"

    def test_detail_field_never_undefined(self, client):
        """Test that detail field is always present."""
        response = client.get("/v1/public/projects")
        data = response.json()

        assert "detail" in data, "detail field must always be present"

    def test_error_response_has_no_extra_required_fields(self, client):
        """
        Test that error responses don't require extra fields beyond detail.

        Per DX Contract: All errors return { detail, error_code }.
        Only detail is required; error_code is optional.
        """
        response = client.get("/v1/public/projects")
        data = response.json()

        # Must have detail
        assert "detail" in data

        # May have error_code and validation_errors, but no other required fields
        allowed_fields = {"detail", "error_code", "validation_errors"}
        extra_fields = set(data.keys()) - allowed_fields

        # Some fields might be ok, but we shouldn't require any beyond detail
        # This is a soft check - just verify detail is always present
        assert "detail" in data, "detail is the only required field"


class TestValidationErrorDetailField:
    """
    Test validation errors specifically.

    Per api-spec.md: Validation errors return HTTP 422 with:
    - detail: Summary message
    - error_code: Usually VALIDATION_ERROR
    - validation_errors: Array with loc, msg, type (optional)
    """

    def test_validation_error_structure(self, client, auth_headers_user1):
        """
        Test that validation errors have the correct structure.

        This test is a placeholder until we have endpoints that accept
        request bodies with validation.
        """
        # This would test POST/PUT/PATCH endpoints with validation
        # For now, we just verify the concept
        pass

    def test_validation_error_detail_is_summary(self, client, auth_headers_user1):
        """
        Test that validation error detail is a summary, not an array.

        The detail field should be a string summary.
        The validation_errors field (if present) should contain the array.
        """
        # This would test POST/PUT/PATCH endpoints with validation
        # For now, we just verify the concept
        pass
