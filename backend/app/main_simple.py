"""
FastAPI application entry point (simplified version for Issue #7).
Implements ZeroDB-compliant API server per PRD and DX Contract.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import APIError, format_error_response
from app.api.projects import router as projects_router
from app.api.auth import router as auth_router
from app.api.embeddings import router as embeddings_router


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
app.include_router(embeddings_router)


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
