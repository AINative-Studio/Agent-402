"""
Custom error classes and error handling.
Implements deterministic error responses per DX Contract.

DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422

Epic 2, Story 3: As a developer, all errors include a detail field.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class APIError(HTTPException):
    """
    Base API error with consistent error_code and detail.

    All custom exceptions should inherit from this class to ensure
    consistent error format across the API.

    Attributes:
        status_code: HTTP status code
        error_code: Machine-readable error code (required)
        detail: Human-readable error message (required)
        headers: Optional HTTP headers
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        # Ensure detail is always a string (never None)
        if not detail:
            detail = "An error occurred"

        # Ensure error_code is always provided
        if not error_code:
            error_code = "ERROR"

        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class InvalidAPIKeyError(APIError):
    """
    Raised when API key is invalid or missing.

    Per DX Contract Section 2: Invalid keys always return 401 INVALID_API_KEY
    Per Epic 2 Story 2 (Issue #7): Handle all invalid API key scenarios

    Scenarios handled:
    - Missing API key (no X-API-Key header)
    - Malformed API key (empty, whitespace, too short, invalid characters)
    - Expired API key (in production: timestamp check; in demo: prefix check)
    - Unauthorized API key (valid format but not found in system)

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: INVALID_API_KEY
        - detail: Human-readable message about the specific invalidity

    All scenarios use the same error_code for security (don't reveal system internals)
    """

    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_API_KEY",
            detail=detail or "Invalid or missing API key"  # Ensure detail never None
        )


class ProjectNotFoundError(APIError):
    """
    Raised when project is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: PROJECT_NOT_FOUND
        - detail: Message including project ID
    """

    def __init__(self, project_id: str):
        detail = f"Project not found: {project_id}" if project_id else "Project not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PROJECT_NOT_FOUND",
            detail=detail
        )


class UnauthorizedError(APIError):
    """
    Raised when user is not authorized to access resource.

    Returns:
        - HTTP 403 (Forbidden)
        - error_code: UNAUTHORIZED
        - detail: Message about unauthorized access
    """

    def __init__(self, detail: str = "Not authorized to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="UNAUTHORIZED",
            detail=detail or "Not authorized to access this resource"
        )


class ProjectLimitExceededError(APIError):
    """
    Raised when user exceeds project creation limit for their tier.

    Returns:
        - HTTP 429 (Too Many Requests)
        - error_code: PROJECT_LIMIT_EXCEEDED
        - detail: Message with current count and limit
    """

    def __init__(self, current_count: int, limit: int, tier: str = ""):
        tier_info = f" for tier '{tier}'" if tier else ""
        detail = (
            f"Project limit exceeded{tier_info}. "
            f"Current projects: {current_count}/{limit}."
        )
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="PROJECT_LIMIT_EXCEEDED",
            detail=detail
        )


class InvalidTierError(APIError):
    """
    Raised when an invalid tier is specified.

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_TIER
        - detail: Message with valid tier options
    """

    def __init__(self, tier: str, valid_tiers: list):
        valid_tiers_str = ", ".join(valid_tiers) if valid_tiers else "unknown"
        detail = (
            f"Invalid tier '{tier}'. "
            f"Valid tiers are: {valid_tiers_str}."
        )
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_TIER",
            detail=detail
        )


class InvalidTokenError(APIError):
    """
    Raised when JWT token is invalid.

    Epic 2 Story 4: JWT authentication support

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: INVALID_TOKEN
        - detail: Message about invalid token
    """

    def __init__(self, detail: str = "Invalid JWT token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            detail=detail or "Invalid JWT token"
        )


class TokenExpiredAPIError(APIError):
    """
    Raised when JWT token has expired.

    Epic 2 Story 4: JWT authentication support

    Returns:
        - HTTP 401 (Unauthorized)
        - error_code: TOKEN_EXPIRED
        - detail: Message about expired token
    """

    def __init__(self, detail: str = "JWT token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            detail=detail or "JWT token has expired"
        )


class AgentNotFoundError(APIError):
    """
    Raised when agent is not found.

    Epic 12 Issue 1: Agent profiles API

    Returns:
        - HTTP 404 (Not Found)
        - error_code: AGENT_NOT_FOUND
        - detail: Message including agent ID
    """

    def __init__(self, agent_id: str):
        detail = f"Agent not found: {agent_id}" if agent_id else "Agent not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="AGENT_NOT_FOUND",
            detail=detail
        )


class DuplicateAgentDIDError(APIError):
    """
    Raised when attempting to create an agent with a duplicate DID.

    Epic 12 Issue 1: Agent profiles API

    Returns:
        - HTTP 409 (Conflict)
        - error_code: DUPLICATE_AGENT_DID
        - detail: Message about duplicate DID
    """

    def __init__(self, did: str, project_id: str):
        detail = f"Agent with DID '{did}' already exists in project: {project_id}"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_AGENT_DID",
            detail=detail
        )


class TableAlreadyExistsError(APIError):
    """
    Raised when attempting to create a table with a duplicate name in a project.

    Epic 7 Issue 1: Table creation with schema definitions.

    Returns:
        - HTTP 409 (Conflict)
        - error_code: TABLE_ALREADY_EXISTS
        - detail: Message about duplicate table name
    """

    def __init__(self, table_name: str, project_id: str):
        detail = f"Table '{table_name}' already exists in project: {project_id}"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="TABLE_ALREADY_EXISTS",
            detail=detail
        )


