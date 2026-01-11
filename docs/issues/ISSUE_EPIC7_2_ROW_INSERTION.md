# Epic 7, Issue 2: Row Insertion with row_data Field

## Overview

Implementation of the row insertion endpoint that allows developers to insert rows using the `row_data` field. This issue is part of Epic 7 (Tables API) and follows PRD Section 10 (Contract stability) requirements.

## Issue Details

- **Issue:** As a developer, I can insert rows using `row_data`.
- **Story Points:** 2
- **PRD Reference:** Section 10 (Contract stability)

## Requirements Implemented

### 1. POST Endpoint

Created `POST /v1/public/{project_id}/tables/{table_id}/rows` endpoint for row insertion.

### 2. Request Schema with row_data Field

The request schema uses `row_data` field (NOT `data` or `rows`) per PRD Section 10:

```json
{
  "row_data": {
    "field1": "value1",
    "field2": 123
  }
}
```

### 3. Response with Generated IDs and Timestamps

Response includes generated `row_id` and `created_at` timestamp:

```json
{
  "rows": [
    {
      "row_id": "row_abc123def456",
      "created_at": "2025-01-01T12:00:00Z",
      "row_data": {
        "field1": "value1",
        "field2": 123
      }
    }
  ],
  "inserted_count": 1
}
```

### 4. Schema Validation

Row data is validated against the table schema with type checking:

- Supports field types: `string`, `integer`, `float`, `boolean`, `json`, `timestamp`
- Validates required fields are present
- Type coercion for numeric types (int accepted for float)
- Returns `SCHEMA_VALIDATION_ERROR` (422) if validation fails

### 5. Error Handling

- `TABLE_NOT_FOUND` (404) - If table doesn't exist in project
- `SCHEMA_VALIDATION_ERROR` (422) - If data doesn't match table schema
- `MISSING_ROW_DATA` (422) - If row_data field is missing
- `INVALID_FIELD_NAME` (422) - If using `data`, `rows`, `items`, or `records` instead

### 6. Batch Insert Support

Supports batch insert with array of rows:

```json
{
  "row_data": [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"}
  ]
}
```

## Files Created/Modified

### New Files

- `/Volumes/Cody/projects/Agent402/backend/app/models/table.py` - Table domain model with schema definitions
- `/Volumes/Cody/projects/Agent402/backend/app/models/row.py` - Row domain model
- `/Volumes/Cody/projects/Agent402/backend/app/services/table_store.py` - In-memory table storage
- `/Volumes/Cody/projects/Agent402/backend/app/services/row_store.py` - In-memory row storage

### Modified Files

- `/Volumes/Cody/projects/Agent402/backend/app/schemas/rows.py` - Added `RowInsertRequest`, `InsertedRow`, `RowInsertResponse`, `SchemaValidationErrorDetail`, `RowErrorResponse` schemas
- `/Volumes/Cody/projects/Agent402/backend/app/services/row_service.py` - Added schema validation and batch insert methods
- `/Volumes/Cody/projects/Agent402/backend/app/core/errors.py` - Added `SchemaValidationError` class
- `/Volumes/Cody/projects/Agent402/backend/app/api/rows.py` - Endpoint already existed, uses row_service

## API Contract

### Request

```http
POST /v1/public/{project_id}/tables/{table_id}/rows
Content-Type: application/json
X-API-Key: <api-key>

{
  "row_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  }
}
```

### Success Response (201 Created)

```json
{
  "rows": [
    {
      "row_id": "row_abc123def456",
      "created_at": "2025-01-01T12:00:00Z",
      "row_data": {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
      }
    }
  ],
  "inserted_count": 1
}
```

### Error Responses

#### TABLE_NOT_FOUND (404)

```json
{
  "detail": "Table not found: tbl_nonexistent",
  "error_code": "TABLE_NOT_FOUND"
}
```

#### SCHEMA_VALIDATION_ERROR (422)

```json
{
  "detail": "Field 'age' expected type 'integer' but got 'string'",
  "error_code": "SCHEMA_VALIDATION_ERROR"
}
```

#### MISSING_ROW_DATA (422)

```json
{
  "detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.",
  "error_code": "MISSING_ROW_DATA"
}
```

## Schema Validation Details

The service validates row data against the table schema:

1. **Required Field Check**: Ensures all required fields are present
2. **Type Validation**: Validates each field's type matches the schema
3. **Default Values**: Applies default values for optional fields not provided
4. **Flexible Schema**: Extra fields not in schema are allowed (NoSQL approach)

### Supported Field Types

| Type | Accepts |
|------|---------|
| `string` | String values only |
| `integer` | Integer values (not booleans) |
| `float` | Float or integer values (numeric flexibility) |
| `boolean` | Boolean values only |
| `json` | Dictionary or list objects |
| `timestamp` | ISO 8601 strings or datetime objects |

## Batch Insert Performance

The implementation supports efficient batch inserts:

- Single transaction for all rows
- Validation runs on all rows before any insertion
- Early failure if any row fails validation
- Row index included in error details for debugging

## DX Contract Compliance

- All errors return `{ detail, error_code }` format
- Consistent HTTP status codes per DX Contract Section 7
- Clear error messages with actionable information
- Deterministic validation behavior per PRD Section 10

## Testing Recommendations

1. **Single Row Insert**: Test basic insertion with valid data
2. **Batch Insert**: Test insertion of multiple rows
3. **Schema Validation**: Test type checking for each field type
4. **Required Fields**: Test missing required field handling
5. **Default Values**: Verify default values are applied
6. **Invalid Table**: Test TABLE_NOT_FOUND error
7. **Invalid Field Names**: Test MISSING_ROW_DATA and INVALID_FIELD_NAME errors

## Dependencies

- Epic 7, Issue 1: Table creation with schema definitions (tables must exist)
- Epic 7, Issue 3: Deterministic errors for missing row_data (error handling)
