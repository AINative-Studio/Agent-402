"""
Rows API endpoints with pagination, filtering, and sorting.
Implements Epic 7 Issue 2: Row insertion with row_data field.
Implements Epic 7 Issue 3: Deterministic errors for missing row_data.
Implements Epic 7 Issue 4: List rows with pagination.

Per PRD Section 6 (ZeroDB Integration) and Section 9 (Demo verification):
- POST /v1/public/{project_id}/tables/{table_id}/rows - Insert rows (Issue 2, 3)
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
- Missing row_data returns MISSING_ROW_DATA (422)
- Invalid field names (data, rows, items, records) return INVALID_FIELD_NAME (422)
"""
from datetime import datetime
from typing import Optional, Any, List, Dict, Union
from fastapi import APIRouter, Depends, status, Path, Query, Request
from app.core.auth import get_current_user
from app.core.errors import APIError, TableNotFoundError
from app.schemas.project import ErrorResponse
from app.schemas.rows import (
    SortOrder,
    RowData,
    RowResponse,
    RowListResponse,
    RowDeleteResponse,
    RowFilter,
    RowInsertRequest,
    RowInsertResponse,
    InsertedRow
)
from app.services.row_service import row_service
from app.services.table_service import table_service
from app.services.project_service import project_service


router = APIRouter(
    prefix="/v1/public",
    tags=["rows"]
)


def validate_project_access(project_id: str, user_id: str) -> None:
    """
    Validate that the user has access to the project.

    Args:
        project_id: Project identifier
        user_id: Authenticated user ID

    Raises:
        ProjectNotFoundError: If project not found
        UnauthorizedError: If user doesn't have access
    """
    # This will raise ProjectNotFoundError or UnauthorizedError
    # Both are APIError subclasses with proper error_code
    project_service.get_project(project_id, user_id)


def validate_table_exists(table_id: str, project_id: str) -> None:
    """
    Validate that the table exists in the project.

    Args:
        table_id: Table identifier
        project_id: Project identifier

    Raises:
        TableNotFoundError: If table not found
    """
    table = table_service.get_table_by_id(table_id, project_id)
    if not table:
        raise TableNotFoundError(table_id)


def extract_filters_from_query(request: Request) -> dict:
    """
    Extract field filters from query parameters.

    Filters out pagination and sorting parameters to get only field filters.
    Supports filtering via query parameters: ?field_name=value

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary of field filters
    """
    # Known non-filter parameters
    reserved_params = {"limit", "offset", "sort_by", "order"}

    filters = {}
    for key, value in request.query_params.items():
        if key not in reserved_params:
            # Try to parse value as appropriate type
            filters[key] = parse_query_value(value)

    return filters


def parse_query_value(value: str) -> Any:
    """
    Parse query parameter value to appropriate Python type.

    Handles:
    - Booleans: 'true'/'false'
    - Integers: numeric strings without decimal
    - Floats: numeric strings with decimal
    - Strings: everything else

    Args:
        value: String value from query parameter

    Returns:
        Parsed value in appropriate type
    """
    # Check for boolean
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    # Check for integer
    try:
        if "." not in value:
            return int(value)
    except ValueError:
        pass

    # Check for float
    try:
        return float(value)
    except ValueError:
        pass

    # Default to string
    return value


# =============================================================================
# Row Insertion Endpoint (Epic 7, Issue 2 & 3)
# =============================================================================


