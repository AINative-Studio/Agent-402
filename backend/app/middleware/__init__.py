"""
Middleware package for FastAPI application.

Provides:
- APIKeyAuthMiddleware: Authentication for public API endpoints
- ImmutableMiddleware: Append-only enforcement for agent tables (Epic 12, Issue 6)
"""
from app.middleware.api_key_auth import APIKeyAuthMiddleware
from app.middleware.immutable import (
    ImmutableMiddleware,
    ImmutableRecordError,
    immutable_table,
    immutable_response,
    enforce_immutable,
    is_immutable_table,
    get_immutable_tables,
    add_immutable_metadata,
    IMMUTABLE_TABLES,
    IMMUTABLE_RECORD_ERROR_CODE
)

__all__ = [
    # Authentication middleware
    "APIKeyAuthMiddleware",
    # Immutable record middleware and utilities (Epic 12, Issue 6)
    "ImmutableMiddleware",
    "ImmutableRecordError",
    "immutable_table",
    "immutable_response",
    "enforce_immutable",
    "is_immutable_table",
    "get_immutable_tables",
    "add_immutable_metadata",
    "IMMUTABLE_TABLES",
    "IMMUTABLE_RECORD_ERROR_CODE"
]
