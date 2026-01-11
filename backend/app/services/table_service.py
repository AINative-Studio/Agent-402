"""
Table Service for Epic 7, Issue 1.
Implements table creation and management with schema definitions.
Per PRD Section 6 (ZeroDB Integration): Compliance records storage.

Business Logic:
- Table names must be unique within a project
- Schema validation before table creation
- Support for field types: string, integer, float, boolean, json, timestamp
- Index management for optimized queries
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import httpx
from app.schemas.tables import TableSchema, FieldDefinition, FieldType
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)


@dataclass
class Table:
    """
    Internal table model for business logic.
    Represents a table definition with schema.
    """
    id: str
    table_name: str
    description: Optional[str]
    schema: Dict[str, Any]
    project_id: str
    row_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class TableService:
    """
    Service for table management operations.

    Provides business logic for:
    - Creating tables with schema definitions
    - Listing tables in a project
    - Retrieving table details
    - Deleting tables

    Per Epic 7 Issue 1:
    - Table names unique within project
    - Support schema with fields and indexes
    - Return TABLE_ALREADY_EXISTS for duplicates
    """

    def __init__(self):
        """Initialize the table service with ZeroDB client."""
        # ZeroDB client will be fetched on demand
        pass

    def _get_client(self):
        """Get the ZeroDB client instance."""
        return get_zerodb_client()

    def _parse_table_response(self, data: Dict[str, Any], project_id: str) -> Table:
        """
        Parse ZeroDB table response into Table dataclass.

        Args:
            data: Raw table data from ZeroDB API
            project_id: Project identifier

        Returns:
            Table instance
        """
        # Handle datetime parsing
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_at = datetime.utcnow()
        elif not isinstance(created_at, datetime):
            created_at = datetime.utcnow()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                updated_at = None
        elif not isinstance(updated_at, datetime):
            updated_at = None

        return Table(
            id=data.get("table_id", data.get("id", "")),
            table_name=data.get("table_name", ""),
            description=data.get("description"),
            schema=data.get("schema", data.get("schema_definition", {})),
            project_id=project_id,
            row_count=data.get("row_count", 0),
            created_at=created_at,
            updated_at=updated_at
        )

    async def create_table(
        self,
        project_id: str,
        table_name: str,
        schema: TableSchema,
        description: Optional[str] = None
    ) -> Tuple[Table, bool]:
        """
        Create a new table with schema definition.

        Args:
            project_id: Project identifier
            table_name: Unique table name within project
            schema: Table schema with fields and indexes
            description: Optional table description

        Returns:
            Tuple of (Table, created) where created is True if new

        Raises:
            TableAlreadyExistsError: If table name already exists in project
        """
        from app.core.errors import TableAlreadyExistsError, ZeroDBError

        # Convert schema to ZeroDB format
        schema_definition = {
            "fields": {
                name: {
                    "type": field_def.type.value,
                    "required": field_def.required,
                    "default": field_def.default
                }
                for name, field_def in schema.fields.items()
            },
            "indexes": schema.indexes or []
        }

        if description:
            schema_definition["description"] = description

        try:
            client = self._get_client()
            result = await client.create_table(table_name, schema_definition)

            # Parse response into Table
            table = self._parse_table_response(result, project_id)
            return table, True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Table already exists
                raise TableAlreadyExistsError(table_name, project_id)
            elif e.response.status_code == 400:
                # Bad request - could be duplicate or invalid schema
                error_detail = ""
                try:
                    error_detail = e.response.json().get("detail", "")
                except Exception:
                    pass
                if "already exists" in error_detail.lower() or "duplicate" in error_detail.lower():
                    raise TableAlreadyExistsError(table_name, project_id)
                raise ZeroDBError(f"Failed to create table: {error_detail or str(e)}")
            else:
                logger.error(f"ZeroDB create_table failed: {e}")
                raise ZeroDBError(f"Failed to create table: {e}")
        except httpx.RequestError as e:
            logger.error(f"ZeroDB connection error: {e}")
            raise ZeroDBError(f"Connection to ZeroDB failed: {e}")

    async def get_table_by_id(
        self,
        table_id: str,
        project_id: str
    ) -> Optional[Table]:
        """
        Get a table by its ID within a project.

        Args:
            table_id: Table identifier
            project_id: Project identifier

        Returns:
            Table if found and belongs to project, None otherwise
        """
        from app.core.errors import ZeroDBError

        try:
            client = self._get_client()
            result = await client.get_table(table_id)
            return self._parse_table_response(result, project_id)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"ZeroDB get_table failed: {e}")
            raise ZeroDBError(f"Failed to get table: {e}")
        except httpx.RequestError as e:
            logger.error(f"ZeroDB connection error: {e}")
            raise ZeroDBError(f"Connection to ZeroDB failed: {e}")

    async def get_table_by_name(
        self,
        table_name: str,
        project_id: str
    ) -> Optional[Table]:
        """
        Get a table by its name within a project.

        Args:
            table_name: Table name
            project_id: Project identifier

        Returns:
            Table if found, None otherwise
        """
        from app.core.errors import ZeroDBError

        try:
            # ZeroDB uses table_name as identifier for get_table
            client = self._get_client()
            result = await client.get_table(table_name)
            return self._parse_table_response(result, project_id)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"ZeroDB get_table failed: {e}")
            raise ZeroDBError(f"Failed to get table: {e}")
        except httpx.RequestError as e:
            logger.error(f"ZeroDB connection error: {e}")
            raise ZeroDBError(f"Connection to ZeroDB failed: {e}")

    async def list_project_tables(
        self,
        project_id: str
    ) -> List[Table]:
        """
        List all tables for a project.

        Args:
            project_id: Project identifier

        Returns:
            List of tables in the project (empty if none)
        """
        from app.core.errors import ZeroDBError

        try:
            client = self._get_client()
            result = await client.list_tables()

            # Parse tables from response
            tables_data = result.get("tables", result.get("items", []))
            if not isinstance(tables_data, list):
                tables_data = []

            return [
                self._parse_table_response(table_data, project_id)
                for table_data in tables_data
            ]

        except httpx.HTTPStatusError as e:
            logger.error(f"ZeroDB list_tables failed: {e}")
            raise ZeroDBError(f"Failed to list tables: {e}")
        except httpx.RequestError as e:
            logger.error(f"ZeroDB connection error: {e}")
            raise ZeroDBError(f"Connection to ZeroDB failed: {e}")

    async def delete_table(
        self,
        table_id: str,
        project_id: str
    ) -> Optional[Table]:
        """
        Delete a table from a project.

        Args:
            table_id: Table identifier (can be table_name in ZeroDB)
            project_id: Project identifier

        Returns:
            Deleted Table if found and removed, None otherwise
        """
        from app.core.errors import ZeroDBError

        try:
            # First get the table to return it after deletion
            client = self._get_client()
            table = await self.get_table_by_id(table_id, project_id)
            if not table:
                # Try by name as fallback
                table = await self.get_table_by_name(table_id, project_id)
                if not table:
                    return None

            # Delete using table_name (ZeroDB uses name for deletion)
            await client.delete_table(table.table_name)
            return table

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"ZeroDB delete_table failed: {e}")
            raise ZeroDBError(f"Failed to delete table: {e}")
        except httpx.RequestError as e:
            logger.error(f"ZeroDB connection error: {e}")
            raise ZeroDBError(f"Connection to ZeroDB failed: {e}")

    async def table_exists(
        self,
        table_name: str,
        project_id: str
    ) -> bool:
        """
        Check if a table exists in a project.

        Args:
            table_name: Table name to check
            project_id: Project identifier

        Returns:
            True if table exists, False otherwise
        """
        table = await self.get_table_by_name(table_name, project_id)
        return table is not None

    async def count_project_tables(self, project_id: str) -> int:
        """
        Count total tables for a project.

        Args:
            project_id: Project identifier

        Returns:
            Number of tables in the project
        """
        tables = await self.list_project_tables(project_id)
        return len(tables)

    async def update_row_count(
        self,
        table_id: str,
        project_id: str,
        count: int
    ) -> bool:
        """
        Update the row count for a table.
        Used when rows are inserted or deleted.

        Note: In ZeroDB, row count is typically managed automatically.
        This method is kept for interface compatibility.

        Args:
            table_id: Table identifier
            project_id: Project identifier
            count: New row count

        Returns:
            True if table exists, False otherwise
        """
        # ZeroDB manages row counts automatically
        # We just verify the table exists
        table = await self.get_table_by_id(table_id, project_id)
        return table is not None


# Singleton instance
table_service = TableService()
