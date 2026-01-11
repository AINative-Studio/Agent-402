"""
Integration tests for Issue #8: All errors include a detail field.

This test suite verifies that the standardized error handling middleware
ensures ALL error responses include the detail field as required by the
DX Contract.

Test Strategy:
1. Test all custom exception types
2. Test FastAPI validation errors
3. Test unexpected exceptions
4. Test various HTTP error codes

Epic 2, Story 3: As a developer, all errors include a detail field.
DX Contract §7: All errors return { detail, error_code }.
"""
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError


# Create a test FastAPI app with our error handlers
def create_test_app():
    """Create a test FastAPI application with error handlers."""
    from backend.app.core.middleware import (
        http_exception_handler,
        validation_exception_handler,
        internal_server_error_handler
    )
    from backend.app.core.errors import APIError

    app = FastAPI()

    # Register error handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, internal_server_error_handler)

    @app.exception_handler(APIError)
    async def api_error_handler(request, exc: APIError):
        from fastapi.responses import JSONResponse
        from backend.app.core.errors import format_error_response
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc.error_code, exc.detail)
        )

    # Test routes
    @app.get("/test/api-error")
    async def trigger_api_error():
        from backend.app.core.errors import InvalidAPIKeyError
        raise InvalidAPIKeyError("Test API error")

    @app.get("/test/http-exception")
    async def trigger_http_exception():
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/test/validation-error")
    async def trigger_validation_error(item_id: int):
        return {"item_id": item_id}

    @app.get("/test/unexpected-error")
    async def trigger_unexpected_error():
        raise ValueError("Unexpected error for testing")

    @app.post("/test/pydantic-validation")
    async def trigger_pydantic_validation(data: dict):
        class TestModel(BaseModel):
            name: str = Field(..., min_length=1)
            age: int = Field(..., ge=0)

        # This will trigger validation error if data is invalid
        model = TestModel(**data)
        return model

    return app


@pytest.fixture
def test_app():
    """Fixture providing test FastAPI app."""
    return create_test_app()


@pytest.fixture
def test_client(test_app):
    """Fixture providing test client."""
    return TestClient(test_app)


