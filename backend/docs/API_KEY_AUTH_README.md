# X-API-Key Authentication Implementation

**Issue:** #6 - As a developer, I can authenticate all public endpoints using X-API-Key
**Epic:** 2, Story 1
**Status:** ✅ Completed

## Overview

All `/v1/public/*` endpoints now require X-API-Key authentication. This implementation ensures secure access control, auditability, and compliance with the DX Contract.

## Quick Start

### Using the API

```bash
# Valid request
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"

# Invalid request (returns 401)
curl -X GET "http://localhost:8000/v1/public/projects"
```

### Demo API Keys

For testing and development, the following API keys are available:

- **User 1:** `demo_key_user1_abc123`
- **User 2:** `demo_key_user2_xyz789`

## Authentication Flow

```
Client Request
     ↓
[APIKeyAuthMiddleware]
     ↓
Check if path starts with /v1/public/
     ↓ Yes
Extract X-API-Key header
     ↓
Validate API key
     ↓
Valid?
     ↓ Yes
Attach user_id to request.state
     ↓
Continue to route handler
     ↓
Return response
```

## Error Responses

All authentication errors follow the DX Contract format:

### Missing API Key

```json
HTTP 401 Unauthorized

{
  "detail": "Missing X-API-Key header",
  "error_code": "INVALID_API_KEY"
}
```

### Invalid API Key

```json
HTTP 401 Unauthorized

{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}
```

## Exempt Endpoints

The following endpoints do NOT require authentication:

- `/` - Root endpoint
- `/health` - Health check
- `/docs` - Swagger UI
- `/redoc` - ReDoc UI
- `/openapi.json` - OpenAPI specification

## Implementation Architecture

### Middleware Design

The authentication middleware (`APIKeyAuthMiddleware`) is a Starlette-based middleware that:

1. **Intercepts Requests:** Checks all incoming requests before they reach route handlers
2. **Path-Based Filtering:** Only validates `/v1/public/*` endpoints
3. **Early Exit:** Returns 401 immediately if authentication fails
4. **State Propagation:** Attaches `user_id` to `request.state` for downstream use
5. **Logging:** Records all authentication attempts for audit trail

### File Structure

```
backend/
├── app/
│   ├── middleware/
│   │   ├── __init__.py              # Package exports
│   │   └── api_key_auth.py          # Main middleware implementation
│   ├── core/
│   │   ├── auth.py                  # Auth helper functions
│   │   ├── config.py                # API key configuration
│   │   ├── errors.py                # Error classes
│   │   └── exceptions.py            # Custom exceptions
│   └── tests/
│       ├── test_api_key_middleware.py  # 20 unit tests
│       └── test_projects_api.py        # 10 integration tests
├── IMPLEMENTATION_SUMMARY_ISSUE_6.md   # Detailed implementation doc
├── API_KEY_AUTH_README.md              # This file
└── test_api_key_smoke.py               # Manual smoke test
```

## Testing

### Unit Tests (20 tests)

```bash
cd backend
python3 -m pytest app/tests/test_api_key_middleware.py -v
```

**Coverage:**
- ✅ Missing API key returns 401
- ✅ Invalid API key returns 401
- ✅ Valid API key allows access
- ✅ Empty/whitespace keys rejected
- ✅ SQL injection attempts blocked
- ✅ Case-insensitive header handling
- ✅ User isolation
- ✅ Concurrent requests
- ✅ Deterministic behavior
- ✅ Exempt endpoints accessible
- ✅ Error format compliance
- ✅ Logging functionality

### Integration Tests (10 tests)

```bash
cd backend
python3 -m pytest app/tests/test_projects_api.py -v
```

**Coverage:**
- ✅ List projects with valid API key
- ✅ User-specific project filtering
- ✅ Missing API key handling
- ✅ Invalid API key handling
- ✅ Response schema validation
- ✅ Deterministic demo data

### Smoke Test (Manual)

```bash
cd backend
# Start server in one terminal
python3 -m uvicorn app.main:app --reload

# Run smoke test in another terminal
python3 test_api_key_smoke.py
```

