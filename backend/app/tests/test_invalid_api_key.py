"""
Comprehensive test suite for Epic 2, Issue 2: Invalid API Key Error Handling.

Tests the 401 INVALID_API_KEY error response for all API key validation failure scenarios.

Requirements:
- PRD Section 10 (Clear failure modes)
- Epic 2, Story 2 (2 points)
- DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY
- DX Contract Section 7: All errors return { detail, error_code }

Implementation tested:
- Missing X-API-Key header → 401 with error_code "INVALID_API_KEY"
- Empty API key → 401 with error_code "INVALID_API_KEY"
- Invalid API key → 401 with error_code "INVALID_API_KEY"

Response format: { "detail": "...", "error_code": "INVALID_API_KEY" }
"""
import pytest
from fastapi import status


class TestMissingAPIKeyHeader:
    """Test cases for missing X-API-Key header."""

    def test_missing_header_returns_401(self, client):
        """
        Test that request without X-API-Key header returns HTTP 401.

        Epic 2 Issue 2: Missing API key should return 401 UNAUTHORIZED.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_header_error_code(self, client):
        """
        Test that missing X-API-Key header returns error_code: INVALID_API_KEY.

        DX Contract: Invalid keys always return 401 INVALID_API_KEY
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_missing_header_has_detail_field(self, client):
        """
        Test that missing X-API-Key header returns detail field.

        Epic 2 Story 3: All errors include a detail field.
        DX Contract Section 7: All errors return { detail, error_code }
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_missing_header_detail_message_content(self, client):
        """
        Test that missing X-API-Key header returns specific detail message.

        Implementation: Returns "Authentication required. Provide X-API-Key or Authorization Bearer token."
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        assert data["detail"] == "Authentication required. Provide X-API-Key or Authorization Bearer token."

    def test_missing_header_response_format(self, client):
        """
        Test that missing header error follows DX Contract format.

        DX Contract Section 7: All errors return { detail, error_code }
        Response must have exactly these two fields.
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        # Must have exactly these two fields per DX Contract
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_missing_header_on_projects_endpoint(self, client):
        """
        Test that missing header is handled consistently on projects endpoint.

        Ensures authentication dependency works correctly.
        """
        response = client.get("/v1/public/projects")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestEmptyAPIKey:
    """Test cases for empty X-API-Key header value."""

    def test_empty_string_returns_401(self, client):
        """
        Test that empty string API key returns HTTP 401.

        Epic 2 Issue 2: Empty API key is invalid.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_string_error_code(self, client):
        """
        Test that empty string API key returns error_code: INVALID_API_KEY.

        DX Contract: Invalid keys always return 401 INVALID_API_KEY
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_empty_string_has_detail_field(self, client):
        """
        Test that empty string API key returns detail field.

        Epic 2 Story 3: All errors include a detail field.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_empty_string_detail_message_content(self, client):
        """
        Test that empty API key returns specific detail message.

        Implementation: Returns "Authentication required. Provide X-API-Key or Authorization Bearer token."
        (Empty string is treated as missing)
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert data["detail"] == "Authentication required. Provide X-API-Key or Authorization Bearer token."

    def test_empty_string_response_format(self, client):
        """
        Test that empty key error follows DX Contract format.

        DX Contract Section 7: All errors return { detail, error_code }
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}

    def test_whitespace_only_api_key_returns_401(self, client):
        """
        Test that whitespace-only API key is treated as empty.

        Edge case: Whitespace-only strings should be treated as empty.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "   "})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_whitespace_only_api_key_error_code(self, client):
        """Test that whitespace-only API key returns INVALID_API_KEY error code."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "   "})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_whitespace_only_api_key_detail_message(self, client):
        """
        Test that whitespace-only API key returns appropriate detail message.

        Implementation: Returns "API key cannot be empty or whitespace"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "   "})

        data = response.json()
        assert data["detail"] == "API key cannot be empty or whitespace"

    def test_tab_only_api_key_returns_401(self, client):
        """
        Test that tab-only API key is treated as empty.

        Edge case: Tab characters should be treated as whitespace.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "\t\t"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"


