"""
Row API schemas for request/response validation.
Implements Epic 7 Issue 2: Row insertion with row_data field.
Implements Epic 7 Issue 4: List rows with pagination.

Per PRD Section 6 (ZeroDB Integration) and Section 9 (Demo verification):
- POST /v1/public/{project_id}/tables/{table_id}/rows - Insert rows (Issue 2)
- GET /v1/public/{project_id}/tables/{table_id}/rows - List rows with pagination
- GET /v1/public/{project_id}/tables/{table_id}/rows/{row_id} - Get single row
- DELETE /v1/public/{project_id}/tables/{table_id}/rows/{row_id} - Delete row

PRD Section 10 (Contract stability): Field name MUST be row_data (NOT data or rows).

Pagination parameters:
- limit: Maximum rows to return (default 100, max 1000)
- offset: Offset for pagination (default 0)

Filtering and sorting:
- Filter via query parameters: ?field_name=value
- Sort via: ?sort_by=field_name&order=asc|desc

DX Contract Compliance:
- All endpoints require X-API-Key authentication
- All errors return { detail, error_code }
- Non-existent rows return ROW_NOT_FOUND (404)
- Non-existent tables return TABLE_NOT_FOUND (404)
- Schema validation failures return SCHEMA_VALIDATION_ERROR (422)
"""
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, model_validator
from app.core.errors import MissingRowDataError, InvalidFieldNameError


# Common field name mistakes that should produce helpful errors
# Epic 7 Issue 3: Detect common mistakes (rows, data, items, records)
INVALID_FIELD_NAMES = frozenset(["data", "rows", "items", "records"])


class SortOrder(str, Enum):
    """
    Sort order for row listing.

    Supported values:
    - asc: Ascending order
    - desc: Descending order
    """
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# Row Insertion Schemas (Epic 7, Issue 2)
# =============================================================================


class RowInsertRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/tables/{table_id}/rows.

    PRD Section 10 (Contract stability): Field MUST be named row_data.
    Supports both single row and batch insert operations.

    Epic 7 Issue 3: Custom validator to detect common field name mistakes.

    - Single row: row_data is a dictionary
    - Batch insert: row_data is an array of dictionaries
    """
    row_data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ...,
        description="Row data to insert. Can be a single object or array for batch insert.",
        examples=[
            {"field1": "value1", "field2": 123},
            [{"field1": "a", "field2": 1}, {"field1": "b", "field2": 2}]
        ]
    )

    @model_validator(mode="before")
    @classmethod
    def validate_field_names(cls, data: Any) -> Any:
        """
        Custom validator to detect common field name mistakes.

        Per Epic 7 Issue 3 and PRD Section 10:
        - If row_data is missing, return MISSING_ROW_DATA error
        - If common mistakes (data, rows, items, records) are present,
          return INVALID_FIELD_NAME error with helpful message

        Args:
            data: Raw request data (dict or other)

        Returns:
            Validated data if row_data is present

        Raises:
            InvalidFieldNameError: If common mistake fields are detected
            MissingRowDataError: If row_data is missing
        """
        # Handle case where data is not a dict (e.g., None or malformed)
        if not isinstance(data, dict):
            raise MissingRowDataError()

        # Check for common field name mistakes first
        # This provides more helpful errors for developers
        for invalid_field in INVALID_FIELD_NAMES:
            if invalid_field in data:
                raise InvalidFieldNameError(invalid_field)

        # Check if row_data is present
        if "row_data" not in data:
            raise MissingRowDataError()

        return data

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Single row insert",
                    "value": {
                        "row_data": {
                            "name": "John Doe",
                            "email": "john@example.com",
                            "age": 30
                        }
                    }
                },
                {
                    "summary": "Batch insert",
                    "value": {
                        "row_data": [
                            {"name": "Alice", "email": "alice@example.com", "age": 25},
                            {"name": "Bob", "email": "bob@example.com", "age": 35}
                        ]
                    }
                }
            ]
        }


class InsertedRow(BaseModel):
    """
    Response schema for a single inserted row.
    Returns generated row_id and timestamp per requirements.
    """
    row_id: str = Field(..., description="Generated unique row identifier")
    created_at: str = Field(..., description="ISO 8601 timestamp of row creation")
    row_data: Dict[str, Any] = Field(..., description="The inserted row data")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "row_id": "row_abc123def456",
                "created_at": "2025-01-01T12:00:00Z",
                "row_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                }
            }
        }


class RowInsertResponse(BaseModel):
    """
    Response schema for row insertion operations.
    Supports both single and batch insert responses.
    """
    rows: List[InsertedRow] = Field(
        ...,
        description="List of inserted rows with their generated IDs and timestamps"
    )
    inserted_count: int = Field(..., description="Number of rows successfully inserted")

    class Config:
        json_schema_extra = {
            "example": {
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
        }


class SchemaValidationErrorDetail(BaseModel):
    """
    Detail for schema validation errors.
    Provides specific information about which fields failed validation.
    """
    field: str = Field(..., description="The field that failed validation")
    expected_type: str = Field(..., description="Expected data type for the field")
    actual_type: str = Field(..., description="Actual data type received")
    message: str = Field(..., description="Human-readable error message")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "age",
                "expected_type": "integer",
                "actual_type": "string",
                "message": "Field 'age' expected type 'integer' but got 'string'"
            }
        }


class RowErrorResponse(BaseModel):
    """
    Error response schema for row operations.
    Extends standard error response with optional validation details.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    validation_errors: Optional[List[SchemaValidationErrorDetail]] = Field(
        None,
        description="Detailed validation errors (only for SCHEMA_VALIDATION_ERROR)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Row data does not match table schema",
                "error_code": "SCHEMA_VALIDATION_ERROR",
                "validation_errors": [
                    {
                        "field": "age",
                        "expected_type": "integer",
                        "actual_type": "string",
                        "message": "Field 'age' expected type 'integer' but got 'string'"
                    }
                ]
            }
        }


