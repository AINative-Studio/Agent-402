"""
Error Handling and Custom Exceptions
Implements standardized error responses as per DX Contract
"""
from typing import Optional, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from api.models import ErrorResponse, ValidationErrorResponse, ValidationErrorDetail


class TierValidationError(HTTPException):
    """
    Custom exception for invalid tier values.
    Returns HTTP 422 with INVALID_TIER error code.
    """
    def __init__(self, invalid_tier: str, valid_tiers: list[str]):
        detail = f"Invalid tier '{invalid_tier}'. Valid options are: {', '.join(valid_tiers)}"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
        self.error_code = "INVALID_TIER"
        self.invalid_tier = invalid_tier
        self.valid_tiers = valid_tiers


class ProjectLimitExceededError(HTTPException):
    """
    Custom exception for project limit exceeded.
    Returns HTTP 422 with PROJECT_LIMIT_EXCEEDED error code.
    """
    def __init__(self, current_count: int, max_allowed: int):
        detail = f"Project limit exceeded. You have {current_count} projects, maximum allowed is {max_allowed}."
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
        self.error_code = "PROJECT_LIMIT_EXCEEDED"


class InvalidAPIKeyError(HTTPException):
    """
    Custom exception for invalid API keys.
    Returns HTTP 401 with INVALID_API_KEY error code.
    """
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
        self.error_code = "INVALID_API_KEY"


async def tier_validation_exception_handler(request: Request, exc: TierValidationError) -> JSONResponse:
    """
    Handler for TierValidationError.
    Returns standardized error response with INVALID_TIER code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors.
    Checks if the error is tier-related and returns appropriate error code.

    As per PRD §10 and DX Contract:
    - Tier validation errors must return INVALID_TIER
    - All validation errors must include detail field
    - Validation errors should include loc/msg/type structure
    """
    errors = exc.errors()

    # Check if this is a tier validation error
    for error in errors:
        # Check if the error location includes 'tier' field
        if 'tier' in error.get('loc', []):
            # Extract the error message which should contain the tier information
            msg = error.get('msg', '')

            # If it's our custom tier validation error, return INVALID_TIER
            if 'Invalid tier' in msg or 'tier' in error.get('type', ''):
                # Extract valid tiers from message if available
                valid_tiers = ['free', 'starter', 'professional', 'enterprise']

                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": msg if msg else f"Invalid tier value. Valid options are: {', '.join(valid_tiers)}",
                        "error_code": "INVALID_TIER"
                    }
                )

    # For other validation errors, return standard format
    validation_errors = [
        ValidationErrorDetail(
            loc=list(err.get('loc', [])),
            msg=err.get('msg', ''),
            type=err.get('type', '')
        ).model_dump()
        for err in errors
    ]

    # Create a summary detail message
    first_error = errors[0] if errors else {}
    field = first_error.get('loc', ['unknown'])[-1]
    detail_msg = f"Validation error: {first_error.get('msg', 'Invalid input')}"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": detail_msg,
            "error_code": "VALIDATION_ERROR",
            "validation_errors": validation_errors
        }
    )


async def project_limit_exception_handler(request: Request, exc: ProjectLimitExceededError) -> JSONResponse:
    """Handler for ProjectLimitExceededError"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )


async def invalid_api_key_exception_handler(request: Request, exc: InvalidAPIKeyError) -> JSONResponse:
    """Handler for InvalidAPIKeyError"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )


async def generic_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Generic handler for HTTPException.
    Ensures consistent error response format.
    """
    # Check if the exception has an error_code attribute (our custom exceptions)
    error_code = getattr(exc, 'error_code', 'HTTP_ERROR')

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": error_code
        }
    )
