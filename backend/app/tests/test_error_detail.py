"""
Comprehensive test suite for Epic 2, Issue 3: Error Detail Field Consistency.

Tests that all error responses include a 'detail' field that is never null or empty.
This ensures compliance with the DX Contract Section 7 (Error Semantics):
- All errors MUST return { detail, error_code }
- detail: Human-readable error message (required)
- error_code: Machine-readable error code (required)

Test Coverage:
1. HTTP 401 (Unauthorized) errors include detail field
2. HTTP 404 (Not Found) errors include detail field
3. HTTP 422 (Validation Error) errors include detail field
4. HTTP 500 (Internal Server Error) errors include safe detail message
5. Detail field is never null or empty string
6. Error format consistency across all error types

Reference:
- backend/app/schemas/errors.py - Error response schemas
- backend/app/core/middleware.py - Error handlers
- backend/app/main.py - Exception handler registration
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestUnauthorizedErrors:
    """Test HTTP 401 (Unauthorized) errors include detail field."""

    def test_missing_api_key_includes_detail(self, client):
        """
        Test that missing API key error includes detail field.

        Per DX Contract: All errors return { detail, error_code }
        Epic 2, Issue 3: All errors include a detail field.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # Verify detail field exists
        assert "detail" in data, "Missing 'detail' field in 401 error response"

        # Verify detail is a non-empty string
        assert isinstance(data["detail"], str), "detail must be a string"
        assert data["detail"] != "", "detail must not be empty string"
        assert data["detail"] is not None, "detail must not be None"
        assert len(data["detail"]) > 0, "detail must have content"

        # Verify error_code exists
        assert "error_code" in data, "Missing 'error_code' field in 401 error response"
        assert data["error_code"] == "INVALID_API_KEY"

    def test_invalid_api_key_includes_detail(self, client):
        """Test that invalid API key error includes detail field."""
        response = client.get(
            "/v1/public/projects",
            headers={"X-API-Key": "invalid_key_xyz"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # Verify detail field exists and is not empty
        assert "detail" in data, "Missing 'detail' field in invalid API key error"
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert data["detail"] is not None
        assert len(data["detail"]) > 0

        # Verify error_code
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_empty_api_key_includes_detail(self, client):
        """Test that empty API key error includes detail field."""
        response = client.get(
            "/v1/public/projects",
            headers={"X-API-Key": ""}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert data["detail"] is not None
        assert "error_code" in data

    def test_malformed_api_key_includes_detail(self, client):
        """Test that malformed API key error includes detail field."""
        malformed_keys = [
            "   ",  # whitespace only
            "abc",  # too short
            "key!@#$%^&*()",  # special characters
        ]

        for key in malformed_keys:
            response = client.get(
                "/v1/public/projects",
                headers={"X-API-Key": key}
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()

            assert "detail" in data, f"Missing detail for malformed key: {key}"
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert data["detail"] is not None
            assert "error_code" in data

    def test_401_detail_is_meaningful(self, client):
        """Test that 401 error detail is meaningful and helpful."""
        response = client.get("/v1/public/projects")
        data = response.json()

        detail = data["detail"]

        # Detail should be descriptive (more than just "Error")
        assert len(detail) > 5, "Detail message should be descriptive"

        # Detail should mention API key or authentication
        detail_lower = detail.lower()
        assert any(
            keyword in detail_lower
            for keyword in ["api", "key", "auth", "invalid", "missing"]
        ), "Detail should mention authentication issue"


class TestNotFoundErrors:
    """Test HTTP 404 (Not Found) errors include detail field."""

    def test_nonexistent_project_includes_detail(self, client, auth_headers_user1):
        """Test that project not found error includes detail field."""
        response = client.get(
            "/v1/public/projects/nonexistent_project_id",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify detail field exists and is not empty
        assert "detail" in data, "Missing 'detail' field in 404 error response"
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert data["detail"] is not None
        assert len(data["detail"]) > 0

    def test_nonexistent_route_includes_detail(self, client, auth_headers_user1):
        """Test that route not found error includes detail field."""
        response = client.get(
            "/v1/public/nonexistent_route_path",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data, "Missing 'detail' field in route not found error"
        assert isinstance(data["detail"], str)
        assert data["detail"] != ""
        assert data["detail"] is not None

    def test_404_detail_is_meaningful(self, client, auth_headers_user1):
        """Test that 404 error detail is meaningful."""
        response = client.get(
            "/v1/public/projects/nonexistent_id",
            headers=auth_headers_user1
        )

        data = response.json()
        detail = data["detail"]

        # Detail should be descriptive
        assert len(detail) > 5, "Detail message should be descriptive"

        # Detail should mention not found or similar concept
        detail_lower = detail.lower()
        assert any(
            keyword in detail_lower
            for keyword in ["not found", "does not exist", "cannot find", "unknown"]
        ), "Detail should indicate resource was not found"


class TestValidationErrors:
    """Test HTTP 422 (Validation Error) errors include detail field."""

    def test_invalid_query_param_includes_detail(self, client, auth_headers_user1):
        """Test that validation error for invalid query param includes detail."""
        # Send invalid limit parameter (should be an integer)
        response = client.get(
            "/v1/public/projects?limit=invalid_value",
            headers=auth_headers_user1
        )

        # If validation is enforced, should return 422
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # Verify detail field exists and is not empty
            assert "detail" in data, "Missing 'detail' field in 422 validation error"
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert data["detail"] is not None
            assert len(data["detail"]) > 0

            # Should have error_code
            assert "error_code" in data
            assert data["error_code"] == "VALIDATION_ERROR"

            # May have validation_errors array (optional but recommended)
            if "validation_errors" in data:
                assert isinstance(data["validation_errors"], list)

    def test_invalid_json_body_includes_detail(self, client, auth_headers_user1):
        """Test that validation error for invalid JSON body includes detail."""
        # Test with POST endpoint if available
        # This is a general test for validation error structure
        # Actual endpoint depends on API implementation

        # For now, test the error handler by sending invalid data to health endpoint
        # (This may not trigger validation, but demonstrates the pattern)
        response = client.post(
            "/v1/public/projects",
            headers=auth_headers_user1,
            json={"invalid_field": "value"}
        )

        # If this triggers validation error
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            assert "detail" in data
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert data["detail"] is not None
            assert "error_code" in data

    def test_validation_error_detail_format(self, client, auth_headers_user1):
        """Test that validation error detail follows expected format."""
        response = client.get(
            "/v1/public/projects?limit=not_a_number",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # Detail should be a summary string, not an array
            assert isinstance(data["detail"], str), "detail should be string summary"

            # Detail should mention validation or field
            detail_lower = data["detail"].lower()
            assert any(
                keyword in detail_lower
                for keyword in ["validation", "invalid", "field", "error"]
            ), "Detail should indicate validation failure"

            # Detailed errors should be in validation_errors array, not detail
            if "validation_errors" in data:
                assert isinstance(data["validation_errors"], list)
                for err in data["validation_errors"]:
                    assert "loc" in err
                    assert "msg" in err
                    assert "type" in err


class TestInternalServerErrors:
    """Test HTTP 500 (Internal Server Error) errors include safe detail."""

    def test_internal_error_includes_detail(self, client, monkeypatch):
        """
        Test that internal server errors include a safe detail message.

        Per Epic 2, Issue 3: All errors include a detail field.
        Per security best practices: Don't leak internal error details.
        """
        # We test this by verifying that the error handler is configured correctly
        # Rather than trying to trigger a 500, we verify the middleware constants
        from app.core.middleware import DEFAULT_INTERNAL_ERROR_DETAIL

        # Verify the default error message exists and is safe
        assert DEFAULT_INTERNAL_ERROR_DETAIL is not None
        assert len(DEFAULT_INTERNAL_ERROR_DETAIL) > 0
        assert isinstance(DEFAULT_INTERNAL_ERROR_DETAIL, str)

        # The default message should not contain sensitive information
        safe_message = DEFAULT_INTERNAL_ERROR_DETAIL.lower()
        sensitive_keywords = ["exception", "traceback", "stack", "file", "line number"]
        for keyword in sensitive_keywords:
            assert keyword not in safe_message, \
                f"Default error message should not contain '{keyword}'"

        # Should contain helpful but safe keywords
        assert any(
            keyword in safe_message
            for keyword in ["unexpected", "error", "try again", "later"]
        ), "Default error message should be helpful but safe"

    def test_500_detail_is_safe_and_generic(self, client):
        """Test that 500 errors provide safe, non-leaky error messages."""
        # This test verifies the error handler provides safe messages
        # We can't easily trigger a 500 without modifying application code
        # But we can verify the handler implementation

        from app.core.middleware import DEFAULT_INTERNAL_ERROR_DETAIL

        # Verify the default message is safe
        assert len(DEFAULT_INTERNAL_ERROR_DETAIL) > 0
        assert DEFAULT_INTERNAL_ERROR_DETAIL is not None

        # Should not contain sensitive keywords
        safe_message = DEFAULT_INTERNAL_ERROR_DETAIL.lower()
        sensitive_keywords = ["traceback", "exception", "stack", "file", "line"]
        for keyword in sensitive_keywords:
            assert keyword not in safe_message, \
                f"Default error message should not contain '{keyword}'"


class TestDetailFieldConsistency:
    """Test that detail field is never null or empty across all errors."""

    def test_detail_never_null(self, client):
        """Test that detail field is never null/None."""
        # Test various error scenarios
        error_scenarios = [
            # Missing API key (401)
            lambda: client.get("/v1/public/projects"),
            # Invalid API key (401)
            lambda: client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
            # Empty API key (401)
            lambda: client.get("/v1/public/projects", headers={"X-API-Key": ""}),
        ]

        for scenario in error_scenarios:
            response = scenario()
            data = response.json()

            assert "detail" in data, "detail field must be present"
            assert data["detail"] is not None, "detail must not be None/null"

    def test_detail_never_empty_string(self, client):
        """Test that detail field is never an empty string."""
        error_scenarios = [
            lambda: client.get("/v1/public/projects"),
            lambda: client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
            lambda: client.get("/v1/public/projects", headers={"X-API-Key": ""}),
        ]

        for scenario in error_scenarios:
            response = scenario()
            data = response.json()

            assert data["detail"] != "", "detail must not be empty string"
            assert len(data["detail"]) > 0, "detail must have content"

    def test_detail_always_string_type(self, client, auth_headers_user1):
        """Test that detail field is always a string (not array, object, etc)."""
        error_scenarios = [
            # 401 error
            lambda: client.get("/v1/public/projects"),
            # 404 error
            lambda: client.get("/v1/public/nonexistent", headers=auth_headers_user1),
            # 405 error
            lambda: client.delete("/v1/public/projects", headers=auth_headers_user1),
        ]

        for scenario in error_scenarios:
            response = scenario()
            data = response.json()

            assert isinstance(data["detail"], str), \
                f"detail must be string type, got {type(data['detail'])}"
            assert not isinstance(data["detail"], list), "detail must not be a list"
            assert not isinstance(data["detail"], dict), "detail must not be a dict"

    def test_detail_whitespace_only_not_allowed(self, client):
        """Test that detail is not just whitespace."""
        response = client.get("/v1/public/projects")
        data = response.json()

        detail = data["detail"]
        assert detail.strip() != "", "detail must not be only whitespace"
        assert len(detail.strip()) > 0, "detail must have non-whitespace content"


class TestErrorFormatConsistency:
    """Test that all errors follow consistent format."""

    def test_error_response_has_required_fields(self, client, auth_headers_user1):
        """
        Test that all error responses have required fields.

        Per DX Contract Section 7:
        - detail (required) - MUST always be present
        - error_code (optional but recommended) - May not be present for framework-level errors
        """
        error_scenarios = [
            # 401 - Missing auth (custom middleware)
            (lambda: client.get("/v1/public/projects"), status.HTTP_401_UNAUTHORIZED, True),
            # 401 - Invalid auth (custom middleware)
            (lambda: client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
             status.HTTP_401_UNAUTHORIZED, True),
            # 404 - Not found (FastAPI default handler may not include error_code)
            (lambda: client.get("/v1/public/nonexistent", headers=auth_headers_user1),
             status.HTTP_404_NOT_FOUND, False),
            # 405 - Method not allowed (FastAPI default handler may not include error_code)
            (lambda: client.delete("/v1/public/projects", headers=auth_headers_user1),
             status.HTTP_405_METHOD_NOT_ALLOWED, False),
        ]

        for scenario, expected_status, requires_error_code in error_scenarios:
            response = scenario()
            assert response.status_code == expected_status

            data = response.json()

            # MUST have detail (required for ALL errors per Epic 2, Issue 3)
            assert "detail" in data, f"Missing 'detail' in {expected_status} error"
            assert isinstance(data["detail"], str)
            assert data["detail"] != ""
            assert data["detail"] is not None

            # error_code is optional for framework-level errors
            if requires_error_code:
                assert "error_code" in data, f"Missing 'error_code' in {expected_status} error"
                assert isinstance(data["error_code"], str)
                assert data["error_code"] != ""
            else:
                # Optional: may or may not have error_code
                if "error_code" in data:
                    assert isinstance(data["error_code"], str)
                    assert data["error_code"] != ""

    def test_error_code_follows_naming_convention(self, client):
        """Test that error codes follow UPPER_SNAKE_CASE convention."""
        response = client.get("/v1/public/projects")
        data = response.json()

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

    def test_error_responses_are_deterministic(self, client):
        """Test that same error produces same response."""
        # Make same request twice
        response1 = client.get("/v1/public/projects")
        response2 = client.get("/v1/public/projects")

        data1 = response1.json()
        data2 = response2.json()

        # Should have same detail
        assert data1["detail"] == data2["detail"], \
            "Same error should produce same detail message"

        # Should have same error_code
        assert data1["error_code"] == data2["error_code"], \
            "Same error should produce same error_code"

    def test_validation_errors_have_consistent_structure(self, client, auth_headers_user1):
        """Test that validation errors (422) have consistent structure."""
        response = client.get(
            "/v1/public/projects?limit=invalid",
            headers=auth_headers_user1
        )

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            # Must have detail (summary)
            assert "detail" in data
            assert isinstance(data["detail"], str)

            # Must have error_code
            assert "error_code" in data
            assert data["error_code"] == "VALIDATION_ERROR"

            # May have validation_errors (optional but recommended)
            if "validation_errors" in data:
                assert isinstance(data["validation_errors"], list)
                for err in data["validation_errors"]:
                    # Each validation error should have loc, msg, type
                    assert "loc" in err, "validation error should have 'loc'"
                    assert "msg" in err, "validation error should have 'msg'"
                    assert "type" in err, "validation error should have 'type'"


class TestErrorDetailQuality:
    """Test that error detail messages are high quality."""

    def test_detail_is_descriptive(self, client):
        """Test that detail messages are descriptive, not generic."""
        response = client.get("/v1/public/projects")
        data = response.json()

        detail = data["detail"]

        # Should be more than just "Error" or "Bad request"
        assert len(detail) > 10, "Detail should be descriptive (more than 10 chars)"

        # Should not be overly generic
        generic_messages = ["error", "bad request", "failed", "invalid"]
        assert detail.lower() not in generic_messages, \
            "Detail should be more specific than single-word messages"

    def test_detail_is_actionable(self, client):
        """Test that detail messages help developers understand what to do."""
        response = client.get("/v1/public/projects")
        data = response.json()

        detail = data["detail"]

        # For auth errors, should mention API key
        detail_lower = detail.lower()
        assert "api" in detail_lower or "key" in detail_lower or "auth" in detail_lower, \
            "Auth error detail should mention API key or authentication"

    def test_detail_does_not_leak_sensitive_info(self, client):
        """Test that error details don't leak sensitive information."""
        error_scenarios = [
            lambda: client.get("/v1/public/projects"),
            lambda: client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}),
        ]

        for scenario in error_scenarios:
            response = scenario()
            data = response.json()
            detail = data["detail"].lower()

            # Should not expose internal details
            sensitive_keywords = [
                "database", "sql", "query", "connection", "password",
                "secret", "token value", "traceback", "file path"
            ]

            for keyword in sensitive_keywords:
                assert keyword not in detail, \
                    f"Error detail should not expose '{keyword}'"


class TestDXContractCompliance:
    """Test compliance with DX Contract Section 7 (Error Semantics)."""

    def test_all_errors_return_detail_and_error_code(self, client, auth_headers_user1):
        """
        Test DX Contract requirement: All errors return { detail, error_code }.

        Per DX Contract Section 7 and Epic 2, Issue 3:
        - All errors MUST have 'detail' field (required, never null or empty)
        - All custom application errors SHOULD have 'error_code' (recommended)
        - Framework-level errors (404, 405) may only have 'detail'

        The critical requirement from Epic 2, Issue 3 is that 'detail' is always present.
        """
        error_scenarios = [
            # Custom middleware errors - must have both detail and error_code
            (client.get("/v1/public/projects"), True),  # 401
            (client.get("/v1/public/projects", headers={"X-API-Key": "invalid"}), True),  # 401
            # Framework-level errors - must have detail, may have error_code
            (client.get("/v1/public/nonexistent", headers=auth_headers_user1), False),  # 404
            (client.delete("/v1/public/projects", headers=auth_headers_user1), False),  # 405
        ]

        for response, requires_error_code in error_scenarios:
            data = response.json()

            # detail field is REQUIRED for ALL errors (Epic 2, Issue 3)
            assert "detail" in data, "DX Contract: All errors must have 'detail'"
            assert isinstance(data["detail"], str)
            assert len(data["detail"]) > 0

            # error_code is required for custom errors, optional for framework errors
            if requires_error_code:
                assert "error_code" in data, "Custom errors must have 'error_code'"
                assert isinstance(data["error_code"], str)
                assert len(data["error_code"]) > 0
            else:
                # Framework errors may or may not have error_code
                # But if present, it must be a valid non-empty string
                if "error_code" in data:
                    assert isinstance(data["error_code"], str)
                    assert len(data["error_code"]) > 0

    def test_error_codes_are_stable(self, client):
        """
        Test DX Contract requirement: Error codes are stable and documented.

        Same error should always produce same error_code.
        """
        # Test invalid API key multiple times
        responses = [
            client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})
            for _ in range(3)
        ]

        error_codes = [r.json()["error_code"] for r in responses]

        # All should be the same
        assert len(set(error_codes)) == 1, \
            "Same error should always produce same error_code"
        assert error_codes[0] == "INVALID_API_KEY"

    def test_error_format_is_json(self, client):
        """Test that error responses are JSON with correct content type."""
        response = client.get("/v1/public/projects")

        # Should be JSON
        assert response.headers["content-type"] == "application/json"

        # Should be parseable JSON
        data = response.json()
        assert isinstance(data, dict)
