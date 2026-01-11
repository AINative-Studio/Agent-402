# Critical: Use `row_data` Field (Not `data`, `rows`, `items`, or `records`)

**Last Updated:** 2026-01-11
**Applies To:** Tables API - Insert and Update Operations
**Severity:** High - Mandatory for all row operations
**PRD Reference:** Section 10 (DX Contract)

---

## Overview

When inserting or updating rows in ZeroDB tables, you **MUST** use the field name `row_data`. Any other field names (`data`, `rows`, `items`, `records`, etc.) will be rejected with a validation error.

This is a **DX Contract guarantee** and will not change without a major version increment.

---

## The Critical Rule

```
For row insertion and updates, ALWAYS use: row_data

NOT: data, rows, items, records, entries, documents, or any other name
```

---

## Why `row_data`?

The `row_data` field name was chosen for several important reasons:

### 1. Disambiguation

The term `rows` is ambiguous - it could refer to:
- The field containing row data to insert
- The response field containing retrieved rows
- A count of rows affected

`row_data` clearly indicates "the data for rows to be inserted/updated."

### 2. Consistency with DX Contract

The ZeroDB DX Contract (Section 10) mandates predictable field naming across all API endpoints. Using a unique, specific field name like `row_data` prevents confusion and enables tooling.

### 3. Avoiding Reserved Word Conflicts

`data` and `rows` are commonly used in:
- Response payloads (`rows` in query responses)
- Metadata fields
- Generic wrapper objects

`row_data` is specific and avoids these conflicts.

### 4. Schema Validation

A distinct field name allows strict schema validation. The API can definitively reject requests that use incorrect field names, providing clear error messages.

---

## WRONG Patterns (Will Fail)

All of these will return **422 Unprocessable Entity**:

### Using `rows`

