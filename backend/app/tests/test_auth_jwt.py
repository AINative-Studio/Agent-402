"""
Integration tests for JWT authentication endpoints and middleware.
Tests Epic 2 Story 4: JWT authentication as alternative to X-API-Key.
"""
import pytest
import jwt
import time
from fastapi import status
from app.core.config import settings


class TestJWTLoginEndpoint:
    """Test suite for POST /v1/public/auth/login endpoint."""

    def test_login_success_user1(self, client):
        """
        Test successful login with valid API key returns JWT token.
        Epic 2 Story 4: Accept credentials and return JWT token.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user_id" in data

        # Verify token type
        assert data["token_type"] == "bearer"

        # Verify user ID
        assert data["user_id"] == "user_1"

        # Verify expires_in is reasonable (should be 3600 seconds = 1 hour)
        assert data["expires_in"] == 3600

        # Verify access_token is a valid JWT
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_success_user2(self, client):
        """
        Test successful login for second demo user.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_2}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == "user_2"

    def test_login_invalid_api_key(self, client):
        """
        Test login with invalid API key returns 401.
        Epic 2 Story 4: Invalid credentials return 401.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": "invalid_key_xyz"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_login_missing_api_key(self, client):
        """
        Test login with missing API key returns 422 validation error.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_empty_api_key(self, client):
        """
        Test login with empty API key returns validation error.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": ""}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_response_schema(self, client):
        """
        Test login response follows documented schema.
        Per DX Contract: Response shapes are stable.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify exact schema
        expected_fields = {"access_token", "token_type", "expires_in", "user_id"}
        assert set(data.keys()) == expected_fields

        # Verify types
        assert isinstance(data["access_token"], str)
        assert isinstance(data["token_type"], str)
        assert isinstance(data["expires_in"], int)
        assert isinstance(data["user_id"], str)

    def test_jwt_token_payload_structure(self, client):
        """
        Test JWT token contains correct payload structure.
        Epic 2 Story 4: JWT should include user/project context.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Decode JWT without verification to check payload
        token = data["access_token"]
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Verify required claims
        assert "sub" in decoded  # Subject (user_id)
        assert "exp" in decoded  # Expiration
        assert "iat" in decoded  # Issued at
        assert "user_id" in decoded

        # Verify claim values
        assert decoded["sub"] == "user_1"
        assert decoded["user_id"] == "user_1"

        # Verify expiration is in the future
        assert decoded["exp"] > time.time()

        # Verify issued at is in the past or present
        assert decoded["iat"] <= time.time() + 1  # Allow 1 second clock skew

    def test_jwt_token_signature_valid(self, client):
        """
        Test JWT token has valid signature.
        Epic 2 Story 4: JWT tokens must be cryptographically valid.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        token = data["access_token"]

        # Should decode successfully with signature verification
        # This will raise an exception if signature is invalid
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        assert decoded["user_id"] == "user_1"

    def test_login_error_response_format(self, client):
        """
        Test error response follows DX Contract format.
        DX Contract: All errors return { detail, error_code }.
        """
        response = client.post(
            "/v1/public/auth/login",
            json={"api_key": "invalid_key"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)


class TestJWTAuthentication:
    """Test suite for JWT-based authentication in protected endpoints."""

    def test_access_protected_endpoint_with_jwt(self, client):
        """
        Test accessing protected endpoint with JWT token.
        Epic 2 Story 4: JWT should be usable as alternative to X-API-Key.
        """
        # First, get JWT token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]

        # Use JWT to access protected endpoint
        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "projects" in data
        assert "total" in data

    def test_jwt_and_api_key_return_same_results(self, client, auth_headers_user1):
        """
        Test that JWT and X-API-Key authentication return identical results.
        Epic 2 Story 4: Support both X-API-Key and Bearer JWT token authentication.
        """
        # Get JWT token
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
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

        # Both should succeed
        assert jwt_response.status_code == status.HTTP_200_OK
        assert api_key_response.status_code == status.HTTP_200_OK

        # Results should be identical
        assert jwt_response.json() == api_key_response.json()

    def test_invalid_jwt_token(self, client):
        """
        Test accessing protected endpoint with invalid JWT token returns 401.
        """
        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"

    def test_expired_jwt_token(self, client):
        """
        Test accessing protected endpoint with expired JWT token returns 401.
        """
        # Create an expired token
        import jwt
        from datetime import datetime, timedelta

        payload = {
            "sub": "user_1",
            "user_id": "user_1",
            "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            "iat": int((datetime.utcnow() - timedelta(hours=2)).timestamp())
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
        data = response.json()
        assert data["error_code"] == "TOKEN_EXPIRED"

    def test_jwt_without_bearer_prefix(self, client):
        """
        Test JWT token without 'Bearer' prefix returns 401.
        """
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )
        token = login_response.json()["access_token"]

        # Send token without 'Bearer' prefix
        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_authorization_header(self, client):
        """
        Test malformed Authorization header returns 401.
        """
        response = client.get(
            "/v1/public/projects",
            headers={"Authorization": "NotBearer token123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_user_isolation(self, client):
        """
        Test that JWT tokens enforce user isolation.
        Different users should see different projects.
        """
        # Login as user 1
        login1 = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )
        token1 = login1.json()["access_token"]

        # Login as user 2
        login2 = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_2}
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

        # Different users should see different projects
        project_ids_1 = {p["id"] for p in data1["projects"]}
        project_ids_2 = {p["id"] for p in data2["projects"]}

        assert len(project_ids_1.intersection(project_ids_2)) == 0

    def test_missing_authorization_header(self, client):
        """
        Test accessing protected endpoint without any authentication returns 401.
        """
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error_code" in data

    def test_both_api_key_and_jwt_provided(self, client, auth_headers_user1):
        """
        Test that when both X-API-Key and JWT are provided, authentication succeeds.
        The middleware should accept either authentication method.
        """
        # Get JWT for user 1
        login_response = client.post(
            "/v1/public/auth/login",
            json={"api_key": settings.demo_api_key_1}
        )
        token = login_response.json()["access_token"]

        # Send request with both auth methods
        headers = {
            "X-API-Key": settings.demo_api_key_1,
            "Authorization": f"Bearer {token}"
        }

        response = client.get("/v1/public/projects", headers=headers)

        # Should succeed
        assert response.status_code == status.HTTP_200_OK
