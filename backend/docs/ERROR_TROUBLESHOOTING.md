# Error Troubleshooting Guide

Top 10 Common API Errors and How to Fix Them

**Version**: 1.0.0
**Epic**: 9 (Error & Response Consistency)
**Issue**: #45
**Last Updated**: 2026-01-15

---

## Table of Contents

1. [INVALID_API_KEY (401)](#1-invalid_api_key-401)
2. [RESOURCE_NOT_FOUND (404)](#2-resource_not_found-404)
3. [PATH_NOT_FOUND (404)](#3-path_not_found-404)
4. [VALIDATION_ERROR (422)](#4-validation_error-422)
5. [MISSING_REQUIRED_FIELD (422)](#5-missing_required_field-422)
6. [PROJECT_NOT_FOUND (404)](#6-project_not_found-404)
7. [TABLE_NOT_FOUND (404)](#7-table_not_found-404)
8. [AGENT_NOT_FOUND (404)](#8-agent_not_found-404)
9. [INTERNAL_SERVER_ERROR (500)](#9-internal_server_error-500)
10. [RATE_LIMIT_EXCEEDED (429)](#10-rate_limit_exceeded-429)

---

## Quick Reference Table

| Error Code | HTTP Status | Common Cause | Quick Fix |
|------------|-------------|--------------|-----------|
| INVALID_API_KEY | 401 | Missing/wrong API key | Add X-API-Key header |
| RESOURCE_NOT_FOUND | 404 | Resource doesn't exist | Check resource ID |
| PATH_NOT_FOUND | 404 | Wrong API endpoint | Check endpoint URL |
| VALIDATION_ERROR | 422 | Invalid request data | Validate request body |
| MISSING_REQUIRED_FIELD | 422 | Missing required field | Add required fields |
| PROJECT_NOT_FOUND | 404 | Invalid project ID | Verify project exists |
| TABLE_NOT_FOUND | 404 | Invalid table ID | Verify table exists |
| AGENT_NOT_FOUND | 404 | Invalid agent ID | Verify agent exists |
| INTERNAL_SERVER_ERROR | 500 | Server-side error | Contact support |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests | Implement rate limiting |

---

## 1. INVALID_API_KEY (401)

### HTTP Status
**401 Unauthorized**

### Example Error Response
```json
{
  "detail": "Invalid or missing API key",
  "error_code": "INVALID_API_KEY"
}
```

### Common Causes
1. Missing `X-API-Key` header in request
2. API key is malformed (empty, whitespace, too short)
3. API key doesn't exist in the system
4. API key has been revoked or expired

### Fix

**Step 1**: Verify you're including the API key header

```bash
# Correct usage
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"
```

**Step 2**: Check API key format
- Demo keys: `demo_key_user{N}_{random}`
- Valid characters: alphanumeric, underscores
- Minimum length: 10 characters

**Step 3**: Verify API key exists
```bash
# Test with known demo key
export API_KEY="demo_key_user1_abc123"
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: $API_KEY"
```

**Step 4**: For production, regenerate API key if necessary
- Contact your administrator
- Generate new key from dashboard
- Update environment variables

### Prevention
- Store API keys in environment variables, never in code
- Use backend proxy pattern for client-side applications
- Implement API key rotation policies
- Monitor API key usage for suspicious activity

---

## 2. RESOURCE_NOT_FOUND (404)

### HTTP Status
**404 Not Found**

### Example Error Response
```json
{
  "detail": "Vector 'vec_abc123' not found in namespace 'default'",
  "error_code": "RESOURCE_NOT_FOUND"
}
```

### Common Causes
1. Resource ID doesn't exist in database
2. Resource was deleted
3. Wrong namespace or project context
4. Typo in resource ID

### Fix

**Step 1**: Verify resource exists by listing all resources

```bash
# List all vectors in namespace
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/vectors?namespace=default" \
  -H "X-API-Key: $API_KEY"

# List all agents in project
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY"
```

**Step 2**: Check resource ID format
- Ensure no leading/trailing whitespace
- Verify correct capitalization (IDs are case-sensitive)
- Use URL encoding for special characters

**Step 3**: Verify correct project/namespace context

```bash
# Check if resource exists in different namespace
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/vectors?namespace=agents" \
  -H "X-API-Key: $API_KEY"
```

**Step 4**: Create resource if it should exist

```bash
# Create missing agent
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "did": "did:ethr:0x123",
    "role": "researcher",
    "name": "Research Agent"
  }'
```

### Prevention
- Implement existence checks before operations
- Cache resource IDs after creation
- Use descriptive, stable resource IDs
- Log resource creation/deletion for audit trail

---

## 3. PATH_NOT_FOUND (404)

### HTTP Status
**404 Not Found**

### Example Error Response
```json
{
  "detail": "Path '/v1/public/project' not found. Check the API documentation for valid endpoints.",
  "error_code": "PATH_NOT_FOUND"
}
```

### Common Causes
1. Typo in API endpoint URL
2. Missing API version prefix (/v1)
3. Using wrong HTTP method for endpoint
4. Endpoint doesn't exist in current API version

### Fix

**Step 1**: Check API documentation for correct endpoint

```bash
# Wrong (missing 's' in projects)
curl -X GET "http://localhost:8000/v1/public/project"

# Correct
curl -X GET "http://localhost:8000/v1/public/projects"
```

**Step 2**: Verify API version prefix

```bash
# Wrong (missing /v1)
curl -X GET "http://localhost:8000/public/projects"

# Correct
curl -X GET "http://localhost:8000/v1/public/projects"
```

**Step 3**: Check HTTP method

```bash
# Wrong (GET instead of POST)
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -d '{"did": "..."}'

# Correct
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -d '{"did": "..."}'
```

**Step 4**: List available endpoints

```bash
# View API documentation
open http://localhost:8000/docs

# Or check OpenAPI spec
curl -X GET "http://localhost:8000/openapi.json"
```

### Prevention
- Use API client libraries with built-in endpoint definitions
- Bookmark API documentation for reference
- Implement automated API tests to catch endpoint changes
- Use environment variables for base URLs

---

## 4. VALIDATION_ERROR (422)

### HTTP Status
**422 Unprocessable Entity**

### Example Error Response
```json
{
  "detail": [
    {
      "loc": ["body", "vector_embedding"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

### Common Causes
1. Request body doesn't match schema
2. Missing required fields
3. Wrong data type (string instead of number)
4. Invalid field values (negative number where positive required)

### Fix

**Step 1**: Read validation error details
- `loc`: Field location (e.g., ["body", "field_name"])
- `msg`: Error message describing the problem
- `type`: Error type (missing, type_error, value_error)

**Step 2**: Fix field types

```bash
# Wrong (score as string)
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/vectors" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2],
    "document": "test",
    "metadata": {"score": "0.8"}
  }'

# Correct (score as number)
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/vectors" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2],
    "document": "test",
    "metadata": {"score": 0.8}
  }'
```

**Step 3**: Add missing required fields

```bash
# Check API documentation for required fields
curl -X GET "http://localhost:8000/docs"

# Include all required fields
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "did": "did:ethr:0x123",
    "role": "researcher",
    "name": "Research Agent"
  }'
```

**Step 4**: Validate JSON syntax

```bash
# Use jq to validate JSON
echo '{"field": "value"}' | jq .

# Or use online JSON validator
```

### Prevention
- Generate request bodies from OpenAPI schema
- Use API client libraries with built-in validation
- Implement request validation in your code before sending
- Create reusable request templates

---

## 5. MISSING_REQUIRED_FIELD (422)

### HTTP Status
**422 Unprocessable Entity**

### Example Error Response
```json
{
  "detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.",
  "error_code": "MISSING_ROW_DATA"
}
```

### Common Causes
1. Forgot to include required field in request
2. Using wrong field name (data vs row_data)
3. Field is null or empty when it shouldn't be
4. Nested required field is missing

### Fix

**Step 1**: Check error message for specific field name

```bash
# Wrong (using 'data' instead of 'row_data')
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}/rows" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"field1": "value1"}
  }'

# Correct (using 'row_data')
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}/rows" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "row_data": {"field1": "value1"}
  }'
```

**Step 2**: Review API documentation for required fields

```bash
# Check endpoint documentation
open http://localhost:8000/docs#/tables/create_table

# Required fields are marked with asterisk (*)
```

**Step 3**: Include all required fields with valid values

```bash
# Complete example with all required fields
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "did": "did:ethr:0x123456",
    "role": "researcher",
    "name": "Financial Research Agent",
    "description": "Analyzes market data",
    "scope": "PROJECT"
  }'
```

**Step 4**: Validate field names against schema

```bash
# Get OpenAPI schema
curl -X GET "http://localhost:8000/openapi.json" | jq '.components.schemas.AgentCreateRequest'
```

### Prevention
- Use API client libraries with type checking
- Create request templates for common operations
- Implement automated tests for API requests
- Document required vs optional fields in your code

---

## 6. PROJECT_NOT_FOUND (404)

### HTTP Status
**404 Not Found**

### Example Error Response
```json
{
  "detail": "Project not found: proj_invalid_123",
  "error_code": "PROJECT_NOT_FOUND"
}
```

### Common Causes
1. Project ID doesn't exist
2. Project was deleted
3. User doesn't have access to project
4. Wrong project ID in URL path

### Fix

**Step 1**: List all accessible projects

```bash
# Get all projects for your API key
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: $API_KEY"

# Response includes all project IDs
{
  "projects": [
    {"id": "proj_demo_u1_001", "name": "Agent Finance Demo"},
    {"id": "proj_demo_u1_002", "name": "X402 Integration"}
  ],
  "total": 2
}
```

**Step 2**: Use correct project ID from list

```bash
# Copy exact project ID from list
export PROJECT_ID="proj_demo_u1_001"

# Use in subsequent requests
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY"
```

**Step 3**: Verify project ownership

```bash
# Projects are scoped to API key
# Use the API key associated with the project

# Demo User 1 API Key
export API_KEY="demo_key_user1_abc123"

# Demo User 1's Projects
export PROJECT_ID="proj_demo_u1_001"
```

**Step 4**: Create project if needed

```bash
# Create new project (if endpoint available)
curl -X POST "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Project",
    "tier": "FREE"
  }'
```

### Prevention
- Cache project IDs after retrieving project list
- Store project ID in environment variables
- Implement project existence check before operations
- Use descriptive project names to avoid confusion

---

## 7. TABLE_NOT_FOUND (404)

### HTTP Status
**404 Not Found**

### Example Error Response
```json
{
  "detail": "Table not found: table_abc123",
  "error_code": "TABLE_NOT_FOUND"
}
```

### Common Causes
1. Table ID doesn't exist in project
2. Table was deleted
3. Wrong table ID or typo
4. Table belongs to different project

### Fix

**Step 1**: List all tables in project

```bash
# Get all tables for project
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/tables" \
  -H "X-API-Key: $API_KEY"

# Response includes all table IDs
{
  "tables": [
    {"id": "table_001", "table_name": "compliance_events"},
    {"id": "table_002", "table_name": "agent_logs"}
  ],
  "total": 2
}
```

**Step 2**: Use correct table ID

```bash
# Copy exact table ID from list
export TABLE_ID="table_001"

# Use in requests
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}" \
  -H "X-API-Key: $API_KEY"
