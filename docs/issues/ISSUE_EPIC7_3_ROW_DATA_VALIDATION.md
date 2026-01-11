# Issue Epic 7 Issue 3: Missing row_data Returns 422 Error

## Summary

**Issue:** As a developer, missing `row_data` returns a clear 422 error. (2 pts)
**PRD Reference:** Section 10 (Deterministic errors)

This implementation provides deterministic error responses when the `row_data` field is missing or when developers use common incorrect field names.

## Requirements Implemented

1. When POST to `/tables/{table_id}/rows` is missing `row_data` field, return 422
2. Error response format with clear error codes
3. Helpful error messages for common field name mistakes
4. Custom validator to detect `rows`, `data`, `items`, `records`
5. Updated error codes in `backend/app/core/errors.py`

## Error Response Formats

### Missing row_data Field

```json
{
  "detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.",
  "error_code": "MISSING_ROW_DATA"
}
```

### Invalid Field Name Used

When request contains `data`, `rows`, `items`, or `records` instead of `row_data`:

```json
{
  "detail": "Invalid field 'data'. Use 'row_data' for inserting rows.",
  "error_code": "INVALID_FIELD_NAME"
}
```

## Files Modified

### 1. `backend/app/core/errors.py`

Added two new error classes:

```python
class MissingRowDataError(APIError):
    """
    Raised when POST to /tables/{table_id}/rows is missing row_data field.

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: MISSING_ROW_DATA
        - detail: Message explaining the required field
    """

class InvalidFieldNameError(APIError):
    """
    Raised when request contains invalid field names instead of row_data.

    Common mistakes detected: 'data', 'rows', 'items', 'records'

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: INVALID_FIELD_NAME
        - detail: Message explaining the correct field name
    """
```

### 2. `backend/app/schemas/rows.py`

Updated `RowInsertRequest` with a custom model validator:

```python
# Common field name mistakes that should produce helpful errors
INVALID_FIELD_NAMES = frozenset(["data", "rows", "items", "records"])

class RowInsertRequest(BaseModel):
    row_data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(...)

    @model_validator(mode="before")
    @classmethod
    def validate_field_names(cls, data: Any) -> Any:
        """
        Custom validator to detect common field name mistakes.

        - If row_data is missing, return MISSING_ROW_DATA error
        - If common mistakes (data, rows, items, records) are present,
          return INVALID_FIELD_NAME error with helpful message
        """
        if not isinstance(data, dict):
            raise MissingRowDataError()

        # Check for common field name mistakes first
        for invalid_field in INVALID_FIELD_NAMES:
            if invalid_field in data:
                raise InvalidFieldNameError(invalid_field)

        if "row_data" not in data:
            raise MissingRowDataError()

        return data
```

### 3. `backend/app/api/rows.py`

Added POST endpoint for row insertion with comprehensive error documentation:

```python
@router.post(
    "/{project_id}/tables/{table_id}/rows",
    response_model=RowInsertResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "description": "Validation error - missing row_data or invalid field name",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_row_data": {...},
                        "invalid_field_name": {...}
                    }
                }
            }
        }
    }
)
async def insert_rows(...)
```

### 4. `backend/app/schemas/errors.py`

Added new error codes to the `ErrorCodes` class:

```python
class ErrorCodes:
    # Validation errors (HTTP 422)
    MISSING_ROW_DATA = "MISSING_ROW_DATA"      # Missing row_data field
    INVALID_FIELD_NAME = "INVALID_FIELD_NAME"  # Wrong field name used
```

## Error Handling Flow

1. **Request received** at POST `/v1/public/{project_id}/tables/{table_id}/rows`
2. **Pydantic model_validator** runs before field validation
3. **Validator checks** for common mistakes:
   - If `data`, `rows`, `items`, or `records` present: raise `InvalidFieldNameError`
   - If `row_data` missing: raise `MissingRowDataError`
4. **Error propagates** to FastAPI exception handler
5. **APIError handler** in main.py formats response with `{ detail, error_code }`

## Test Scenarios

| Scenario | Request Body | Expected Response |
|----------|--------------|-------------------|
| Missing row_data | `{}` | 422 MISSING_ROW_DATA |
| Using 'data' | `{"data": [...]}` | 422 INVALID_FIELD_NAME |
| Using 'rows' | `{"rows": [...]}` | 422 INVALID_FIELD_NAME |
| Using 'items' | `{"items": [...]}` | 422 INVALID_FIELD_NAME |
| Using 'records' | `{"records": [...]}` | 422 INVALID_FIELD_NAME |
| Correct field | `{"row_data": [...]}` | 201 Created |

## Design Decisions

1. **Check invalid fields before missing field**: Provides more specific error messages when a common mistake is detected

2. **Use model_validator(mode="before")**: Validates raw input before Pydantic field validation, allowing custom error handling

3. **Custom APIError subclasses**: Allows consistent error format per DX Contract while providing specific error codes

4. **Frozen set for invalid fields**: Immutable and efficient lookup for the set of common mistakes

5. **Error messages include guidance**: Messages explicitly tell developers what field to use, reducing debugging time

## References

- PRD Section 10: Deterministic errors
- DX Contract Section 7: Error Semantics
- Epic 7 Issue 2: Row insertion with row_data field
- `backend/app/core/errors.py` - Error classes
- `backend/app/schemas/rows.py` - Request schema with validator
- `backend/app/api/rows.py` - Row API endpoints
