# Error Codes Reference

This document provides a comprehensive reference for all error codes returned by the ZeroDB Agent Finance API.

## Overview

Per DX Contract Section 7 (Error Semantics), all API error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE"
}
```

## Error Code Format

- All error codes use **UPPER_SNAKE_CASE** format
- Error codes are **stable** and will not change between releases
- Error codes are **deterministic** - the same error always produces the same code

## Authentication Errors (HTTP 401)

### INVALID_API_KEY
- **Status:** 401 Unauthorized
- **Description:** API key is missing, invalid, malformed, or expired
- **Example:** `{"detail": "Invalid or missing API key", "error_code": "INVALID_API_KEY"}`

### INVALID_TOKEN
- **Status:** 401 Unauthorized
- **Description:** JWT token is invalid or malformed
- **Example:** `{"detail": "Invalid JWT token", "error_code": "INVALID_TOKEN"}`

### TOKEN_EXPIRED
- **Status:** 401 Unauthorized
- **Description:** JWT token has expired
- **Example:** `{"detail": "JWT token has expired", "error_code": "TOKEN_EXPIRED"}`

## Authorization Errors (HTTP 403)

### UNAUTHORIZED
- **Status:** 403 Forbidden
- **Description:** User lacks permission to access the resource
- **Example:** `{"detail": "Not authorized to access this resource", "error_code": "UNAUTHORIZED"}`

### IMMUTABLE_RECORD
- **Status:** 403 Forbidden
- **Description:** Attempt to modify or delete an immutable (append-only) record
- **Protected Tables:** agents, agent_memory, compliance_events, x402_requests
- **Example:** `{"detail": "Cannot update records in 'agents' table. This table is append-only for audit trail integrity.", "error_code": "IMMUTABLE_RECORD"}`

## Not Found Errors (HTTP 404)

### PATH_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The API endpoint/route does not exist (typo in URL)
- **Example:** `{"detail": "Path '/v1/public/invalid' not found. Check the API documentation.", "error_code": "PATH_NOT_FOUND"}`

### RESOURCE_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** Generic resource not found (endpoint exists, resource doesn't)
- **Example:** `{"detail": "Resource 'xyz' not found", "error_code": "RESOURCE_NOT_FOUND"}`

### PROJECT_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The specified project does not exist
- **Example:** `{"detail": "Project not found: project_123", "error_code": "PROJECT_NOT_FOUND"}`

### AGENT_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The specified agent does not exist
- **Example:** `{"detail": "Agent not found: agent_456", "error_code": "AGENT_NOT_FOUND"}`

### TABLE_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The specified table does not exist
- **Example:** `{"detail": "Table not found: table_789", "error_code": "TABLE_NOT_FOUND"}`

### VECTOR_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The specified vector does not exist
- **Example:** `{"detail": "Vector 'vec_123' not found in namespace 'default'", "error_code": "VECTOR_NOT_FOUND"}`

### MODEL_NOT_FOUND
- **Status:** 404 Not Found
- **Description:** The requested embedding model is not available
- **Example:** `{"detail": "Model 'gpt-5' not found. Available models: text-embedding-ada-002", "error_code": "MODEL_NOT_FOUND"}`

## Conflict Errors (HTTP 409)

### DUPLICATE_AGENT_DID
- **Status:** 409 Conflict
- **Description:** An agent with the specified DID already exists
- **Example:** `{"detail": "Agent with DID 'did:ethr:0x123' already exists in project: project_456", "error_code": "DUPLICATE_AGENT_DID"}`

### TABLE_ALREADY_EXISTS
- **Status:** 409 Conflict
- **Description:** A table with the specified name already exists
- **Example:** `{"detail": "Table 'users' already exists in project: project_123", "error_code": "TABLE_ALREADY_EXISTS"}`

### VECTOR_ALREADY_EXISTS
- **Status:** 409 Conflict
- **Description:** A vector with the specified ID already exists
- **Example:** `{"detail": "Vector with ID 'vec_123' already exists in namespace 'default'. Use upsert=true to update.", "error_code": "VECTOR_ALREADY_EXISTS"}`

## Validation Errors (HTTP 422)

### VALIDATION_ERROR
- **Status:** 422 Unprocessable Entity
- **Description:** Request data failed validation
- **Example:** `{"detail": "Validation error on field 'email': Invalid format", "error_code": "VALIDATION_ERROR", "validation_errors": [...]}`

### INVALID_TIER
- **Status:** 422 Unprocessable Entity
- **Description:** The specified tier is not valid
- **Example:** `{"detail": "Invalid tier 'premium'. Valid tiers are: free, pro.", "error_code": "INVALID_TIER"}`

### INVALID_NAMESPACE
- **Status:** 422 Unprocessable Entity
- **Description:** Namespace format is invalid
- **Example:** `{"detail": "Invalid namespace format. Must be alphanumeric with underscores/hyphens.", "error_code": "INVALID_NAMESPACE"}`

### INVALID_METADATA_FILTER
- **Status:** 422 Unprocessable Entity
- **Description:** Metadata filter format is invalid
- **Example:** `{"detail": "Invalid metadata filter format.", "error_code": "INVALID_METADATA_FILTER"}`

### INVALID_TIMESTAMP
- **Status:** 422 Unprocessable Entity
- **Description:** Timestamp format is invalid (not ISO8601)
- **Example:** `{"detail": "Invalid timestamp format. Expected ISO8601 format.", "error_code": "INVALID_TIMESTAMP"}`

### MISSING_ROW_DATA
- **Status:** 422 Unprocessable Entity
- **Description:** Required row_data field is missing
- **Example:** `{"detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.", "error_code": "MISSING_ROW_DATA"}`

### INVALID_FIELD_NAME
- **Status:** 422 Unprocessable Entity
- **Description:** Request contains invalid field names
- **Example:** `{"detail": "Invalid field 'data'. Use 'row_data' for inserting rows.", "error_code": "INVALID_FIELD_NAME"}`

### SCHEMA_VALIDATION_ERROR
- **Status:** 422 Unprocessable Entity
- **Description:** Row data doesn't match table schema
- **Example:** `{"detail": "Row data does not match table schema", "error_code": "SCHEMA_VALIDATION_ERROR"}`

## Rate Limiting Errors (HTTP 429)

### PROJECT_LIMIT_EXCEEDED
- **Status:** 429 Too Many Requests
- **Description:** Project creation limit exceeded for current tier
- **Example:** `{"detail": "Project limit exceeded for tier 'free'. Current projects: 5/5.", "error_code": "PROJECT_LIMIT_EXCEEDED"}`

### RATE_LIMIT_EXCEEDED
- **Status:** 429 Too Many Requests
- **Description:** Rate limit exceeded
- **Example:** `{"detail": "Rate limit exceeded. Please try again later.", "error_code": "RATE_LIMIT_EXCEEDED"}`

## Server Errors (HTTP 5xx)

### INTERNAL_SERVER_ERROR
- **Status:** 500 Internal Server Error
- **Description:** An unexpected internal server error occurred
- **Example:** `{"detail": "An unexpected error occurred. Please try again later.", "error_code": "INTERNAL_SERVER_ERROR"}`

### BAD_GATEWAY
- **Status:** 502 Bad Gateway
- **Description:** Error communicating with upstream service
- **Example:** `{"detail": "Bad gateway error", "error_code": "BAD_GATEWAY"}`

### SERVICE_UNAVAILABLE
- **Status:** 503 Service Unavailable
- **Description:** The service is temporarily unavailable
- **Example:** `{"detail": "Service temporarily unavailable", "error_code": "SERVICE_UNAVAILABLE"}`

### GATEWAY_TIMEOUT
- **Status:** 504 Gateway Timeout
- **Description:** Upstream service timed out
- **Example:** `{"detail": "Gateway timeout", "error_code": "GATEWAY_TIMEOUT"}`

## Best Practices

### Error Handling Example

```python
import requests

response = requests.get("/v1/public/projects", headers={"X-API-Key": "your-key"})

if response.status_code != 200:
    error = response.json()
    error_code = error.get("error_code")

    if error_code == "INVALID_API_KEY":
        # Handle authentication error
        refresh_api_key()
    elif error_code == "PROJECT_LIMIT_EXCEEDED":
        # Handle quota exceeded
        upgrade_tier()
    else:
        # Generic error handling
        print(f"Error: {error['detail']}")
```

### Retry Logic for Transient Errors

```python
RETRYABLE_ERRORS = [
    "INTERNAL_SERVER_ERROR",
    "SERVICE_UNAVAILABLE",
    "RATE_LIMIT_EXCEEDED"
]

def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()

        error = response.json()
        if error.get("error_code") in RETRYABLE_ERRORS:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            continue

        raise Exception(f"API Error: {error['detail']}")
```

## Related Documentation

- [API Documentation](/docs) - Swagger UI
- [DX Contract](../PRD.md#10-success-criteria-dx-contract) - Section 7 (Error Semantics)
- [Authentication Guide](./API_KEY_AUTH_README.md)