```

**Step 3**: Verify table belongs to project

```bash
# Tables are scoped to projects
# Ensure PROJECT_ID and TABLE_ID match

# Wrong (table from different project)
curl -X GET "http://localhost:8000/v1/public/proj_001/tables/table_from_proj_002"

# Correct (table from same project)
curl -X GET "http://localhost:8000/v1/public/proj_001/tables/table_from_proj_001"
```

**Step 4**: Create table if needed

```bash
# Create new table with schema
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "compliance_events",
    "description": "Regulatory compliance audit trail",
    "schema": {
      "fields": {
        "event_type": {"type": "string", "required": true},
        "timestamp": {"type": "timestamp", "required": true},
        "agent_id": {"type": "string", "required": true},
        "data": {"type": "json", "required": false}
      },
      "indexes": ["event_type", "timestamp", "agent_id"]
    }
  }'
```

### Prevention
- Cache table IDs after creation
- Use consistent table naming conventions
- Implement table existence checks
- Document table schemas in code comments

---

## 8. AGENT_NOT_FOUND (404)

### HTTP Status
**404 Not Found**

### Example Error Response
```json
{
  "detail": "Agent not found: agent_xyz789",
  "error_code": "AGENT_NOT_FOUND"
}
```

### Common Causes
1. Agent ID doesn't exist in project
2. Agent was deleted
3. Wrong agent ID or typo
4. Agent belongs to different project

### Fix

**Step 1**: List all agents in project

```bash
# Get all agents for project
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY"