```json
// WRONG
{
  "rows": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Using `data`

```json
// WRONG
{
  "data": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Using `items`

```json
// WRONG
{
  "items": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Using `records`

```json
// WRONG
{
  "records": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Using `entries`

```json
// WRONG
{
  "entries": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Using `documents`

```json
// WRONG
{
  "documents": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

---

## RIGHT Pattern (Required)

### Correct Field Name

```json
// CORRECT
{
  "row_data": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

### Complete Insert Request

```json
// CORRECT - Full insert request
{
  "row_data": [
    {
      "id": "cust-001",
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "created_at": "2026-01-11T12:00:00Z"
    },
    {
      "id": "cust-002",
      "name": "Bob Smith",
      "email": "bob@example.com",
      "created_at": "2026-01-11T12:05:00Z"
    }
  ],
  "return_ids": true
}
```

---

## Error Response for Wrong Field Names

When you use an incorrect field name, you will receive:

**HTTP 422 Unprocessable Entity**

```json
{
  "detail": "Invalid field. Use 'row_data' instead of 'rows'. See ROW_DATA_WARNING.md for details.",
  "error_code": "INVALID_FIELD_NAME",
  "expected_field": "row_data",
  "received_field": "rows",
  "documentation": "https://docs.ainative.studio/api/ROW_DATA_WARNING"
}
```

**Error Code:** `INVALID_FIELD_NAME`

The error response explicitly tells you:
- What field you used incorrectly
- What field you should use instead
- Where to find documentation

---

## Language-Specific Examples

### Python (requests)

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.ainative.studio/v1/public/database"

# CORRECT - Using row_data
response = requests.post(
    f"{BASE_URL}/tables/customers/rows",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "row_data": [  # CORRECT field name
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"}
        ]
    }
)

# Check for success
if response.status_code == 201:
    print(f"Inserted {response.json()['inserted_count']} rows")
```

### JavaScript (fetch)

```javascript
const API_KEY = "your_api_key";
const BASE_URL = "https://api.ainative.studio/v1/public/database";

// CORRECT - Using row_data
const response = await fetch(`${BASE_URL}/tables/customers/rows`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    row_data: [  // CORRECT field name
      { id: "1", name: "Alice", email: "alice@example.com" },
      { id: "2", name: "Bob", email: "bob@example.com" }
    ]
  })
});

if (response.ok) {
  const result = await response.json();
  console.log(`Inserted ${result.inserted_count} rows`);
}
```

### cURL

```bash
# CORRECT - Using row_data
curl -X POST "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "row_data": [
      {"id": "1", "name": "Alice", "email": "alice@example.com"},
      {"id": "2", "name": "Bob", "email": "bob@example.com"}
    ]
  }'
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type InsertRequest struct {
    RowData []map[string]interface{} `json:"row_data"` // CORRECT field name
}

func insertRows() error {
    data := InsertRequest{
        RowData: []map[string]interface{}{
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"},
        },
    }

    payload, _ := json.Marshal(data)

    req, err := http.NewRequest(
        "POST",
        "https://api.ainative.studio/v1/public/database/tables/customers/rows",
        bytes.NewBuffer(payload),
    )
    if err != nil {
        return err
    }

    req.Header.Set("X-API-Key", "your_api_key")
    req.Header.Set("Content-Type", "application/json")

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    return nil
}
```

---

## Common Migration Patterns

If you're migrating from another database or API that uses different field names:

### From MongoDB-style `documents`

```python
# OLD (MongoDB-style)
# db.customers.insert_many(documents=[...])

# NEW (ZeroDB)
requests.post(
    f"{BASE_URL}/tables/customers/rows",
    json={"row_data": documents}  # Rename the field
)
```

### From REST API using `data`

```python
# OLD pattern
payload = {"data": records}

# NEW pattern
payload = {"row_data": records}  # Just rename the key
```

### Wrapper Function

```python
def insert_rows(table_name: str, records: list) -> dict:
    """
    Insert rows into a ZeroDB table.

    Args:
        table_name: Name of the table
        records: List of row dictionaries (accepts any variable name)

    Returns:
        Insert result with inserted_count and row_ids
    """
    response = requests.post(
        f"{BASE_URL}/tables/{table_name}/rows",
        headers={"X-API-Key": API_KEY},
        json={"row_data": records}  # Always use row_data
    )
    response.raise_for_status()
    return response.json()

# Usage - pass any variable name, it gets mapped to row_data
customers = [{"id": "1", "name": "Alice"}]
result = insert_rows("customers", customers)
```

---

## DX Contract Guarantee

Per the ZeroDB Developer Experience Contract (Section 10):

1. **The `row_data` field name is PERMANENT** - It will not change without a major version increment

2. **Error messages are guaranteed** - The API will always return a helpful error when wrong field names are used

3. **Validation is strict** - Unknown fields like `rows` or `data` will always be rejected, never silently ignored

4. **Documentation links are provided** - Error responses include links to this documentation

---

## Quick Reference Checklist

Before making a row insert request, verify:

- [ ] Field name is exactly `row_data` (not `rows`, `data`, `items`, etc.)
- [ ] Value is an array of objects
- [ ] Each object matches the table schema
- [ ] Path includes `/database/` prefix

**Mental Model:**

```
POST /v1/public/database/tables/{table}/rows

Body:
{
  "row_data": [...]  <-- ALWAYS THIS FIELD NAME
}
```

---

## Troubleshooting

### Getting 422 "Invalid field" error?

1. Check your request body for `rows`, `data`, `items`, or `records`
2. Rename the field to `row_data`
3. Ensure the value is an array

### Using a code generator or SDK?

Check that your SDK uses `row_data`. If it uses a different name, you may need to:
- Configure the field mapping
- Use a custom serializer
- Update to a newer SDK version

### Copy-pasting from other APIs?

Many APIs use `data` or `rows`. When adapting code for ZeroDB:
1. Find the payload construction
2. Replace the field name with `row_data`
3. Keep the array structure the same

---

## Summary

```
+---------------------------------------------------------------+
|                                                               |
|  INSERT/UPDATE ROWS: Use row_data                            |
|                                                               |
|  CORRECT:  { "row_data": [...] }                             |
|                                                               |
|  WRONG:    { "rows": [...] }                                 |
|  WRONG:    { "data": [...] }                                 |
|  WRONG:    { "items": [...] }                                |
|  WRONG:    { "records": [...] }                              |
|                                                               |
|  DX Contract: This is a permanent, guaranteed behavior        |
|                                                               |
+---------------------------------------------------------------+
```

---

## Related Documentation

- [TABLES_API.md](/docs/api/TABLES_API.md) - Complete Tables API specification
- [TABLES_QUICK_START.md](/docs/quick-reference/TABLES_QUICK_START.md) - Quick start guide
- [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) - Endpoint prefix requirement

