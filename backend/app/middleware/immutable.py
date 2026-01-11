"""
Immutable Record Middleware and Decorator.

Implements append-only enforcement for agent-related tables per PRD Section 10 (Non-repudiation).

Epic 12, Issue 6: As a system, all agent records are append-only.

This module provides:
1. ImmutableRecordError exception for immutability violations
2. @immutable_table decorator for service methods
3. ImmutableMiddleware for route-level enforcement
4. Response metadata enrichment with immutable flag

Protected tables (append-only):
- agents: Agent registration and configuration
- agent_memory: Agent recall and learning data
- compliance_events: Regulatory audit trail
- x402_requests: Payment protocol transactions

These tables are critical for:
- Audit trails and regulatory compliance
- Non-repudiation of agent actions
- Payment transaction integrity
- Forensic analysis capability
"""
from typing import Callable, Set, List, Optional, Dict, Any
from functools import wraps
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.errors import APIError, format_error_response
import logging

logger = logging.getLogger(__name__)

# Protected tables that enforce append-only semantics
IMMUTABLE_TABLES: Set[str] = {
    "agents",
    "agent_memory",
    "compliance_events",
    "x402_requests"
}

# HTTP methods that violate append-only semantics
MUTATING_METHODS: Set[str] = {"PUT", "PATCH", "DELETE"}

# Error code for immutability violations (per PRD Section 10)
IMMUTABLE_RECORD_ERROR_CODE = "IMMUTABLE_RECORD"


class ImmutableRecordError(APIError):
    """
    Raised when an attempt is made to update or delete an immutable record.

    Per PRD Section 10 (Non-repudiation):
    - All agent-related records are append-only
    - UPDATE and DELETE operations are forbidden
    - Returns HTTP 403 Forbidden with IMMUTABLE_RECORD error code

    Returns:
        - HTTP 403 (Forbidden)
        - error_code: IMMUTABLE_RECORD
        - detail: Message explaining the immutability constraint
    """

    def __init__(
        self,
        table_name: str,
        operation: str = "modify",
        detail: Optional[str] = None
    ):
        """
        Initialize ImmutableRecordError.

        Args:
            table_name: Name of the immutable table
            operation: The attempted operation (update/delete)
            detail: Optional custom detail message
        """
        if detail is None:
            detail = (
                f"Cannot {operation} records in '{table_name}' table. "
                f"This table is append-only for audit trail integrity. "
                f"Per PRD Section 10: Agent records are immutable for non-repudiation."
            )

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=IMMUTABLE_RECORD_ERROR_CODE,
            detail=detail
        )
        self.table_name = table_name
        self.operation = operation


