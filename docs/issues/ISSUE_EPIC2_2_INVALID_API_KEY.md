# Issue: Epic 2, Issue 2 - Invalid API Key Error Handling

## Summary

As a developer, invalid API keys return `401 INVALID_API_KEY`.

**PRD Reference:** Section 10 (Clear failure modes)
**DX Contract Reference:** Section 2 (Authentication), Section 7 (Error Semantics)
**Story Points:** 2

## Requirements

1. All API key validation failures return HTTP 401
2. Response format: `{ "detail": "...", "error_code": "INVALID_API_KEY" }`
3. Handle these cases consistently:
   - Missing `X-API-Key` header: 401 INVALID_API_KEY with detail "Missing X-API-Key header"
   - Empty API key: 401 INVALID_API_KEY with detail "Empty API key"
   - Invalid/unknown API key: 401 INVALID_API_KEY with detail "Invalid API key"
4. Error responses follow DX Contract format

## Implementation

### Files Modified

#### `backend/app/middleware/api_key_auth.py`

Updated the authentication middleware to return consistent `INVALID_API_KEY` error codes for all API key validation failures:

1. **Missing X-API-Key Header**
   - When no `X-API-Key` header is present and no valid JWT is provided
   - Returns: `{ "detail": "Missing X-API-Key header", "error_code": "INVALID_API_KEY" }`

2. **Empty API Key**
   - When `X-API-Key` header is present but value is empty or whitespace-only
   - Returns: `{ "detail": "Empty API key", "error_code": "INVALID_API_KEY" }`

3. **Invalid/Unknown API Key**
   - When `X-API-Key` header contains a value not matching any valid key
   - Returns: `{ "detail": "Invalid API key", "error_code": "INVALID_API_KEY" }`

### Key Changes

```python
# _authenticate_request method now handles:

# 1. Empty API key check
if api_key is not None:
    if api_key == "" or api_key.strip() == "":
        request.state.auth_error = {
            "error_code": "INVALID_API_KEY",
            "detail": "Empty API key"
        }
        return None

# 2. Invalid API key check
    user_id = settings.get_user_id_from_api_key(api_key)
    if not user_id:
        request.state.auth_error = {
            "error_code": "INVALID_API_KEY",
            "detail": "Invalid API key"
        }
        return None

# 3. dispatch method default fallback for missing header
return JSONResponse(
    status_code=status.HTTP_401_UNAUTHORIZED,
    content=format_error_response(
        error_code="INVALID_API_KEY",
        detail="Missing X-API-Key header"
    )
)
```

#### `backend/app/core/errors.py`

The `InvalidAPIKeyError` class was already present and properly defined:

```python
class InvalidAPIKeyError(APIError):
    """
    Raised when API key is invalid or missing.

    Per DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: INVALID_API_KEY
        - detail: Human-readable message
    """
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_API_KEY",
            detail=detail or "Invalid or missing API key"
        )
```

## Response Format

All API key validation errors follow the DX Contract format:

```json
{
    "detail": "<human-readable message>",
    "error_code": "INVALID_API_KEY"
}
```

### Example Responses

**Missing X-API-Key Header:**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
    "detail": "Missing X-API-Key header",
    "error_code": "INVALID_API_KEY"
}
```

**Empty API Key:**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
    "detail": "Empty API key",
    "error_code": "INVALID_API_KEY"
}
```

**Invalid API Key:**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
    "detail": "Invalid API key",
    "error_code": "INVALID_API_KEY"
}
```

## Security Considerations

- All API key errors use the same `error_code` ("INVALID_API_KEY") to prevent information leakage about valid vs invalid keys
- Error messages are generic enough to not reveal system internals
- Different detail messages help developers diagnose issues without compromising security

## Test Coverage

Existing tests in `backend/app/tests/test_invalid_api_keys.py` cover:

- Missing API key scenarios
- Empty API key scenarios
- Malformed API key scenarios
- Expired API key scenarios (simulated)
- Unauthorized API key scenarios
- DX Contract compliance verification
- Error message quality checks
- Security (no information leakage)

## Dependencies

- `backend/app/core/errors.py` - `format_error_response` function
- `backend/app/core/config.py` - API key validation via `settings.get_user_id_from_api_key()`

## Acceptance Criteria

- [x] Missing X-API-Key header returns 401 with `INVALID_API_KEY` error code
- [x] Empty API key returns 401 with `INVALID_API_KEY` error code
- [x] Invalid/unknown API key returns 401 with `INVALID_API_KEY` error code
- [x] Response format follows DX Contract: `{ "detail": "...", "error_code": "INVALID_API_KEY" }`
- [x] `InvalidAPIKeyError` class exists in `errors.py`
