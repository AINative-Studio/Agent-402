# Epic 7, Issue 1: Table Creation with Schema Definitions

## Summary

Implementation of table creation and management endpoints for ZeroDB Integration per PRD Section 6 (Compliance records).

## Issue Details

- **Epic:** 7 - ZeroDB Integration
- **Issue:** 1 - Table Creation with Schema Definitions
- **Story Points:** 2
- **PRD Reference:** Section 6 (ZeroDB Integration - Compliance records)

## Requirements Implemented

1. **POST /v1/public/{project_id}/tables** - Create a new table
2. **GET /v1/public/{project_id}/tables** - List all tables
3. **GET /v1/public/{project_id}/tables/{table_id}** - Get table details with schema
4. **DELETE /v1/public/{project_id}/tables/{table_id}** - Delete a table
5. Table names unique within project
6. Return `TABLE_ALREADY_EXISTS` error (409) for duplicate names

## Files Created/Modified

### Created Files

| File | Description |
|------|-------------|
| `backend/app/schemas/tables.py` | Request/response Pydantic schemas |
| `backend/app/services/table_service.py` | Business logic for table operations |
| `backend/app/api/tables.py` | FastAPI router with endpoints |
| `docs/issues/ISSUE_EPIC7_1_TABLE_CREATION.md` | This documentation |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/main.py` | Added tables router import and registration |
| `backend/app/core/errors.py` | Added `TableAlreadyExistsError` and `TableNotFoundError` |

## API Endpoints

### POST /v1/public/{project_id}/tables

Create a new table with schema definition.

**Request Body:**
```json
{
  "table_name": "compliance_events",
  "description": "Stores compliance event records for audit trail",
  "schema": {
    "fields": {
      "event_type": { "type": "string", "required": true },
      "agent_id": { "type": "string", "required": true },
      "payload": { "type": "json", "required": false },
      "timestamp": { "type": "timestamp", "required": true }
    },
    "indexes": ["event_type", "agent_id"]
  }
}
```

**Response (201 Created):**
```json
{
  "id": "tbl_abc123def456",
  "table_name": "compliance_events",
  "description": "Stores compliance event records for audit trail",
  "schema": {
    "fields": {
      "event_type": { "type": "string", "required": true },
      "agent_id": { "type": "string", "required": true },
      "payload": { "type": "json", "required": false },
      "timestamp": { "type": "timestamp", "required": true }
    },
    "indexes": ["event_type", "agent_id"]
  },
  "project_id": "proj_demo_u1_001",
  "row_count": 0,
  "created_at": "2026-01-11T00:00:00Z",
  "updated_at": null
}
```

**Error Response (409 Conflict):**
```json
{
  "detail": "Table 'compliance_events' already exists in project: proj_demo_u1_001",
  "error_code": "TABLE_ALREADY_EXISTS"
}
```

### GET /v1/public/{project_id}/tables

List all tables for a project.

**Response (200 OK):**
```json
{
  "tables": [
    {
      "id": "tbl_abc123def456",
      "table_name": "compliance_events",
      "description": "Stores compliance event records",
      "schema": { ... },
      "project_id": "proj_demo_u1_001",
      "row_count": 150,
      "created_at": "2026-01-11T00:00:00Z",
      "updated_at": null
    }
  ],
  "total": 1
}
```

### GET /v1/public/{project_id}/tables/{table_id}

Get table details by ID.

**Response (200 OK):**
```json
{
  "id": "tbl_abc123def456",
  "table_name": "compliance_events",
  "description": "Stores compliance event records",
  "schema": {
    "fields": {
      "event_type": { "type": "string", "required": true },
      "agent_id": { "type": "string", "required": true }
    },
    "indexes": ["event_type", "agent_id"]
  },
  "project_id": "proj_demo_u1_001",
  "row_count": 150,
  "created_at": "2026-01-11T00:00:00Z",
  "updated_at": null
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Table not found: tbl_invalid",
  "error_code": "TABLE_NOT_FOUND"
}
```

### DELETE /v1/public/{project_id}/tables/{table_id}

Delete a table and all its data.

**Response (200 OK):**
```json
{
  "id": "tbl_abc123def456",
  "table_name": "compliance_events",
  "deleted": true,
  "deleted_at": "2026-01-11T12:00:00Z"
}
```

## Supported Field Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text data | `"hello world"` |
| `integer` | Whole numbers | `42` |
| `float` | Decimal numbers | `3.14159` |
| `boolean` | true/false values | `true` |
| `json` | Nested JSON objects | `{"key": "value"}` |
| `timestamp` | ISO 8601 datetime strings | `"2026-01-11T12:00:00Z"` |

## Table Name Rules

- Must be unique within the project
- Must start with a lowercase letter
- Can only contain lowercase letters, numbers, and underscores
- Maximum 100 characters
- Pattern: `^[a-z][a-z0-9_]*$`

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `TABLE_ALREADY_EXISTS` | 409 | Table name already exists in project |
| `TABLE_NOT_FOUND` | 404 | Table ID not found or not in project |
| `PROJECT_NOT_FOUND` | 404 | Project does not exist |
| `UNAUTHORIZED` | 403 | User not authorized for project |
| `INVALID_API_KEY` | 401 | Missing or invalid API key |

## Architecture

```
backend/app/
  api/
    tables.py          # FastAPI router (HTTP layer)
  schemas/
    tables.py          # Pydantic request/response models
  services/
    table_service.py   # Business logic layer
  core/
    errors.py          # Custom error classes
```

## Schema Design

### TableSchema Model

The `TableSchema` model validates:
- Fields dictionary with at least one field
- Each field has a valid type (string, integer, float, boolean, json, timestamp)
- Each field can specify required (default: false) and default value
- Indexes must reference existing field names

### Field Validation

- Field names follow standard naming conventions
- Index fields are validated to exist in schema
- Default values are type-checked where possible

## Authentication

All endpoints require the `X-API-Key` header. The API key determines:
- User identity
- Project access permissions
- Rate limiting tier

## DX Contract Compliance

Per DX Contract Section 7 (Error Semantics):
- All errors return `{ detail, error_code }`
- Error codes are stable and documented
- Validation errors use HTTP 422

## Future Enhancements

- Schema migrations and versioning
- Field-level validation rules
- Foreign key relationships
- Row-level security
- Audit logging for schema changes