class TableNotFoundError(APIError):
    """
    Raised when table is not found.

    Epic 7 Issue 1: Table creation with schema definitions.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: TABLE_NOT_FOUND
        - detail: Message including table ID
    """

    def __init__(self, table_id: str):
        detail = f"Table not found: {table_id}" if table_id else "Table not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TABLE_NOT_FOUND",
            detail=detail
        )


class SchemaValidationError(APIError):
    """
    Raised when row data doesn't match the table schema.

    Epic 7 Issue 2: Row insertion with schema validation.

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: SCHEMA_VALIDATION_ERROR
        - detail: Message about schema validation failure
    """

    def __init__(
        self,
        detail: str = "Row data does not match table schema",
        validation_errors: Optional[list] = None
    ):
        """
        Initialize SchemaValidationError.

        Args:
            detail: Human-readable error message
            validation_errors: Optional list of validation error details
        """
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="SCHEMA_VALIDATION_ERROR",
            detail=detail
        )
        self.validation_errors = validation_errors or []


class ImmutableRecordError(APIError):
    """
    Raised when an attempt is made to update or delete an immutable record.

    Epic 12 Issue 6: Append-only enforcement for agent records.
    PRD Section 10: Non-repudiation

    Protected tables (append-only):
    - agents: Agent registration and configuration
    - agent_memory: Agent recall and learning data
    - compliance_events: Regulatory audit trail
    - x402_requests: Payment protocol transactions

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
            error_code="IMMUTABLE_RECORD",
            detail=detail
        )
        self.table_name = table_name
        self.operation = operation


class MissingRowDataError(APIError):
    """
    Raised when POST to /tables/{table_id}/rows is missing row_data field.

    Epic 7 Issue 3: Deterministic errors for missing row_data.
    PRD Section 10: Deterministic errors

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: MISSING_ROW_DATA
        - detail: Message explaining the required field
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="MISSING_ROW_DATA",
            detail="Missing required field: row_data. Use row_data instead of 'data' or 'rows'."
        )


class InvalidFieldNameError(APIError):
    """
    Raised when request contains invalid field names instead of row_data.

    Epic 7 Issue 3: Deterministic errors for common field name mistakes.
    PRD Section 10: Deterministic errors

    Common mistakes detected: 'data', 'rows', 'items', 'records'

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_FIELD_NAME
        - detail: Message explaining the correct field name
    """

    def __init__(self, field_name: str):
        detail = f"Invalid field '{field_name}'. Use 'row_data' for inserting rows."
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_FIELD_NAME",
            detail=detail
        )
        self.field_name = field_name


class InvalidTimestampError(APIError):
    """
    Raised when timestamp format is invalid.

    GitHub Issue #39: As a developer, invalid timestamps return clear errors.
    Epic 8 Story 3: Invalid timestamps return clear errors.

    Per DX Contract §7:
    - Returns HTTP 422 (Unprocessable Entity)
    - error_code: INVALID_TIMESTAMP
    - detail: Message with expected format and examples

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_TIMESTAMP
        - detail: Message about invalid timestamp with examples
    """

    def __init__(self, detail: str = None):
        if not detail:
            detail = (
                "Invalid timestamp format. Expected ISO8601 format (RFC 3339). "
                "Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', "
                "'2026-01-10T12:34:56+00:00', '2026-01-10T12:34:56-05:00'"
            )
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_TIMESTAMP",
            detail=detail
        )


class VectorAlreadyExistsError(APIError):
    """
    Raised when attempting to store a vector with an ID that already exists.

    Epic 4 Issue #18: Upsert behavior for embed-and-store operations.
    PRD Section 10: Replayability - deterministic error for duplicate IDs.

    When upsert=false and a vector_id already exists, this error is raised
    to prevent accidental duplication. Use upsert=true for idempotent updates.

    Returns:
        - HTTP 409 (Conflict)
        - error_code: VECTOR_ALREADY_EXISTS
        - detail: Message about duplicate vector ID
    """

    def __init__(self, vector_id: str, namespace: str = "default"):
        """
        Initialize VectorAlreadyExistsError.

        Args:
            vector_id: The duplicate vector ID
            namespace: The namespace where the conflict occurred
        """
        detail = (
            f"Vector with ID '{vector_id}' already exists in namespace '{namespace}'. "
            f"Use upsert=true to update existing vectors."
        )
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="VECTOR_ALREADY_EXISTS",
            detail=detail
        )
        self.vector_id = vector_id
        self.namespace = namespace


class InvalidNamespaceError(APIError):
    """
    Raised when namespace format is invalid.

    Epic 4 Issue #17: Namespace scopes retrieval correctly.
    PRD Section 6: Agent-scoped memory.

    Namespace validation rules:
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_NAMESPACE
        - detail: Message explaining the validation failure
    """

    def __init__(self, detail: str = "Invalid namespace format"):
        """
        Initialize InvalidNamespaceError.

        Args:
            detail: Human-readable error message explaining the validation failure
        """
        if not detail:
            detail = (
                "Invalid namespace format. "
                "Namespace must contain only alphanumeric characters, underscores, and hyphens. "
                "Max length: 64 characters. Cannot start with underscore or hyphen."
            )
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_NAMESPACE",
            detail=detail
        )


def format_error_response(error_code: str, detail: str) -> Dict[str, str]:
    """
    Format error response per DX Contract.

    All errors MUST return { detail, error_code }.

    Args:
        error_code: Machine-readable error code
        detail: Human-readable error message

    Returns:
        Dictionary with detail and error_code fields
    """
    # Ensure detail is never empty or None
    if not detail:
        detail = "An error occurred"

    # Ensure error_code is never empty or None
    if not error_code:
        error_code = "ERROR"

    return {
        "detail": detail,
        "error_code": error_code
    }
