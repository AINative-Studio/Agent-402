# ZeroDB Agent Finance API - Backend

FastAPI implementation of the public projects API per PRD Epic 1 Story 2.

## Features

- **GET /v1/public/projects** - List user projects with authentication
- X-API-Key authentication
- Deterministic demo data per PRD §9
- DX Contract compliant error handling
- Comprehensive test coverage

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration (optional for demo)
```

### 3. Run Server

```bash
# From backend directory
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Using demo API key for user 1
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"

# Using demo API key for user 2
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user2_xyz789"
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit
```

## Demo API Keys

For deterministic demo per PRD §9:

| User   | API Key                    | Projects |
|--------|----------------------------|----------|
| user_1 | demo_key_user1_abc123      | 2        |
| user_2 | demo_key_user2_xyz789      | 3        |

## Project Structure

```
backend/
├── app/
│   ├── api/              # API route handlers
│   │   └── projects.py   # GET /v1/public/projects
│   ├── core/             # Core functionality
│   │   ├── auth.py       # X-API-Key authentication
│   │   ├── config.py     # Configuration settings
│   │   └── errors.py     # Error handling
│   ├── models/           # Domain models
│   │   └── project.py    # Project model
│   ├── schemas/          # Pydantic schemas
│   │   └── project.py    # API request/response schemas
│   ├── services/         # Business logic
│   │   ├── project_service.py
│   │   └── project_store.py
│   ├── tests/            # Tests
│   │   ├── conftest.py
│   │   ├── test_projects_api.py
│   │   └── test_project_service.py
│   └── main.py           # FastAPI application
├── requirements.txt      # Python dependencies
├── pytest.ini           # Pytest configuration
└── README.md            # This file
```

## Epic 1 Story 2 Implementation

### Requirements

- ✅ Create endpoint GET /v1/public/projects
- ✅ Return array of projects for authenticated user
- ✅ Each project includes: id, name, status, tier
- ✅ Filter projects by user's API key
- ✅ Return empty array if no projects exist
- ✅ Require X-API-Key authentication
- ✅ Follow PRD §9 for deterministic demo setup

### API Response Format

```json
{
  "projects": [
    {
      "id": "proj_demo_u1_001",
      "name": "Agent Finance Demo",
      "status": "ACTIVE",
      "tier": "FREE"
    },
    {
      "id": "proj_demo_u1_002",
      "name": "X402 Integration",
      "status": "ACTIVE",
      "tier": "STARTER"
    }
  ],
  "total": 2
}
```

### Error Response Format (DX Contract)

```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```

## DX Contract Compliance

This implementation follows the ZeroDB DX Contract:

1. ✅ All errors return `{ detail, error_code }`
2. ✅ X-API-Key authentication consistently enforced
3. ✅ Invalid keys return `401 INVALID_API_KEY`
4. ✅ Deterministic behavior for demo setup
5. ✅ Response shapes are stable and documented

## Development

### Running in Debug Mode

```bash
# Set DEBUG=true in .env
DEBUG=true python -m app.main
```

### Adding New Endpoints

1. Create route handler in `app/api/`
2. Define schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Add tests in `app/tests/`
5. Register router in `app/main.py`

## Production Considerations

This is an MVP demo implementation. For production:

1. Replace in-memory `ProjectStore` with ZeroDB integration
2. Implement proper API key management (database, secrets manager)
3. Add rate limiting middleware
4. Implement pagination for large result sets
5. Add logging and monitoring
6. Configure CORS appropriately
7. Use environment-based configuration
8. Implement comprehensive security headers

## License

See LICENSE file in project root.
