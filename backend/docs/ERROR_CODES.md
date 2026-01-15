# Error Codes Reference

This document provides a comprehensive reference for all error codes in the ZeroDB Agent Finance API.

Per DX Contract Section 7 (Error Semantics):
- All errors return `{ detail, error_code }`
- Error codes are stable and documented
- Validation errors use HTTP 422

## 404 Error Distinction

The API distinguishes between two types of 404 errors:

### PATH_NOT_FOUND
**When:** The API endpoint/route doesn't exist (typo in URL)
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Path '/v1/public/nonexistent' not found. Check the API documentation for valid endpoints.",
  "error_code": "PATH_NOT_FOUND"
}
```

**Common Causes:**
- Typo in the URL path
- Using an incorrect API version
- Requesting an endpoint that doesn't exist

**How to Fix:**
- Check the API documentation at `/docs` for valid endpoints
- Verify the URL path matches the documented endpoints
- Ensure you're using the correct API version prefix `/v1/public`

---

### RESOURCE_NOT_FOUND
**When:** The endpoint exists but the resource doesn't (missing data)
**HTTP Status:** 404
**Note:** This is a generic error. Use specific resource errors when possible.

**Specific Resource Errors:**

#### PROJECT_NOT_FOUND
**When:** A project with the specified ID doesn't exist
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Project not found: invalid-project-id",
  "error_code": "PROJECT_NOT_FOUND"
}
```

**Common Causes:**
- Invalid project ID in the URL
- Project was deleted
- User doesn't have access to the project

---

#### AGENT_NOT_FOUND
**When:** An agent with the specified ID doesn't exist in the project
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Agent not found: invalid-agent-id",
  "error_code": "AGENT_NOT_FOUND"
}
```

**Common Causes:**
- Invalid agent ID
- Agent was deleted
- Agent exists in a different project

---

#### TABLE_NOT_FOUND
**When:** A table with the specified ID doesn't exist in the project
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Table not found: invalid-table-id",
  "error_code": "TABLE_NOT_FOUND"
}
```

**Common Causes:**
- Invalid table ID
- Table was deleted
- Table exists in a different project

---

#### VECTOR_NOT_FOUND
**When:** A vector with the specified ID doesn't exist in the namespace
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Vector 'invalid-vector-id' not found in namespace 'default'",
  "error_code": "VECTOR_NOT_FOUND"
}
```

**Common Causes:**
- Invalid vector ID
- Vector exists in a different namespace
- Vector was deleted

---

#### RUN_NOT_FOUND
**When:** An agent run with the specified ID doesn't exist in the project
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Run not found: invalid-run-id in project project-123",
  "error_code": "RUN_NOT_FOUND"
}
```

**Common Causes:**
- Invalid run ID
- Run exists in a different project
- Run data was not properly recorded

---

## Authentication Errors

### INVALID_API_KEY
**When:** API key is invalid, missing, or malformed
**HTTP Status:** 401
**Example Response:**
```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```

**Common Causes:**
- Missing `X-API-Key` header
- Expired API key
- Malformed API key format
- API key not found in system

---

### INVALID_TOKEN
**When:** JWT token is invalid
**HTTP Status:** 401
**Example Response:**
```json
{
  "detail": "Invalid JWT token",
  "error_code": "INVALID_TOKEN"
}
```

---

### TOKEN_EXPIRED
**When:** JWT token has expired
**HTTP Status:** 401
**Example Response:**
```json
{
  "detail": "JWT token has expired",
  "error_code": "TOKEN_EXPIRED"
}
```

---

## Authorization Errors

### UNAUTHORIZED
**When:** User is not authorized to access the resource
**HTTP Status:** 403
**Example Response:**
```json
{
  "detail": "Not authorized to access this resource",
  "error_code": "UNAUTHORIZED"
}
```

---

### IMMUTABLE_RECORD
**When:** Attempt to update or delete an immutable record
**HTTP Status:** 403
**Example Response:**
```json
{
  "detail": "Cannot modify records in 'agents' table. This table is append-only for audit trail integrity. Per PRD Section 10: Agent records are immutable for non-repudiation.",
  "error_code": "IMMUTABLE_RECORD"
}
```

**Protected Tables (Append-Only):**
- `agents` - Agent registration and configuration
- `agent_memory` - Agent recall and learning data
- `compliance_events` - Regulatory audit trail
- `x402_requests` - Payment protocol transactions

