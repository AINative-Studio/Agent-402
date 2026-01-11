"""
Timestamp validation utilities for ZeroDB API.

GitHub Issue #39: As a developer, invalid timestamps return clear errors.
Epic 8 Story 3: Invalid timestamps return clear errors.

Per DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Invalid timestamps return HTTP 422
- Error code: INVALID_TIMESTAMP
- Error message includes expected format and examples

Technical Requirements:
- Validate ISO8601 format (RFC 3339)
- Support multiple valid ISO8601 variants
- Return clear error messages with examples
- Deterministic validation (PRD §10)
"""
from datetime import datetime
from typing import Optional, Union
import re


# ISO8601 / RFC 3339 regex pattern
# Supports formats like:
# - 2026-01-10T12:34:56Z
# - 2026-01-10T12:34:56.789Z
# - 2026-01-10T12:34:56+00:00
# - 2026-01-10T12:34:56.789+00:00
# - 2026-01-10T12:34:56-05:00
ISO8601_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$'
)


def is_valid_iso8601(timestamp: str) -> bool:
    """
    Check if timestamp string is valid ISO8601 format.

    Args:
        timestamp: Timestamp string to validate

    Returns:
        True if valid ISO8601, False otherwise
    """
    if not timestamp or not isinstance(timestamp, str):
        return False

    # Basic pattern check
    if not ISO8601_PATTERN.match(timestamp):
        return False

    # Attempt to parse with datetime to ensure semantic validity
    try:
        # Try parsing with common ISO8601 formats
        if timestamp.endswith('Z'):
            # UTC timezone with 'Z' suffix
            dt_str = timestamp[:-1] + '+00:00'
        else:
            dt_str = timestamp

        # Parse with fromisoformat (Python 3.7+)
        datetime.fromisoformat(dt_str)
        return True
    except (ValueError, AttributeError):
        return False


def validate_timestamp(
    timestamp: Optional[str],
    field_name: str = "timestamp"
) -> str:
    """
    Validate timestamp and return normalized value.

    Raises ValueError with detailed message if invalid.

    Args:
        timestamp: Timestamp string to validate (can be None)
        field_name: Name of field for error messages

    Returns:
        Validated and normalized timestamp string

    Raises:
        ValueError: If timestamp is invalid, with detailed message

    Examples:
        >>> validate_timestamp("2026-01-10T12:34:56Z")
        "2026-01-10T12:34:56Z"

        >>> validate_timestamp("invalid")
        ValueError: Invalid timestamp format for 'timestamp'...
    """
    if timestamp is None:
        raise ValueError(
            f"Missing required field: {field_name}. "
            f"Expected ISO8601 timestamp format. "
            f"Examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00'"
        )

    if not isinstance(timestamp, str):
        raise ValueError(
            f"Invalid timestamp type for '{field_name}': expected string, got {type(timestamp).__name__}. "
            f"Expected ISO8601 timestamp format. "
            f"Examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00'"
        )

    timestamp = timestamp.strip()

    if not timestamp:
        raise ValueError(
            f"Empty timestamp for '{field_name}'. "
            f"Expected ISO8601 timestamp format. "
            f"Examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00'"
        )

    if not is_valid_iso8601(timestamp):
        # Provide specific guidance based on common errors
        detail = f"Invalid timestamp format for '{field_name}': '{timestamp}'. "
        detail += "Expected ISO8601 format (RFC 3339). "
        detail += "Valid examples: "
        detail += "'2026-01-10T12:34:56Z' (UTC with Z suffix), "
        detail += "'2026-01-10T12:34:56.789Z' (with milliseconds), "
        detail += "'2026-01-10T12:34:56+00:00' (with timezone offset), "
        detail += "'2026-01-10T12:34:56-05:00' (with negative offset)"

        raise ValueError(detail)

    return timestamp


def parse_timestamp(timestamp: str) -> datetime:
    """
    Parse validated ISO8601 timestamp to datetime object.

    Args:
        timestamp: Valid ISO8601 timestamp string

    Returns:
        datetime object

    Raises:
        ValueError: If timestamp cannot be parsed
    """
    try:
        # Normalize 'Z' suffix to '+00:00'
        if timestamp.endswith('Z'):
            dt_str = timestamp[:-1] + '+00:00'
        else:
            dt_str = timestamp

        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Failed to parse timestamp '{timestamp}': {str(e)}")


def get_current_timestamp_iso8601() -> str:
    """
    Get current UTC timestamp in ISO8601 format.

    Returns:
        ISO8601 formatted timestamp string with Z suffix

    Example:
        "2026-01-10T12:34:56.789Z"
    """
    return datetime.utcnow().isoformat() + 'Z'


# Common timestamp format examples for error messages
TIMESTAMP_EXAMPLES = [
    "2026-01-10T12:34:56Z",
    "2026-01-10T12:34:56.789Z",
    "2026-01-10T12:34:56+00:00",
    "2026-01-10T12:34:56-05:00"
]


def get_timestamp_error_message(field_name: str = "timestamp", invalid_value: str = "") -> str:
    """
    Generate standardized timestamp error message.

    Args:
        field_name: Name of the timestamp field
        invalid_value: The invalid value that was provided

    Returns:
        Formatted error message with examples
    """
    msg = f"Invalid timestamp format for '{field_name}'"
    if invalid_value:
        msg += f": '{invalid_value}'"
    msg += ". Expected ISO8601 format (RFC 3339). "
    msg += "Valid examples: " + ", ".join(f"'{ex}'" for ex in TIMESTAMP_EXAMPLES)
    return msg
