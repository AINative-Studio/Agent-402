"""
Tables API endpoints.
Implements table creation and management per Epic 7, Issue 1.
Per PRD Section 6 (ZeroDB Integration): Compliance records storage.

Endpoints:
- POST /v1/public/{project_id}/tables - Create a new table
- GET /v1/public/{project_id}/tables - List all tables
- GET /v1/public/{project_id}/tables/{table_id} - Get table details
- DELETE /v1/public/{project_id}/tables/{table_id} - Delete a table
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, status
from app.core.auth import get_current_user
from app.core.errors import TableNotFoundError
from app.schemas.tables import (
    TableCreateRequest,
    TableResponse,
    TableListResponse,
    TableDeleteResponse,
    TableSchema,
    FieldDefinition,
    FieldType,
    ErrorResponse
)
from app.services.table_service import table_service
from app.services.project_service import project_service


router = APIRouter(
    prefix="/v1/public",
    tags=["tables"]
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


def table_to_response(table) -> TableResponse:
    """
    Convert internal Table model to TableResponse schema.

    Args:
        table: Internal Table model

    Returns:
        TableResponse schema object
    """
    # Convert stored schema dict back to TableSchema
    schema_fields = {}
    for field_name, field_data in table.schema.get("fields", {}).items():
        schema_fields[field_name] = FieldDefinition(
            type=FieldType(field_data["type"]),
            required=field_data.get("required", False),
            default=field_data.get("default")
        )

    table_schema = TableSchema(
        fields=schema_fields,
        indexes=table.schema.get("indexes", [])
    )

    return TableResponse(
        id=table.id,
        table_name=table.table_name,
        description=table.description,
        schema=table_schema,
        project_id=table.project_id,
        row_count=table.row_count,
        created_at=table.created_at,
        updated_at=table.updated_at
    )


@router.post(
    "/{project_id}/tables",
    response_model=TableResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Table created successfully",
            "model": TableResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        },
        409: {
            "description": "Table with name already exists in project",
            "model": ErrorResponse
        },
        422: {
            "description": "Validation error in request body",
            "model": ErrorResponse
        }
    },
    summary="Create table with schema",
    description="""
    Create a new table with schema definition within a project.

    **Authentication:** Requires X-API-Key header

    **Per PRD Section 6 (ZeroDB Integration):**
    - Tables store compliance records and audit data
    - Schema defines field types and constraints
    - Indexes optimize query performance

    **Table Name Rules:**
    - Must be unique within the project
    - Must start with a lowercase letter
    - Can only contain lowercase letters, numbers, and underscores
    - Maximum 100 characters

    **Supported Field Types:**
    - string: Text data
    - integer: Whole numbers
    - float: Decimal numbers
    - boolean: true/false values
    - json: Nested JSON objects
    - timestamp: ISO 8601 datetime strings

    **Epic 7 Issue 1 Requirements:**
    - Return 409 TABLE_ALREADY_EXISTS for duplicate names
    - Support schema with fields and indexes
    - Validate index fields exist in schema
    """
)
async def create_table(
    project_id: str,
    request: TableCreateRequest,
    current_user: str = Depends(get_current_user)
) -> TableResponse:
    """
    Create a new table with schema definition in a project.

    Args:
        project_id: Project identifier from URL
        request: Table creation request body
        current_user: User ID from X-API-Key authentication

    Returns:
        TableResponse with created table details
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Create table - TableAlreadyExistsError is an APIError and will be
    # handled by the exception handler with proper error_code
    table, created = await table_service.create_table(
        project_id=project_id,
        table_name=request.table_name,
        schema=request.schema,
        description=request.description
    )

    return table_to_response(table)


@router.get(
    "/{project_id}/tables",
    response_model=TableListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved tables list",
            "model": TableListResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project not found",
            "model": ErrorResponse
        }
    },
    summary="List tables in project",
    description="""
    List all tables for a project.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Array of tables with id, table_name, description, schema, row_count
    - Empty array if no tables exist

    **Per PRD Section 6:** Lists all ZeroDB tables registered to project.
    """
)
async def list_tables(
    project_id: str,
    current_user: str = Depends(get_current_user)
) -> TableListResponse:
    """
    List all tables for a project.

    Args:
        project_id: Project identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        TableListResponse with list of tables and total count
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Get tables for project
    tables = await table_service.list_project_tables(project_id)

    # Convert to response models
    table_responses: List[TableResponse] = [
        table_to_response(table)
        for table in tables
    ]

    return TableListResponse(
        tables=table_responses,
        total=len(table_responses)
    )


@router.get(
    "/{project_id}/tables/{table_id}",
    response_model=TableResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved table",
            "model": TableResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project or table not found",
            "model": ErrorResponse
        }
    },
    summary="Get table by ID",
    description="""
    Get a single table with schema by ID.

    **Authentication:** Requires X-API-Key header

    **Returns:**
    - Table details with id, table_name, description, schema, row_count
    - 404 if table not found or doesn't belong to project
    """
)
async def get_table(
    project_id: str,
    table_id: str,
    current_user: str = Depends(get_current_user)
) -> TableResponse:
    """
    Get a single table by ID.

    Args:
        project_id: Project identifier from URL
        table_id: Table identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        TableResponse with table details
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Get table
    table = table_service.get_table_by_id(table_id, project_id)
    if not table:
        raise TableNotFoundError(table_id)

    return table_to_response(table)


@router.delete(
    "/{project_id}/tables/{table_id}",
    response_model=TableDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Table deleted successfully",
            "model": TableDeleteResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Not authorized to access project",
            "model": ErrorResponse
        },
        404: {
            "description": "Project or table not found",
            "model": ErrorResponse
        }
    },
    summary="Delete table",
    description="""
    Delete a table and all its data from a project.

    **Authentication:** Requires X-API-Key header

    **Warning:** This operation is irreversible. All data in the table will be lost.

    **Returns:**
    - Confirmation of deletion with table ID and name
    - 404 if table not found or doesn't belong to project
    """
)
async def delete_table(
    project_id: str,
    table_id: str,
    current_user: str = Depends(get_current_user)
) -> TableDeleteResponse:
    """
    Delete a table from a project.

    Args:
        project_id: Project identifier from URL
        table_id: Table identifier from URL
        current_user: User ID from X-API-Key authentication

    Returns:
        TableDeleteResponse with deletion confirmation
    """
    # Validate project access
    validate_project_access(project_id, current_user)

    # Delete table
    table = table_service.delete_table(table_id, project_id)
    if not table:
        raise TableNotFoundError(table_id)

    return TableDeleteResponse(
        id=table.id,
        table_name=table.table_name,
        deleted=True,
        deleted_at=datetime.utcnow()
    )
