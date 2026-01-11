"""
Error response schemas for the ZeroDB Agent Finance API.

Per DX Contract Section 7 (Error Semantics):
- All errors MUST return { detail, error_code }
- detail: Human-readable error message (required)
- error_code: Machine-readable error code (required)

Per PRD Section 10 (Replay + Explainability):
- Error messages should be clear and actionable
- Error codes should be stable and documented

Epic 2, Issue 3: As a developer, all errors include a detail field.
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Base error response schema.

    All API error responses MUST follow this format to ensure consistency
    and compliance with the DX Contract.

    Attributes:
        detail: Human-readable error message explaining what went wrong.
                This should be clear, actionable, and helpful for debugging.
        error_code: Machine-readable error code in UPPER_SNAKE_CASE format.
                    Error codes are stable and documented.

    Example:
        {
            "detail": "Invalid or missing API key",
            "error_code": "INVALID_API_KEY"
        }
    """
    detail: str = Field(
        ...,
        description="Human-readable error message",
        min_length=1,
        examples=["Invalid or missing API key"]
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code in UPPER_SNAKE_CASE",
        pattern=r"^[A-Z][A-Z0-9_]*$",
        examples=["INVALID_API_KEY", "VALIDATION_ERROR", "NOT_FOUND"]
    )


class ValidationErrorItem(BaseModel):
    """
    Individual validation error detail.

    Used within ValidationErrorResponse to provide detailed information
    about each validation failure.

    Attributes:
        loc: Location path of the error (e.g., ["body", "email"])
        msg: Human-readable validation error message
        type: Pydantic validation error type identifier
    """
    loc: List[Any] = Field(
        ...,
        description="Path to the field that failed validation"
    )
    msg: str = Field(
        ...,
        description="Validation error message"
    )
    type: str = Field(
        ...,
        description="Validation error type identifier"
    )


class ValidationErrorResponse(ErrorResponse):
    """
    Validation error response schema (HTTP 422).

    Extends the base ErrorResponse with additional validation details.
    Used for Pydantic validation failures.

    Per DX Contract:
    - Returns HTTP 422 (Unprocessable Entity)
    - Includes summary in detail field
    - Includes validation_errors array with specific field errors

    Attributes:
        detail: Summary of the validation error
        error_code: Always "VALIDATION_ERROR"
        validation_errors: List of individual validation errors with loc, msg, type

    Example:
        {
            "detail": "Validation error on field 'email': Invalid email format",
            "error_code": "VALIDATION_ERROR",
            "validation_errors": [
                {
                    "loc": ["body", "email"],
                    "msg": "Invalid email format",
                    "type": "value_error.email"
                }
            ]
        }
    """
    validation_errors: Optional[List[ValidationErrorItem]] = Field(
        None,
        description="Detailed validation errors for each failing field"
    )


# Standard error codes used across the API
# These are documented and stable per DX Contract
class ErrorCodes:
    """
    Standard error codes used across the API.

    Error codes are stable and documented per DX Contract.
    All error codes follow UPPER_SNAKE_CASE naming convention.
    """

    # Authentication errors (HTTP 401)
    INVALID_API_KEY = "INVALID_API_KEY"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Authorization errors (HTTP 403)
    FORBIDDEN = "FORBIDDEN"
    IMMUTABLE_RECORD = "IMMUTABLE_RECORD"

    # Resource errors (HTTP 404)
    NOT_FOUND = "NOT_FOUND"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"  # Epic 9: Unknown API route/endpoint
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"  # Generic resource not found
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    X402_REQUEST_NOT_FOUND = "X402_REQUEST_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    VECTOR_NOT_FOUND = "VECTOR_NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"

    # Client errors (HTTP 4xx)
    BAD_REQUEST = "BAD_REQUEST"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    DUPLICATE_AGENT_DID = "DUPLICATE_AGENT_DID"
    TABLE_ALREADY_EXISTS = "TABLE_ALREADY_EXISTS"
    VECTOR_ALREADY_EXISTS = "VECTOR_ALREADY_EXISTS"

    # Validation errors (HTTP 422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_TIER = "INVALID_TIER"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    INVALID_MODEL = "INVALID_MODEL"
    INVALID_NAMESPACE = "INVALID_NAMESPACE"
    INVALID_METADATA_FILTER = "INVALID_METADATA_FILTER"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    MISSING_ROW_DATA = "MISSING_ROW_DATA"  # Epic 7 Issue 3: Missing row_data field
    INVALID_FIELD_NAME = "INVALID_FIELD_NAME"  # Epic 7 Issue 3: Wrong field name used
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"  # Epic 7 Issue 2: Schema validation

    # Rate limiting (HTTP 429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    PROJECT_LIMIT_EXCEEDED = "PROJECT_LIMIT_EXCEEDED"

    # Server errors (HTTP 5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_GATEWAY = "BAD_GATEWAY"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"


def create_error_response(detail: str, error_code: str) -> Dict[str, str]:
    """
    Create a standardized error response dictionary.

    This is a utility function for creating error responses that comply
    with the DX Contract error format.

    Args:
        detail: Human-readable error message
        error_code: Machine-readable error code

    Returns:
        Dictionary with detail and error_code fields

    Example:
        >>> create_error_response("Resource not found", "NOT_FOUND")
        {"detail": "Resource not found", "error_code": "NOT_FOUND"}
    """
    # Ensure detail is never empty or None
    if not detail:
        detail = "An error occurred"

    # Ensure error_code is never empty or None
    if not error_code:
        error_code = ErrorCodes.HTTP_ERROR

    return {
        "detail": detail,
        "error_code": error_code
    }


# Export commonly used error response examples for OpenAPI documentation
ERROR_RESPONSES = {
    401: {
        "description": "Authentication failed",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid or missing API key",
                    "error_code": "INVALID_API_KEY"
                }
            }
        }
    },
    403: {
        "description": "Access forbidden",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Not authorized to access this resource",
                    "error_code": "FORBIDDEN"
                }
            }
        }
    },
    404: {
        "description": "Resource not found",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Resource not found",
                    "error_code": "NOT_FOUND"
                }
            }
        }
    },
    422: {
        "description": "Validation error",
        "model": ValidationErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Validation error on field 'email': Invalid email format",
                    "error_code": "VALIDATION_ERROR",
                    "validation_errors": [
                        {
                            "loc": ["body", "email"],
                            "msg": "Invalid email format",
                            "type": "value_error.email"
                        }
                    ]
                }
            }
        }
    },
    429: {
        "description": "Rate limit exceeded",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            }
        }
    },
    500: {
        "description": "Internal server error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "An unexpected error occurred. Please try again later.",
                    "error_code": "INTERNAL_SERVER_ERROR"
                }
            }
        }
    }
}
