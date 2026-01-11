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
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from app.schemas.tables import TableSchema, FieldDefinition, FieldType


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
        """Initialize the table service with in-memory storage."""
        # Structure: {project_id: {table_name: Table}}
        self._tables: Dict[str, Dict[str, Table]] = {}
        # Index by table_id for fast lookups: {table_id: (project_id, table_name)}
        self._table_id_index: Dict[str, Tuple[str, str]] = {}

    def generate_table_id(self) -> str:
        """
        Generate a unique table ID.

        Returns:
            str: Unique table identifier with 'tbl_' prefix
        """
        return f"tbl_{uuid.uuid4().hex[:16]}"

    def create_table(
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
        from app.core.errors import TableAlreadyExistsError

        # Initialize project tables dict if not exists
        if project_id not in self._tables:
            self._tables[project_id] = {}

        # Check for duplicate table name
        if table_name in self._tables[project_id]:
            raise TableAlreadyExistsError(table_name, project_id)

        # Generate table ID
        table_id = self.generate_table_id()

        # Convert schema to dict for storage
        schema_dict = {
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

        # Create table instance
        table = Table(
            id=table_id,
            table_name=table_name,
            description=description,
            schema=schema_dict,
            project_id=project_id,
            row_count=0,
            created_at=datetime.utcnow(),
            updated_at=None
        )

        # Store table
        self._tables[project_id][table_name] = table
        self._table_id_index[table_id] = (project_id, table_name)

        return table, True

    def get_table_by_id(
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
        if table_id not in self._table_id_index:
            return None

        stored_project_id, table_name = self._table_id_index[table_id]

        # Verify project ownership
        if stored_project_id != project_id:
            return None

        return self._tables.get(project_id, {}).get(table_name)

    def get_table_by_name(
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
        return self._tables.get(project_id, {}).get(table_name)

    def list_project_tables(
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
        project_tables = self._tables.get(project_id, {})
        return list(project_tables.values())

    def delete_table(
        self,
        table_id: str,
        project_id: str
    ) -> Optional[Table]:
        """
        Delete a table from a project.

        Args:
            table_id: Table identifier
            project_id: Project identifier

        Returns:
            Deleted Table if found and removed, None otherwise
        """
        if table_id not in self._table_id_index:
            return None

        stored_project_id, table_name = self._table_id_index[table_id]

        # Verify project ownership
        if stored_project_id != project_id:
            return None

        # Get table before deletion
        table = self._tables.get(project_id, {}).get(table_name)
        if not table:
            return None

        # Remove from storage
        del self._tables[project_id][table_name]
        del self._table_id_index[table_id]

        # Clean up empty project dict
        if not self._tables[project_id]:
            del self._tables[project_id]

        return table

    def table_exists(
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
        return table_name in self._tables.get(project_id, {})

    def count_project_tables(self, project_id: str) -> int:
        """
        Count total tables for a project.

        Args:
            project_id: Project identifier

        Returns:
            Number of tables in the project
        """
        return len(self._tables.get(project_id, {}))

    def update_row_count(
        self,
        table_id: str,
        project_id: str,
        count: int
    ) -> bool:
        """
        Update the row count for a table.
        Used when rows are inserted or deleted.

        Args:
            table_id: Table identifier
            project_id: Project identifier
            count: New row count

        Returns:
            True if updated, False if table not found
        """
        table = self.get_table_by_id(table_id, project_id)
        if not table:
            return False

        table.row_count = count
        table.updated_at = datetime.utcnow()
        return True


# Singleton instance
table_service = TableService()
