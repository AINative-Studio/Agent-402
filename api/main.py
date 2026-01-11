"""
ZeroDB API - Main FastAPI Application
Implements project creation and management with tier validation
"""
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, status, Depends
from fastapi.exceptions import RequestValidationError

from api.models import (
    CreateProjectRequest,
    ProjectResponse,
    ProjectStatus,
    ProjectTier,
    ErrorResponse
)
from api.errors import (
    TierValidationError,
    ProjectLimitExceededError,
    InvalidAPIKeyError,
    tier_validation_exception_handler,
    validation_exception_handler,
    project_limit_exception_handler,
    invalid_api_key_exception_handler,
    generic_http_exception_handler
)


# In-memory storage for MVP (would be replaced with ZeroDB in production)
projects_db = {}
user_api_keys = {
    "test_api_key_123": {"user_id": "user_1", "project_limit": 10}
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    print("🚀 ZeroDB API Server starting up...")
    yield
    # Shutdown
    print("👋 ZeroDB API Server shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="ZeroDB API",
    description="Autonomous Fintech Agent Crew - API Implementation",
    version="1.0.0",
    lifespan=lifespan
)


# Register exception handlers
app.add_exception_handler(TierValidationError, tier_validation_exception_handler)
app.add_exception_handler(ProjectLimitExceededError, project_limit_exception_handler)
app.add_exception_handler(InvalidAPIKeyError, invalid_api_key_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, generic_http_exception_handler)


# Dependency: API Key Authentication
async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> dict:
    """
    Verify API key from X-API-Key header.
    As per DX Contract §2, invalid keys return 401 INVALID_API_KEY.
    """
    if not x_api_key:
        raise InvalidAPIKeyError()

    user_data = user_api_keys.get(x_api_key)
    if not user_data:
        raise InvalidAPIKeyError()

    return user_data


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "ZeroDB API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.post(
    "/v1/public/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Project created successfully"},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        422: {"model": ErrorResponse, "description": "Validation error (INVALID_TIER or PROJECT_LIMIT_EXCEEDED)"}
    }
)
async def create_project(
    project: CreateProjectRequest,
    user_data: dict = Depends(verify_api_key)
) -> ProjectResponse:
    """
    Create a new project.

    As per PRD §6 and Epic 1:
    - Validates tier against allowed values (free, starter, professional, enterprise)
    - Returns HTTP 422 with INVALID_TIER for invalid tiers
    - Returns HTTP 422 with PROJECT_LIMIT_EXCEEDED if user exceeds limit
    - Returns consistent error format with detail and error_code

    The tier validation happens in the Pydantic model validator, which will
    raise a ValueError that gets converted to a proper validation error with
    INVALID_TIER code by our custom exception handler.
    """
    user_id = user_data["user_id"]
    project_limit = user_data["project_limit"]

    # Check project limit
    user_projects = [p for p in projects_db.values() if p.get("user_id") == user_id]
    if len(user_projects) >= project_limit:
        raise ProjectLimitExceededError(
            current_count=len(user_projects),
            max_allowed=project_limit
        )

    # Create project
    project_id = str(uuid4())
    now = datetime.now(timezone.utc)

    project_data = {
        "id": project_id,
        "user_id": user_id,
        "name": project.name,
        "description": project.description,
        "tier": project.tier,  # Already validated by Pydantic
        "status": ProjectStatus.ACTIVE,
        "database_enabled": project.database_enabled,
        "created_at": now,
        "updated_at": now
    }

    # Store in database
    projects_db[project_id] = project_data

    # Return response (exclude user_id from response)
    return ProjectResponse(
        id=project_data["id"],
        name=project_data["name"],
        description=project_data["description"],
        tier=project_data["tier"],
        status=project_data["status"],
        database_enabled=project_data["database_enabled"],
        created_at=project_data["created_at"],
        updated_at=project_data["updated_at"]
    )


@app.get(
    "/v1/public/projects",
    response_model=list[ProjectResponse],
    responses={
        200: {"description": "List of projects"},
        401: {"model": ErrorResponse, "description": "Invalid API key"}
    }
)
async def list_projects(
    user_data: dict = Depends(verify_api_key)
) -> list[ProjectResponse]:
    """
    List all projects for the authenticated user.

    As per Epic 1:
    - Returns id, name, status, tier for each project
    - Requires valid X-API-Key authentication
    """
    user_id = user_data["user_id"]

    # Filter projects by user
    user_projects = [
        ProjectResponse(
            id=p["id"],
            name=p["name"],
            description=p.get("description"),
            tier=p["tier"],
            status=p["status"],
            database_enabled=p["database_enabled"],
            created_at=p["created_at"],
            updated_at=p.get("updated_at")
        )
        for p in projects_db.values()
        if p.get("user_id") == user_id
    ]

    return user_projects


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
