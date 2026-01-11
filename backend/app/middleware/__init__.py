"""
Middleware package for FastAPI application.
"""
from app.middleware.api_key_auth import APIKeyAuthMiddleware

__all__ = ["APIKeyAuthMiddleware"]
