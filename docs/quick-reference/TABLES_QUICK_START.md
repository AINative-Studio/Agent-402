# Tables API Quick Start Guide

Get started with ZeroDB Tables in 5 minutes.

---

## Prerequisites

- ZeroDB API key
- Terminal or HTTP client

---

## Important Notes Before You Start

1. **All endpoints require `/database/` prefix**
2. **Use `row_data` field for inserts (NOT `rows`, `data`, or `items`)**

---

## Step 1: Create a Table (30 seconds)

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "customers",
    "schema": {
      "fields": {
        "id": "string",
        "name": "string",
        "email": "string",
        "balance": "number"
      }
    }
  }'
```

**Response:**
```json
{
  "table_id": "tbl_abc123",
  "table_name": "customers",
  "row_count": 0
}
```

---

## Step 2: Insert Rows (30 seconds)

**IMPORTANT:** Use `row_data`, NOT `rows` or `data`.

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "row_data": [
      {"id": "1", "name": "Alice", "email": "alice@example.com", "balance": 1500},
      {"id": "2", "name": "Bob", "email": "bob@example.com", "balance": 2300}
    ]
  }'
```

**Response:**
```json
{
  "inserted_count": 2,
  "row_ids": ["row_abc123", "row_def456"]
}
```

---

## Step 3: Query Rows (30 seconds)

```bash
curl -X POST "https://api.ainative.studio/v1/public/database/tables/customers/query" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"balance": {"$gte": 1000}},
    "sort": {"balance": -1},
    "limit": 10
  }'
```

**Response:**
```json
{
  "rows": [
    {"_id": "row_def456", "id": "2", "name": "Bob", "balance": 2300},
    {"_id": "row_abc123", "id": "1", "name": "Alice", "balance": 1500}
  ],
  "total": 2
}
```

---

## Step 4: Update a Row (30 seconds)

```bash
curl -X PATCH "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"id": "1"},
    "update": {"$set": {"balance": 2000}}
  }'
```

**Response:**
```json
{
  "matched_count": 1,
  "modified_count": 1
}
```

---

## Step 5: Delete Rows (30 seconds)

```bash
curl -X DELETE "https://api.ainative.studio/v1/public/database/tables/customers/rows" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"balance": {"$lt": 100}}
  }'
```

**Response:**
```json
{
  "deleted_count": 0
}
```

---

## Common Mistakes to Avoid

### Mistake 1: Wrong Field Name for Insert

```json
// WRONG - Will return 422 error
{"rows": [...]}
{"data": [...]}
{"items": [...]}

// CORRECT
{"row_data": [...]}
```

### Mistake 2: Missing /database/ Prefix

```bash
# WRONG - Returns 404
POST /v1/public/tables/...

# CORRECT
POST /v1/public/database/tables/...
```

---

## Python Quick Example

```python
import requests

API_KEY = "your_api_key"
BASE = "https://api.ainative.studio/v1/public/database"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Create table
requests.post(f"{BASE}/tables", headers=HEADERS, json={
    "table_name": "products",
    "schema": {"fields": {"sku": "string", "price": "number"}}
})

# Insert rows (use row_data!)
requests.post(f"{BASE}/tables/products/rows", headers=HEADERS, json={
    "row_data": [
        {"sku": "PROD-001", "price": 29.99},
        {"sku": "PROD-002", "price": 49.99}
    ]
})

# Query
response = requests.post(f"{BASE}/tables/products/query", headers=HEADERS, json={
    "filter": {"price": {"$lt": 40}}
})
print(response.json()["rows"])
```

---

## Quick Reference Card

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create Table | POST | `/database/tables` |
| List Tables | GET | `/database/tables` |
| Get Table | GET | `/database/tables/{id}` |
| Delete Table | DELETE | `/database/tables/{id}?confirm=true` |
| Insert Rows | POST | `/database/tables/{id}/rows` |
| Query Rows | POST | `/database/tables/{id}/query` |
| Update Rows | PATCH | `/database/tables/{id}/rows` |
| Delete Rows | DELETE | `/database/tables/{id}/rows` |

**Base URL:** `https://api.ainative.studio/v1/public`

---

## Filter Operators Quick Reference

| Operator | Example |
|----------|---------|
| `$eq` | `{"status": {"$eq": "active"}}` |
| `$ne` | `{"status": {"$ne": "deleted"}}` |
| `$gt` | `{"price": {"$gt": 100}}` |
| `$gte` | `{"price": {"$gte": 100}}` |
| `$lt` | `{"price": {"$lt": 50}}` |
| `$lte` | `{"price": {"$lte": 50}}` |
| `$in` | `{"color": {"$in": ["red", "blue"]}}` |

---

## Next Steps

- [TABLES_API.md](/docs/api/TABLES_API.md) - Full API documentation
- [ROW_DATA_WARNING.md](/docs/api/ROW_DATA_WARNING.md) - Field naming details
- [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) - Prefix requirements

