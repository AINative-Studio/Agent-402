"""
Standardized error handling middleware for ZeroDB API.

Implements DX Contract Section 7 (Error Semantics):
- All errors return { detail, error_code }
- Validation errors use HTTP 422
- Error codes are stable and documented

This middleware ensures that ALL errors across the API include a detail field,
regardless of their source (FastAPI exceptions, Pydantic validation, custom errors,
or unexpected exceptions).

Epic 2, Issue 3: As a developer, all errors include a detail field.
Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND 404 errors.

404 Error Distinction:
- PATH_NOT_FOUND: The API endpoint/route doesn't exist (typo in URL)
- RESOURCE_NOT_FOUND: The endpoint exists but the resource doesn't
- Specific resource errors: PROJECT_NOT_FOUND, AGENT_NOT_FOUND, TABLE_NOT_FOUND

Reference: backend/app/schemas/errors.py for error response schemas and error codes.
"""
from typing import Union, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import ValidationError
import logging
from app.core.exceptions import ZeroDBException

# Configure logging
logger = logging.getLogger(__name__)

# Default error messages for various scenarios
DEFAULT_ERROR_DETAIL = "An error occurred"
DEFAULT_VALIDATION_ERROR_DETAIL = "Validation error: Invalid request data"
DEFAULT_INTERNAL_ERROR_DETAIL = "An unexpected error occurred. Please try again later."


def format_error_response(
    error_code: str,
    detail: str,
    validation_errors: Union[list, None] = None
) -> Dict[str, Any]:
    """
    Format error response per DX Contract.

    All errors MUST return:
    - detail: Human-readable error message (required, never empty)
    - error_code: Machine-readable error code (required, UPPER_SNAKE_CASE)

    Per Epic 2, Issue 3: As a developer, all errors include a detail field.
    Per Epic 9, Issue 42: All errors return { detail, error_code }.

    Args:
        error_code: Machine-readable error code (UPPER_SNAKE_CASE)
        detail: Human-readable error message
        validation_errors: Optional list of validation error details

    Returns:
        Dictionary with standardized error format: { detail, error_code }
    """
    # Ensure detail is never empty or None (required by DX Contract)
    if not detail or not str(detail).strip():
        detail = DEFAULT_ERROR_DETAIL

    # Ensure error_code is never empty or None
    if not error_code or not str(error_code).strip():
        error_code = "ERROR"

    response: Dict[str, Any] = {
        "detail": str(detail),
        "error_code": str(error_code)
    }

    # Include validation errors if present (for 422 responses)
    if validation_errors:
        response["validation_errors"] = validation_errors

    return response


