# Issue Epic 2.1: X-API-Key Authentication for All Public Endpoints

**Issue:** As a developer, I can authenticate all public endpoints using `X-API-Key`.
**Points:** 2
**PRD Reference:** Section 10 (Signed requests + auditability)
**DX Contract Reference:** Section 2 (Authentication)

## Overview

This issue implements comprehensive API key authentication for all `/v1/public/*` endpoints,
ensuring secure access control and user identification for downstream processing.

## Implementation Summary

### Middleware Location

**File:** `/backend/app/middleware/api_key_auth.py`

The `APIKeyAuthMiddleware` class enforces authentication on all public endpoints using either:
1. `X-API-Key` header authentication (primary method)
2. JWT Bearer token authentication (alternative method per Epic 2 Story 4)

### Authentication Flow

```
Request to /v1/public/* endpoint
        |
        v
+-------------------+
| Check if exempt   |---> Yes ---> Allow through
| path?             |
+-------------------+
        | No
        v
+-------------------+
| Extract X-API-Key |
| header            |
+-------------------+
        |
        v
+-------------------+
| Validate against  |---> Valid ---> Set request.state.user_id
| configured keys   |               Continue to handler
+-------------------+
        | Invalid/Missing
        v
+-------------------+
| Try JWT Bearer    |---> Valid ---> Set request.state.user_id
| token             |               Continue to handler
+-------------------+
        | Invalid/Missing
        v
+-------------------+
| Return 401        |
| UNAUTHORIZED      |
+-------------------+
```

### Key Features

#### 1. X-API-Key Header Extraction
- Extracts API key from `X-API-Key` HTTP header
- Case-sensitive header name per HTTP specification

#### 2. API Key Validation
- Validates against configured API keys in `settings.valid_api_keys`
- Returns associated `user_id` for valid keys
- Logs warning for invalid keys (with prefix only for security)

#### 3. Request State Population
- Sets `request.state.user_id` for authenticated requests
- Downstream route handlers can access via dependency injection

#### 4. Error Responses
All authentication failures return HTTP 401 with consistent error format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "INVALID_API_KEY"
}
```

Error codes and their specific detail messages:

| Error Code | Detail Message | Scenario |
|------------|----------------|----------|
| `INVALID_API_KEY` | "Missing X-API-Key header" | No X-API-Key header and no JWT token |
| `INVALID_API_KEY` | "Empty API key" | X-API-Key header present but empty/whitespace |
| `INVALID_API_KEY` | "Invalid API key" | X-API-Key header present but not recognized |
| `TOKEN_EXPIRED` | "JWT token has expired" | JWT token signature valid but past expiration |
| `INVALID_TOKEN` | "Invalid JWT token" | Malformed or tampered JWT token |

#### 5. Exempt Paths
The following paths bypass authentication:
- `/` - Root endpoint
- `/health` - Health check endpoint
- `/docs` - OpenAPI documentation (Swagger UI)
- `/redoc` - ReDoc documentation
- `/openapi.json` - OpenAPI schema
- `/v1/public/auth/login` - Login endpoint (to obtain JWT)
- `/v1/public/embeddings/models` - Public model listing

### Configuration

API keys are configured in `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # Demo API Keys (hardcoded for deterministic demo per PRD Section 9)
    demo_api_key_1: str = "demo_key_user1_abc123"
    demo_api_key_2: str = "demo_key_user2_xyz789"

    @property
    def valid_api_keys(self) -> Dict[str, str]:
        """Return mapping of API key to user ID."""
        return {
            self.demo_api_key_1: "user_1",
            self.demo_api_key_2: "user_2",
        }

    def get_user_id_from_api_key(self, api_key: str) -> str | None:
        """Get user ID from API key, or None if invalid."""
        return self.valid_api_keys.get(api_key)
```

### Middleware Registration

Registered in `backend/app/main.py`:

```python
from app.middleware import APIKeyAuthMiddleware

app = FastAPI(...)

# API Key Authentication middleware
app.add_middleware(APIKeyAuthMiddleware)
```

Middleware order (top to bottom = outer to inner):
1. ImmutableMiddleware - Append-only enforcement
2. APIKeyAuthMiddleware - Authentication
3. CORSMiddleware - CORS handling

### Protected Endpoints

All endpoints under `/v1/public/` require authentication:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| auth | `/v1/public/auth` | `/login` (exempt) |
| projects | `/v1/public` | `/projects` |
| embeddings | `/v1/public` | `/{project_id}/embeddings/generate`, `/{project_id}/embeddings/embed-and-store` |
| vectors | `/v1/public` | `/{project_id}/database/vectors/upsert`, `/vectors/{namespace}` |
| compliance_events | `/v1/public` | `/{project_id}/compliance-events` |
| agents | `/v1/public` | `/{project_id}/agents` |
| agent_memory | `/v1/public` | `/{project_id}/agent-memory` |
| x402_requests | `/v1/public` | `/{project_id}/x402-requests` |
| runs | `/v1/public` | `/{project_id}/runs` |

### Usage Examples

#### With X-API-Key Header

```bash
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"
```

#### With JWT Bearer Token

```bash
# First, obtain JWT token via login
curl -X POST "http://localhost:8000/v1/public/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "demo_key_user1_abc123"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer", ...}

# Then use JWT token
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "Authorization: Bearer eyJ..."
```

### Route Handler Access to User ID

Route handlers can access the authenticated user via FastAPI dependency:

```python
from app.core.auth import get_current_user

@router.get("/projects")
async def list_projects(
    current_user: str = Depends(get_current_user)
) -> ProjectListResponse:
    # current_user contains the authenticated user_id
    projects = project_service.list_user_projects(current_user)
    return ProjectListResponse(projects=projects)
```

### Security Considerations

1. **API Key Security**
   - Keys are validated against server-side configuration
   - Invalid key prefixes logged for audit (not full key)
   - Consistent error responses to prevent enumeration attacks

2. **JWT Security**
   - Tokens signed with HMAC-SHA256
   - Configurable expiration (default: 1 hour)
   - Expired tokens rejected with specific error code

3. **Logging**
   - All authentication attempts logged
   - Successful auth: INFO level with user_id
   - Failed auth: WARNING level with path and auth method attempted

### Files Modified

1. `/backend/app/middleware/api_key_auth.py` - Core middleware implementation
2. `/backend/app/middleware/__init__.py` - Module exports
3. `/backend/app/main.py` - Middleware registration
4. `/backend/app/core/config.py` - API key configuration
5. `/backend/app/core/auth.py` - get_current_user dependency

### Verification Checklist

- [x] All `/v1/public/*` endpoints require X-API-Key header
- [x] Middleware extracts X-API-Key from request headers
- [x] API keys validated against configured keys in settings
- [x] `request.state.user_id` set for downstream use
- [x] 401 returned for missing or invalid API key
- [x] Middleware registered in main.py
- [x] All routers use consistent `/v1/public/` prefix
- [x] JWT Bearer token supported as alternative auth method
- [x] Error responses follow DX Contract format

---

*Built by AINative Dev Team*