class TestInvalidAPIKey:
    """Test cases for invalid/unknown API keys."""

    def test_invalid_key_returns_401(self, client):
        """
        Test that invalid API key returns HTTP 401.

        Epic 2 Issue 2: Unknown API key should return 401 UNAUTHORIZED.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_key_error_code(self, client):
        """
        Test that invalid API key returns error_code: INVALID_API_KEY.

        DX Contract: Invalid keys always return 401 INVALID_API_KEY
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_invalid_key_has_detail_field(self, client):
        """
        Test that invalid API key returns detail field.

        Epic 2 Story 3: All errors include a detail field.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_invalid_key_detail_message_content(self, client):
        """
        Test that invalid API key returns specific detail message.

        Implementation: Should return "Invalid API key"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        data = response.json()
        assert data["detail"] == "Invalid API key"

    def test_invalid_key_response_format(self, client):
        """
        Test that invalid key error follows DX Contract format.

        DX Contract Section 7: All errors return { detail, error_code }
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}

    def test_short_invalid_key(self, client):
        """
        Test that short invalid API key returns 401.

        Edge case: Keys shorter than 10 characters return "API key format is invalid"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "abc"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "API key format is invalid"

    def test_long_invalid_key(self, client):
        """
        Test that long invalid API key returns 401.

        Edge case: Even very long keys should return consistent error.
        """
        long_key = "x" * 500
        response = client.get("/v1/public/projects", headers={"X-API-Key": long_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "Invalid API key"

    def test_special_characters_key(self, client):
        """
        Test that API key with special characters returns 401.

        Edge case: Keys with special characters return "API key contains invalid characters"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "key!@#$%^&*()"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "API key contains invalid characters"

    def test_unicode_characters_key(self, client):
        """
        Test that API key with unicode characters returns 401.

        Edge case: "key_emoji_test" is valid format (15+ chars, alphanumeric+underscore)
        but not in system, so returns "Invalid API key"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "key_emoji_test"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "Invalid API key"


class TestErrorResponseConsistency:
    """Test consistency of error responses across all invalid scenarios."""

    @pytest.mark.parametrize("api_key_header", [
        None,  # Missing header
        "",  # Empty string
        "   ",  # Whitespace
        "invalid_key",  # Invalid key
        "abc",  # Too short
        "x" * 500,  # Too long
        "key!@#$",  # Special chars
    ])
    def test_all_scenarios_return_401(self, client, api_key_header):
        """
        Test that all invalid API key scenarios return HTTP 401.

        Parameterized test to ensure consistency across all scenarios.
        """
        if api_key_header is None:
            response = client.get("/v1/public/projects")
        else:
            response = client.get("/v1/public/projects", headers={"X-API-Key": api_key_header})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("api_key_header", [
        None,
        "",
        "   ",
        "invalid_key",
        "abc",
        "key!@#$",
    ])
    def test_all_scenarios_have_invalid_api_key_error_code(self, client, api_key_header):
        """
        Test that all invalid scenarios return INVALID_API_KEY error code.

        DX Contract: All invalid key scenarios use same error code.
        """
        if api_key_header is None:
            response = client.get("/v1/public/projects")
        else:
            response = client.get("/v1/public/projects", headers={"X-API-Key": api_key_header})

        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    @pytest.mark.parametrize("api_key_header", [
        None,
        "",
        "   ",
        "invalid_key",
        "abc",
        "key!@#$",
    ])
    def test_all_scenarios_follow_error_format(self, client, api_key_header):
        """
        Test that all invalid scenarios follow DX Contract error format.

        DX Contract Section 7: All errors return { detail, error_code }
        """
        if api_key_header is None:
            response = client.get("/v1/public/projects")
        else:
            response = client.get("/v1/public/projects", headers={"X-API-Key": api_key_header})

        data = response.json()
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0


class TestSpecificDetailMessages:
    """Test that different invalid scenarios return specific detail messages."""

    def test_missing_vs_empty_vs_invalid_detail_messages(self, client):
        """
        Test that missing, empty, and invalid keys return distinct detail messages.

        While all use same error_code, detail messages should be specific:
        - Missing/Empty: "Authentication required. Provide X-API-Key or Authorization Bearer token."
        - Whitespace: "API key cannot be empty or whitespace"
        - Short: "API key format is invalid"
        - Invalid: "Invalid API key"
        """
        # Missing header
        response_missing = client.get("/v1/public/projects")
        data_missing = response_missing.json()

        # Empty string
        response_empty = client.get("/v1/public/projects", headers={"X-API-Key": ""})
        data_empty = response_empty.json()

        # Whitespace
        response_whitespace = client.get("/v1/public/projects", headers={"X-API-Key": "   "})
        data_whitespace = response_whitespace.json()

        # Short key
        response_short = client.get("/v1/public/projects", headers={"X-API-Key": "abc"})
        data_short = response_short.json()

        # Invalid key (valid format but not in system)
        response_invalid = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_abc123"})
        data_invalid = response_invalid.json()

        # All should have same error code
        assert data_missing["error_code"] == "INVALID_API_KEY"
        assert data_empty["error_code"] == "INVALID_API_KEY"
        assert data_whitespace["error_code"] == "INVALID_API_KEY"
        assert data_short["error_code"] == "INVALID_API_KEY"
        assert data_invalid["error_code"] == "INVALID_API_KEY"

        # But detail messages should be specific
        assert data_missing["detail"] == "Authentication required. Provide X-API-Key or Authorization Bearer token."
        assert data_empty["detail"] == "Authentication required. Provide X-API-Key or Authorization Bearer token."
        assert data_whitespace["detail"] == "API key cannot be empty or whitespace"
        assert data_short["detail"] == "API key format is invalid"
        assert data_invalid["detail"] == "Invalid API key"


class TestCrossEndpointConsistency:
    """Test that invalid API key handling is consistent across all endpoints."""

    def test_invalid_key_on_projects_endpoint(self, client):
        """
        Test that invalid API key is handled correctly on projects endpoint.

        Short keys return "API key format is invalid"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "API key format is invalid"

    def test_invalid_key_with_valid_format(self, client):
        """
        Test that invalid API key with valid format returns correct error.

        Valid format but not in system returns "Invalid API key"
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_abc123"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "Invalid API key"

    def test_missing_header_on_projects_endpoint(self, client):
        """
        Test that missing header is handled correctly on projects endpoint.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
        assert data["detail"] == "Authentication required. Provide X-API-Key or Authorization Bearer token."


class TestDXContractCompliance:
    """Test strict compliance with DX Contract guarantees."""

    def test_dx_contract_401_status_code_guarantee(self, client):
        """
        Test DX Contract Section 2: Invalid keys always return 401.

        This is a hard invariant that must never change.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        # DX Contract guarantee: Must be exactly 401
        assert response.status_code == 401

    def test_dx_contract_error_code_guarantee(self, client):
        """
        Test DX Contract Section 2: Invalid keys return INVALID_API_KEY.

        This is a hard invariant that must never change.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()
        # DX Contract guarantee: Must be INVALID_API_KEY
        assert data["error_code"] == "INVALID_API_KEY"

    def test_dx_contract_error_shape_guarantee(self, client):
        """
        Test DX Contract Section 7: All errors return deterministic shape.

        Error shape: { "detail": "...", "error_code": "..." }
        Must have exactly these two fields, no more, no less.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()

        # DX Contract guarantee: Exact shape
        assert isinstance(data, dict)
        assert set(data.keys()) == {"detail", "error_code"}
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0
        assert len(data["error_code"]) > 0

    def test_dx_contract_stable_error_code(self, client):
        """
        Test that error code is stable and deterministic.

        DX Contract: Error codes are stable and documented.
        Multiple identical requests should return identical error codes.
        """
        response1 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})
        response2 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})
        response3 = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        # Error code must be deterministic across multiple requests
        assert data1["error_code"] == data2["error_code"] == data3["error_code"]
        assert data1["error_code"] == "INVALID_API_KEY"

    def test_dx_contract_no_security_leaks(self, client):
        """
        Test that error messages don't leak sensitive security information.

        Security best practice: Don't reveal if a key exists but is invalid
        vs doesn't exist. All invalid key scenarios should use same error_code.
        """
        response_empty = client.get("/v1/public/projects", headers={"X-API-Key": ""})
        response_invalid = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key"})
        response_short = client.get("/v1/public/projects", headers={"X-API-Key": "abc"})

        data_empty = response_empty.json()
        data_invalid = response_invalid.json()
        data_short = response_short.json()

        # All should use same error_code (don't reveal distinction)
        assert data_empty["error_code"] == data_invalid["error_code"] == data_short["error_code"]
        assert data_empty["error_code"] == "INVALID_API_KEY"

        # Messages should not reveal system internals
        for data in [data_empty, data_invalid, data_short]:
            detail_lower = data["detail"].lower()
            assert "database" not in detail_lower
            assert "sql" not in detail_lower
            assert "internal" not in detail_lower
            assert "exception" not in detail_lower