@router.post(
    "/{project_id}/tables/{table_id}/rows",
    response_model=RowInsertResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Rows inserted successfully",
            "model": RowInsertResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Table not found",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error - missing row_data or invalid field name",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_row_data": {
                            "summary": "Missing row_data field",
                            "value": {
                                "detail": "Missing required field: row_data. Use row_data instead of 'data' or 'rows'.",
                                "error_code": "MISSING_ROW_DATA"
                            }
                        },
                        "invalid_field_name": {
                            "summary": "Invalid field name used",
                            "value": {
                                "detail": "Invalid field 'data'. Use 'row_data' for inserting rows.",
                                "error_code": "INVALID_FIELD_NAME"
                            }
                        }
                    }
                }
            }
        }
    },
    summary="Insert rows into table",
    description="""
    Insert one or more rows into a table.

    **Authentication:** Requires X-API-Key header

    **Epic 7 Issue 2 & 3:** Row insertion with deterministic error handling.

    **PRD Section 10 (Contract stability):** Field MUST be named `row_data`.

    **Request Body:**
    - row_data: Required. Single object for one row, or array for batch insert.

    **Common Mistakes (422 errors):**
    - Missing `row_data` field returns MISSING_ROW_DATA
    - Using `data`, `rows`, `items`, or `records` instead returns INVALID_FIELD_NAME

    **Response:**
    - inserted_count: Number of rows inserted
    - rows: Array of inserted rows with generated row_id and created_at
    """
)
async def insert_rows(
    project_id: str = Path(..., description="Project ID"),
    table_id: str = Path(..., description="Table ID"),
    request: RowInsertRequest = ...,
    current_user: str = Depends(get_current_user)
) -> RowInsertResponse:
    """
    Insert rows into a table.

    Epic 7 Issue 2: Row insertion with row_data field.
    Epic 7 Issue 3: Deterministic errors for missing row_data.

    The RowInsertRequest schema has a model_validator that:
    - Returns MISSING_ROW_DATA (422) if row_data is missing
    - Returns INVALID_FIELD_NAME (422) if data, rows, items, or records are used

    Args:
        project_id: Project identifier from URL
        table_id: Table identifier from URL
        request: Row insert request with row_data field
        current_user: User ID from X-API-Key authentication

    Returns:
        RowInsertResponse with inserted rows and count

    Raises:
        MissingRowDataError: If row_data field is missing
        InvalidFieldNameError: If common mistake fields are detected
        TableNotFoundError: If table doesn't exist
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Validate table exists
    validate_table_exists(table_id, project_id)

    # Normalize row_data to always be a list
    row_data_list: List[Dict[str, Any]]
    if isinstance(request.row_data, dict):
        row_data_list = [request.row_data]
    else:
        row_data_list = request.row_data

    # Insert rows via service
    inserted_rows = row_service.insert_rows(
        project_id=project_id,
        table_id=table_id,
        rows=row_data_list
    )

    # Build response
    response_rows = [
        InsertedRow(
            row_id=row["row_id"],
            created_at=row["created_at"],
            row_data=row["row_data"]
        )
        for row in inserted_rows
    ]

    return RowInsertResponse(
        inserted_count=len(response_rows),
        rows=response_rows
    )


# =============================================================================
# Row Listing Endpoint (Epic 7, Issue 4)
# =============================================================================


@router.get(
    "/{project_id}/tables/{table_id}/rows",
    response_model=RowListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved rows",
            "model": RowListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Table not found",
            "model": ErrorResponse
        }
    },
    summary="List rows with pagination",
    description="""
    List rows from a table with pagination, filtering, and sorting.

    **Authentication:** Requires X-API-Key header

    **Epic 7 Issue 4:** As a developer, I can list rows with pagination.

    **Pagination:**
    - limit: Maximum rows to return (default: 100, max: 1000)
    - offset: Offset for pagination (default: 0)

    **Filtering:**
    - Use query parameters to filter by field values
    - Example: ?name=John&active=true
    - Supports string, number, and boolean values

    **Sorting:**
    - sort_by: Field name to sort by (row_data fields or system fields)
    - order: Sort order - 'asc' (ascending) or 'desc' (descending)
    - Default: sorted by created_at descending

    **Response:**
    - rows: Array of row data
    - total: Total count of rows matching filters
    - limit: Current limit value
    - offset: Current offset value
    - has_more: True if more rows exist beyond current page
    """
)
async def list_rows(
    request: Request,
    project_id: str = Path(..., description="Project ID"),
    table_id: str = Path(..., description="Table ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: Optional[str] = Query(None, description="Field name to sort by"),
    order: SortOrder = Query(SortOrder.ASC, description="Sort order (asc or desc)"),
    current_user: str = Depends(get_current_user)
) -> RowListResponse:
    """
    List rows with pagination, filtering, and sorting.

    Epic 7 Issue 4 Implementation:
    - Supports pagination via limit/offset
    - Supports filtering via query parameters
    - Supports sorting via sort_by/order
    - Returns has_more indicator for pagination

    Args:
        request: FastAPI request for extracting query params
        project_id: Project identifier
        table_id: Table identifier
        limit: Maximum number of rows to return
        offset: Pagination offset
        sort_by: Optional field to sort by
        order: Sort order (asc/desc)
        current_user: Authenticated user ID

    Returns:
        RowListResponse with paginated rows and metadata
    """
    # Extract field filters from query parameters
    field_filters = extract_filters_from_query(request)

    # Build filter object
    filters = RowFilter(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        filters=field_filters
    )

    # Get rows from service
    rows, total = row_service.list_rows(
        project_id=project_id,
        table_id=table_id,
        filters=filters
    )

    # Convert to RowData objects
    row_data_list = [
        RowData(
            row_id=row["row_id"],
            table_id=row["table_id"],
            row_data=row["row_data"],
            created_at=row["created_at"],
            updated_at=row.get("updated_at")
        )
        for row in rows
    ]

    # Calculate has_more
    has_more = (offset + limit) < total

    return RowListResponse(
        rows=row_data_list,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more
    )


@router.get(
    "/{project_id}/tables/{table_id}/rows/{row_id}",
    response_model=RowResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved row",
            "model": RowResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Row not found",
            "model": ErrorResponse
        }
    },
    summary="Get single row",
    description="""
    Get a single row by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Full row data including all fields
    - 404 ROW_NOT_FOUND if row does not exist
    """
)
async def get_row(
    project_id: str = Path(..., description="Project ID"),
    table_id: str = Path(..., description="Table ID"),
    row_id: str = Path(..., description="Row ID"),
    current_user: str = Depends(get_current_user)
) -> RowResponse:
    """
    Get a single row by ID.

    Args:
        project_id: Project identifier
        table_id: Table identifier
        row_id: Row identifier
        current_user: Authenticated user ID

    Returns:
        RowResponse with full row data

    Raises:
        APIError: If row not found (404 ROW_NOT_FOUND)
    """
    row = row_service.get_row(
        project_id=project_id,
        table_id=table_id,
        row_id=row_id
    )

    if not row:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ROW_NOT_FOUND",
            detail=f"Row not found: {row_id}"
        )

    return RowResponse(
        row_id=row["row_id"],
        table_id=row["table_id"],
        project_id=row["project_id"],
        row_data=row["row_data"],
        created_at=row["created_at"],
        updated_at=row.get("updated_at")
    )


@router.delete(
    "/{project_id}/tables/{table_id}/rows/{row_id}",
    response_model=RowDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully deleted row",
            "model": RowDeleteResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Row not found",
            "model": ErrorResponse
        }
    },
    summary="Delete row",
    description="""
    Delete a row from a table.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Confirmation of deletion with timestamp
    - 404 ROW_NOT_FOUND if row does not exist
    """
)
async def delete_row(
    project_id: str = Path(..., description="Project ID"),
    table_id: str = Path(..., description="Table ID"),
    row_id: str = Path(..., description="Row ID"),
    current_user: str = Depends(get_current_user)
) -> RowDeleteResponse:
    """
    Delete a row from a table.

    Args:
        project_id: Project identifier
        table_id: Table identifier
        row_id: Row identifier
        current_user: Authenticated user ID

    Returns:
        RowDeleteResponse confirming deletion

    Raises:
        APIError: If row not found (404 ROW_NOT_FOUND)
    """
    # Check if row exists first
    if not row_service.row_exists(project_id, table_id, row_id):
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ROW_NOT_FOUND",
            detail=f"Row not found: {row_id}"
        )

    # Delete the row
    deleted = row_service.delete_row(
        project_id=project_id,
        table_id=table_id,
        row_id=row_id
    )

    if not deleted:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ROW_NOT_FOUND",
            detail=f"Row not found: {row_id}"
        )

    return RowDeleteResponse(
        row_id=row_id,
        table_id=table_id,
        deleted=True,
        deleted_at=datetime.utcnow().isoformat() + "Z"
    )