# Response includes all agent IDs
{
  "agents": [
    {
      "id": "agent_001",
      "did": "did:ethr:0x123",
      "role": "researcher",
      "name": "Research Agent"
    }
  ],
  "total": 1
}
```

**Step 2**: Use correct agent ID

```bash
# Copy exact agent ID from list
export AGENT_ID="agent_001"

# Use in requests
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents/${AGENT_ID}" \
  -H "X-API-Key: $API_KEY"
```

**Step 3**: Verify agent belongs to project

```bash
# Agents are scoped to projects
# Ensure PROJECT_ID and AGENT_ID match

# Check agent's project_id field
curl -X GET "http://localhost:8000/v1/public/${PROJECT_ID}/agents/${AGENT_ID}" \
  -H "X-API-Key: $API_KEY" | jq '.project_id'
```

**Step 4**: Create agent if needed

```bash
# Create new agent profile
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/agents" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "did": "did:ethr:0x123456789",
    "role": "researcher",
    "name": "Financial Research Agent",
    "description": "Analyzes market trends and financial data",
    "scope": "PROJECT"
  }'
```

### Prevention
- Cache agent IDs after creation
- Use agent DIDs for stable identifiers
- Implement agent existence checks
- Store agent metadata for quick lookups

---

## 9. INTERNAL_SERVER_ERROR (500)

### HTTP Status
**500 Internal Server Error**

### Example Error Response
```json
{
  "detail": "An internal server error occurred. Please try again later.",
  "error_code": "INTERNAL_SERVER_ERROR"
}
```

### Common Causes
1. Unexpected server-side error
2. Database connection failure
3. External service (ZeroDB) unavailable
4. Server resource exhaustion
5. Unhandled exception in code

### Fix

**Step 1**: Retry the request after a brief delay

```bash
# Simple retry with exponential backoff
for i in 1 2 4 8; do
  echo "Attempt with ${i}s delay..."
  sleep $i
  response=$(curl -s -w "\n%{http_code}" \
    -X GET "http://localhost:8000/v1/public/projects" \
    -H "X-API-Key: $API_KEY")

  http_code=$(echo "$response" | tail -n1)
  if [ "$http_code" = "200" ]; then
    echo "Success!"
    break
  fi
