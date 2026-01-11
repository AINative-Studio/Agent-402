# Issue: Epic 2 Issue 4 - JWT Authentication

## Summary

As a developer, I can optionally authenticate via JWT using `POST /v1/public/auth/login`.

**Epic:** 2 (Developer Experience & Authentication)
**Issue:** 4
**Story Points:** 2
**PRD Reference:** Section 12 (Future extensibility)

## Requirements Implemented

1. **POST /v1/public/auth/login** - Exchange API key for JWT tokens
   - Accepts `{ "api_key": "..." }` in request body
   - Returns access token, refresh token, and metadata
   - Response format: `{ "access_token": "...", "token_type": "bearer", "expires_in": 3600, "user_id": "...", "refresh_token": "..." }`

2. **POST /v1/public/auth/refresh** - Refresh expired access tokens
   - Accepts `{ "refresh_token": "..." }` in request body
   - Returns new access token
   - Response format: `{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }`

3. **GET /v1/public/auth/me** - Get current authenticated user info
   - Requires JWT Bearer token in Authorization header
   - Returns user info from JWT claims
   - Response format: `{ "user_id": "...", "issued_at": "...", "expires_at": "...", "token_type": "access" }`

4. **JWT Token Claims**
   - `sub`: Subject (user_id)
   - `user_id`: User ID from API key mapping
   - `exp`: Expiration timestamp
   - `iat`: Issued at timestamp
   - `token_type`: "access" or "refresh"

5. **Dual Authentication Support**
   - All `/v1/public/*` endpoints accept either:
     - `X-API-Key` header (API key authentication)
     - `Authorization: Bearer <token>` header (JWT authentication)

6. **Configuration via settings**
   - `JWT_SECRET_KEY`: Secret key for signing (minimum 32 characters)
   - `JWT_ALGORITHM`: Signing algorithm (default: HS256)
   - `JWT_EXPIRATION_SECONDS`: Access token expiration (default: 3600)
   - Refresh token expiration: 7 days (604800 seconds)

## Files Created/Updated

### Created
- `backend/app/services/auth_service.py` - Authentication service with JWT operations
- `docs/issues/ISSUE_EPIC2_4_JWT_AUTH.md` - This documentation

### Updated
- `backend/app/api/auth.py` - Added refresh and me endpoints
- `backend/app/schemas/auth.py` - Added RefreshTokenRequest, RefreshTokenResponse, UserInfoResponse schemas
- `backend/app/middleware/api_key_auth.py` - Exempted /v1/public/auth/refresh from authentication

## API Usage Examples

### Login with API Key

```bash
curl -X POST http://localhost:8000/v1/public/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "demo_key_user1_abc123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "user_1",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Use JWT Token for Authentication

```bash
curl -X GET http://localhost:8000/v1/public/projects \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Refresh Access Token

```bash
curl -X POST http://localhost:8000/v1/public/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get Current User Info

```bash
curl -X GET http://localhost:8000/v1/public/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response:
```json
{
  "user_id": "user_1",
  "issued_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T11:30:00Z",
  "token_type": "access"
}
```

## Error Responses

All errors follow the DX Contract format: `{ "detail": "...", "error_code": "..." }`

| Scenario | HTTP Status | Error Code | Detail |
|----------|-------------|------------|--------|
| Invalid API key on login | 401 | INVALID_API_KEY | Invalid API key |
| Missing refresh token | 422 | VALIDATION_ERROR | Field required |
| Expired refresh token | 401 | TOKEN_EXPIRED | Refresh token has expired |
| Invalid refresh token | 401 | INVALID_TOKEN | Invalid refresh token |
| Missing Authorization header | 401 | INVALID_API_KEY | Authentication required |
| Invalid Authorization format | 401 | INVALID_API_KEY | Invalid Authorization header format |
| Expired access token | 401 | TOKEN_EXPIRED | JWT token has expired |
| Invalid access token | 401 | INVALID_TOKEN | Invalid JWT token |

## Security Considerations

1. **Token Signing**: All tokens are signed using HMAC-SHA256 with a configurable secret key
2. **Token Expiration**: Access tokens expire after 1 hour (configurable), refresh tokens after 7 days
3. **Clock Skew Tolerance**: 10-second leeway for clock synchronization differences
4. **Secure Defaults**: Secret key must be changed in production (default is for development only)
5. **No Token Storage**: Tokens are stateless; revocation requires key rotation or token blacklisting (future enhancement)

## Architecture

```
                    +-------------------+
                    |   API Endpoints   |
                    +-------------------+
                           |
              +------------+------------+
              |                         |
    +---------v---------+     +---------v---------+
    | POST /auth/login  |     | POST /auth/refresh |
    | (no auth required)|     | (no auth required) |
    +-------------------+     +--------------------+
              |                         |
              v                         v
    +-------------------+     +--------------------+
    |   AuthService     |<----|   AuthService      |
    | login_with_api_key|     | refresh_access_token|
    +-------------------+     +--------------------+
              |                         |
              v                         v
    +-------------------+     +--------------------+
    | JWT Module        |     | JWT Module         |
    | create_access_token|    | decode/validate    |
    +-------------------+     +--------------------+


    +-------------------+
    | GET /auth/me      |
    | (JWT required)    |
    +-------------------+
              |
              v
    +-------------------+
    |   AuthService     |
    |   get_user_info   |
    +-------------------+
              |
              v
    +-------------------+
    | JWT Module        |
    | decode_access_token|
    +-------------------+
```

## Implementation Notes

1. The `/v1/public/auth/refresh` endpoint is exempt from middleware authentication because it uses the refresh token in the request body, not in headers.

2. The `/v1/public/auth/me` endpoint explicitly requires JWT Bearer token authentication (does not accept X-API-Key) to demonstrate JWT-specific functionality.

3. All other `/v1/public/*` endpoints support both X-API-Key and JWT Bearer token authentication transparently via the middleware.

4. The auth service is implemented as a singleton with a factory function for dependency injection compatibility.
