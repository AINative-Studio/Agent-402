# Tables API Specification

**Version:** v1
**Last Updated:** 2026-01-11
**Base URL:** `https://api.ainative.studio/v1/public/database`
**Epic Reference:** Epic 7 - NoSQL Tables API

---

## Overview

The Tables API provides NoSQL document storage capabilities within ZeroDB projects. Tables allow you to store structured data with flexible schemas, perform queries with MongoDB-style filters, and manage records with full CRUD operations.

**Key Features:**
- Flexible schema design with field type definitions
- MongoDB-style query filters
- Pagination support for large datasets
- Bulk insert operations
- Index creation for query optimization

---

## Authentication

All Table API requests require the `X-API-Key` header.

```bash
curl -X GET "https://api.ainative.studio/v1/public/database/tables" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json"
```

**Important:** API keys must ONLY be used server-side. See [API_KEY_SECURITY.md](/docs/api/API_KEY_SECURITY.md) for details.

---

## WARNING: Critical Field Naming Requirement

> **The `row_data` field is MANDATORY for all insert and update operations.**

See [ROW_DATA_WARNING.md](/docs/api/ROW_DATA_WARNING.md) for complete details on this critical requirement.

**Quick Reference:**

```json
// WRONG - Will fail validation
{ "rows": [...] }
{ "data": [...] }
{ "items": [...] }
{ "records": [...] }

// CORRECT - Required field name
{ "row_data": [...] }
```

---

## Endpoint Path Requirement

All Tables API endpoints require the `/database/` prefix. See [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) for details.

```
/v1/public/database/tables
           ^^^^^^^^^ REQUIRED
```

---

## Endpoints

### 1. Create Table

Creates a new NoSQL table with a defined schema.

**Endpoint:** `POST /v1/public/database/tables`

**Request Body:**

```json
{
  "table_name": "customers",
  "schema": {
    "fields": {
      "id": "string",
      "name": "string",
      "email": "string",
      "created_at": "timestamp",
      "balance": "number",
      "active": "boolean"
    },
    "indexes": [
      {"name": "email_idx", "columns": ["email"], "unique": true},
      {"name": "created_idx", "columns": ["created_at"]}
    ]
  },
  "description": "Customer records table"
}
```

**Field Types:**

| Type | Description | Example Value |
|------|-------------|---------------|
| `string` | Text data | `"John Doe"` |
| `number` | Numeric values (integers and floats) | `99.99` |
| `boolean` | True/false values | `true` |
| `timestamp` | ISO 8601 datetime | `"2026-01-11T12:00:00Z"` |
| `object` | Nested JSON object | `{"key": "value"}` |
| `array` | JSON array | `[1, 2, 3]` |

**Success Response (201 Created):**

```json
{
  "table_id": "tbl_abc123xyz456",
  "table_name": "customers",
  "schema": {
    "fields": {
      "id": "string",
      "name": "string",
      "email": "string",
      "created_at": "timestamp",
      "balance": "number",
      "active": "boolean"
    },
    "indexes": [
      {"name": "email_idx", "columns": ["email"], "unique": true},
      {"name": "created_idx", "columns": ["created_at"]}
    ]
  },
  "description": "Customer records table",
  "row_count": 0,
  "created_at": "2026-01-11T12:00:00Z"
}
```

**Error Responses:**

```json
// 400 Bad Request - Table already exists
{
  "detail": "Table 'customers' already exists",
  "error_code": "TABLE_ALREADY_EXISTS"
}

// 400 Bad Request - Invalid schema
{
  "detail": "Invalid field type 'date'. Supported types: string, number, boolean, timestamp, object, array",
  "error_code": "INVALID_SCHEMA"
}

// 401 Unauthorized
{
  "detail": "Invalid API key",
  "error_code": "INVALID_API_KEY"
}
```

**Example Request:**

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "customers",
    "schema": {
      "fields": {
        "id": "string",
        "name": "string",
        "email": "string"
      }
    }
  }'