done
```

**Step 2**: Check service health

```bash
# Health check endpoint
curl -X GET "http://localhost:8000/health"

# Expected response
{
  "status": "healthy",
  "service": "ZeroDB Agent Finance API",
  "version": "1.0.0"
}
```

**Step 3**: Review request for issues

```bash
# Simplify request to minimal valid example
curl -X GET "http://localhost:8000/v1/public/projects" \
  -H "X-API-Key: demo_key_user1_abc123"

# If simple request works, issue is with complex request
```

**Step 4**: Contact support with details

Provide the following information:
- Timestamp of error
- Request method and endpoint
- Request body (sanitized, no sensitive data)
- Response status code and body
- Your API key (first 10 characters only)

```bash
# Example support request format
echo "Error Report:
Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Endpoint: POST /v1/public/proj_001/agents
Status: 500
API Key: demo_key_u...
Request: {sanitized JSON}
Response: {error JSON}
"
```

### Prevention
- Implement request timeout handling
- Use exponential backoff for retries
- Monitor API health endpoint
- Implement circuit breaker pattern
- Log all requests for debugging

---

## 10. RATE_LIMIT_EXCEEDED (429)

### HTTP Status
**429 Too Many Requests**

### Example Error Response
```json
{
  "detail": "Rate limit exceeded. Maximum 100 requests per minute. Try again in 30 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

### Common Causes
1. Too many requests in short time period
2. No rate limiting in client code
3. Retry loop without backoff
4. Parallel requests exceeding limit
5. Shared API key across multiple services

### Fix

**Step 1**: Implement exponential backoff

```bash
# Example retry with exponential backoff
retry_request() {
  local max_retries=5
  local retry=0
  local delay=1

  while [ $retry -lt $max_retries ]; do
    response=$(curl -s -w "\n%{http_code}" \
      -X GET "$1" \
      -H "X-API-Key: $API_KEY")

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
      echo "$response" | head -n -1
      return 0
    elif [ "$http_code" = "429" ]; then
      echo "Rate limited. Waiting ${delay}s..." >&2
      sleep $delay
      delay=$((delay * 2))
      retry=$((retry + 1))
    else
      echo "Error: $http_code" >&2
      return 1
    fi
  done

  echo "Max retries exceeded" >&2
  return 1
}

# Usage
retry_request "http://localhost:8000/v1/public/projects"
```

**Step 2**: Implement request throttling

```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []

    def wait_if_needed(self):
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove old requests
        self.requests = [r for r in self.requests if r > cutoff]

        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            oldest = self.requests[0]
            wait_seconds = (oldest + timedelta(seconds=self.window_seconds) - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                self.requests = []

        self.requests.append(now)

# Usage
limiter = RateLimiter(max_requests=100, window_seconds=60)

def make_request(url):
    limiter.wait_if_needed()
    # Make your API request here
    response = requests.get(url, headers={"X-API-Key": api_key})
    return response
```

**Step 3**: Use batch operations when available

```bash
# Instead of multiple single inserts
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}/rows" \
  -d '{"row_data": {"field": "value1"}}'
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}/rows" \
  -d '{"row_data": {"field": "value2"}}'

# Use batch insert if available
curl -X POST "http://localhost:8000/v1/public/${PROJECT_ID}/tables/${TABLE_ID}/rows/batch" \
  -d '{
    "rows": [
      {"field": "value1"},
      {"field": "value2"}
    ]
  }'
```

**Step 4**: Monitor request rates

```bash
# Add request tracking
log_request() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") $1" >> api_requests.log
}

# Count requests in last minute
count_recent_requests() {
  one_minute_ago=$(date -u -d '1 minute ago' +"%Y-%m-%dT%H:%M:%SZ")
  grep -c "$one_minute_ago" api_requests.log || echo 0
}

# Check before making request
if [ $(count_recent_requests) -lt 90 ]; then
  curl -X GET "http://localhost:8000/v1/public/projects" \
    -H "X-API-Key: $API_KEY"
  log_request "GET /v1/public/projects"
else
  echo "Approaching rate limit, waiting..."
  sleep 10
fi
```

### Prevention
- Implement client-side rate limiting
- Use exponential backoff for all retries
- Cache responses when possible
- Use webhooks instead of polling
- Distribute requests across multiple API keys if permitted
- Monitor request rates in application metrics

---

## Additional Resources

### Related Documentation
- [ERROR_CODES.md](./ERROR_CODES.md) - Complete error code reference
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [DX Contract](../DEVELOPER_EXPERIENCE.md) - Error response standards

### Best Practices
1. **Always check HTTP status codes** before parsing response body
2. **Implement retry logic** with exponential backoff for 5xx errors
3. **Validate requests** before sending to catch errors early
4. **Use environment variables** for API keys and base URLs
5. **Log all errors** with timestamp and request details
6. **Monitor error rates** to detect issues early

### Debugging Checklist
- [ ] Verify API key is correct and not expired
- [ ] Check request URL for typos
- [ ] Validate JSON request body syntax
- [ ] Ensure all required fields are included
- [ ] Verify resource IDs exist
- [ ] Check project/namespace context
- [ ] Review API documentation for endpoint details
- [ ] Test with minimal request first
- [ ] Check service health endpoint
- [ ] Review rate limit status

### Getting Help
- Check the [API Documentation](http://localhost:8000/docs)
- Review [GitHub Issues](https://github.com/your-repo/issues)
- Contact support with error details
- Search existing error discussions

---

**Note**: This guide covers the most common errors. For a complete list of all error codes and their meanings, see [ERROR_CODES.md](./ERROR_CODES.md).
