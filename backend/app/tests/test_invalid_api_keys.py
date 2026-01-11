"""
Test suite for Issue #7: Invalid API Key Error Handling.

Tests all scenarios where API keys should return HTTP 401 with INVALID_API_KEY error code:
- Missing API key
- Malformed API key
- Expired API key
- Unauthorized API key (valid format but not in system)

Requirements:
- PRD Section 10 (Clear failure modes)
- Epic 2, Story 2 (2 points)
- DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY
- DX Contract Section 7: All errors return { detail, error_code }
"""
import pytest
from fastapi import status


class TestMissingAPIKey:
    """Test cases for missing X-API-Key header."""

    def test_missing_api_key_returns_401(self, client):
        """
        Test that requests without X-API-Key header return HTTP 401.

        DX Contract: Invalid keys always return 401 INVALID_API_KEY
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_api_key_error_code(self, client):
        """
        Test that missing API key returns error_code: INVALID_API_KEY.

        Epic 2 Story 2: Error response must include error_code: "INVALID_API_KEY"
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_missing_api_key_has_detail_message(self, client):
        """
        Test that missing API key returns clear detail message.

        Epic 2 Story 2: Error response must include clear detail message
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # Should mention missing or API key
        assert "api key" in data["detail"].lower() or "missing" in data["detail"].lower()

    def test_missing_api_key_error_format(self, client):
        """
        Test that error response follows DX Contract format.

        DX Contract Section 7: All errors return { detail, error_code }
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        # Must have exactly these two fields per DX Contract
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)


class TestMalformedAPIKey:
    """Test cases for malformed API keys."""

    def test_empty_string_api_key_returns_401(self, client):
        """
        Test that empty string API key returns HTTP 401.

        Malformed key scenario: Empty string is not a valid API key format
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_string_api_key_error_code(self, client):
        """Test that empty string API key returns INVALID_API_KEY error code."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_whitespace_only_api_key_returns_401(self, client):
        """
        Test that whitespace-only API key returns HTTP 401.

        Malformed key scenario: Whitespace is not a valid API key
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "   "})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_whitespace_only_api_key_error_code(self, client):
        """Test that whitespace-only API key returns INVALID_API_KEY error code."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "   "})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_malformed_too_short_api_key_returns_401(self, client):
        """
        Test that extremely short API key returns HTTP 401.

        Malformed key scenario: Valid API keys should have minimum length
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "abc"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_too_short_api_key_error_code(self, client):
        """Test that too short API key returns INVALID_API_KEY error code."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "abc"})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_malformed_special_chars_api_key_returns_401(self, client):
        """
        Test that API key with invalid special characters returns HTTP 401.

        Malformed key scenario: API keys should not contain certain special chars
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "key!@#$%^&*()"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_special_chars_api_key_error_code(self, client):
        """Test that malformed API key with special chars returns INVALID_API_KEY."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "key!@#$%^&*()"})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_malformed_api_key_has_detail_message(self, client):
        """Test that malformed API key returns clear detail message."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0


class TestExpiredAPIKey:
    """Test cases for expired API keys."""

    def test_expired_api_key_returns_401(self, client):
        """
        Test that expired API key returns HTTP 401.

        For MVP demo with hardcoded keys, we simulate expired keys with
        special prefix to demonstrate the error handling pattern.
        """
        # Simulate expired key with "expired_" prefix
        expired_key = "expired_demo_key_abc123"
        response = client.get("/v1/public/projects", headers={"X-API-Key": expired_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_api_key_error_code(self, client):
        """Test that expired API key returns INVALID_API_KEY error code."""
        expired_key = "expired_demo_key_abc123"
        response = client.get("/v1/public/projects", headers={"X-API-Key": expired_key})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_expired_api_key_has_detail_message(self, client):
        """Test that expired API key returns clear detail message."""
        expired_key = "expired_demo_key_abc123"
        response = client.get("/v1/public/projects", headers={"X-API-Key": expired_key})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # Detail should mention expiration if system detects it
        # For MVP with hardcoded keys, this just needs to indicate invalidity


class TestUnauthorizedAPIKey:
    """Test cases for unauthorized API keys (valid format but not in system)."""

    def test_unauthorized_valid_format_key_returns_401(self, client):
        """
        Test that valid-looking but unauthorized API key returns HTTP 401.

        Scenario: API key has correct format but doesn't exist in system
        """
        unauthorized_key = "demo_key_unknown_xyz999"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_valid_format_key_error_code(self, client):
        """Test that unauthorized API key returns INVALID_API_KEY error code."""
        unauthorized_key = "demo_key_unknown_xyz999"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_unauthorized_random_key_returns_401(self, client):
        """
        Test that random unauthorized API key returns HTTP 401.
        """
        unauthorized_key = "totally_random_key_12345678"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_random_key_error_code(self, client):
        """Test that random unauthorized key returns INVALID_API_KEY error code."""
        unauthorized_key = "totally_random_key_12345678"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_unauthorized_api_key_has_detail_message(self, client):
        """Test that unauthorized API key returns clear detail message."""
        unauthorized_key = "demo_key_unknown_xyz999"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        assert "api key" in data["detail"].lower() or "invalid" in data["detail"].lower()

    def test_unauthorized_key_error_response_format(self, client):
        """
        Test that unauthorized key error follows DX Contract format.

        DX Contract: All errors return { detail, error_code }
        """
        unauthorized_key = "demo_key_unknown_xyz999"
        response = client.get("/v1/public/projects", headers={"X-API-Key": unauthorized_key})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}


class TestMultipleInvalidAPIKeyScenarios:
    """Test multiple invalid scenarios to ensure consistency."""

    @pytest.mark.parametrize("invalid_key", [
        "",  # empty
        "   ",  # whitespace
        "abc",  # too short
        "invalid_key_xyz",  # unauthorized
        "expired_key_123",  # expired pattern
        "key!@#$",  # special chars
        None,  # None value (will be converted to missing header)
    ])
    def test_all_invalid_keys_return_401(self, client, invalid_key):
        """
        Test that all invalid API key scenarios return HTTP 401.

        Parameterized test to ensure consistency across all scenarios.
        """
        if invalid_key is None:
            response = client.get("/v1/public/projects")
        else:
            response = client.get("/v1/public/projects", headers={"X-API-Key": invalid_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("invalid_key", [
        "",
        "   ",
        "abc",
        "invalid_key_xyz",
        "expired_key_123",
        "key!@#$",
    ])
    def test_all_invalid_keys_return_error_code(self, client, invalid_key):
        """
        Test that all invalid API keys return INVALID_API_KEY error code.

        Ensures consistent error_code across all scenarios.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": invalid_key})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    @pytest.mark.parametrize("invalid_key", [
        "",
        "   ",
        "abc",
        "invalid_key_xyz",
        "expired_key_123",
        "key!@#$",
    ])
    def test_all_invalid_keys_follow_error_format(self, client, invalid_key):
        """
        Test that all invalid API keys follow DX Contract error format.

        DX Contract: All errors return { detail, error_code }
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": invalid_key})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0


class TestInvalidAPIKeyAcrossEndpoints:
    """Test that invalid API key handling is consistent across all endpoints."""

    def test_invalid_key_on_list_projects(self, client):
        """Test invalid API key on GET /v1/public/projects."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    # When more endpoints are added, test them here
    # def test_invalid_key_on_create_project(self, client):
    #     """Test invalid API key on POST /v1/public/projects."""
    #     response = client.post("/v1/public/projects",
    #                           headers={"X-API-Key": "invalid"},
    #                           json={"name": "Test"})
    #
    #     assert response.status_code == status.HTTP_401_UNAUTHORIZED
    #     data = response.json()
    #     assert data["error_code"] == "INVALID_API_KEY"


