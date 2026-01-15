# Error Codes Reference

This document provides a comprehensive reference for all error codes in the ZeroDB Agent Finance API.

Per DX Contract Section 7 (Error Semantics):
- All errors return `{ detail, error_code }`
- Error codes are stable and documented
- Validation errors use HTTP 422

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

## Related Documentation

- **API Documentation**: `/docs` (Swagger UI)
- **DX Contract**: Section 7 (Error Semantics)
- **PRD**: Section 10 (Success Criteria - Deterministic Errors)
- **Error Troubleshooting Guide**: See `ERROR_TROUBLESHOOTING.md`
