# Issue Implementation: Epic 7, Issue 4 - Row Pagination

## Summary

**Issue:** As a developer, I can list rows with pagination. (2 pts)
**PRD Reference:** Section 9 (Demo verification)
**Epic:** Epic 7 - Tables API (NoSQL)

## Requirements Implemented

1. **GET /v1/public/{project_id}/tables/{table_id}/rows** - List rows endpoint
   - Pagination via `limit` (default 100, max 1000) and `offset` (default 0)
   - Response format with `rows`, `total`, `limit`, `offset`, `has_more`
   - Filtering via query parameters: `?field_name=value`
   - Sorting via `?sort_by=field_name&order=asc|desc`

2. **GET /v1/public/{project_id}/tables/{table_id}/rows/{row_id}** - Get single row
   - Returns full row data including system fields
   - 404 ROW_NOT_FOUND for non-existent rows

3. **DELETE /v1/public/{project_id}/tables/{table_id}/rows/{row_id}** - Delete row
   - Removes row from table
   - Returns deletion confirmation with timestamp
   - 404 ROW_NOT_FOUND for non-existent rows

## Files Modified/Created

### Created Files

1. **backend/app/schemas/rows.py**
   - `SortOrder` enum (asc/desc)
   - `RowData` - Row data representation
   - `RowResponse` - Single row response
   - `RowListResponse` - Paginated list response with has_more indicator
   - `RowDeleteResponse` - Deletion confirmation
   - `RowFilter` - Query filter parameters

2. **backend/app/services/row_service.py**
   - `RowService` class with CRUD operations
   - `list_rows()` - Pagination, filtering, sorting
   - `get_row()` - Single row retrieval
   - `delete_row()` - Row deletion
   - `row_exists()` - Existence check
   - Field filtering with type-aware matching
   - Sorting by row_data fields or system fields

3. **backend/app/api/rows.py**
   - `GET /{project_id}/tables/{table_id}/rows` - List with pagination
   - `GET /{project_id}/tables/{table_id}/rows/{row_id}` - Get single row
   - `DELETE /{project_id}/tables/{table_id}/rows/{row_id}` - Delete row
   - Query parameter extraction for filtering
   - Value parsing (boolean, integer, float, string)

### Updated Files

4. **backend/app/main.py**
   - Added import for rows_router
   - Registered rows_router with FastAPI app

## API Response Format

### List Rows Response
```json
{
  "rows": [
    {
      "row_id": "row_abc123",
      "table_id": "tbl_xyz789",
      "row_data": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "created_at": "2026-01-10T12:34:56.789Z",
      "updated_at": null
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

### Single Row Response
```json
{
  "row_id": "row_abc123def456",
  "table_id": "tbl_xyz789",
  "project_id": "proj_001",
  "row_data": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "created_at": "2026-01-10T12:34:56.789Z",
  "updated_at": null
}
```

### Delete Response
```json
{
  "row_id": "row_abc123def456",
  "table_id": "tbl_xyz789",
  "deleted": true,
  "deleted_at": "2026-01-10T14:00:00.000Z"
}
```

## Error Handling

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| ROW_NOT_FOUND | 404 | Row does not exist |
| INVALID_API_KEY | 401 | Missing or invalid API key |
| VALIDATION_ERROR | 422 | Invalid request parameters |

## Usage Examples

### List Rows with Pagination
```bash
curl -X GET "https://api.example.com/v1/public/proj_001/tables/tbl_users/rows?limit=50&offset=0" \
  -H "X-API-Key: your-api-key"
```

### List Rows with Filtering
```bash
curl -X GET "https://api.example.com/v1/public/proj_001/tables/tbl_users/rows?active=true&role=admin" \
  -H "X-API-Key: your-api-key"
```

### List Rows with Sorting
```bash
curl -X GET "https://api.example.com/v1/public/proj_001/tables/tbl_users/rows?sort_by=created_at&order=desc" \
  -H "X-API-Key: your-api-key"
```

### Get Single Row
```bash
curl -X GET "https://api.example.com/v1/public/proj_001/tables/tbl_users/rows/row_abc123" \
  -H "X-API-Key: your-api-key"
```

### Delete Row
```bash
curl -X DELETE "https://api.example.com/v1/public/proj_001/tables/tbl_users/rows/row_abc123" \
  -H "X-API-Key: your-api-key"
```

## DX Contract Compliance

- All endpoints require X-API-Key authentication
- All errors return `{ detail, error_code }` format
- Pagination defaults are deterministic (limit=100, offset=0)
- Default sorting is by created_at descending for consistent ordering
- Field filtering supports type coercion (boolean, integer, float, string)

## Implementation Notes

1. **In-Memory Storage**: Uses in-memory storage for MVP. Production deployment should use ZeroDB persistence.

2. **Filter Parsing**: Query parameter values are automatically parsed to appropriate types:
   - `"true"/"false"` -> boolean
   - Numeric strings -> int/float
   - Everything else -> string

3. **Sorting**: Supports sorting by:
   - System fields: `row_id`, `table_id`, `created_at`, `updated_at`
   - Row data fields: Any field within `row_data`

4. **has_more Calculation**: `has_more = (offset + limit) < total`
