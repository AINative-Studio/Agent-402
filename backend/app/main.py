"""
FastAPI application entry point.
Implements ZeroDB-compliant API server per PRD and DX Contract.

DX Contract Section 7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422

Epic 2, Issue 3: As a developer, all errors include a detail field.
Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND 404 errors.

404 Error Distinction:
- PATH_NOT_FOUND: The API endpoint/route doesn't exist (typo in URL)
- RESOURCE_NOT_FOUND: The endpoint exists but the resource doesn't
- Specific resource errors: PROJECT_NOT_FOUND, AGENT_NOT_FOUND, TABLE_NOT_FOUND

Reference: backend/app/schemas/errors.py for error response schemas.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.errors import APIError, format_error_response
from app.core.exceptions import ZeroDBException
from app.core.middleware import (
    zerodb_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_server_error_handler,
    DEFAULT_ERROR_DETAIL
)
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
# Use full embeddings API with generate, embed-and-store, and search endpoints
# Includes Issue #17 namespace scoping and Issue #23 search namespace parameter
from app.api.embeddings import router as embeddings_router
# Epic 4 Issue 16: Embed-and-store endpoint with texts field
from app.api.embeddings_embed_store import router as embed_store_router
from app.api.vectors import router as vectors_router
# Epic 8: Events API
from app.api.events import router as events_router
# Epic 12 Issue 3: Compliance events API
from app.api.compliance_events import router as compliance_events_router
# Epic 12 Issue 1: Agent profiles API
from app.api.agents import router as agents_router
# Epic 12 Issue 2: Agent memory persistence
from app.api.agent_memory import router as agent_memory_router
# Epic 12 Issue 4: X402 requests linked to agent + task
from app.api.x402_requests import router as x402_requests_router
# Epic 12 Issue 5: Agent run replay from ZeroDB records
from app.api.runs import router as runs_router
# Epic 7 Issue 1: Table creation with schema definitions
from app.api.tables import router as tables_router
# Epic 7 Issue 4: Row pagination and retrieval
from app.api.rows import router as rows_router
from app.middleware import APIKeyAuthMiddleware, ImmutableMiddleware


# Create FastAPI application
app = FastAPI(
    title="ZeroDB Agent Finance API",
    description="Autonomous Fintech Agent Crew - AINative Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Immutable Record middleware - enforces append-only semantics
# Per Epic 12 Issue 6 and PRD Section 10: Non-repudiation
# Must be added before authentication to reject mutations early
app.add_middleware(ImmutableMiddleware)

# API Key Authentication middleware - must be added before CORS
# Per Epic 2 Story 1: All /v1/public/* endpoints require X-API-Key
app.add_middleware(APIKeyAuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers - implement DX Contract error format
# Handlers are registered in order of specificity (most specific first)

# 1. Handle custom ZeroDB exceptions (from app.core.exceptions)
app.add_exception_handler(ZeroDBException, zerodb_exception_handler)

# 2. Handle custom API errors (from app.core.errors)
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """
    Handle custom API errors with consistent format.
    Per DX Contract: All errors return { detail, error_code }.
    Per Epic 2, Issue 3: All errors include a detail field.
    """
    # Ensure detail and error_code are never empty (defensive programming)
    detail = exc.detail if exc.detail else DEFAULT_ERROR_DETAIL
    error_code = exc.error_code if exc.error_code else "ERROR"

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )

# 3. Handle Pydantic validation errors (HTTP 422)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 4. Handle FastAPI HTTPException
app.add_exception_handler(HTTPException, http_exception_handler)

# 5. Handle Starlette HTTPException (for cases not caught by FastAPI)
# Per Epic 9, Issue 42: All errors return { detail, error_code }
# Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle Starlette HTTPException with consistent error format.
    Per DX Contract: All errors return { detail, error_code }.
    Per Epic 9, Issue 42: All error responses include detail and error_code.
    Per Epic 9, Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND.

    404 Error Distinction:
    - PATH_NOT_FOUND: FastAPI/Starlette returns 404 for unknown routes
    - RESOURCE_NOT_FOUND: Custom exceptions return 404 for missing resources
    """
    from app.core.middleware import _derive_error_code_from_status, _is_route_not_found

    detail = str(exc.detail) if exc.detail else DEFAULT_ERROR_DETAIL

    # Epic 9 Issue 43: Detect route-not-found 404s
    if exc.status_code == 404 and _is_route_not_found(exc):
        error_code = "PATH_NOT_FOUND"
        detail = (
            f"Path '{request.url.path}' not found. "
            f"Check the API documentation for valid endpoints."
        )
    else:
        error_code = _derive_error_code_from_status(exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )

# 6. Handle all other unexpected exceptions (catch-all)
app.add_exception_handler(Exception, internal_server_error_handler)


# X402 Protocol Discovery Endpoint - Issue #73
# Per PRD Section 9: Discovery endpoint for X402 protocol
# Must be BEFORE middleware registration to ensure public access
@app.get(
    "/.well-known/x402",
    tags=["x402"],
    summary="X402 Protocol Discovery",
    status_code=status.HTTP_200_OK,
    response_model=None
)
async def x402_discovery():
    """
    X402 Protocol Discovery Endpoint.

    Per PRD Section 9 (System Architecture):
    - Public discovery endpoint (no authentication required)
    - Returns X402 protocol metadata and capabilities
    - Enables agent-native service discovery

    This endpoint allows agents and clients to discover:
    - Protocol version
    - X402 endpoint location
    - Supported DID methods
    - Supported signature algorithms
    - Server information

    Returns:
        JSON object with X402 protocol metadata:
        - version: Protocol version (1.0)
        - endpoint: X402 signed request endpoint (/x402)
        - supported_dids: List of supported DID methods (["did:ethr"])
        - signature_methods: List of supported signature algorithms (["ECDSA"])
        - server_info: Server name and description
    """
    return {
        "version": "1.0",
        "endpoint": "/x402",
        "supported_dids": ["did:ethr"],
        "signature_methods": ["ECDSA"],
        "server_info": {
            "name": "ZeroDB Agent Finance API",
            "description": "Autonomous Fintech Agent Crew - AINative Edition"
        }
    }


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "ZeroDB Agent Finance API",
        "version": "1.0.0"
    }


# Include routers
app.include_router(auth_router)
app.include_router(projects_router)
# Issue #79: embeddings_router must come first to handle single 'text' field properly
# embeddings_router handles single text (text field), embed_store_router handles batch (documents field)
app.include_router(embeddings_router)
app.include_router(embed_store_router)
app.include_router(vectors_router)
app.include_router(events_router)
app.include_router(compliance_events_router)
app.include_router(agents_router)
app.include_router(agent_memory_router)
app.include_router(x402_requests_router)
app.include_router(runs_router)
app.include_router(tables_router)
app.include_router(rows_router)


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ZeroDB Agent Finance API",
        "version": "1.0.0",
        "description": "Autonomous Fintech Agent Crew - AINative Edition",
        "docs_url": "/docs",
        "health_url": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
