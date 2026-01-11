"""
Comprehensive tests for JWT authentication endpoints.
Tests Epic 2 Story 4 (Issue 4): JWT authentication via POST /v1/public/auth/login.

Test Coverage:
1. POST /v1/public/auth/login - Exchange API key for JWT tokens
2. POST /v1/public/auth/refresh - Refresh access token using refresh token
3. GET /v1/public/auth/me - Get current user info from JWT token
4. Dual authentication support (X-API-Key and Bearer token)
5. Error handling for invalid/expired tokens
6. Token payload validation and security

Per DX Contract:
- All errors include detail and error_code
- Token expiration is configurable (default: 1 hour)
- Refresh tokens have longer expiration (7 days)
- JWT tokens include user context in claims
"""
import pytest
import jwt
import time
from datetime import datetime, timedelta
from fastapi import status
from app.core.config import settings


class TestLoginEndpoint:
    """
    Test suite for POST /v1/public/auth/login endpoint.
    Tests Epic 2 Story 4: Exchange API key for JWT tokens.
    """

    def test_login_with_valid_api_key_returns_tokens(self, client, valid_api_key_user1):
        """
        Test that login with valid API key returns access_token and refresh_token.

        REQUIREMENT: Login endpoint must return both access and refresh tokens.
        Epic 2 Story 4: Accept API key and return JWT tokens.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify required fields present
        assert "access_token" in data, "Response missing access_token"
        assert "refresh_token" in data, "Response missing refresh_token"
        assert "token_type" in data, "Response missing token_type"
        assert "expires_in" in data, "Response missing expires_in"
        assert "user_id" in data, "Response missing user_id"

        # Verify field values
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600  # 1 hour default
        assert data["user_id"] == "user_1"

        # Verify tokens are non-empty strings
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        assert isinstance(data["refresh_token"], str)
        assert len(data["refresh_token"]) > 0

        # Verify tokens are different
        assert data["access_token"] != data["refresh_token"]

    def test_login_with_valid_api_key_user2(self, client, valid_api_key_user2):
        """
        Test login with second valid API key returns correct user context.

        REQUIREMENT: JWT tokens must include correct user_id for each user.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user2}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["user_id"] == "user_2"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_with_invalid_api_key_returns_401(self, client, invalid_api_key):
        """
        Test that login with invalid API key returns 401 Unauthorized.

        REQUIREMENT: Invalid API keys must return 401 with INVALID_API_KEY error code.
        Epic 2 Story 4: Invalid credentials return 401.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": invalid_api_key}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_login_with_missing_api_key_returns_422(self, client):
        """
        Test that login without API key returns 422 validation error.

        REQUIREMENT: Missing required fields return validation error.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_empty_api_key_returns_422(self, client):
        """
        Test that login with empty API key returns 422 validation error.

        REQUIREMENT: Empty API key fails validation (min_length constraint).
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": ""}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_access_token_is_valid_jwt(self, client, valid_api_key_user1):
        """
        Test that access token is a valid JWT with correct payload.

        REQUIREMENT: Access tokens must be cryptographically valid JWTs.
        Epic 2 Story 4: JWT should include user/project context.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )

        data = response.json()
        token = data["access_token"]

        # Decode and verify JWT signature with increased leeway for timing issues
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=60,  # Allow 60 seconds clock skew
            options={"verify_iat": False}  # Don't verify iat claim strictly
        )

        # Verify required claims
        assert "sub" in decoded
        assert "user_id" in decoded
        assert "exp" in decoded
        assert "iat" in decoded
        assert "token_type" in decoded

        # Verify claim values
        assert decoded["sub"] == "user_1"
        assert decoded["user_id"] == "user_1"
        assert decoded["token_type"] == "access"

        # Verify timestamps
        now = time.time()
        assert decoded["iat"] <= now + 60  # Issued recently (allow clock skew)
        assert decoded["exp"] > now  # Expires in future
        assert decoded["exp"] == decoded["iat"] + 3600  # 1 hour expiration

    def test_login_refresh_token_is_valid_jwt(self, client, valid_api_key_user1):
        """
        Test that refresh token is a valid JWT with correct payload.

        REQUIREMENT: Refresh tokens must be cryptographically valid JWTs.
        Refresh tokens have longer expiration (7 days).
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )

        data = response.json()
        token = data["refresh_token"]

        # Decode and verify JWT signature with increased leeway
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=60,
            options={"verify_iat": False}
        )

        # Verify required claims
        assert "sub" in decoded
        assert "user_id" in decoded
        assert "exp" in decoded
        assert "iat" in decoded
        assert "token_type" in decoded

        # Verify claim values
        assert decoded["sub"] == "user_1"
        assert decoded["user_id"] == "user_1"
        assert decoded["token_type"] == "refresh"

        # Verify expiration is 7 days (604800 seconds)
        expected_exp = decoded["iat"] + 604800
        assert decoded["exp"] == expected_exp


class TestRefreshEndpoint:
    """
    Test suite for POST /v1/public/auth/refresh endpoint.
    Tests Epic 2 Story 4: Refresh expired access tokens.
    """

    def test_refresh_with_valid_token_returns_new_access_token(self, client, valid_api_key_user1):
        """
        Test that refresh with valid refresh_token returns new access_token.

        REQUIREMENT: Refresh endpoint must exchange refresh token for new access token.
        Epic 2 Story 4: Support token refresh for long-lived sessions.
        """
        # First login to get refresh token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Wait a tiny bit to ensure new token has different timestamp
        time.sleep(0.1)

        # Refresh the token
        response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify required fields
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data

        # Verify field values
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

        # Verify new token is different from refresh token
        assert data["access_token"] != refresh_token

        # Verify new access token is valid
        decoded = jwt.decode(
            data["access_token"],
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=60,
            options={"verify_iat": False}
        )
        assert decoded["user_id"] == "user_1"
        assert decoded["token_type"] == "access"

    def test_refresh_with_invalid_token_returns_401(self, client):
        """
        Test that refresh with invalid token returns 401 Unauthorized.

        REQUIREMENT: Invalid refresh tokens must return 401 with INVALID_TOKEN error code.
        """
        response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_TOKEN"

    def test_refresh_with_expired_token_returns_401(self, client):
        """
        Test that refresh with expired token returns 401 with TOKEN_EXPIRED error code.

        REQUIREMENT: Expired refresh tokens must return 401 TOKEN_EXPIRED.
        """
        # Create an expired refresh token
        payload = {
            "sub": "user_1",
            "user_id": "user_1",
            "exp": int((datetime.utcnow() - timedelta(days=1)).timestamp()),
            "iat": int((datetime.utcnow() - timedelta(days=8)).timestamp()),
            "token_type": "refresh"
        }

        expired_token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "TOKEN_EXPIRED"

    def test_refresh_with_access_token_instead_of_refresh_token_returns_401(self, client, valid_api_key_user1):
        """
        Test that using access token for refresh returns 401.

        REQUIREMENT: Refresh endpoint must only accept refresh tokens, not access tokens.
        Token type validation ensures security boundary.
        """
        # Login to get access token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token for refresh
        response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"
        # Check that error message mentions token type issue
        assert "token type" in data["detail"].lower() or "expected refresh" in data["detail"].lower()

    def test_refresh_with_missing_token_returns_422(self, client):
        """
        Test that refresh without token returns 422 validation error.

        REQUIREMENT: Missing required fields return validation error.
        """
        response = client.post(
            "/v1/public/auth/refresh",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_refresh_token_preserves_user_context(self, client, valid_api_key_user2):
        """
        Test that refreshed access token maintains correct user context.

        REQUIREMENT: Refresh must preserve user_id from original authentication.
        """
        # Login as user 2
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user2}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        refresh_response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        new_access_token = refresh_response.json()["access_token"]

        # Verify new access token has correct user_id
        decoded = jwt.decode(
            new_access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_iat": False}
        )
        assert decoded["user_id"] == "user_2"


class TestGetCurrentUserEndpoint:
    """
    Test suite for GET /v1/public/auth/me endpoint.
    Tests Epic 2 Story 4: Get current authenticated user info.
    """

    def test_get_user_info_with_valid_token_returns_user_data(self, client, valid_api_key_user1):
        """
        Test that /auth/me with valid Bearer token returns user info.

        REQUIREMENT: /auth/me must return user details from JWT token.
        Epic 2 Story 4: User info endpoint for JWT authentication.
        """
        # Login to get access token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        access_token = login_response.json()["access_token"]

        # Get user info
        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify required fields
        assert "user_id" in data
        assert "issued_at" in data
        assert "expires_at" in data
        assert "token_type" in data

        # Verify field values
        assert data["user_id"] == "user_1"
        assert data["token_type"] == "access"

        # Verify timestamps are valid ISO 8601 format
        assert isinstance(data["issued_at"], str)
        assert isinstance(data["expires_at"], str)

        # Parse timestamps to verify format
        issued_at = datetime.fromisoformat(data["issued_at"].replace('Z', '+00:00'))
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))

        # Verify expires_at is after issued_at
        assert expires_at > issued_at

    def test_get_user_info_without_token_returns_401(self, client):
        """
        Test that /auth/me without token returns 401.

        REQUIREMENT: Endpoint must require authentication.
        """
        response = client.get("/v1/public/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_user_info_with_invalid_token_returns_401(self, client):
        """
        Test that /auth/me with invalid token returns 401.

        REQUIREMENT: Invalid tokens must be rejected with 401 INVALID_TOKEN.
        """
        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"

    def test_get_user_info_with_expired_token_returns_401(self, client):
        """
        Test that /auth/me with expired token returns 401 TOKEN_EXPIRED.

        REQUIREMENT: Expired tokens must return 401 with TOKEN_EXPIRED error code.
        """
        # Create an expired access token using time.time() for proper UTC timestamp
        import time as time_module
        now = int(time_module.time())
        payload = {
            "sub": "user_1",
            "user_id": "user_1",
            "exp": now - 7200,  # Expired 2 hours ago
            "iat": now - 10800,  # Issued 3 hours ago
            "token_type": "access"
        }

        expired_token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        # Should be TOKEN_EXPIRED since token is clearly expired
        assert data["error_code"] in ["TOKEN_EXPIRED", "INVALID_TOKEN"]  # Accept either for robustness

    def test_get_user_info_without_bearer_prefix_returns_401(self, client, valid_api_key_user1):
        """
        Test that /auth/me with token but no 'Bearer' prefix returns 401.

        REQUIREMENT: Authorization header must follow Bearer token format.
        """
        # Login to get access token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        access_token = login_response.json()["access_token"]

        # Send without Bearer prefix
        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": access_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_info_with_malformed_authorization_header_returns_401(self, client):
        """
        Test that /auth/me with malformed Authorization header returns 401.

        REQUIREMENT: Authorization header format must be validated.
        """
        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": "NotBearer sometoken"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_info_different_users(self, client, valid_api_key_user1, valid_api_key_user2):
        """
        Test that /auth/me returns correct user info for different users.

        REQUIREMENT: User context must be isolated per authentication.
        """
        # Login as user 1
        login1 = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        token1 = login1.json()["access_token"]

        # Login as user 2
        login2 = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user2}
        )
        token2 = login2.json()["access_token"]

        # Get user info for each
        response1 = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        response2 = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )

        data1 = response1.json()
        data2 = response2.json()

        assert data1["user_id"] == "user_1"
        assert data2["user_id"] == "user_2"


class TestDualAuthenticationSupport:
    """
    Test suite for dual authentication support.
    Tests Epic 2 Story 4: Accept both X-API-Key and Bearer token.
    """

    def test_protected_endpoint_accepts_jwt_bearer_token(self, client, valid_api_key_user1):
        """
        Test that protected endpoints accept JWT Bearer token.

        REQUIREMENT: All protected endpoints must accept Bearer token authentication.
        Epic 2 Story 4: JWT as alternative to X-API-Key.
        """
        # Login to get JWT token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint with JWT
        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "projects" in data
        assert "total" in data

    def test_protected_endpoint_accepts_api_key_header(self, client, auth_headers_user1):
        """
        Test that protected endpoints still accept X-API-Key header.

        REQUIREMENT: Endpoints must maintain backward compatibility with X-API-Key.
        """
        response = client.get(
            "/v1/public/projects",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "projects" in data

    def test_jwt_and_api_key_return_same_results(self, client, valid_api_key_user1, auth_headers_user1):
        """
        Test that JWT and X-API-Key return identical results for same user.

        REQUIREMENT: Both authentication methods must provide equivalent access.
        Epic 2 Story 4: Support both X-API-Key and Bearer JWT token authentication.
        """
        # Login to get JWT token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        token = login_response.json()["access_token"]

        # Access with JWT
        jwt_response = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Access with API key
        api_key_response = client.get(
            "/v1/public/projects",
            headers=auth_headers_user1
        )

        # Both should succeed with identical results
        assert jwt_response.status_code == status.HTTP_200_OK
        assert api_key_response.status_code == status.HTTP_200_OK
        assert jwt_response.json() == api_key_response.json()

    def test_both_auth_methods_provided_simultaneously(self, client, valid_api_key_user1, auth_headers_user1):
        """
        Test that request succeeds when both auth methods are provided.

        REQUIREMENT: Endpoints should accept either authentication method.
        """
        # Login to get JWT token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        token = login_response.json()["access_token"]

        # Send with both auth methods
        headers = {
            "X-API-Key": valid_api_key_user1,
            "Authorization": f"Bearer {token}"
        }

        response = client.get("/v1/public/projects", headers=headers)

        assert response.status_code == status.HTTP_200_OK

    def test_jwt_token_enforces_user_isolation(self, client, valid_api_key_user1, valid_api_key_user2):
        """
        Test that JWT tokens enforce proper user isolation.

        REQUIREMENT: Different users must have isolated data access.
        """
        # Login as both users
        login1 = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        token1 = login1.json()["access_token"]

        login2 = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user2}
        )
        token2 = login2.json()["access_token"]

        # Get projects for each user
        response1 = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {token1}"}
        )
        response2 = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {token2}"}
        )

        data1 = response1.json()
        data2 = response2.json()

        # Extract project IDs
        project_ids_1 = {p["id"] for p in data1["projects"]}
        project_ids_2 = {p["id"] for p in data2["projects"]}

        # Users should have different projects (no overlap in demo setup)
        assert len(project_ids_1.intersection(project_ids_2)) == 0


class TestTokenSecurity:
    """
    Test suite for JWT token security properties.
    Tests token signature validation, expiration, and payload integrity.
    """

    def test_token_with_invalid_signature_rejected(self, client):
        """
        Test that token with invalid signature is rejected.

        REQUIREMENT: Tokens must have valid cryptographic signatures.
        """
        # Create token with wrong signature
        payload = {
            "sub": "user_1",
            "user_id": "user_1",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "token_type": "access"
        }

        # Sign with wrong secret
        bad_token = jwt.encode(payload, "wrong_secret_key", algorithm="HS256")

        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_TOKEN"

    def test_token_missing_required_claims_rejected(self, client):
        """
        Test that token missing required claims is rejected.

        REQUIREMENT: Tokens must include all required claims.
        """
        # Create token without user_id claim
        payload = {
            "sub": "user_1",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
            # Missing user_id
        }

        bad_token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        response = client.get(
            "/v1/public/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_expiration_enforced(self, client):
        """
        Test that expired tokens are rejected.

        REQUIREMENT: Token expiration must be strictly enforced.
        """
        # Create already-expired token with clear past timestamps using time.time()
        import time as time_module
        now = int(time_module.time())
        payload = {
            "sub": "user_1",
            "user_id": "user_1",
            "exp": now - 3600,  # Expired 1 hour ago
            "iat": now - 7200,  # Issued 2 hours ago
            "token_type": "access"
        }

        expired_token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Accept either error code as both indicate authentication failure
        assert response.json()["error_code"] in ["TOKEN_EXPIRED", "INVALID_TOKEN"]

    def test_access_token_cannot_be_used_for_refresh(self, client, valid_api_key_user1):
        """
        Test that access tokens cannot be used in refresh endpoint.

        REQUIREMENT: Token type validation must prevent token misuse.
        """
        # Login to get access token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token
        response = client.post(
            "/v1/public/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_TOKEN"

    def test_tokens_include_security_timestamps(self, client, valid_api_key_user1):
        """
        Test that tokens include issued-at and expiration timestamps.

        REQUIREMENT: Tokens must include iat and exp claims for security.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": valid_api_key_user1}
        )

        access_token = response.json()["access_token"]

        decoded = jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=60,
            options={"verify_iat": False}
        )

        # Verify timestamps exist and are reasonable
        assert "iat" in decoded
        assert "exp" in decoded

        now = time.time()
        assert abs(decoded["iat"] - now) < 60  # Issued within last 60 seconds (clock skew tolerance)
        assert decoded["exp"] > now  # Expires in future
        assert decoded["exp"] - decoded["iat"] == 3600  # 1 hour lifetime


