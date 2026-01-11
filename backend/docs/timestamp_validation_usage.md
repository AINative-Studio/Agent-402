# Timestamp Validation Usage Guide

**GitHub Issue #39: As a developer, invalid timestamps return clear errors**

This guide demonstrates how to use the timestamp validation utilities in your API endpoints.

## Overview

The timestamp validation system ensures that all timestamp inputs follow the ISO8601 (RFC 3339) standard and returns clear, helpful error messages when validation fails.

### Key Features

- **ISO8601 Format Validation**: Strict validation of timestamp formats
- **HTTP 422 Responses**: Invalid timestamps return HTTP 422 Unprocessable Entity
- **Clear Error Messages**: Error messages include expected format and examples
- **DX Contract Compliance**: Follows error response format `{ detail, error_code }`
- **Deterministic Behavior**: Same input always produces same result (PRD §10)

## Quick Start

### 1. Basic Timestamp Validation

```python
from app.core.timestamp_validator import validate_timestamp

# Valid timestamp
timestamp = "2026-01-10T12:34:56Z"
validated = validate_timestamp(timestamp)  # Returns: "2026-01-10T12:34:56Z"

# Invalid timestamp
try:
    validate_timestamp("invalid-timestamp")
except ValueError as e:
    print(e)
    # Output: "Invalid timestamp format for 'timestamp': 'invalid-timestamp'.
    #          Expected ISO8601 format (RFC 3339). Valid examples: ..."
```

### 2. Using in Pydantic Models

```python
from pydantic import BaseModel, validator
from app.core.timestamp_validator import validate_timestamp

class EventRequest(BaseModel):
    event_type: str
    data: dict
    timestamp: str

    @validator('timestamp')
    def validate_timestamp_format(cls, v):
        """Validate timestamp is in ISO8601 format."""
        try:
            return validate_timestamp(v, field_name="timestamp")
        except ValueError as e:
            raise ValueError(str(e))
```

### 3. Using in FastAPI Endpoints

```python
from fastapi import APIRouter, HTTPException
from app.core.errors import InvalidTimestampError

router = APIRouter()

@router.post("/events")
async def create_event(request: EventRequest):
    # Pydantic validation will automatically validate timestamp
    # If invalid, returns HTTP 422 with clear error message
    return {"status": "created", "timestamp": request.timestamp}
```

## Supported Timestamp Formats

All timestamps must be in ISO8601 (RFC 3339) format:

### Valid Formats

```python
# UTC with Z suffix
"2026-01-10T12:34:56Z"

# UTC with milliseconds
"2026-01-10T12:34:56.789Z"

# UTC with microseconds
"2026-01-10T12:34:56.123456Z"

# With timezone offset
"2026-01-10T12:34:56+00:00"
"2026-01-10T12:34:56-05:00"

# With milliseconds and timezone
"2026-01-10T12:34:56.789+00:00"
```

### Invalid Formats (Will be Rejected)

```python
# Missing timezone
"2026-01-10T12:34:56"

# Date only
"2026-01-10"

# Time only
"12:34:56Z"

# Unix timestamp
"1704891296"

# Human readable
"January 10, 2026 12:34:56"

# Wrong separator (space instead of T)
"2026-01-10 12:34:56Z"
```

## Error Response Format

When timestamp validation fails, the API returns HTTP 422 with the following format:

### Example Error Response

```json
{
  "detail": "Invalid timestamp format for 'timestamp': 'invalid'. Expected ISO8601 format (RFC 3339). Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00', '2026-01-10T12:34:56-05:00'",
  "error_code": "INVALID_TIMESTAMP"
}
```

### Error Response Fields

- `detail`: Human-readable error message with examples
- `error_code`: Machine-readable error code (`INVALID_TIMESTAMP`)
- HTTP Status: `422 Unprocessable Entity`

## API Functions

### `validate_timestamp(timestamp, field_name)`

Validate timestamp string and return normalized value.

**Parameters:**
- `timestamp` (str): Timestamp string to validate
- `field_name` (str, optional): Field name for error messages (default: "timestamp")

**Returns:**
- `str`: Validated and normalized timestamp string

**Raises:**
- `ValueError`: If timestamp is invalid, with detailed message

**Example:**
```python
from app.core.timestamp_validator import validate_timestamp

# Valid
result = validate_timestamp("2026-01-10T12:34:56Z")
# Returns: "2026-01-10T12:34:56Z"

# Invalid
try:
    validate_timestamp("bad-timestamp", field_name="created_at")
except ValueError as e:
    print(e)
    # Error message includes field name "created_at"
```

### `is_valid_iso8601(timestamp)`

Check if timestamp string is valid ISO8601 format.

**Parameters:**
- `timestamp` (str): Timestamp string to check

**Returns:**
- `bool`: True if valid ISO8601, False otherwise

**Example:**
```python
from app.core.timestamp_validator import is_valid_iso8601

is_valid_iso8601("2026-01-10T12:34:56Z")  # True
is_valid_iso8601("invalid")  # False
```

### `parse_timestamp(timestamp)`

Parse validated ISO8601 timestamp to datetime object.

**Parameters:**
- `timestamp` (str): Valid ISO8601 timestamp string

