"""
ZeroDB Public API - Main application.

FastAPI application with custom exception handlers for domain-specific errors.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.projects import router as projects_router
from app.core.config import settings
from app.core.exceptions import ZeroDBException
from app.models.project import ErrorResponse


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="""
ZeroDB Public API - Agent-Native Database Platform

**Features:**
- Project management with tier-based limits
- Vector embeddings and semantic search
- NoSQL tables for structured data
- Event streaming for agent workflows
- X402 protocol integration for signed requests

**Authentication:**
All endpoints require an `X-API-Key` header with a valid API key.

**Error Codes:**
- `INVALID_API_KEY`: Missing or invalid API key
- `INVALID_TIER`: Invalid project tier specified
- `PROJECT_LIMIT_EXCEEDED`: User has reached their project limit
- `MODEL_NOT_FOUND`: Invalid embedding model specified
- `DIMENSION_MISMATCH`: Vector dimension mismatch

**Support:**
For questions or issues, contact support@ainative.studio
""",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Register routers
    app.include_router(
        projects_router,
        prefix=settings.api_prefix
    )

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers.

    Ensures all ZeroDB exceptions return consistent error responses
    with appropriate HTTP status codes and error_code fields.
    """

    @app.exception_handler(ZeroDBException)
    async def zerodb_exception_handler(
        request: Request,
        exc: ZeroDBException
    ) -> JSONResponse:
        """
        Handle all ZeroDB domain exceptions.

        Returns a consistent error response with:
        - detail: Human-readable error message
        - error_code: Machine-readable error code
        - Appropriate HTTP status code
        """
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                error_code=exc.error_code
            ).model_dump(),
            headers=exc.headers
        )


# Create the application instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "ZeroDB Public API",
        "version": settings.api_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.api_version
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