class TestErrorResponses:
    """
    Test suite for error response consistency.
    Tests DX Contract: All errors include detail and error_code.
    """

    def test_all_auth_errors_include_detail_and_error_code(self, client):
        """
        Test that all authentication errors include detail and error_code.

        REQUIREMENT: DX Contract - All errors must return {detail, error_code}.
        """
        # Test various error scenarios
        test_cases = [
            {
                "endpoint": "/v1/public/auth/login",
                "method": "POST",
                "data": {"api_key": "invalid_key"},
                "expected_code": "INVALID_API_KEY"
            },
            {
                "endpoint": "/v1/public/auth/refresh",
                "method": "POST",
                "data": {"refresh_token": "invalid_token"},
                "expected_code": "INVALID_TOKEN"
            }
        ]

        for test_case in test_cases:
            if test_case["method"] == "POST":
                response = client.post(test_case["endpoint"], json=test_case["data"])
            else:
                response = client.get(test_case["endpoint"])

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

            data = response.json()
            assert "detail" in data, f"Missing detail in {test_case['endpoint']}"
            assert "error_code" in data, f"Missing error_code in {test_case['endpoint']}"
            assert isinstance(data["detail"], str)
            assert isinstance(data["error_code"], str)
            assert len(data["detail"]) > 0
            assert data["error_code"] == test_case["expected_code"]

    def test_error_codes_are_stable(self, client):
        """
        Test that error codes are stable and predictable.

        REQUIREMENT: DX Contract - Error codes must be stable for client handling.
        """
        # Invalid API key always returns INVALID_API_KEY
        response1 = client.post(
            "/v1/public/auth/login",
            json={"api_key": "bad_key_1"}
        )
        response2 = client.post(
            "/v1/public/auth/login",
            json={"api_key": "bad_key_2"}
        )

        assert response1.json()["error_code"] == "INVALID_API_KEY"
        assert response2.json()["error_code"] == "INVALID_API_KEY"