**Returns:**
- `datetime`: Parsed datetime object

**Raises:**
- `ValueError`: If timestamp cannot be parsed

**Example:**
```python
from app.core.timestamp_validator import parse_timestamp

dt = parse_timestamp("2026-01-10T12:34:56Z")
print(dt.year)  # 2026
print(dt.month)  # 1
print(dt.day)  # 10
```

### `get_current_timestamp_iso8601()`

Get current UTC timestamp in ISO8601 format.

**Returns:**
- `str`: ISO8601 formatted timestamp with Z suffix

**Example:**
```python
from app.core.timestamp_validator import get_current_timestamp_iso8601

timestamp = get_current_timestamp_iso8601()
# Returns: "2026-01-10T12:34:56.789Z"
```

## Raising InvalidTimestampError

For direct error handling in API endpoints:

```python
from app.core.errors import InvalidTimestampError

# Raise with default message
raise InvalidTimestampError()

# Raise with custom message
raise InvalidTimestampError(
    detail="The 'created_at' field must be in ISO8601 format"
)
```

## Testing

### Unit Testing Timestamp Validation

```python
import pytest
from app.core.timestamp_validator import validate_timestamp

def test_valid_timestamp():
    """Test valid timestamp is accepted."""
    result = validate_timestamp("2026-01-10T12:34:56Z")
    assert result == "2026-01-10T12:34:56Z"

def test_invalid_timestamp():
    """Test invalid timestamp raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        validate_timestamp("invalid")
    assert "Invalid timestamp format" in str(exc_info.value)
    assert "ISO8601" in str(exc_info.value)
```

### Integration Testing API Endpoints

```python
from fastapi.testclient import TestClient

def test_invalid_timestamp_returns_422(client: TestClient):
    """Test invalid timestamp returns HTTP 422."""
    response = client.post("/api/events", json={
        "event_type": "test_event",
        "data": {},
        "timestamp": "invalid-timestamp"
    })

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
```

## DX Contract Compliance

This implementation follows the DX Contract §7 (Error Semantics):

1. **Error Format**: All errors return `{ detail, error_code }`
2. **Error Codes**: `INVALID_TIMESTAMP` is stable and documented
3. **HTTP Status**: Validation errors use HTTP 422
4. **Deterministic**: Same input always produces same error
5. **Clear Messages**: Error messages include examples and expected format

## Best Practices

1. **Always validate timestamps at the API boundary** (in Pydantic models)
2. **Use field_name parameter** for clear error messages
3. **Don't catch and suppress errors** - let them bubble up as HTTP 422
4. **Store timestamps in ISO8601 format** for consistency
5. **Use UTC timezone** (Z suffix) for server-side timestamps

## Integration Examples

### Events API Endpoint

```python
from pydantic import BaseModel, validator
from app.core.timestamp_validator import validate_timestamp

class CreateEventRequest(BaseModel):
    event_type: str
    event_data: dict
    timestamp: str

    @validator('timestamp')
    def validate_timestamp_format(cls, v):
        return validate_timestamp(v, field_name="timestamp")

@router.post("/database/events")
async def create_event(request: CreateEventRequest):
    # Timestamp is automatically validated by Pydantic
    # Invalid timestamps return HTTP 422 with clear error
    return {
        "event_id": "evt_123",
        "event_type": request.event_type,
        "timestamp": request.timestamp,
        "status": "created"
    }
```

### Agent Memory Storage

```python
class AgentMemoryRequest(BaseModel):
    agent_id: str
    task_id: str
    content: str
    created_at: str

    @validator('created_at')
    def validate_created_at(cls, v):
        return validate_timestamp(v, field_name="created_at")
```

## Common Errors and Solutions

### Error: "Invalid timestamp format"

**Cause**: Timestamp is not in ISO8601 format

**Solution**: Use ISO8601 format with timezone:
```python
# ✅ Correct
"2026-01-10T12:34:56Z"

# ❌ Incorrect
"2026-01-10 12:34:56"  # Space instead of T
"2026-01-10T12:34:56"   # Missing timezone
```

### Error: "Missing required field: timestamp"

**Cause**: Timestamp field is None or not provided

**Solution**: Always provide timestamp value:
```python
# ✅ Correct
{"timestamp": "2026-01-10T12:34:56Z"}

# ❌ Incorrect
{"timestamp": None}
{}  # Missing field
```

### Error: "Invalid timestamp type: expected string"

**Cause**: Timestamp is not a string (e.g., integer, datetime object)

**Solution**: Convert to ISO8601 string:
```python
from datetime import datetime

# ✅ Correct
timestamp = datetime.utcnow().isoformat() + 'Z'

# ❌ Incorrect
timestamp = datetime.utcnow()  # datetime object
timestamp = 1704891296  # Unix timestamp
```

## Related Documentation

- [DX Contract - Error Semantics](/DX-Contract.md#7-error-semantics)
- [PRD §10 - Deterministic Behavior](/prd.md#10-deliverables)
- [Epic 8 - Events API](/backlog.md#epic-8--events-api)
- [GitHub Issue #39](https://github.com/your-repo/issues/39)