---

## Validation Errors

### VALIDATION_ERROR
**When:** Request data fails validation
**HTTP Status:** 422
**Issue:** Epic 9, Issue #44 - Validation errors include loc/msg/type

**Response Structure:**
All validation errors (HTTP 422) include:
- `detail`: Summary of the first validation error (human-readable)
- `error_code`: Always set to "VALIDATION_ERROR"
- `validation_errors`: Array of validation error objects

**Validation Error Object Structure:**
Each validation error in the `validation_errors` array contains:
- `loc`: Array showing the path to the failing field (e.g., `["body", "email"]`)
- `msg`: Human-readable error message (e.g., "Field required", "Invalid email format")
- `type`: Pydantic error type identifier (e.g., "missing", "string_too_short", "value_error")

**Example Response (Single Field Error):**
```json
{
  "detail": "Validation error on field 'event_type': Field required",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {
      "loc": ["body", "event_type"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

**Example Response (Multiple Field Errors):**
```json
{
  "detail": "Validation error on field 'event_type': String should have at least 1 character",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {
      "loc": ["body", "event_type"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    },
    {
      "loc": ["body", "data"],
      "msg": "Field required",
      "type": "missing"
    },
    {
      "loc": ["body", "timestamp"],
      "msg": "Value error, timestamp must be in ISO8601 datetime format",
      "type": "value_error"
    }
  ]
}
```

**Common Validation Error Types:**
- `missing` - Required field is missing
- `string_too_short` - String is shorter than minimum length
- `string_too_long` - String exceeds maximum length
- `dict_type` - Expected a dictionary/object
- `value_error` - Custom validation failed
- `type_error` - Wrong data type provided

**Field Path (loc) Examples:**
- `["body", "name"]` - Top-level field in request body
- `["body", "metadata", "key"]` - Nested field
- `["query", "limit"]` - Query parameter
- `["path", "project_id"]` - Path parameter

**How to Handle:**
1. Check the `validation_errors` array for all failing fields
2. Use `loc` to identify which fields need correction
3. Read `msg` for human-readable guidance
4. Use `type` for programmatic error handling if needed

---

### SCHEMA_VALIDATION_ERROR
**When:** Row data doesn't match the table schema
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Row data does not match table schema",
  "error_code": "SCHEMA_VALIDATION_ERROR"
}
```

---

### MISSING_ROW_DATA
**When:** POST to `/tables/{table_id}/rows` is missing `row_data` field
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.",
  "error_code": "MISSING_ROW_DATA"
}
```

---

### INVALID_FIELD_NAME
**When:** Request contains invalid field names
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Invalid field 'data'. Use 'row_data' for inserting rows.",
  "error_code": "INVALID_FIELD_NAME"
}
```

---

### INVALID_TIMESTAMP
**When:** Timestamp format is invalid
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Invalid timestamp format. Expected ISO8601 format (RFC 3339). Valid examples: '2026-01-10T12:34:56Z', '2026-01-10T12:34:56.789Z', '2026-01-10T12:34:56+00:00', '2026-01-10T12:34:56-05:00'",
  "error_code": "INVALID_TIMESTAMP"
}
```

---

### INVALID_NAMESPACE
**When:** Namespace format is invalid
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Invalid namespace format. Namespace must contain only alphanumeric characters, underscores, and hyphens. Max length: 64 characters. Cannot start with underscore or hyphen.",
  "error_code": "INVALID_NAMESPACE"
}
```

**Validation Rules:**
- Valid characters: a-z, A-Z, 0-9, underscore, hyphen
- Max length: 64 characters
- Cannot start with underscore or hyphen
- Cannot be empty if provided

---

