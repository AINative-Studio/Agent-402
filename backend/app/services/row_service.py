"""
Row Service for Epic 7:
- Issue 2: Row insertion with row_data field and schema validation
- Issue 4: List rows with pagination

Implements row query operations for the Tables API.
Provides pagination, filtering, and sorting for table rows.

Per PRD Section 6 (ZeroDB Integration):
- Support row insertion with schema validation
- Support row listing with pagination
- Enable filtering via field values
- Support sorting by field names

Per PRD Section 9 (Demo verification):
- Provide deterministic query behavior
- Support pagination for demo verification
- Enable row retrieval and deletion

Per PRD Section 10 (Contract stability):
- Field name MUST be row_data (NOT data or rows)
- TABLE_NOT_FOUND (404) if table doesn't exist
- SCHEMA_VALIDATION_ERROR (422) if data doesn't match schema

DX Contract Compliance:
- All operations are deterministic
- Clear error handling for non-existent rows
- Consistent response formats
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from app.schemas.rows import SortOrder, RowData, RowFilter
from app.services.table_service import table_service
from app.schemas.tables import FieldType
from app.core.errors import TableNotFoundError, SchemaValidationError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)


class RowService:
    """
    Service for table row operations.

    Provides CRUD operations and query functionality for table rows.
    Implements Epic 7 Issue 2 (row insertion) and Issue 4 (pagination/filtering).
    """

    def __init__(self):
        """Initialize the row service with lazy ZeroDB client."""
        self._table_service = table_service
        self._client = None

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # =========================================================================
    # Schema Validation Methods (Epic 7, Issue 2)
    # =========================================================================

    def _get_python_type_name(self, value: Any) -> str:
        """
        Get a human-readable type name for a Python value.

        Args:
            value: Any Python value

        Returns:
            Human-readable type name
        """
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return type(value).__name__

    def _validate_field_type(
        self,
        field_name: str,
        value: Any,
        expected_type: FieldType
    ) -> Optional[Dict[str, str]]:
        """
        Validate a single field value against expected type.

        Args:
            field_name: Name of the field
            value: Value to validate
            expected_type: Expected FieldType

        Returns:
            None if valid, or error dict with validation details
        """
        # None values are allowed for non-required fields (checked separately)
        if value is None:
            return None

        actual_type = self._get_python_type_name(value)

        # Type checking based on expected type
        valid = False
        if expected_type == FieldType.STRING:
            valid = isinstance(value, str)
        elif expected_type == FieldType.INTEGER:
            # Accept int but not bool (bool is subclass of int in Python)
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == FieldType.FLOAT:
            # Accept float or int for numeric flexibility
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == FieldType.BOOLEAN:
            valid = isinstance(value, bool)
        elif expected_type == FieldType.TIMESTAMP:
            # Accept string (ISO format) or datetime objects
            valid = isinstance(value, (str, datetime))
        elif expected_type == FieldType.JSON:
            # Accept dict or list for JSON type
            valid = isinstance(value, (dict, list))
        elif expected_type == FieldType.ARRAY:
            valid = isinstance(value, list)

        if not valid:
            return {
                "field": field_name,
                "expected_type": expected_type.value,
                "actual_type": actual_type,
                "message": f"Field '{field_name}' expected type '{expected_type.value}' but got '{actual_type}'"
            }

        return None

    def _validate_row_against_schema(
        self,
        row_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Validate row data against table schema.

        Args:
            row_data: Row data to validate
            schema: Table schema dictionary with 'fields' key

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[Dict[str, str]] = []

        # Schema is a dict: {"fields": {...}, "indexes": [...]}
        fields = schema.get("fields", {})

        # Check for required fields
        for field_name, field_def in fields.items():
            is_required = field_def.get("required", False)
            if is_required and field_name not in row_data:
                errors.append({
                    "field": field_name,
                    "expected_type": field_def.get("type", "unknown"),
                    "actual_type": "missing",
                    "message": f"Required field '{field_name}' is missing"
                })

        # Validate field types for provided fields
        for field_name, value in row_data.items():
            if field_name in fields:
                field_def = fields[field_name]
                field_type_str = field_def.get("type", "string")
                try:
                    field_type = FieldType(field_type_str)
                    error = self._validate_field_type(field_name, value, field_type)
                    if error:
                        errors.append(error)
                except ValueError:
                    # Unknown field type, skip validation
                    pass
            # Extra fields not in schema are allowed (flexible schema approach)

        return errors

    def get_table(self, table_id: str, project_id: str) -> Any:
        """
        Get a table by ID and verify it belongs to the project.

        Epic 7 Issue 2: Validate table exists before row insertion.

        Args:
            table_id: Table identifier
            project_id: Project identifier

        Returns:
            Table if found and belongs to project

        Raises:
            TableNotFoundError: If table doesn't exist or doesn't belong to project
        """
        table = self._table_service.get_table_by_id(table_id, project_id)

        if not table:
            raise TableNotFoundError(table_id)

        return table

    async def insert_rows_validated(
        self,
        project_id: str,
        table_id: str,
        row_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Insert one or more rows into a table with schema validation.

        Epic 7 Issue 2: Row insertion with row_data field.
        - Validates table exists
        - Validates row data against schema if present
        - Supports batch insert with array of rows

        Args:
            project_id: Project identifier
            table_id: Table identifier
            row_data: Single row dict or list of row dicts

        Returns:
            List of created row records with row_id and created_at

        Raises:
            TableNotFoundError: If table doesn't exist or doesn't belong to project
            SchemaValidationError: If row data doesn't match table schema
        """
        # Verify table exists and belongs to project
        table = self.get_table(table_id, project_id)

        # Normalize to list for uniform processing
        rows_to_insert: List[Dict[str, Any]] = []
        if isinstance(row_data, list):
            rows_to_insert = row_data
        else:
            rows_to_insert = [row_data]

        # Validate all rows against schema if schema exists
        if table.schema:
            all_errors: List[Dict[str, str]] = []
            for idx, data in enumerate(rows_to_insert):
                errors = self._validate_row_against_schema(data, table.schema)
                if errors:
                    # Add row index to errors for batch operations
                    for error in errors:
                        error["row_index"] = str(idx)
                    all_errors.extend(errors)

            if all_errors:
                # Build detailed error message
                if len(all_errors) == 1:
                    detail = all_errors[0]["message"]
                else:
                    detail = f"Schema validation failed with {len(all_errors)} errors"
                raise SchemaValidationError(detail=detail, validation_errors=all_errors)

        # Insert all rows
        created_rows: List[Dict[str, Any]] = []

        for data in rows_to_insert:
            # Apply default values from schema if not provided
            final_data = data.copy()
            if table.schema:
                # Schema is a dict: {"fields": {...}, "indexes": [...]}
                fields = table.schema.get("fields", {})
                for field_name, field_def in fields.items():
                    default_value = field_def.get("default")
                    if field_name not in final_data and default_value is not None:
                        final_data[field_name] = default_value

            # Insert the row using existing method
            row_record = await self.insert_row(
                project_id=project_id,
                table_id=table_id,
                row_data=final_data
            )
            created_rows.append(row_record)

        return created_rows

    async def insert_rows(
        self,
        project_id: str,
        table_id: str,
        rows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Insert multiple rows into a table with schema validation.

        Epic 7 Issue 2: Row insertion with row_data field.
        This method is called by the API endpoint.

        Args:
            project_id: Project identifier
            table_id: Table identifier
            rows: List of row data dictionaries

        Returns:
            List of created row records with row_id and created_at

        Raises:
            TableNotFoundError: If table doesn't exist or doesn't belong to project
            SchemaValidationError: If row data doesn't match table schema
        """
        # Use the validated insert method
        return await self.insert_rows_validated(
            project_id=project_id,
            table_id=table_id,
            row_data=rows
        )

    # =========================================================================
    # Core Row Operations (ZeroDB-backed methods)
    # =========================================================================

    def _get_table_name(self, table_id: str) -> str:
        """
        Get the table name for ZeroDB API calls.

        The ZeroDB API uses table_name (or table_id) in the URL path.

        Args:
            table_id: Table identifier

        Returns:
            Table name/id for API calls
        """
        return table_id

    async def insert_row(
        self,
        project_id: str,
        table_id: str,
        row_data: Dict[str, Any],
        row_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Insert a new row into a table via ZeroDB API.

        Args:
            project_id: Project identifier
            table_id: Table identifier
            row_data: Row data as key-value pairs
            row_id: Optional row ID (ignored, ZeroDB generates its own)

        Returns:
            Complete row record with system fields from ZeroDB
        """
        table_name = self._get_table_name(table_id)

        try:
            # ZeroDB insert_row returns the created row with row_id
            result = await self.client.insert_row(table_name, row_data)

            # Normalize response to expected format
            row_record = {
                "row_id": result.get("row_id"),
                "table_id": table_id,
                "project_id": project_id,
                "row_data": result.get("row_data", row_data),
                "created_at": result.get("created_at", datetime.utcnow().isoformat() + "Z"),
                "updated_at": result.get("updated_at")
            }
            return row_record

        except Exception as e:
            logger.error(f"Failed to insert row into table {table_id}: {e}")
            raise

    async def get_row(
        self,
        project_id: str,
        table_id: str,
        row_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single row by ID from ZeroDB.

        Args:
            project_id: Project identifier
            table_id: Table identifier
            row_id: Row identifier

        Returns:
            Row record or None if not found
        """
        table_name = self._get_table_name(table_id)

        try:
            result = await self.client.get_row(table_name, row_id)

            # Normalize response to expected format
            row_record = {
                "row_id": result.get("row_id", row_id),
                "table_id": table_id,
                "project_id": project_id,
                "row_data": result.get("row_data", {}),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at")
            }
            return row_record

        except Exception as e:
            # Check for 404 (not found) - return None
            # httpx raises HTTPStatusError with response attribute
            if hasattr(e, 'response'):
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 404:
                    return None
            logger.error(f"Failed to get row {row_id} from table {table_id}: {e}")
            raise

    async def delete_row(
        self,
        project_id: str,
        table_id: str,
        row_id: str
    ) -> bool:
        """
        Delete a row from a table via ZeroDB API.

        Args:
            project_id: Project identifier
            table_id: Table identifier
            row_id: Row identifier

        Returns:
            True if row was deleted, False if not found
        """
        table_name = self._get_table_name(table_id)

        try:
            await self.client.delete_row(table_name, row_id)
            return True

        except Exception as e:
            # Check for 404 (not found) - return False
            # httpx raises HTTPStatusError with response attribute
            if hasattr(e, 'response'):
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 404:
                    return False
            logger.error(f"Failed to delete row {row_id} from table {table_id}: {e}")
            raise

    async def list_rows(
        self,
        project_id: str,
        table_id: str,
        filters: Optional[RowFilter] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List rows with pagination, filtering, and sorting via ZeroDB API.

        Epic 7 Issue 4 Implementation:
        - Supports pagination via limit/offset
        - Supports filtering via query parameters
        - Supports sorting via sort_by/order

        Args:
            project_id: Project identifier
            table_id: Table identifier
            filters: Optional filter parameters

        Returns:
            Tuple of (paginated_rows, total_count)
        """
        table_name = self._get_table_name(table_id)
        limit = filters.limit if filters else 100
        offset = filters.offset if filters else 0

        try:
            # Use query_rows if filters are provided, otherwise list_rows
            if filters and filters.filters:
                # Convert filters to MongoDB-style query
                query_filter = {}
                for field_name, value in filters.filters.items():
                    query_filter[f"row_data.{field_name}"] = value

                result = await self.client.query_rows(
                    table_name,
                    filter=query_filter,
                    limit=limit,
                    skip=offset
                )
            else:
                result = await self.client.list_rows(
                    table_name,
                    skip=offset,
                    limit=limit
                )

            # Extract rows from response
            rows = result.get("rows", [])
            total_count = result.get("total", len(rows))

            # Normalize rows to expected format
            normalized_rows = []
            for row in rows:
                normalized_row = {
                    "row_id": row.get("row_id"),
                    "table_id": table_id,
                    "project_id": project_id,
                    "row_data": row.get("row_data", {}),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                }
                normalized_rows.append(normalized_row)

            # Apply sorting locally if specified (ZeroDB may not support all sort options)
            if filters and filters.sort_by:
                normalized_rows = self._apply_sorting(
                    normalized_rows,
                    filters.sort_by,
                    filters.order
                )
            else:
                # Default sort by created_at descending
                normalized_rows = sorted(
                    normalized_rows,
                    key=lambda x: x.get("created_at", "") or "",
                    reverse=True
                )

            return normalized_rows, total_count

        except Exception as e:
            logger.error(f"Failed to list rows from table {table_id}: {e}")
            raise

    def _apply_filters(
        self,
        rows: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply field filters to rows.

        Filters match against the row_data field values.
        Supports exact match comparison.

        Args:
            rows: List of row records
            filters: Field filters as key-value pairs

        Returns:
            Filtered list of rows
        """
        if not filters:
            return rows

        filtered_rows = []
        for row in rows:
            row_data = row.get("row_data", {})
            match = True

            for field_name, expected_value in filters.items():
                actual_value = row_data.get(field_name)
                if actual_value != expected_value:
                    match = False
                    break

            if match:
                filtered_rows.append(row)

        return filtered_rows

    def _apply_sorting(
        self,
        rows: List[Dict[str, Any]],
        sort_by: str,
        order: SortOrder
    ) -> List[Dict[str, Any]]:
        """
        Apply sorting to rows.

        Sorts by row_data field or system fields (created_at, updated_at, row_id).

        Args:
            rows: List of row records
            sort_by: Field name to sort by
            order: Sort order (asc or desc)

        Returns:
            Sorted list of rows
        """
        reverse = order == SortOrder.DESC

        def get_sort_key(row: Dict[str, Any]) -> Any:
            # Check system fields first
            if sort_by in ("created_at", "updated_at", "row_id", "table_id"):
                value = row.get(sort_by, "")
            else:
                # Check row_data fields
                value = row.get("row_data", {}).get(sort_by, "")

            # Handle None values for sorting
            if value is None:
                return ""
            return value

        return sorted(rows, key=get_sort_key, reverse=reverse)

    async def row_exists(
        self,
        project_id: str,
        table_id: str,
        row_id: str
    ) -> bool:
        """
        Check if a row exists via ZeroDB API.

        Args:
            project_id: Project identifier
            table_id: Table identifier
            row_id: Row identifier

        Returns:
            True if row exists, False otherwise
        """
        row = await self.get_row(project_id, table_id, row_id)
        return row is not None

    async def get_table_stats(
        self,
        project_id: str,
        table_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics for a table via ZeroDB API.

        Args:
            project_id: Project identifier
            table_id: Table identifier

        Returns:
            Dictionary with table statistics
        """
        table_name = self._get_table_name(table_id)

        try:
            # Get row count by listing with limit 0 (or use a small limit and get total)
            result = await self.client.list_rows(table_name, skip=0, limit=1)
            row_count = result.get("total", 0)

            return {
                "table_id": table_id,
                "project_id": project_id,
                "row_count": row_count
            }

        except Exception as e:
            logger.error(f"Failed to get table stats for {table_id}: {e}")
            raise


# Singleton instance
row_service = RowService()