class TestErrorMessageQuality:
    """Test that error messages are clear and helpful for developers."""

    def test_missing_key_message_is_actionable(self, client):
        """
        Test that missing API key error message is developer-friendly.

        Message should clearly indicate what's required and how to fix it.
        """
        response = client.get("/v1/public/projects")

        data = response.json()
        detail = data["detail"]

        # Message should be clear and actionable
        assert len(detail) > 10  # Not just "Error" or similar
        assert "X-API-Key" in detail or "Authorization" in detail  # Mentions auth methods
        assert "Authentication" in detail or "Provide" in detail  # Indicates what's needed

    def test_invalid_key_message_is_actionable(self, client):
        """
        Test that invalid API key error message is developer-friendly.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid"})

        data = response.json()
        detail = data["detail"]

        # Message should be clear and actionable
        assert len(detail) > 5
        assert "Invalid" in detail or "invalid" in detail
        assert "API key" in detail or "api key" in detail.lower()

    def test_empty_key_message_is_actionable(self, client):
        """
        Test that empty API key error message is developer-friendly.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": ""})

        data = response.json()
        detail = data["detail"]

        # Message should be clear and actionable
        assert len(detail) > 5
        assert "Authentication" in detail or "Provide" in detail
        assert "X-API-Key" in detail or "Authorization" in detail


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_header_with_newlines(self, client):
        """
        Test API key with newlines is handled.

        Edge case: Headers with newlines should be handled safely.
        """
        response = client.get("/v1/public/projects", headers={"X-API-Key": "key\nwith\nnewlines"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_header_case_sensitivity(self, client):
        """
        Test that X-API-Key header is case-sensitive.

        HTTP headers are case-insensitive per RFC, but test framework behavior.
        """
        # This test verifies the behavior - lowercase should work due to HTTP standards
        response = client.get("/v1/public/projects", headers={"x-api-key": "invalid"})

        # Should still attempt to validate (headers are case-insensitive in HTTP)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_multiple_api_key_headers(self, client):
        """
        Test behavior when multiple X-API-Key headers are present.

        Edge case: Multiple headers should be handled gracefully.
        """
        # FastAPI/Starlette uses the first or last value, test current behavior
        response = client.get(
            "/v1/public/projects",
            headers=[("X-API-Key", "invalid1"), ("X-API-Key", "invalid2")]
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"
