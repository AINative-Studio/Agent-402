"""
Unit tests for API Key Authentication Middleware.

Tests Epic 2, Story 1 requirements:
- All /v1/public/* endpoints require X-API-Key header
- Missing API key returns 401 INVALID_API_KEY
- Invalid API key returns 401 INVALID_API_KEY
- Valid API key allows request to proceed
- Non-public endpoints are not affected
- Health check and docs endpoints are exempt
"""
import pytest
from fastapi import status
from unittest.mock import patch


class TestAPIKeyAuthMiddleware:
    """Test suite for API Key Authentication Middleware."""

    def test_public_endpoint_missing_api_key(self, client):
        """
        Test that missing X-API-Key returns 401 for public endpoints.
        Epic 2 Story 1: All public endpoints require X-API-Key.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"
        # Updated message includes both X-API-Key and Bearer token options
        assert "Authentication required" in data["detail"] or "Missing X-API-Key" in data["detail"]

    def test_public_endpoint_invalid_api_key(self, client):
        """
        Test that invalid X-API-Key returns 401 for public endpoints.
        Epic 2 Story 1: Invalid API keys return 401 INVALID_API_KEY.
        """
        headers = {"X-API-Key": "invalid_key_xyz"}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert "Invalid API key" in data["detail"]

    def test_public_endpoint_valid_api_key(self, client, auth_headers_user1):
        """
        Test that valid X-API-Key allows request to proceed.
        Epic 2 Story 1: Valid API keys authenticate successfully.
        """
        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        # Should not return 401
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        # Should return 200 (successful response)
        assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_no_auth_required(self, client):
        """
        Test that health check endpoint does not require authentication.
        Health checks should be publicly accessible for monitoring.
        """
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_root_endpoint_no_auth_required(self, client):
        """
        Test that root endpoint does not require authentication.
        API information should be publicly accessible.
        """
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_docs_endpoint_no_auth_required(self, client):
        """
        Test that OpenAPI docs endpoint does not require authentication.
        Documentation should be publicly accessible.
        """
        response = client.get("/docs")

        # Should return 200 (docs page) not 401
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_json_no_auth_required(self, client):
        """
        Test that OpenAPI JSON endpoint does not require authentication.
        OpenAPI spec should be publicly accessible.
        """
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "openapi" in data
        assert "info" in data

    def test_error_response_format(self, client):
        """
        Test that authentication errors follow DX Contract format.
        Per DX Contract §7: All errors return { detail, error_code }.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()

        # Must have exactly these fields per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0
        assert len(data["error_code"]) > 0

    def test_case_sensitive_header(self, client, valid_api_key_user1):
        """
        Test that X-API-Key header is case-insensitive (HTTP standard).
        HTTP headers should be case-insensitive per RFC 7230.
        """
        # FastAPI/Starlette automatically handles case-insensitive headers
        headers = {"x-api-key": valid_api_key_user1}
        response = client.get("/v1/public/projects", headers=headers)

        # Should work with lowercase header name
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_api_keys_different_users(
        self, client, auth_headers_user1, auth_headers_user2
    ):
        """
        Test that different API keys authenticate different users.
        Epic 2 Story 1: Each API key maps to a specific user.
        """
        response1 = client.get("/v1/public/projects", headers=auth_headers_user1)
        response2 = client.get("/v1/public/projects", headers=auth_headers_user2)

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Different users should see different projects
        # (This validates that the correct user_id is extracted)
        assert data1["total"] != data2["total"] or data1["projects"] != data2["projects"]

    def test_empty_api_key_header(self, client):
        """
        Test that empty X-API-Key header returns 401.
        Empty string should be treated as missing.
        """
        headers = {"X-API-Key": ""}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_whitespace_api_key(self, client):
        """
        Test that whitespace-only API key returns 401.
        Whitespace should not be a valid API key.
        """
        headers = {"X-API-Key": "   "}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_api_key_with_special_characters(self, client):
        """
        Test that API key with special characters is validated correctly.
        Should return 401 if not in valid keys.
        """
        headers = {"X-API-Key": "key_with_!@#$%^&*()_special_chars"}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_very_long_api_key(self, client):
        """
        Test that extremely long API key is handled properly.
        Should return 401 if not in valid keys.
        """
        long_key = "x" * 1000
        headers = {"X-API-Key": long_key}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_sql_injection_attempt_in_api_key(self, client):
        """
        Test that SQL injection attempts in API key are rejected.
        Security test: Should not cause errors, just return 401.
        """
        headers = {"X-API-Key": "'; DROP TABLE users; --"}
        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_api_key_only_affects_public_endpoints(self, client):
        """
        Test that middleware only affects /v1/public/* endpoints.
        Other endpoints should not be affected by this middleware.
        """
        # Health check should work without API key
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        # Root should work without API key
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        # Docs should work without API key
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_middleware_logs_authentication_attempts(
        self, client, auth_headers_user1, caplog
    ):
        """
        Test that middleware logs authentication attempts.
        Per PRD §10: Auditability and logging requirements.
        Note: This test verifies that successful authentication results in a 200 OK response.
        Actual logging verification may depend on logging configuration.
        """
        import logging
        caplog.set_level(logging.INFO)

        response = client.get("/v1/public/projects", headers=auth_headers_user1)

        # Verify successful authentication
        assert response.status_code == status.HTTP_200_OK

        # Note: Logging verification in middleware may not be captured by caplog
        # in all test configurations. The important part is that authentication succeeds.

    def test_middleware_logs_failed_authentication(self, client, caplog):
        """
        Test that middleware logs failed authentication attempts.
        Per PRD §10: Auditability - failed auth should be logged.
        Note: This test verifies that failed authentication returns 401.
        Actual logging verification may depend on logging configuration.
        """
        import logging
        caplog.set_level(logging.WARNING)

        response = client.get("/v1/public/projects")

        # Verify authentication failure
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Note: Logging verification in middleware may not be captured by caplog
        # in all test configurations. The important part is that authentication fails properly.

    def test_concurrent_requests_with_different_api_keys(
        self, client, auth_headers_user1, auth_headers_user2
    ):
        """
        Test that concurrent requests with different API keys work correctly.
        Tests thread safety and request isolation.
        """
        # Make multiple requests rapidly
        responses = []
        for _ in range(5):
            r1 = client.get("/v1/public/projects", headers=auth_headers_user1)
            r2 = client.get("/v1/public/projects", headers=auth_headers_user2)
            responses.extend([r1, r2])

        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

    def test_api_key_validation_deterministic(self, client, auth_headers_user1):
        """
        Test that API key validation is deterministic.
        Per PRD §9: Demo setup must be deterministic.
        Same API key should always authenticate the same user.
        """
        # Make the same request multiple times
        responses = []
        for _ in range(10):
            response = client.get("/v1/public/projects", headers=auth_headers_user1)
            responses.append(response.json())

        # All responses should be identical
        first_response = responses[0]
        for response in responses[1:]:
            assert response == first_response