## Security Considerations

### 1. API Key Validation

- Keys are validated against a configurable mapping
- No information leakage in error messages
- Generic "Invalid API key" response for all failures

### 2. Input Validation

- Empty and whitespace-only keys rejected
- SQL injection attempts caught and rejected
- Very long keys rejected
- Special characters handled safely

### 3. Audit Logging

All authentication attempts are logged with:
- Timestamp
- Request path
- User ID (on success)
- API key prefix (on failure, for debugging)
- Client information

Example log entries:
```
INFO: Authenticated request to /v1/public/projects (user_id=user_1)
WARNING: Invalid X-API-Key for request to /v1/public/projects
WARNING: Missing X-API-Key header for request to /v1/public/projects
```

### 4. Request Isolation

Each request has isolated state to prevent:
- Cross-request contamination
- User ID leakage between requests
- Race conditions in concurrent requests

## Compliance

This implementation satisfies:

✅ **PRD §10:** Signed requests + auditability
✅ **DX Contract §2:** All public endpoints accept X-API-Key
✅ **DX Contract §7:** Error semantics (detail + error_code)
✅ **Epic 2, Story 1:** X-API-Key authentication for all public endpoints

## Production Considerations

When deploying to production, consider:

### 1. API Key Management

Replace hardcoded demo keys with:
- Database-backed key storage
- Encrypted key storage
- Key rotation policies
- Expiration dates

### 2. Rate Limiting

Add per-API-key rate limiting:
```python
# Future enhancement
rate_limiter = RateLimiter(
    key_func=lambda request: request.state.user_id,
    rate="100/minute"
)
```

### 3. Monitoring

Set up monitoring for:
- Failed authentication attempts
- API key usage patterns
- Potential brute-force attacks
- Unusual access patterns

### 4. Key Scopes

Implement permission scopes:
```python
# Future enhancement
api_key = {
    "key": "sk_live_...",
    "user_id": "user_123",
    "scopes": ["projects:read", "projects:write"]
}
```

## Extending the Implementation

### Adding New Protected Endpoints

New endpoints under `/v1/public/*` are automatically protected:

```python
@router.get("/v1/public/new-endpoint")
async def new_endpoint(request: Request):
    # Middleware already validated X-API-Key
    user_id = request.state.user_id  # Available automatically
    # Your endpoint logic here
```

### Custom Authentication Logic

To extend the middleware for custom validation:

```python
# In api_key_auth.py
class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # ... existing code ...

        # Add custom validation
        if not self._is_key_active(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=format_error_response(
                    error_code="API_KEY_EXPIRED",
                    detail="API key has expired"
                )
            )
```

### Supporting Multiple Auth Methods

The middleware can be extended to support JWT tokens (Epic 2, Story 4):

```python
# Check for X-API-Key OR Authorization header
api_key = request.headers.get("X-API-Key")
auth_header = request.headers.get("Authorization")

if api_key:
    user_id = validate_api_key(api_key)
elif auth_header:
    user_id = validate_jwt_token(auth_header)
else:
    return 401_error()
```

## Troubleshooting

### Common Issues

**Issue:** Getting 401 on all requests
**Solution:** Ensure X-API-Key header is set correctly

**Issue:** Tests failing with "Connection refused"
**Solution:** Server is not running. Start with `uvicorn app.main:app --reload`

**Issue:** API key worked before but not now
**Solution:** Check API key hasn't been modified. Use exact demo keys.

### Debug Mode

Enable debug logging:

```python
# In config.py
debug: bool = Field(default=True)

# Logs will show detailed authentication flow
```

## Support

For issues or questions:
1. Check test suite for examples
2. Review implementation summary document
3. Check DX Contract for API standards
4. Review PRD §10 for requirements

## Version History

- **v1.0.0** (2026-01-10): Initial implementation
  - X-API-Key middleware
  - 30 comprehensive tests
  - Full DX Contract compliance
  - Audit logging support
