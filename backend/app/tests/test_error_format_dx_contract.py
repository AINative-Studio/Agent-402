"""
Comprehensive test suite for Issue #42: Error Format DX Contract.

Tests that ALL API errors return consistent { detail, error_code } format.

Issue #42 Acceptance Criteria:
- All API errors return JSON with detail and error_code fields
- detail is human-readable error message
- error_code is UPPER_SNAKE_CASE machine-readable code
- 4xx and 5xx errors follow this format
- Tests verify error format across all endpoints
- Error codes are documented
- Test coverage >= 80%

Reference:
- backend/app/core/errors.py - Custom error classes
- backend/app/core/middleware.py - Error handling middleware
- backend/app/schemas/errors.py - Error response schemas
- PRD Section 10: DX Contract Section 7 (Error Semantics)
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.core.errors import (
    APIError,
    InvalidAPIKeyError,
    ProjectNotFoundError,
    UnauthorizedError,
    ProjectLimitExceededError,
    InvalidTierError,
    InvalidTokenError,
    TokenExpiredAPIError,
    AgentNotFoundError,
    DuplicateAgentDIDError,
    TableAlreadyExistsError,
    TableNotFoundError,
    SchemaValidationError,
    ImmutableRecordError,
    MissingRowDataError,
    InvalidFieldNameError,
    InvalidTimestampError,
    VectorAlreadyExistsError,
    InvalidNamespaceError,
    InvalidMetadataFilterError,
    PathNotFoundError,
    ResourceNotFoundError,
    ModelNotFoundError,
    VectorNotFoundError,
    format_error_response,
)
from app.schemas.errors import ErrorResponse, ErrorCodes


class TestAPIErrorBaseClass:
    """Test the base APIError class for consistent error format."""

    def test_api_error_has_detail_and_error_code(self):
        """Test that APIError base class includes detail and error_code."""
        error = APIError(
            status_code=400,
            error_code="TEST_ERROR",
            detail="Test error message"
        )

        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
        assert error.detail == "Test error message"

    def test_api_error_detail_never_empty(self):
        """Test that APIError detail is never empty."""
        error = APIError(status_code=400, error_code="TEST", detail="")
        assert error.detail == "An error occurred"

    def test_api_error_detail_never_none(self):
        """Test that APIError detail is never None."""
        error = APIError(status_code=400, error_code="TEST", detail=None)
        assert error.detail == "An error occurred"

    def test_api_error_code_never_empty(self):
        """Test that APIError error_code is never empty."""
        error = APIError(status_code=400, error_code="", detail="Test")
        assert error.error_code == "ERROR"

    def test_api_error_code_never_none(self):
        """Test that APIError error_code is never None."""
        error = APIError(status_code=400, error_code=None, detail="Test")
        assert error.error_code == "ERROR"


class TestInvalidAPIKeyError:
    """Test InvalidAPIKeyError format and behavior."""

    def test_invalid_api_key_error_format(self):
        """Test InvalidAPIKeyError has correct format."""
        error = InvalidAPIKeyError()

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "INVALID_API_KEY"
        assert error.detail == "Invalid or missing API key"

    def test_invalid_api_key_error_custom_detail(self):
        """Test InvalidAPIKeyError with custom detail."""
        error = InvalidAPIKeyError(detail="API key has expired")
        assert error.error_code == "INVALID_API_KEY"
        assert error.detail == "API key has expired"

    def test_invalid_api_key_error_empty_detail(self):
        """Test InvalidAPIKeyError handles empty detail."""
        error = InvalidAPIKeyError(detail="")
        assert error.detail == "Invalid or missing API key"


class TestProjectNotFoundError:
    """Test ProjectNotFoundError format and behavior."""

    def test_project_not_found_error_format(self):
        """Test ProjectNotFoundError has correct format."""
        error = ProjectNotFoundError(project_id="test_project_123")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "PROJECT_NOT_FOUND"
        assert "test_project_123" in error.detail

    def test_project_not_found_error_empty_id(self):
        """Test ProjectNotFoundError handles empty project_id."""
        error = ProjectNotFoundError(project_id="")
        assert error.detail == "Project not found"


class TestUnauthorizedError:
    """Test UnauthorizedError format and behavior."""

    def test_unauthorized_error_format(self):
        """Test UnauthorizedError has correct format."""
        error = UnauthorizedError()

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.error_code == "UNAUTHORIZED"
        assert error.detail == "Not authorized to access this resource"

    def test_unauthorized_error_custom_detail(self):
        """Test UnauthorizedError with custom detail."""
        error = UnauthorizedError(detail="You cannot delete this project")
        assert error.error_code == "UNAUTHORIZED"
        assert error.detail == "You cannot delete this project"


class TestProjectLimitExceededError:
    """Test ProjectLimitExceededError format and behavior."""

    def test_project_limit_exceeded_error_format(self):
        """Test ProjectLimitExceededError has correct format."""
        error = ProjectLimitExceededError(current_count=5, limit=5)

        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.error_code == "PROJECT_LIMIT_EXCEEDED"
        assert "5/5" in error.detail

    def test_project_limit_exceeded_error_with_tier(self):
        """Test ProjectLimitExceededError includes tier info."""
        error = ProjectLimitExceededError(current_count=10, limit=10, tier="free")
        assert "free" in error.detail
        assert "10/10" in error.detail


class TestInvalidTierError:
    """Test InvalidTierError format and behavior."""

    def test_invalid_tier_error_format(self):
        """Test InvalidTierError has correct format."""
        error = InvalidTierError(tier="premium", valid_tiers=["free", "pro"])

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "INVALID_TIER"
        assert "premium" in error.detail
        assert "free" in error.detail
        assert "pro" in error.detail


class TestTokenErrors:
    """Test JWT token error formats."""

    def test_invalid_token_error_format(self):
        """Test InvalidTokenError has correct format."""
        error = InvalidTokenError()

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "INVALID_TOKEN"
        assert error.detail == "Invalid JWT token"

    def test_token_expired_error_format(self):
        """Test TokenExpiredAPIError has correct format."""
        error = TokenExpiredAPIError()

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "TOKEN_EXPIRED"
        assert error.detail == "JWT token has expired"


class TestAgentErrors:
    """Test agent-related error formats."""

    def test_agent_not_found_error_format(self):
        """Test AgentNotFoundError has correct format."""
        error = AgentNotFoundError(agent_id="agent_123")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "AGENT_NOT_FOUND"
        assert "agent_123" in error.detail

    def test_duplicate_agent_did_error_format(self):
        """Test DuplicateAgentDIDError has correct format."""
        error = DuplicateAgentDIDError(did="did:ethr:0x123", project_id="project_456")

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.error_code == "DUPLICATE_AGENT_DID"
        assert "did:ethr:0x123" in error.detail
        assert "project_456" in error.detail


class TestTableErrors:
    """Test table-related error formats."""

    def test_table_already_exists_error_format(self):
        """Test TableAlreadyExistsError has correct format."""
        error = TableAlreadyExistsError(table_name="users", project_id="project_123")

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.error_code == "TABLE_ALREADY_EXISTS"
        assert "users" in error.detail
        assert "project_123" in error.detail

    def test_table_not_found_error_format(self):
        """Test TableNotFoundError has correct format."""
        error = TableNotFoundError(table_id="table_xyz")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "TABLE_NOT_FOUND"
        assert "table_xyz" in error.detail

    def test_schema_validation_error_format(self):
        """Test SchemaValidationError has correct format."""
        error = SchemaValidationError()

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "SCHEMA_VALIDATION_ERROR"
        assert "schema" in error.detail.lower()

    def test_schema_validation_error_with_errors(self):
        """Test SchemaValidationError includes validation_errors."""
        validation_errors = [{"field": "email", "msg": "Invalid format"}]
        error = SchemaValidationError(
            detail="Email validation failed",
            validation_errors=validation_errors
        )

        assert error.error_code == "SCHEMA_VALIDATION_ERROR"
        assert error.validation_errors == validation_errors


class TestImmutableRecordError:
    """Test ImmutableRecordError format and behavior."""

    def test_immutable_record_error_format(self):
        """Test ImmutableRecordError has correct format."""
        error = ImmutableRecordError(table_name="agents", operation="update")

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.error_code == "IMMUTABLE_RECORD"
        assert "agents" in error.detail
        assert "update" in error.detail
        assert error.table_name == "agents"
        assert error.operation == "update"

    def test_immutable_record_error_custom_detail(self):
        """Test ImmutableRecordError with custom detail."""
        error = ImmutableRecordError(
            table_name="compliance_events",
            operation="delete",
            detail="Cannot delete audit trail records"
        )

        assert error.error_code == "IMMUTABLE_RECORD"
        assert error.detail == "Cannot delete audit trail records"


class TestRowDataErrors:
    """Test row data validation error formats."""

    def test_missing_row_data_error_format(self):
        """Test MissingRowDataError has correct format."""
        error = MissingRowDataError()

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "MISSING_ROW_DATA"
        assert "row_data" in error.detail

    def test_invalid_field_name_error_format(self):
        """Test InvalidFieldNameError has correct format."""
        error = InvalidFieldNameError(field_name="data")

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "INVALID_FIELD_NAME"
        assert "data" in error.detail
        assert "row_data" in error.detail
        assert error.field_name == "data"


class TestTimestampError:
    """Test timestamp validation error format."""

    def test_invalid_timestamp_error_format(self):
        """Test InvalidTimestampError has correct format."""
        error = InvalidTimestampError()

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "INVALID_TIMESTAMP"
        assert "ISO8601" in error.detail or "RFC 3339" in error.detail

    def test_invalid_timestamp_error_custom_detail(self):
        """Test InvalidTimestampError with custom detail."""
        error = InvalidTimestampError(detail="Timestamp '2026-13-45' is invalid")

        assert error.error_code == "INVALID_TIMESTAMP"
        assert "2026-13-45" in error.detail


class TestVectorErrors:
    """Test vector-related error formats."""

    def test_vector_already_exists_error_format(self):
        """Test VectorAlreadyExistsError has correct format."""
        error = VectorAlreadyExistsError(vector_id="vec_123", namespace="agents")

        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.error_code == "VECTOR_ALREADY_EXISTS"
        assert "vec_123" in error.detail
        assert "agents" in error.detail
        assert error.vector_id == "vec_123"
        assert error.namespace == "agents"

    def test_vector_not_found_error_format(self):
        """Test VectorNotFoundError has correct format."""
        error = VectorNotFoundError(vector_id="vec_xyz", namespace="default")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "VECTOR_NOT_FOUND"
        assert "vec_xyz" in error.detail
        assert error.vector_id == "vec_xyz"

    def test_invalid_namespace_error_format(self):
        """Test InvalidNamespaceError has correct format."""
        error = InvalidNamespaceError()

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "INVALID_NAMESPACE"
        assert "namespace" in error.detail.lower()

    def test_invalid_metadata_filter_error_format(self):
        """Test InvalidMetadataFilterError has correct format."""
        error = InvalidMetadataFilterError()

        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "INVALID_METADATA_FILTER"
        assert "metadata" in error.detail.lower()


class TestPathVsResourceErrors:
    """Test PATH_NOT_FOUND vs RESOURCE_NOT_FOUND distinction."""

    def test_path_not_found_error_format(self):
        """Test PathNotFoundError has correct format."""
        error = PathNotFoundError(path="/v1/public/invalid_endpoint")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "PATH_NOT_FOUND"
        assert "/v1/public/invalid_endpoint" in error.detail
        assert error.path == "/v1/public/invalid_endpoint"

    def test_resource_not_found_error_format(self):
        """Test ResourceNotFoundError has correct format."""
        error = ResourceNotFoundError(resource_type="Vector", resource_id="vec_123")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert "Vector" in error.detail
        assert "vec_123" in error.detail
        assert error.resource_type == "Vector"
        assert error.resource_id == "vec_123"

    def test_model_not_found_error_format(self):
        """Test ModelNotFoundError has correct format."""
        error = ModelNotFoundError(
            model_name="gpt-5",
            available_models=["text-embedding-ada-002"]
        )

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "MODEL_NOT_FOUND"
        assert "gpt-5" in error.detail
        assert "text-embedding-ada-002" in error.detail




class TestFormatErrorResponse:
    """Test the format_error_response utility function."""

    def test_format_error_response_basic(self):
        """Test format_error_response returns correct structure."""
        result = format_error_response(error_code="TEST_ERROR", detail="Test error message")

        assert isinstance(result, dict)
        assert "detail" in result
        assert "error_code" in result
        assert result["detail"] == "Test error message"
        assert result["error_code"] == "TEST_ERROR"

    def test_format_error_response_empty_detail(self):
        """Test format_error_response handles empty detail."""
        result = format_error_response(error_code="TEST_ERROR", detail="")
        assert result["detail"] == "An error occurred"

    def test_format_error_response_empty_error_code(self):
        """Test format_error_response handles empty error_code."""
        result = format_error_response(error_code="", detail="Test error")
        assert result["error_code"] == "ERROR"


class TestErrorResponseSchema:
    """Test ErrorResponse Pydantic schema."""

    def test_error_response_schema_valid(self):
        """Test ErrorResponse schema validates correct data."""
        data = {"detail": "Test error message", "error_code": "TEST_ERROR"}
        error_response = ErrorResponse(**data)

        assert error_response.detail == "Test error message"
        assert error_response.error_code == "TEST_ERROR"

    def test_error_response_schema_requires_detail(self):
        """Test ErrorResponse schema requires detail field."""
        data = {"error_code": "TEST_ERROR"}

        with pytest.raises(Exception):
            ErrorResponse(**data)

    def test_error_response_schema_requires_error_code(self):
        """Test ErrorResponse schema requires error_code field."""
        data = {"detail": "Test error"}

        with pytest.raises(Exception):
            ErrorResponse(**data)

    def test_error_response_schema_validates_error_code_pattern(self):
        """Test ErrorResponse schema validates error_code pattern."""
        valid_data = {"detail": "Test error", "error_code": "VALID_ERROR_CODE"}
        ErrorResponse(**valid_data)

        invalid_data = {"detail": "Test error", "error_code": "invalid_code"}
        with pytest.raises(Exception):
            ErrorResponse(**invalid_data)


class TestErrorCodesClass:
    """Test ErrorCodes class constants."""

    def test_error_codes_are_uppercase(self):
        """Test that all error codes are UPPER_SNAKE_CASE."""
        error_codes = [
            ErrorCodes.INVALID_API_KEY,
            ErrorCodes.PROJECT_NOT_FOUND,
            ErrorCodes.VALIDATION_ERROR,
            ErrorCodes.INTERNAL_SERVER_ERROR,
        ]

        for code in error_codes:
            assert code == code.upper()
            assert " " not in code
            assert "-" not in code

    def test_all_expected_error_codes_exist(self):
        """Test that all expected error codes are defined."""
        expected_codes = [
            "INVALID_API_KEY", "INVALID_TOKEN", "TOKEN_EXPIRED", "UNAUTHORIZED",
            "FORBIDDEN", "IMMUTABLE_RECORD", "NOT_FOUND", "PATH_NOT_FOUND",
            "RESOURCE_NOT_FOUND", "PROJECT_NOT_FOUND", "AGENT_NOT_FOUND",
            "TABLE_NOT_FOUND", "VECTOR_NOT_FOUND", "MODEL_NOT_FOUND",
            "BAD_REQUEST", "VALIDATION_ERROR", "INVALID_TIER", "INVALID_NAMESPACE",
            "INVALID_METADATA_FILTER", "INVALID_TIMESTAMP", "MISSING_ROW_DATA",
            "INVALID_FIELD_NAME", "SCHEMA_VALIDATION_ERROR", "DUPLICATE_AGENT_DID",
            "TABLE_ALREADY_EXISTS", "VECTOR_ALREADY_EXISTS", "PROJECT_LIMIT_EXCEEDED",
            "RATE_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR", "SERVICE_UNAVAILABLE",
            "BAD_GATEWAY",
        ]

        for code in expected_codes:
            assert hasattr(ErrorCodes, code)


class TestErrorIntegrationWithAPI:
    """Test error format integration with actual API endpoints."""

    def test_missing_api_key_returns_correct_format(self, client):
        """Test that missing API key returns correct error format."""
        response = client.get("/v1/public/projects")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0

    def test_invalid_api_key_returns_correct_format(self, client):
        """Test that invalid API key returns correct error format."""
        response = client.get("/v1/public/projects", headers={"X-API-Key": "invalid_key_xyz"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        assert data["error_code"] == "INVALID_API_KEY"
        assert "detail" in data

    def test_path_not_found_returns_correct_format(self, client, auth_headers_user1):
        """Test that invalid path returns PATH_NOT_FOUND format."""
        response = client.get("/v1/public/nonexistent_endpoint_xyz", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert data["error_code"] == "PATH_NOT_FOUND"
        assert "detail" in data
        assert "path" in data["detail"].lower()

    def test_resource_not_found_returns_correct_format(self, client, auth_headers_user1):
        """Test that missing resource returns correct error format."""
        response = client.get("/v1/public/nonexistent_project_123/agents", headers=auth_headers_user1)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] in ["PROJECT_NOT_FOUND", "RESOURCE_NOT_FOUND"]

    def test_validation_error_returns_correct_format(self, client, auth_headers_user1):
        """Test that validation errors return correct format."""
        response = client.get("/v1/public/projects?limit=invalid_value", headers=auth_headers_user1)

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()

            assert "detail" in data
            assert "error_code" in data
            assert data["error_code"] == "VALIDATION_ERROR"


class TestErrorCoverage:
    """Tests to improve coverage of error handling code."""

    def test_all_custom_errors_instantiate_correctly(self):
        """Test that all custom error classes can be instantiated."""
        errors = [
            InvalidAPIKeyError(),
            ProjectNotFoundError("proj_123"),
            UnauthorizedError(),
            ProjectLimitExceededError(5, 5),
            InvalidTierError("premium", ["free", "pro"]),
            InvalidTokenError(),
            TokenExpiredAPIError(),
            AgentNotFoundError("agent_123"),
            DuplicateAgentDIDError("did:ethr:0x123", "proj_456"),
            TableAlreadyExistsError("users", "proj_123"),
            TableNotFoundError("table_xyz"),
            SchemaValidationError(),
            ImmutableRecordError("agents", "update"),
            MissingRowDataError(),
            InvalidFieldNameError("data"),
            InvalidTimestampError(),
            VectorAlreadyExistsError("vec_123"),
            InvalidNamespaceError(),
            InvalidMetadataFilterError(),
            PathNotFoundError("/invalid"),
            ResourceNotFoundError("Vector", "vec_123"),
            ModelNotFoundError("gpt-5"),
            VectorNotFoundError("vec_xyz"),
        ]

        for error in errors:
            assert hasattr(error, "detail")
            assert hasattr(error, "error_code")
            assert hasattr(error, "status_code")
            assert isinstance(error.detail, str)
            assert isinstance(error.error_code, str)
            assert isinstance(error.status_code, int)
            assert len(error.detail) > 0
            assert len(error.error_code) > 0
            assert error.status_code >= 400


class TestErrorDeterminism:
    """Test that errors are deterministic and replayable."""

    def test_same_error_same_code(self):
        """Test that the same error always produces the same error_code."""
        errors = [InvalidAPIKeyError(), InvalidAPIKeyError(), InvalidAPIKeyError()]
        error_codes = [e.error_code for e in errors]
        assert len(set(error_codes)) == 1

    def test_same_error_same_detail(self):
        """Test that the same error produces consistent detail."""
        errors = [ProjectNotFoundError("proj_123"), ProjectNotFoundError("proj_123")]
        details = [e.detail for e in errors]
        assert len(set(details)) == 1

    def test_format_error_response_deterministic(self):
        """Test that format_error_response is deterministic."""
        results = [
            format_error_response("TEST_ERROR", "Test message"),
            format_error_response("TEST_ERROR", "Test message"),
            format_error_response("TEST_ERROR", "Test message"),
        ]

        assert all(r == results[0] for r in results)