class TestErrorMiddlewareDetailField:
    """Test that error middleware ensures detail field in all responses."""

    def test_api_error_has_detail(self, test_client):
        """Test that custom APIError includes detail field."""
        response = test_client.get("/test/api-error")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "APIError response missing detail field"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

        # MUST have error_code
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_http_exception_has_detail(self, test_client):
        """Test that HTTPException includes detail field."""
        response = test_client.get("/test/http-exception")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "HTTPException response missing detail field"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

        # SHOULD have error_code
        assert "error_code" in data

    def test_validation_error_has_detail(self, test_client):
        """Test that validation errors include detail field."""
        # Send invalid query parameter (string instead of int)
        response = test_client.get("/test/validation-error?item_id=invalid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "Validation error response missing detail field"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

        # SHOULD have error_code
        assert "error_code" in data
        assert data["error_code"] == "VALIDATION_ERROR"

        # MAY have validation_errors array
        # This is helpful but not required by DX Contract

    def test_unexpected_exception_has_detail(self, test_client):
        """Test that unexpected exceptions include detail field."""
        response = test_client.get("/test/unexpected-error")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "500 error response missing detail field"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

        # MUST have error_code
        assert "error_code" in data
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"

    def test_pydantic_validation_has_detail(self, test_client):
        """Test that Pydantic validation errors include detail field."""
        # Send invalid request body
        response = test_client.post("/test/pydantic-validation", json={
            "name": "",  # Too short
            "age": -1    # Negative not allowed
        })

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # MUST have detail field
        assert "detail" in data, "Pydantic validation error missing detail field"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

        # SHOULD have error_code
        assert "error_code" in data

        # MAY have validation_errors for debugging
        if "validation_errors" in data:
            assert isinstance(data["validation_errors"], list)


class TestErrorDetailFieldFormat:
    """Test the format and content of detail field."""

    def test_detail_is_always_string(self, test_client):
        """Test that detail field is always a string, never an array or object."""
        endpoints = [
            "/test/api-error",
            "/test/http-exception",
            "/test/validation-error?item_id=invalid",
            "/test/unexpected-error"
        ]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            data = response.json()

            assert "detail" in data
            assert isinstance(data["detail"], str), \
                f"detail must be string for {endpoint}, got {type(data['detail'])}"

    def test_detail_is_never_empty(self, test_client):
        """Test that detail field is never empty or null."""
        endpoints = [
            "/test/api-error",
            "/test/http-exception",
            "/test/validation-error?item_id=invalid",
            "/test/unexpected-error"
        ]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            data = response.json()

            assert "detail" in data
            assert data["detail"] is not None, f"detail is null for {endpoint}"
            assert len(data["detail"]) > 0, f"detail is empty for {endpoint}"

    def test_detail_is_human_readable(self, test_client):
        """Test that detail field contains human-readable messages."""
        response = test_client.get("/test/api-error")
        data = response.json()

        detail = data["detail"]
        # Should be more than a few characters
        assert len(detail) > 5
        # Should contain meaningful words (not just error codes)
        assert any(c.isalpha() for c in detail), "detail should contain letters"


class TestErrorCodeConsistency:
    """Test error_code field consistency."""

    def test_error_codes_are_uppercase_snake_case(self, test_client):
        """Test that error codes follow UPPER_SNAKE_CASE convention."""
        endpoints = [
            ("/test/api-error", "INVALID_API_KEY"),
            ("/test/validation-error?item_id=invalid", "VALIDATION_ERROR"),
            ("/test/unexpected-error", "INTERNAL_SERVER_ERROR"),
        ]

        for endpoint, expected_code in endpoints:
            response = test_client.get(endpoint)
            data = response.json()

            if "error_code" in data:
                error_code = data["error_code"]
                # Should be uppercase
                assert error_code == error_code.upper(), \
                    f"Error code should be uppercase: {error_code}"
                # Should use underscores, not spaces
                assert " " not in error_code
                # Should match expected
                if expected_code:
                    assert error_code == expected_code

    def test_error_codes_are_stable(self, test_client):
        """Test that same error returns same error code."""
        # Make same request twice
        response1 = test_client.get("/test/api-error")
        response2 = test_client.get("/test/api-error")

        data1 = response1.json()
        data2 = response2.json()

        assert data1.get("error_code") == data2.get("error_code"), \
            "Same error should return same error_code"


class TestDXContractCompliance:
    """Test compliance with DX Contract §7 (Error Semantics)."""

    def test_all_errors_follow_contract_schema(self, test_client):
        """
        Test that all errors follow DX Contract schema.

        DX Contract §7: All errors return { detail, error_code }
        - detail is required
        - error_code is recommended
        """
        error_endpoints = [
            "/test/api-error",
            "/test/http-exception",
            "/test/validation-error?item_id=invalid",
            "/test/unexpected-error"
        ]

        for endpoint in error_endpoints:
            response = test_client.get(endpoint)
            data = response.json()

            # REQUIRED: detail field
            assert "detail" in data, \
                f"Missing detail field for {endpoint} (DX Contract violation)"
            assert isinstance(data["detail"], str)
            assert len(data["detail"]) > 0

            # RECOMMENDED: error_code field
            # We enforce this in our implementation
            assert "error_code" in data, \
                f"Missing error_code field for {endpoint}"
            assert isinstance(data["error_code"], str)
            assert len(data["error_code"]) > 0

    def test_validation_errors_use_422(self, test_client):
        """
        Test that validation errors use HTTP 422.

        DX Contract §7: Validation errors always use HTTP 422.
        """
        response = test_client.get("/test/validation-error?item_id=invalid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            "Validation errors must use HTTP 422 per DX Contract"

        data = response.json()
        assert "detail" in data
        assert data.get("error_code") == "VALIDATION_ERROR"

    def test_error_response_is_deterministic(self, test_client):
        """
        Test that error responses are deterministic.

        Per PRD §10 (Replay + Explainability):
        Same input should produce same error response.
        """
        # Make same request multiple times
        responses = [
            test_client.get("/test/api-error")
            for _ in range(3)
        ]

        # All responses should be identical
        first_data = responses[0].json()
        for response in responses[1:]:
            assert response.json() == first_data, \
                "Same error should produce identical response"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