# =============================================================================
# Row Listing Schemas (Epic 7, Issue 4)
# =============================================================================


class RowData(BaseModel):
    """
    Schema for row data in responses.

    Represents a single row from a table with system-generated fields.
    """
    row_id: str = Field(
        ...,
        description="Unique identifier for the row"
    )
    table_id: str = Field(
        ...,
        description="Table ID this row belongs to"
    )
    row_data: Dict[str, Any] = Field(
        ...,
        description="Row data as key-value pairs"
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 timestamp when the row was created"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when the row was last updated"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "row_id": "row_abc123def456",
                "table_id": "tbl_xyz789",
                "row_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30,
                    "active": True
                },
                "created_at": "2026-01-10T12:34:56.789Z",
                "updated_at": "2026-01-10T13:45:00.000Z"
            }
        }


class RowResponse(BaseModel):
    """
    Response schema for single row operations.

    Returns the full row data including system-generated fields.
    """
    row_id: str = Field(
        ...,
        description="Unique identifier for the row"
    )
    table_id: str = Field(
        ...,
        description="Table ID this row belongs to"
    )
    project_id: str = Field(
        ...,
        description="Project ID this row belongs to"
    )
    row_data: Dict[str, Any] = Field(
        ...,
        description="Row data as key-value pairs"
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 timestamp when the row was created"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when the row was last updated"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "row_id": "row_abc123def456",
                "table_id": "tbl_xyz789",
                "project_id": "proj_001",
                "row_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                },
                "created_at": "2026-01-10T12:34:56.789Z",
                "updated_at": None
            }
        }


class RowListResponse(BaseModel):
    """
    Response schema for listing rows with pagination.

    Epic 7 Issue 4: List rows with pagination.

    Response format per requirements:
    - rows: Array of row data
    - total: Total number of rows matching filters
    - limit: Maximum rows returned
    - offset: Current offset
    - has_more: Boolean indicating if more rows exist
    """
    rows: List[RowData] = Field(
        default_factory=list,
        description="List of rows"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of rows matching the query"
    )
    limit: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Maximum number of rows returned"
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Offset for pagination"
    )
    has_more: bool = Field(
        ...,
        description="True if more rows exist beyond this page"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "rows": [
                    {
                        "row_id": "row_abc123",
                        "table_id": "tbl_xyz789",
                        "row_data": {
                            "name": "John Doe",
                            "email": "john@example.com"
                        },
                        "created_at": "2026-01-10T12:34:56.789Z",
                        "updated_at": None
                    }
                ],
                "total": 150,
                "limit": 100,
                "offset": 0,
                "has_more": True
            }
        }


class RowDeleteResponse(BaseModel):
    """
    Response schema for row deletion.

    Confirms successful deletion of a row.
    """
    row_id: str = Field(
        ...,
        description="ID of the deleted row"
    )
    table_id: str = Field(
        ...,
        description="Table ID the row was deleted from"
    )
    deleted: bool = Field(
        default=True,
        description="Confirmation that the row was deleted"
    )
    deleted_at: str = Field(
        ...,
        description="ISO 8601 timestamp when the row was deleted"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "row_id": "row_abc123def456",
                "table_id": "tbl_xyz789",
                "deleted": True,
                "deleted_at": "2026-01-10T14:00:00.000Z"
            }
        }


class RowFilter(BaseModel):
    """
    Query parameters for filtering and paginating rows.

    Supports:
    - Pagination via limit/offset
    - Sorting via sort_by/order
    - Dynamic field filtering via filters dict
    """
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of rows to return (1-1000, default: 100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)"
    )
    sort_by: Optional[str] = Field(
        default=None,
        description="Field name to sort by"
    )
    order: SortOrder = Field(
        default=SortOrder.ASC,
        description="Sort order: asc (ascending) or desc (descending)"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Field filters as key-value pairs (e.g., field_name=value)"
    )
