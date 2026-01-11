"""
FastAPI application entry point.
Implements ZeroDB-compliant API server per PRD and DX Contract.

DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422

Epic 2, Story 3: As a developer, all errors include a detail field.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from app.core.config import settings
from app.core.errors import APIError, format_error_response
from app.core.exceptions import ZeroDBException
from app.core.middleware import (
    zerodb_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    internal_server_error_handler
)
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
# Use embeddings API with Issue #16 implementation for batch embed-and-store
from app.api.embeddings_issue16 import router as embeddings_router
from app.api.vectors import router as vectors_router
from app.middleware import APIKeyAuthMiddleware


# Create FastAPI application
app = FastAPI(
    title="ZeroDB Agent Finance API",
    description="Autonomous Fintech Agent Crew - AINative Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

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
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc.error_code, exc.detail)
    )

# 3. Handle Pydantic validation errors (HTTP 422)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 4. Handle FastAPI HTTPException
app.add_exception_handler(HTTPException, http_exception_handler)

# 5. Handle all other unexpected exceptions (catch-all)
app.add_exception_handler(Exception, internal_server_error_handler)


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
app.include_router(embeddings_router)
app.include_router(vectors_router)


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