def immutable_table(table_name: str):
    """
    Decorator to enforce append-only semantics on service methods.

    Use this decorator on service methods that should reject UPDATE/DELETE operations.
    The decorator checks if the method name indicates a mutating operation and
    raises ImmutableRecordError if the table is protected.

    Usage:
        @immutable_table("agents")
        async def update_agent(self, agent_id: str, data: dict):
            # This will raise ImmutableRecordError
            pass

    Args:
        table_name: Name of the table being protected

    Returns:
        Decorator function

    Raises:
        ImmutableRecordError: If attempting update/delete on protected table
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if this is a mutating operation based on method name
            func_name = func.__name__.lower()

            if table_name in IMMUTABLE_TABLES:
                if "update" in func_name or "modify" in func_name or "edit" in func_name:
                    logger.warning(
                        f"Blocked UPDATE operation on immutable table",
                        extra={
                            "table": table_name,
                            "function": func.__name__,
                            "error_code": IMMUTABLE_RECORD_ERROR_CODE
                        }
                    )
                    raise ImmutableRecordError(
                        table_name=table_name,
                        operation="update"
                    )

                if "delete" in func_name or "remove" in func_name:
                    logger.warning(
                        f"Blocked DELETE operation on immutable table",
                        extra={
                            "table": table_name,
                            "function": func.__name__,
                            "error_code": IMMUTABLE_RECORD_ERROR_CODE
                        }
                    )
                    raise ImmutableRecordError(
                        table_name=table_name,
                        operation="delete"
                    )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check if this is a mutating operation based on method name
            func_name = func.__name__.lower()

            if table_name in IMMUTABLE_TABLES:
                if "update" in func_name or "modify" in func_name or "edit" in func_name:
                    logger.warning(
                        f"Blocked UPDATE operation on immutable table",
                        extra={
                            "table": table_name,
                            "function": func.__name__,
                            "error_code": IMMUTABLE_RECORD_ERROR_CODE
                        }
                    )
                    raise ImmutableRecordError(
                        table_name=table_name,
                        operation="update"
                    )

                if "delete" in func_name or "remove" in func_name:
                    logger.warning(
                        f"Blocked DELETE operation on immutable table",
                        extra={
                            "table": table_name,
                            "function": func.__name__,
                            "error_code": IMMUTABLE_RECORD_ERROR_CODE
                        }
                    )
                    raise ImmutableRecordError(
                        table_name=table_name,
                        operation="delete"
                    )

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def enforce_immutable(table_name: str, operation: str) -> None:
    """
    Utility function to enforce immutability at any point in code.

    Call this function before performing any mutating operation on
    protected tables. Raises ImmutableRecordError if the table is protected.

    Usage:
        enforce_immutable("agents", "update")  # Raises ImmutableRecordError
        enforce_immutable("regular_table", "delete")  # No error

    Args:
        table_name: Name of the table being modified
        operation: The operation being attempted (update/delete)

    Raises:
        ImmutableRecordError: If table is in IMMUTABLE_TABLES
    """
    if table_name in IMMUTABLE_TABLES:
        logger.warning(
            f"Blocked {operation.upper()} operation on immutable table",
            extra={
                "table": table_name,
                "operation": operation,
                "error_code": IMMUTABLE_RECORD_ERROR_CODE
            }
        )
        raise ImmutableRecordError(
            table_name=table_name,
            operation=operation
        )


def is_immutable_table(table_name: str) -> bool:
    """
    Check if a table is marked as immutable.

    Args:
        table_name: Name of the table to check

    Returns:
        True if the table is immutable, False otherwise
    """
    return table_name in IMMUTABLE_TABLES


def get_immutable_tables() -> List[str]:
    """
    Get list of all immutable tables.

    Returns:
        List of table names that are append-only
    """
    return list(IMMUTABLE_TABLES)


def add_immutable_metadata(response_data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """
    Add immutable metadata flag to response data.

    Per Epic 12 Issue 6 requirement: Add `immutable: true` flag to response
    metadata for immutable table endpoints.

    Args:
        response_data: Original response dictionary
        table_name: Table name to check for immutability

    Returns:
        Response data with immutable metadata added
    """
    if is_immutable_table(table_name):
        if "metadata" not in response_data:
            response_data["metadata"] = {}
        response_data["metadata"]["immutable"] = True
        response_data["metadata"]["append_only"] = True
        response_data["metadata"]["prd_reference"] = "PRD Section 10 (Non-repudiation)"
    return response_data


class ImmutableMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce append-only semantics at the HTTP route level.

    This middleware intercepts requests to immutable table endpoints and
    blocks PUT, PATCH, and DELETE operations, returning HTTP 403 with
    IMMUTABLE_RECORD error code.

    Protected endpoints (pattern-based detection):
    - /v1/public/*/agents/*
    - /v1/public/*/agent_memory/*
    - /v1/public/*/compliance_events/*
    - /v1/public/*/x402_requests/*

    Allowed operations on immutable tables:
    - GET (read)
    - POST (create/append)

    Blocked operations on immutable tables:
    - PUT (full update)
    - PATCH (partial update)
    - DELETE (removal)

    Per PRD Section 10: Non-repudiation
    Per Epic 12 Issue 6: Append-only enforcement
    """

    # Path patterns for immutable tables (lowercase for matching)
    IMMUTABLE_PATH_PATTERNS: List[str] = [
        "/agents",
        "/agent_memory",
        "/agent-memory",
        "/compliance_events",
        "/compliance-events",
        "/x402_requests",
        "/x402-requests",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercept and validate requests to immutable table endpoints.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: Either a 403 error or the result of call_next
        """
        path = request.url.path.lower()
        method = request.method.upper()

        # Check if this is a mutating request to an immutable table
        if method in MUTATING_METHODS:
            for pattern in self.IMMUTABLE_PATH_PATTERNS:
                if pattern in path:
                    # Extract table name from pattern
                    table_name = pattern.strip("/").replace("-", "_")

                    # Map operation from HTTP method
                    operation_map = {
                        "PUT": "update",
                        "PATCH": "update",
                        "DELETE": "delete"
                    }
                    operation = operation_map.get(method, "modify")

                    logger.warning(
                        f"Blocked {method} request to immutable endpoint",
                        extra={
                            "path": path,
                            "method": method,
                            "table": table_name,
                            "error_code": IMMUTABLE_RECORD_ERROR_CODE
                        }
                    )

                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content=format_error_response(
                            error_code=IMMUTABLE_RECORD_ERROR_CODE,
                            detail=(
                                f"Cannot {operation} records in '{table_name}' table. "
                                f"This table is append-only for audit trail integrity. "
                                f"Per PRD Section 10: Agent records are immutable for non-repudiation."
                            )
                        )
                    )

        # Continue to route handler for allowed operations
        return await call_next(request)


# Convenience decorator for route handlers
def immutable_response(table_name: str):
    """
    Decorator for route handlers to add immutable metadata to responses.

    This decorator wraps a route handler and adds the `immutable: true`
    flag to the response metadata for immutable table endpoints.

    Usage:
        @router.post("/agents")
        @immutable_response("agents")
        async def create_agent(request: AgentCreateRequest):
            # Response will have metadata.immutable = true
            return {"id": "agent-123", "name": "Agent Smith"}

    Args:
        table_name: Name of the immutable table

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Add immutable metadata if result is a dict
            if isinstance(result, dict):
                result = add_immutable_metadata(result, table_name)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Add immutable metadata if result is a dict
            if isinstance(result, dict):
                result = add_immutable_metadata(result, table_name)

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
