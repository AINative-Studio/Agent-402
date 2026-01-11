"""
Namespace validation module for Issue #17.

Epic 4 Story 2: As a developer, namespace scopes retrieval correctly.
PRD Reference: Section 6 (Agent-scoped memory)

This module provides centralized namespace validation to ensure:
- Consistent validation across all API endpoints
- Security against injection attacks
- Clear error messages for invalid namespaces

Namespace Rules (per Issue #17):
- Valid characters: a-z, A-Z, 0-9, underscore, hyphen
- Max length: 64 characters
- Cannot start with underscore or hyphen
- Cannot be empty if provided
- Defaults to "default" when not specified

DX Contract Guarantee:
- INVALID_NAMESPACE (422) returned for invalid namespace format
- Error format: { detail, error_code }
"""
import re
from typing import Optional, Tuple


# Default namespace constant
DEFAULT_NAMESPACE = "default"

# Maximum namespace length
MAX_NAMESPACE_LENGTH = 64

# Regex pattern for valid namespace characters
# Allows: alphanumeric, underscore, hyphen
# Must start with alphanumeric
NAMESPACE_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')


class NamespaceValidationError(Exception):
    """
    Exception raised when namespace validation fails.

    Contains both a human-readable message and error code
    for consistent API error responses.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error code (INVALID_NAMESPACE)
    """

    def __init__(self, message: str):
        self.message = message
        self.error_code = "INVALID_NAMESPACE"
        super().__init__(message)


def validate_namespace(namespace: Optional[str]) -> str:
    """
    Validate and normalize a namespace parameter.

    Issue #17 Requirements:
    - Valid characters: a-z, A-Z, 0-9, underscore, hyphen
    - Max length: 64 characters
    - Cannot start with underscore or hyphen
    - Cannot be empty if provided
    - Defaults to "default" when None or empty

    Args:
        namespace: The namespace string to validate, or None

    Returns:
        str: Validated namespace (DEFAULT_NAMESPACE if None/empty)

    Raises:
        NamespaceValidationError: If namespace format is invalid

    Examples:
        >>> validate_namespace(None)
        'default'
        >>> validate_namespace("")
        'default'
        >>> validate_namespace("agent_memory")
        'agent_memory'
        >>> validate_namespace("my-namespace-123")
        'my-namespace-123'
        >>> validate_namespace("_invalid")  # Raises NamespaceValidationError
        >>> validate_namespace("-invalid")  # Raises NamespaceValidationError
    """
    # Handle None - return default namespace
    if namespace is None:
        return DEFAULT_NAMESPACE

    # Ensure it's a string
    if not isinstance(namespace, str):
        raise NamespaceValidationError(
            "Namespace must be a string"
        )

    # Strip whitespace
    cleaned = namespace.strip()

    # Empty string after stripping - return default
    if not cleaned:
        return DEFAULT_NAMESPACE

    # Check maximum length
    if len(cleaned) > MAX_NAMESPACE_LENGTH:
        raise NamespaceValidationError(
            f"Namespace cannot exceed {MAX_NAMESPACE_LENGTH} characters. "
            f"Received {len(cleaned)} characters."
        )

    # Check if namespace starts with underscore or hyphen
    if cleaned.startswith('_'):
        raise NamespaceValidationError(
            "Namespace cannot start with underscore"
        )

    if cleaned.startswith('-'):
        raise NamespaceValidationError(
            "Namespace cannot start with hyphen"
        )

    # Validate against pattern (alphanumeric, underscore, hyphen)
    if not NAMESPACE_PATTERN.match(cleaned):
        raise NamespaceValidationError(
            "Namespace can only contain alphanumeric characters, "
            "underscores, and hyphens"
        )

    return cleaned


def validate_namespace_safe(namespace: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Validate namespace with safe error handling (no exceptions).

    This function is useful when you want to handle validation errors
    without exception handling, such as in Pydantic validators.

    Args:
        namespace: The namespace string to validate, or None

    Returns:
        Tuple of (validated_namespace, error_message)
        - If valid: (namespace, None)
        - If invalid: (DEFAULT_NAMESPACE, error_message)

    Examples:
        >>> validate_namespace_safe("valid_namespace")
        ('valid_namespace', None)
        >>> validate_namespace_safe("_invalid")
        ('default', 'Namespace cannot start with underscore')
    """
    try:
        validated = validate_namespace(namespace)
        return (validated, None)
    except NamespaceValidationError as e:
        return (DEFAULT_NAMESPACE, e.message)


def is_valid_namespace(namespace: str) -> bool:
    """
    Check if a namespace string is valid without raising exceptions.

    Args:
        namespace: The namespace string to check

    Returns:
        bool: True if valid, False otherwise

    Examples:
        >>> is_valid_namespace("agent_memory")
        True
        >>> is_valid_namespace("my-namespace-123")
        True
        >>> is_valid_namespace("_invalid")
        False
        >>> is_valid_namespace("-invalid")
        False
        >>> is_valid_namespace("has spaces")
        False
    """
    if not namespace or not isinstance(namespace, str):
        return False

    cleaned = namespace.strip()

    if not cleaned:
        return False

    if len(cleaned) > MAX_NAMESPACE_LENGTH:
        return False

    if cleaned.startswith('_') or cleaned.startswith('-'):
        return False

    return bool(NAMESPACE_PATTERN.match(cleaned))


def get_namespace_or_default(namespace: Optional[str]) -> str:
    """
    Get validated namespace or default, with permissive fallback.

    Unlike validate_namespace(), this function never raises exceptions.
    Invalid namespaces silently fall back to DEFAULT_NAMESPACE.

    Use this when you want graceful degradation instead of errors.

    Args:
        namespace: The namespace string, or None

    Returns:
        str: Validated namespace or DEFAULT_NAMESPACE

    Examples:
        >>> get_namespace_or_default(None)
        'default'
        >>> get_namespace_or_default("valid_ns")
        'valid_ns'
        >>> get_namespace_or_default("_invalid")
        'default'
    """
    try:
        return validate_namespace(namespace)
    except NamespaceValidationError:
        return DEFAULT_NAMESPACE
