# Quick Start Guide - Issue #57 Implementation

> **⚠️ SECURITY WARNING:** This demo uses hardcoded API keys for demonstration purposes only. **NEVER use hardcoded API keys in production.** Always use environment variables, secret managers, and implement proper authentication. See [/SECURITY.md](/SECURITY.md) for production best practices.

## Test the Implementation (No Server Required)

The fastest way to verify the implementation:

```bash
cd /Users/aideveloper/Agent-402/backend
python3 test_manual.py
```

Expected output: All tests pass ✅

## Run the Server (Requires Dependencies)

### Option 1: Direct Python

```bash
cd /Users/aideveloper/Agent-402/backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv
python -m app.main
```

### Option 2: Use the Run Script

```bash
cd /Users/aideveloper/Agent-402/backend
chmod +x run_server.sh
./run_server.sh
```

Server will start at: http://localhost:8000

## Test the API

### List Projects (User 1)

```bash
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"
```

Expected: 2 projects

### List Projects (User 2)

```bash
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user2_xyz789"
```

Expected: 3 projects

### Test Error Handling

```bash
# Missing API key (should return 401)
curl -X GET "http://localhost:8000/v1/public/projects"

# Invalid API key (should return 401)
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: invalid_key"
```

## View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## File Locations

All implementation files are in:
```
/Users/aideveloper/Agent-402/backend/
```

Key files:
- `app/api/projects.py` - GET /v1/public/projects endpoint
- `app/core/auth.py` - X-API-Key authentication
- `app/services/project_store.py` - Demo data
- `test_manual.py` - Quick validation tests
- `README.md` - Full documentation

## Demo API Keys

| User | API Key | Projects |
|------|---------|----------|
| user_1 | demo_key_user1_abc123 | 2 |
| user_2 | demo_key_user2_xyz789 | 3 |

## Troubleshooting

**Problem:** Python dependencies won't install

**Solution:** Use Python 3.9-3.11 (avoid 3.14 due to pydantic compatibility)

**Problem:** Want to test without installing dependencies

**Solution:** Run `python3 test_manual.py` - tests core logic without FastAPI

**Problem:** Port 8000 already in use

**Solution:** Change port in `.env` or run with custom port:
```bash
PORT=8001 python -m app.main
```

## Security Notes for Production

**This demo is for testing only.** For production deployments:

### ⚠️ Critical Security Changes Required

1. **Replace demo API keys with secure authentication**
   - Current: Hardcoded keys in `app/core/auth.py`
   - Production: Environment variables or secret manager
   - See [/SECURITY.md](/SECURITY.md) for implementation patterns

2. **Use environment-based configuration**
   ```python
   # ✅ Production pattern
   import os

   VALID_API_KEYS = {
       os.getenv('USER_1_API_KEY'): 'user_1',
       os.getenv('USER_2_API_KEY'): 'user_2',
   }
   ```

3. **Implement proper key rotation**
   - Rotate API keys every 90 days
   - Support dual-key mode during rotation
   - Log all authentication attempts

4. **Add rate limiting**
   ```python
   from slowapi import Limiter

   limiter = Limiter(key_func=get_remote_address)

   @app.get("/v1/public/projects")
   @limiter.limit("100/hour")
   async def list_projects():
       # ...
   ```

5. **Enable HTTPS only**
   - Never expose API keys over HTTP
   - Use TLS 1.2 or higher
   - Implement HSTS headers

6. **Monitor and alert**
   - Log failed authentication attempts
   - Alert on suspicious patterns
   - Track API usage per user

### Client-Side Application Pattern

If this backend proxies to ZeroDB for a client-side app:

```python
# ✅ Secure backend proxy pattern
@app.post('/api/search')
async def search_proxy(
    query: str,
    user: User = Depends(verify_user_jwt)  # User auth separate from API key
):
    # Your user is authenticated via JWT
    # Now make request to ZeroDB with YOUR API key
    response = await httpx.post(
        'https://api.ainative.studio/v1/public/embeddings/search',
        headers={'X-API-Key': os.getenv('ZERODB_API_KEY')},
        json={'query': query}
    )
    return response.json()
```

**Frontend should NEVER have access to ZeroDB API keys.**

### Compliance Considerations

For fintech applications (per PRD §12):
- API key exposure violates SOC 2, PCI DSS, GDPR
- Implement audit logging for all data access
- Maintain access control per user
- Enable non-repudiation through signed requests

**📚 Full Security Guide:** [/SECURITY.md](/SECURITY.md)

---

## Next Steps

1. ✅ Implementation is complete
2. Review the code in `/Users/aideveloper/Agent-402/backend/`
3. Read full docs in `README.md`
4. Check implementation summary in `ISSUE_57_IMPLEMENTATION.md`
5. **Before production:** Review [/SECURITY.md](/SECURITY.md)
