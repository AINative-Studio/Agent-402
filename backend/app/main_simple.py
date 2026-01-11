"""
FastAPI application entry point (simplified version for Issue #7).
Implements ZeroDB-compliant API server per PRD and DX Contract.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.errors import APIError, format_error_response
from app.core.middleware import validation_exception_handler
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
from app.api.embeddings import router as embeddings_router
from app.api.vectors import router as vectors_router
from app.api.events import router as events_router
# Epic 4 Issue 16: Embed-and-store endpoint
from app.api.embeddings_embed_store import router as embed_store_router
from app.api.agent_memory import router as agent_memory_router
from app.api.x402_requests import router as x402_requests_router
from app.api.agents import router as agents_router
from app.api.compliance_events import router as compliance_events_router
from app.api.runs import router as runs_router
from app.api.tables import router as tables_router
from app.api.rows import router as rows_router


# Create FastAPI application
app = FastAPI(
    title="ZeroDB Agent Finance API",
    description="Autonomous Fintech Agent Crew - AINative Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers - implement DX Contract error format
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """
    Handle custom API errors with consistent format.
    Per DX Contract: All errors return { detail, error_code }.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc.error_code, exc.detail)
    )


# Handle Pydantic validation errors (HTTP 422)
# Per Epic 9, Issue 44: Validation errors include loc/msg/type
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle Starlette/FastAPI HTTPException with DX Contract error format.
    Epic 9 Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND 404 errors.
    Per DX Contract Section 4.1: ALL errors return {detail, error_code}.

    404 Error Distinction:
    - PATH_NOT_FOUND: The API endpoint/route doesn't exist (typo in URL)
    - RESOURCE_NOT_FOUND: The endpoint exists but the resource doesn't
    - Specific resource errors: PROJECT_NOT_FOUND, AGENT_NOT_FOUND, TABLE_NOT_FOUND

    Note: FastAPI uses Starlette's HTTPException for route not found (404).
    This handler catches both FastAPI and Starlette HTTPExceptions.
    """
    # Extract error_code if available (from custom exceptions)
    error_code = getattr(exc, 'error_code', None)
    detail = str(exc.detail) if exc.detail else "An error occurred"

    if not error_code:
        # Epic 9 Issue 43: Distinguish PATH_NOT_FOUND vs RESOURCE_NOT_FOUND
        if exc.status_code == 404:
            # Check if this is FastAPI's default 404 for unknown routes
            # FastAPI uses "Not Found" as the exact detail for route not found
            if exc.detail == "Not Found":
                error_code = "PATH_NOT_FOUND"
                detail = (
                    f"Path '{request.url.path}' not found. "
                    f"Check the API documentation for valid endpoints."
                )
            else:
                # Resource-not-found errors have custom detail messages
                error_code = "RESOURCE_NOT_FOUND"
        else:
            # Derive error code from status code for other cases
            error_codes = {
                400: "BAD_REQUEST",
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "RESOURCE_NOT_FOUND",
                405: "METHOD_NOT_ALLOWED",
                409: "CONFLICT",
                422: "VALIDATION_ERROR",
                429: "RATE_LIMIT_EXCEEDED",
                500: "INTERNAL_SERVER_ERROR",
                502: "BAD_GATEWAY",
                503: "SERVICE_UNAVAILABLE",
                504: "GATEWAY_TIMEOUT"
            }
            error_code = error_codes.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(error_code, detail)
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions with consistent format.
    Per DX Contract: All errors return { detail, error_code }.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred"
        )
    )


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
# Epic 4 Issue 16: Include embed-store router
app.include_router(embed_store_router)
app.include_router(embeddings_router)
app.include_router(vectors_router)
app.include_router(events_router)
app.include_router(agent_memory_router)
app.include_router(x402_requests_router)
app.include_router(agents_router)
app.include_router(compliance_events_router)
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