```

---

### 2. List Tables

Retrieves all tables in the project.

**Endpoint:** `GET /v1/public/database/tables`

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `limit` | integer | Maximum tables to return | 100 |
| `offset` | integer | Pagination offset | 0 |

**Success Response (200 OK):**

```json
{
  "tables": [
    {
      "table_id": "tbl_abc123xyz456",
      "table_name": "customers",
      "description": "Customer records table",
      "row_count": 1250,
      "created_at": "2026-01-11T12:00:00Z",
      "updated_at": "2026-01-11T14:30:00Z"
    },
    {
      "table_id": "tbl_def789uvw012",
      "table_name": "orders",
      "description": "Order transactions",
      "row_count": 8456,
      "created_at": "2026-01-10T09:00:00Z",
      "updated_at": "2026-01-11T15:45:00Z"
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

**Example Request:**

```bash
curl -X GET "https://api.ainative.studio/v1/public/database/tables?limit=10" \
  -H "X-API-Key: your_api_key_here"
```

---

### 3. Get Table Details

Retrieves details for a specific table including schema.

**Endpoint:** `GET /v1/public/database/tables/{table_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `table_id` | string | Table ID or table name |

**Success Response (200 OK):**

```json
{
  "table_id": "tbl_abc123xyz456",
  "table_name": "customers",
  "schema": {
    "fields": {
      "id": "string",
      "name": "string",
      "email": "string"
    },
    "indexes": [
      {"name": "email_idx", "columns": ["email"], "unique": true}
    ]
  },
  "description": "Customer records table",
  "row_count": 1250,
  "created_at": "2026-01-11T12:00:00Z",
  "updated_at": "2026-01-11T14:30:00Z"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Table not found",
  "error_code": "TABLE_NOT_FOUND"
}
```

---

### 4. Delete Table

Deletes a table and all its data.

**Endpoint:** `DELETE /v1/public/database/tables/{table_id}`

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `confirm` | boolean | Confirmation flag (required to be `true`) | false |

**Success Response (200 OK):**

```json
{
  "message": "Table 'customers' deleted successfully",
  "table_id": "tbl_abc123xyz456",
  "rows_deleted": 1250
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Confirmation required. Set confirm=true to delete table.",
  "error_code": "CONFIRMATION_REQUIRED"
}
```

**Example Request:**

```bash
curl -X DELETE "https://api.ainative.studio/v1/public/database/tables/customers?confirm=true" \
  -H "X-API-Key: your_api_key_here"
```

---

### 5. Insert Rows

Inserts one or more rows into a table.

**Endpoint:** `POST /v1/public/database/tables/{table_id}/rows`

**CRITICAL:** Use `row_data` field, NOT `rows`, `data`, `items`, or `records`.

**Request Body:**

```json
{
  "row_data": [
    {
      "id": "cust-001",
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "balance": 1500.00,
      "active": true
    },
    {
      "id": "cust-002",
      "name": "Bob Smith",
      "email": "bob@example.com",
      "balance": 2300.50,
      "active": true
    }
  ],
  "return_ids": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `row_data` | array | Yes | Array of row objects to insert |
| `return_ids` | boolean | No | Return inserted row IDs (default: true) |

**WRONG Field Names (Will Fail):**

```json
// These will return 422 Unprocessable Entity
{ "rows": [...] }      // WRONG
{ "data": [...] }      // WRONG
{ "items": [...] }     // WRONG
{ "records": [...] }   // WRONG
```

**Success Response (201 Created):**

```json
{
  "inserted_count": 2,
  "row_ids": [
    "row_9f8e7d6c5b4a3210",
    "row_1a2b3c4d5e6f7890"
  ]
}
```

**Error Responses:**

```json
// 422 Unprocessable Entity - Wrong field name
{
  "detail": "Invalid field. Use 'row_data' instead of 'rows'. See ROW_DATA_WARNING.md for details.",
  "error_code": "INVALID_FIELD_NAME",
  "expected_field": "row_data",
  "received_field": "rows"
}

// 400 Bad Request - Schema validation failure
{
  "detail": "Field 'email' is required but missing in row 2",
  "error_code": "SCHEMA_VALIDATION_ERROR",
  "row_index": 1
}
```

**Example Request:**

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "row_data": [
      {
        "id": "cust-001",
        "name": "Alice Johnson",
        "email": "alice@example.com"
      }
    ]
  }'
```

---

### 6. Query Rows

Queries rows from a table using MongoDB-style filters.

**Endpoint:** `POST /v1/public/database/tables/{table_id}/query`

**Request Body:**

```json
{
  "filter": {
    "active": true,
    "balance": {"$gte": 1000}
  },
  "projection": {
    "id": 1,
    "name": 1,
    "balance": 1
  },
  "sort": {
    "balance": -1
  },
  "limit": 50,
  "offset": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter` | object | No | MongoDB-style query filter |
| `projection` | object | No | Fields to include (1) or exclude (0) |
| `sort` | object | No | Sort specification (1=asc, -1=desc) |
| `limit` | integer | No | Maximum rows to return (default: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Supported Filter Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `$eq` | Equal to | `{"status": {"$eq": "active"}}` |
| `$ne` | Not equal to | `{"status": {"$ne": "deleted"}}` |
| `$gt` | Greater than | `{"balance": {"$gt": 100}}` |
| `$gte` | Greater than or equal | `{"balance": {"$gte": 100}}` |
| `$lt` | Less than | `{"balance": {"$lt": 1000}}` |
| `$lte` | Less than or equal | `{"balance": {"$lte": 1000}}` |
| `$in` | In array | `{"status": {"$in": ["active", "pending"]}}` |
| `$nin` | Not in array | `{"status": {"$nin": ["deleted"]}}` |
| `$exists` | Field exists | `{"email": {"$exists": true}}` |
| `$regex` | Regex match | `{"name": {"$regex": "^John"}}` |

**Success Response (200 OK):**

```json
{
  "rows": [
    {
      "_id": "row_9f8e7d6c5b4a3210",
      "id": "cust-002",
      "name": "Bob Smith",
      "balance": 2300.50
    },
    {
      "_id": "row_1a2b3c4d5e6f7890",
      "id": "cust-001",
      "name": "Alice Johnson",
      "balance": 1500.00
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Example Request:**

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables/customers/query" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"active": true},
    "sort": {"created_at": -1},
    "limit": 10
  }'
```

---

### 7. Update Rows

Updates rows matching a filter.

**Endpoint:** `PATCH /v1/public/database/tables/{table_id}/rows`

**Request Body:**

```json
{
  "filter": {
    "id": "cust-001"
  },
  "update": {
    "$set": {
      "balance": 2000.00,
      "updated_at": "2026-01-11T16:00:00Z"
    },
    "$inc": {
      "login_count": 1
    }
  },
  "upsert": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter` | object | Yes | MongoDB-style query filter |
| `update` | object | Yes | Update operations |
| `upsert` | boolean | No | Insert if not found (default: false) |

**Supported Update Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `$set` | Set field value | `{"$set": {"name": "New Name"}}` |
| `$unset` | Remove field | `{"$unset": {"temp_field": 1}}` |
| `$inc` | Increment number | `{"$inc": {"count": 1}}` |
| `$push` | Add to array | `{"$push": {"tags": "new-tag"}}` |
| `$pull` | Remove from array | `{"$pull": {"tags": "old-tag"}}` |

**Success Response (200 OK):**

```json
{
  "matched_count": 1,
  "modified_count": 1
}
```

**Example Request:**

```bash
curl -X PATCH "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"id": "cust-001"},
    "update": {"$set": {"balance": 2000.00}}
  }'
```

---

### 8. Delete Rows

Deletes rows matching a filter.

**Endpoint:** `DELETE /v1/public/database/tables/{table_id}/rows`

**Request Body:**

```json
{
  "filter": {
    "active": false
  },
  "limit": 100
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter` | object | Yes | MongoDB-style query filter |
| `limit` | integer | No | Maximum rows to delete (default: unlimited) |

**Success Response (200 OK):**

```json
{
  "deleted_count": 15
}
```

**Example Request:**

```bash
curl -X DELETE "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"active": false}
  }'
```

---

## Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key is missing or invalid |
| `TABLE_NOT_FOUND` | 404 | Specified table does not exist |
| `TABLE_ALREADY_EXISTS` | 400 | Table with same name already exists |
| `INVALID_SCHEMA` | 400 | Schema definition is invalid |
| `INVALID_FIELD_NAME` | 422 | Wrong field name used (e.g., `rows` instead of `row_data`) |
| `SCHEMA_VALIDATION_ERROR` | 400 | Row data does not match schema |
| `CONFIRMATION_REQUIRED` | 400 | Delete confirmation flag not set |
| `QUERY_SYNTAX_ERROR` | 400 | Invalid filter or query syntax |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Pagination

All list and query endpoints support pagination.

**Parameters:**

| Parameter | Description | Default | Maximum |
|-----------|-------------|---------|---------|
| `limit` | Rows per page | 100 | 1000 |
| `offset` | Starting position | 0 | - |

**Example: Paginating Through Results**

```python
import requests

def get_all_customers():
    all_customers = []
    offset = 0
    limit = 100

    while True:
        response = requests.post(
            "https://api.ainative.studio/v1/public/database/tables/customers/query",
            headers={"X-API-Key": API_KEY},
            json={"limit": limit, "offset": offset}
        )
        data = response.json()
        all_customers.extend(data["rows"])

        if len(data["rows"]) < limit:
            break
        offset += limit

    return all_customers
```

---

## Rate Limits

| Tier | Requests/minute | Bulk Insert Limit |
|------|-----------------|-------------------|
| Free | 60 | 100 rows/request |
| Starter | 300 | 500 rows/request |
| Pro | 1000 | 1000 rows/request |
| Enterprise | Custom | Custom |

---

## Best Practices

1. **Always use `row_data`** - Never use `rows`, `data`, `items`, or `records`
2. **Include `/database/` prefix** - All table endpoints require this prefix
3. **Use indexes wisely** - Create indexes for frequently queried fields
4. **Paginate large results** - Use `limit` and `offset` for large datasets
5. **Validate before insert** - Check data matches schema before bulk inserts
6. **Use projections** - Only request fields you need for better performance

---

## Related Documentation

- [ROW_DATA_WARNING.md](/docs/api/ROW_DATA_WARNING.md) - Critical field naming requirement
- [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) - Endpoint prefix requirement
- [TABLES_QUICK_START.md](/docs/quick-reference/TABLES_QUICK_START.md) - Quick start guide
- [API_KEY_SECURITY.md](/docs/api/API_KEY_SECURITY.md) - Security best practices

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-11 | Initial Tables API specification |