class TestErrorMessageQuality:
    """Test that error messages are clear and helpful for developers."""

    def test_missing_key_message_is_clear(self, client):
        """Test that missing API key error message is developer-friendly."""
        response = client.get("/v1/public/projects")

        data = response.json()
        detail = data["detail"]

        # Message should be clear and actionable
        assert len(detail) > 10  # Not just "Error" or similar
        assert isinstance(detail, str)

    def test_invalid_key_message_is_clear(self, client):
        """Test that invalid API key error message is developer-friendly."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()
        detail = data["detail"]

        # Message should be clear and actionable
        assert len(detail) > 10
        assert isinstance(detail, str)

    def test_error_messages_dont_leak_security_info(self, client):
        """
        Test that error messages don't leak sensitive security information.

        Security best practice: Don't reveal if a key exists but is invalid vs doesn't exist
        """
        response1 = client.get("/v1/public/projects", headers={"X-API-Key": ""})
        response2 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key"})

        data1 = response1.json()
        data2 = response2.json()

        # Both should use same error_code (don't reveal distinction)
        assert data1["error_code"] == data2["error_code"] == "INVALID_API_KEY"

        # Messages can vary slightly but shouldn't reveal system internals
        assert "database" not in data1["detail"].lower()
        assert "database" not in data2["detail"].lower()


class TestDXContractCompliance:
    """Test strict compliance with DX Contract guarantees."""

    def test_dx_contract_401_guarantee(self, client):
        """
        Test DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY.

        This is a hard invariant that must never change.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        # DX Contract guarantee: Must be exactly 401
        assert response.status_code == 401

        # DX Contract guarantee: Must have INVALID_API_KEY error code
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_dx_contract_error_shape_guarantee(self, client):
        """
        Test DX Contract Section 7: All errors return deterministic shape.

        Error shape: { "detail": "...", "error_code": "..." }
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()

        # DX Contract guarantee: Exact shape
        assert isinstance(data, dict)
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_dx_contract_stable_error_code(self, client):
        """
        Test that error code is stable and deterministic.

        DX Contract: Error codes are stable and documented.
        Multiple identical requests should return identical error responses.
        """
        response1 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})
        response2 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data1 = response1.json()
        data2 = response2.json()

        # Error code must be deterministic
        assert data1["error_code"] == data2["error_code"]
        assert data1["error_code"] == "INVALID_API_KEY"