async def zerodb_exception_handler(request: Request, exc: ZeroDBException) -> JSONResponse:
    """
    Handle custom ZeroDB exceptions.

    These exceptions already have detail and error_code fields,
    so we just format them consistently.

    Per Epic 2, Issue 3: As a developer, all errors include a detail field.

    Args:
        request: FastAPI request object
        exc: ZeroDBException instance

    Returns:
        JSONResponse with standardized error format: { detail, error_code }
    """
    # Ensure detail is never empty (defensive programming)
    detail = exc.detail if exc.detail else DEFAULT_ERROR_DETAIL
    error_code = exc.error_code if exc.error_code else "ERROR"

    logger.warning(
        f"ZeroDB exception: {error_code} - {detail}",
        extra={
            "error_code": error_code,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            detail=detail,
            error_code=error_code
        ),
        headers=exc.headers
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException with standardized format.

    Ensures all HTTPException errors include a detail field.
    If the exception has an error_code attribute, use it; otherwise derive one.

    Per Epic 2, Issue 3: As a developer, all errors include a detail field.
    Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND.

    404 Error Distinction:
    - PATH_NOT_FOUND: FastAPI returns 404 for unknown routes (detail="Not Found")
    - RESOURCE_NOT_FOUND: Custom exceptions return 404 for missing resources
      (with specific error_code like PROJECT_NOT_FOUND, AGENT_NOT_FOUND, etc.)

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        JSONResponse with standardized error format: { detail, error_code }
    """
    # Extract error_code if available (from custom exceptions)
    error_code = getattr(exc, 'error_code', None)

    # Ensure detail is always a non-empty string
    detail = str(exc.detail) if exc.detail else DEFAULT_ERROR_DETAIL

    # Epic 9 Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
    # FastAPI returns 404 with detail="Not Found" for unknown routes
    # Custom resource-not-found exceptions have their own error_code attribute
    if not error_code:
        if exc.status_code == 404 and _is_route_not_found(exc):
            # This is FastAPI's default 404 for unknown routes
            error_code = "PATH_NOT_FOUND"
            detail = (
                f"Path '{request.url.path}' not found. "
                f"Check the API documentation for valid endpoints."
            )
        else:
            # Derive error code from status code for other cases
            error_code = _derive_error_code_from_status(exc.status_code)

    logger.warning(
        f"HTTP exception: {error_code} - {detail}",
        extra={
            "error_code": error_code,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            detail=detail,
            error_code=error_code
        ),
        headers=exc.headers
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with standardized format.

    Per DX Contract and api-spec.md:
    - Returns HTTP 422 (Unprocessable Entity)
    - Includes detail field with summary message
    - Includes validation_errors array with loc, msg, type
    - Uses VALIDATION_ERROR error code by default

    Args:
        request: FastAPI request object
        exc: RequestValidationError from FastAPI/Pydantic

    Returns:
        JSONResponse with standardized error format
    """
    errors = exc.errors()

    # Format validation errors as per DX Contract
    validation_errors = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", "")
        }
        for err in errors
    ]

    # Create a human-readable detail message
    # Use the first error for the summary
    # Per Epic 2, Issue 3: All errors include a detail field
    if errors:
        first_error = errors[0]
        field_name = first_error.get("loc", ["unknown"])[-1]
        error_msg = first_error.get("msg", "Invalid input")
        detail = f"Validation error on field '{field_name}': {error_msg}"
    else:
        detail = DEFAULT_VALIDATION_ERROR_DETAIL

    logger.warning(
        f"Validation error: {detail}",
        extra={
            "error_code": "VALIDATION_ERROR",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "path": request.url.path,
            "validation_errors": validation_errors
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            detail=detail,
            error_code="VALIDATION_ERROR",
            validation_errors=validation_errors
        )
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with standardized format.

    This is the catch-all handler for any unhandled exceptions.
    Always includes a detail field per DX Contract.

    Per Epic 2, Issue 3: As a developer, all errors include a detail field.

    Args:
        request: FastAPI request object
        exc: Any unhandled exception

    Returns:
        JSONResponse with standardized error format (500)
    """
    # Log the full exception for debugging
    logger.error(
        f"Internal server error: {str(exc)}",
        exc_info=True,
        extra={
            "error_code": "INTERNAL_SERVER_ERROR",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "path": request.url.path,
            "exception_type": type(exc).__name__
        }
    )

    # Don't expose internal error details in production
    # Always provide a generic but helpful message with detail field
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            detail=DEFAULT_INTERNAL_ERROR_DETAIL,
            error_code="INTERNAL_SERVER_ERROR"
        )
    )


def _derive_error_code_from_status(status_code: int) -> str:
    """
    Derive a reasonable error code from HTTP status code.

    Args:
        status_code: HTTP status code

    Returns:
        String error code
    """
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }

    return error_codes.get(status_code, "HTTP_ERROR")


def _is_route_not_found(exc: HTTPException) -> bool:
    """
    Detect if an HTTPException is FastAPI's default route-not-found error.

    Epic 9 Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND.

    FastAPI returns a 404 HTTPException with detail="Not Found" when a route
    doesn't exist. Custom resource-not-found exceptions typically have:
    - Custom detail messages (e.g., "Project not found: xyz")
    - error_code attribute set

    This function checks for FastAPI's default 404 signature.

    Args:
        exc: HTTPException to check

    Returns:
        True if this is FastAPI's route-not-found error, False otherwise
    """
    # FastAPI's default 404 has detail="Not Found" (exact match)
    # Custom exceptions typically have more specific messages
    if exc.status_code != 404:
        return False

    # Check for FastAPI's default detail message
    # FastAPI uses "Not Found" as the default detail for 404 responses
    detail = str(exc.detail) if exc.detail else ""
    return detail == "Not Found"
