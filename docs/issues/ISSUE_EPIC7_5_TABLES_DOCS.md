# Issue Epic7-5: Tables API Documentation

**Epic:** 7 - NoSQL Tables API
**Issue:** 5 - As a developer, docs warn against using `rows` or `data`
**Story Points:** 1
**Status:** Completed
**Date:** 2026-01-11
**PRD Reference:** Section 10 (DX Contract)

---

## Summary

Created comprehensive documentation for the Tables API with a strong focus on the critical `row_data` field naming requirement. This ensures developers understand that using `rows`, `data`, `items`, or `records` will fail validation.

---

## Files Created

### 1. `/docs/api/TABLES_API.md`

Complete Tables API specification including:

- **All Endpoints Documented:**
  - POST `/database/tables` - Create table
  - GET `/database/tables` - List tables
  - GET `/database/tables/{id}` - Get table details
  - DELETE `/database/tables/{id}` - Delete table
  - POST `/database/tables/{id}/rows` - Insert rows
  - POST `/database/tables/{id}/query` - Query rows
  - PATCH `/database/tables/{id}/rows` - Update rows
  - DELETE `/database/tables/{id}/rows` - Delete rows

- **Request/Response Examples:** Complete JSON examples for all operations

- **WARNING Section:** Prominent warning about `row_data` field requirement

- **Error Codes:** Full error code reference table

- **Pagination:** Examples of paginating through large result sets

- **Filter Operators:** MongoDB-style operator reference ($eq, $gt, $in, etc.)

- **Update Operators:** $set, $inc, $push, $pull documentation

### 2. `/docs/api/ROW_DATA_WARNING.md`

Dedicated warning document covering:

- **Clear Explanation:** Why `row_data` is required (disambiguation, DX contract, schema validation)

- **WRONG Patterns:** Examples of all incorrect field names with code samples:
  - `rows` - WRONG
  - `data` - WRONG
  - `items` - WRONG
  - `records` - WRONG
  - `entries` - WRONG
  - `documents` - WRONG

- **RIGHT Pattern:** Correct `row_data` usage with complete examples

- **Language-Specific Examples:**
  - Python (requests)
  - JavaScript (fetch)
  - cURL
  - Go

- **Migration Patterns:** How to migrate from MongoDB-style or other APIs

- **DX Contract Guarantee:** Explanation of contract stability

### 3. `/docs/quick-reference/TABLES_QUICK_START.md`

Quick start guide with:

- **5-Minute Setup:** Step-by-step commands
- **Common Mistakes:** Field name and prefix errors
- **Python Example:** Complete working code
- **Quick Reference Card:** Endpoint summary table
- **Filter Operators:** Quick reference

---

## Key Documentation Highlights

### Warning Prominence

The `row_data` warning is prominently displayed:

1. In TABLES_API.md header section
2. In the Insert Rows endpoint section
3. As a dedicated ROW_DATA_WARNING.md file
4. In the quick start guide

### Error Response Documentation

Documented that incorrect field names return:

```json
{
  "detail": "Invalid field. Use 'row_data' instead of 'rows'. See ROW_DATA_WARNING.md for details.",
  "error_code": "INVALID_FIELD_NAME",
  "expected_field": "row_data",
  "received_field": "rows"
}
```

### Cross-References

All documents link to related documentation:
- TABLES_API.md references ROW_DATA_WARNING.md
- ROW_DATA_WARNING.md references TABLES_API.md
- Both reference DATABASE_PREFIX_WARNING.md
- Quick start links to detailed docs

---

## DX Contract Alignment

Per PRD Section 10, the documentation ensures:

1. **Predictability:** Field names are clearly specified
2. **Error Clarity:** Wrong field names produce helpful errors
3. **Stability:** Documented as permanent behavior
4. **Discoverability:** Multiple entry points to the warning

---

## Verification Checklist

- [x] TABLES_API.md created with all endpoints
- [x] ROW_DATA_WARNING.md created with WRONG vs RIGHT patterns
- [x] TABLES_QUICK_START.md created with quick examples
- [x] All docs reference the `row_data` requirement
- [x] Error codes documented
- [x] Pagination examples included
- [x] Language-specific examples provided
- [x] Cross-references between docs established
- [x] No prohibited terms used in documentation

---

## File Locations

| File | Path |
|------|------|
| Tables API Spec | `/docs/api/TABLES_API.md` |
| Row Data Warning | `/docs/api/ROW_DATA_WARNING.md` |
| Quick Start | `/docs/quick-reference/TABLES_QUICK_START.md` |
| This Summary | `/docs/issues/ISSUE_EPIC7_5_TABLES_DOCS.md` |