### INVALID_METADATA_FILTER
**When:** Metadata filter format is invalid
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Invalid metadata filter format. Filters must be dictionaries with field names as keys. Supported operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $exists, $contains. Example: {'score': {'$gte': 0.8}, 'status': {'$in': ['active', 'pending']}}",
  "error_code": "INVALID_METADATA_FILTER"
}
```

**Supported Operators:**
- `$eq` - equals (default if no operator)
- `$ne` - not equals
- `$gt`, `$gte`, `$lt`, `$lte` - numeric comparisons
- `$in` - value in array
- `$nin` - value not in array
- `$exists` - field exists/doesn't exist
- `$contains` - string contains substring

---

### INVALID_TIER
**When:** An invalid tier is specified
**HTTP Status:** 422
**Example Response:**
```json
{
  "detail": "Invalid tier 'premium'. Valid tiers are: free, basic, pro.",
  "error_code": "INVALID_TIER"
}
```

---

## Conflict Errors

### TABLE_ALREADY_EXISTS
**When:** Attempting to create a table with a duplicate name in a project
**HTTP Status:** 409
**Example Response:**
```json
{
  "detail": "Table 'users' already exists in project: project-123",
  "error_code": "TABLE_ALREADY_EXISTS"
}
```

---

### DUPLICATE_AGENT_DID
**When:** Attempting to create an agent with a duplicate DID
**HTTP Status:** 409
**Example Response:**
```json
{
  "detail": "Agent with DID 'did:ethr:0x123...' already exists in project: project-123",
  "error_code": "DUPLICATE_AGENT_DID"
}
```

---

### VECTOR_ALREADY_EXISTS
**When:** Attempting to store a vector with an ID that already exists (when `upsert=false`)
**HTTP Status:** 409
**Example Response:**
```json
{
  "detail": "Vector with ID 'vector-123' already exists in namespace 'default'. Use upsert=true to update existing vectors.",
  "error_code": "VECTOR_ALREADY_EXISTS"
}
```

---

## Rate Limiting Errors

### PROJECT_LIMIT_EXCEEDED
**When:** User exceeds project creation limit for their tier
**HTTP Status:** 429
**Example Response:**
```json
{
  "detail": "Project limit exceeded for tier 'free'. Current projects: 3/3.",
  "error_code": "PROJECT_LIMIT_EXCEEDED"
}
```

---

## Server Errors

### INTERNAL_SERVER_ERROR
**When:** An unexpected error occurred
**HTTP Status:** 500
**Example Response:**
```json
{
  "detail": "An unexpected error occurred. Please try again later.",
  "error_code": "INTERNAL_SERVER_ERROR"
}
```

---

### ZERODB_ERROR
**When:** ZeroDB API calls fail
**HTTP Status:** 502
**Example Response:**
```json
{
  "detail": "ZeroDB service error",
  "error_code": "ZERODB_ERROR"
}
```

**Common Causes:**
- ZeroDB service is unavailable
- Network timeout
- Invalid ZeroDB API response

---

### MODEL_NOT_FOUND
**When:** A requested embedding model is not found
**HTTP Status:** 404
**Example Response:**
```json
{
  "detail": "Model 'invalid-model' not found. Available models: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large",
  "error_code": "MODEL_NOT_FOUND"
}
```

---

## Best Practices

### Distinguishing Path vs Resource Errors

When you receive a 404 error, check the `error_code` field to understand the issue:

1. **PATH_NOT_FOUND**: You have a typo in the URL or are requesting an invalid endpoint
   - Solution: Check the API documentation and verify the URL path

2. **PROJECT_NOT_FOUND, AGENT_NOT_FOUND, TABLE_NOT_FOUND, etc.**: The endpoint is correct, but the resource doesn't exist
   - Solution: Verify the resource ID exists and you have access to it

### Example Error Handling

```python
import requests

response = requests.get(
    "https://api.example.com/v1/public/project-123/agents",
    headers={"X-API-Key": "your-api-key"}
)

if response.status_code == 404:
    error = response.json()

    if error["error_code"] == "PATH_NOT_FOUND":
        print(f"Invalid endpoint: {error['detail']}")
        print("Check the API documentation for valid endpoints")

    elif error["error_code"] == "PROJECT_NOT_FOUND":
        print(f"Project doesn't exist: {error['detail']}")
        print("Verify the project ID is correct")

    elif error["error_code"] == "AGENT_NOT_FOUND":
        print(f"Agent doesn't exist: {error['detail']}")
        print("Verify the agent ID is correct")
```

---

## Related Documentation

- **API Documentation**: `/docs` (Swagger UI)
- **DX Contract**: Section 7 (Error Semantics)
- **PRD**: Section 10 (Success Criteria - Deterministic Errors)
- **Issue #43**: 404 Error Distinction Implementation
- **Issue #42**: Error Response Format Consistency
