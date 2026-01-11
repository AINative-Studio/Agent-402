# Issue Epic 2 Issue 3: All Errors Include Detail Field

## Summary

**Issue:** As a developer, all errors include a `detail` field. (1 pt)
**PRD Reference:** Section 10 (Replay + explainability)
**DX Contract Reference:** Section 7 (Error Semantics)

This implementation ensures that every error response from the API includes a `detail` field with a human-readable error message, along with an `error_code` field for machine-readable error identification.

## Requirements Implemented

1. **Audit all error responses** - Reviewed all exception handlers and error responses across the codebase
2. **Base error response model** - Created `ErrorResponse` schema that enforces `detail` and `error_code`
3. **Updated exception handlers** in `backend/app/main.py`:
   - All HTTPExceptions include `detail`
   - All validation errors include `detail`
   - All custom exceptions include `detail`
   - Internal server errors include a safe `detail` message
4. **Consistent error response schema** in `backend/app/schemas/errors.py`
5. **Error response format:** `{ "detail": "Human readable message", "error_code": "ERROR_CODE" }`

## Files Modified

### 1. `backend/app/schemas/errors.py` (Created)

New schema file defining the standard error response format:

```python
class ErrorResponse(BaseModel):
    """Base error response schema."""
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")

class ValidationErrorResponse(ErrorResponse):
    """Validation error with additional details."""
    validation_errors: Optional[List[ValidationErrorItem]] = None

class ErrorCodes:
    """Standard error codes used across the API."""
    INVALID_API_KEY = "INVALID_API_KEY"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    # ... and more
```

Key features:
- `ErrorResponse` - Base model with required `detail` and `error_code` fields
- `ValidationErrorResponse` - Extended model for 422 validation errors
- `ErrorCodes` - Class with all standard error codes
- `create_error_response()` - Utility function for creating error responses
- `ERROR_RESPONSES` - Pre-built responses for OpenAPI documentation

### 2. `backend/app/schemas/__init__.py` (Updated)

Added exports for error schemas:
- `ErrorResponse`
- `ValidationErrorResponse`
- `ValidationErrorItem`
- `ErrorCodes`
- `create_error_response`
- `ERROR_RESPONSES`

### 3. `backend/app/core/middleware.py` (Updated)

Enhanced error handling middleware with:
- Default error messages as constants
- Defensive programming to ensure `detail` is never empty
- Updated docstrings referencing Epic 2 Issue 3
- Improved `format_error_response()` function with null checks

Key changes:
```python
# Default error messages for various scenarios
DEFAULT_ERROR_DETAIL = "An error occurred"
DEFAULT_VALIDATION_ERROR_DETAIL = "Validation error: Invalid request data"
DEFAULT_INTERNAL_ERROR_DETAIL = "An unexpected error occurred. Please try again later."

def format_error_response(detail, error_code, validation_errors=None):
    """Format error response per DX Contract."""
    # Ensure detail is never empty or None (required by DX Contract)
    if not detail or not str(detail).strip():
        detail = DEFAULT_ERROR_DETAIL
    # ...
```

### 4. `backend/app/main.py` (Updated)

Updated the API error handler with defensive programming:
```python
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors with consistent format."""
    # Ensure detail and error_code are never empty
    detail = exc.detail if exc.detail else DEFAULT_ERROR_DETAIL
    error_code = exc.error_code if exc.error_code else "ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )
```

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Human readable message explaining what went wrong",
  "error_code": "MACHINE_READABLE_CODE"
}
```

For validation errors (HTTP 422):

```json
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
```

## Exception Handlers Coverage

| Handler | Exception Type | Includes Detail | Error Code |
|---------|---------------|-----------------|------------|
| `zerodb_exception_handler` | ZeroDBException | Yes | From exception |
| `api_error_handler` | APIError | Yes | From exception |
| `validation_exception_handler` | RequestValidationError | Yes | VALIDATION_ERROR |
| `http_exception_handler` | HTTPException | Yes | Derived from status |
| `internal_server_error_handler` | Exception | Yes | INTERNAL_SERVER_ERROR |

## Standard Error Codes

| Error Code | HTTP Status | Description |
|-----------|-------------|-------------|
| INVALID_API_KEY | 401 | Invalid or missing API key |
| INVALID_TOKEN | 401 | Invalid JWT token |
| TOKEN_EXPIRED | 401 | JWT token has expired |
| UNAUTHORIZED | 403 | Not authorized to access resource |
| FORBIDDEN | 403 | Access forbidden |
| IMMUTABLE_RECORD | 403 | Cannot modify append-only record |
| NOT_FOUND | 404 | Resource not found |
| PROJECT_NOT_FOUND | 404 | Project not found |
| AGENT_NOT_FOUND | 404 | Agent not found |
| RUN_NOT_FOUND | 404 | Run not found |
| METHOD_NOT_ALLOWED | 405 | HTTP method not allowed |
| CONFLICT | 409 | Resource conflict |
| DUPLICATE_AGENT_DID | 409 | Agent DID already exists |
| VALIDATION_ERROR | 422 | Request validation failed |
| INVALID_TIER | 422 | Invalid tier specified |
| RATE_LIMIT_EXCEEDED | 429 | Rate limit exceeded |
| PROJECT_LIMIT_EXCEEDED | 429 | Project creation limit exceeded |
| INTERNAL_SERVER_ERROR | 500 | Unexpected server error |

## Design Decisions

1. **Defensive Programming**: All exception handlers check for null/empty `detail` values and provide defaults
2. **Constants for Default Messages**: Default error messages are defined as constants for consistency
3. **Schema-Based Validation**: `ErrorResponse` schema uses Pydantic validation to enforce the format
4. **Backward Compatibility**: Existing error classes (`APIError`, `ZeroDBException`) continue to work
5. **OpenAPI Documentation**: `ERROR_RESPONSES` dict provides pre-built responses for API docs

## Testing

Existing tests in `backend/app/tests/test_error_detail_field.py` validate:
- All errors have `detail` field
- Detail is a non-empty string
- Error codes follow UPPER_SNAKE_CASE convention
- Same error produces same detail message (determinism)
- Various error scenarios (auth, validation, not found, etc.)

## References

- PRD Section 10: Replay + Explainability
- DX Contract Section 7: Error Semantics
- `backend/app/schemas/errors.py` - Error response schemas
- `backend/app/core/errors.py` - Custom error classes
- `backend/app/core/middleware.py` - Exception handlers
- `backend/app/tests/test_error_detail_field.py` - Error tests
