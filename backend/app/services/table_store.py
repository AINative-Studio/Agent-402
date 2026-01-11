"""
Table data store.
For MVP demo (PRD Section 9), we use deterministic in-memory storage.
In production, this would connect to ZeroDB or a database.
Epic 7, Issue 2: Row insertion support requires table store.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.models.table import Table, TableSchema, FieldDefinition, FieldType


class TableStore:
    """
    In-memory table store for deterministic demo.
    Per PRD Section 9: Demo setup must be deterministic.
    """

    def __init__(self):
        self._tables: Dict[str, Table] = {}
        self._initialize_demo_tables()

    def _initialize_demo_tables(self):
        """
        Initialize deterministic demo tables per PRD Section 9.
        Creates predefined tables for demo projects.
        """
        demo_tables = [
            # Tables for user_1 project 1
            Table(
                id="tbl_demo_001",
                name="customers",
                description="Customer records for financial transactions",
                project_id="proj_demo_u1_001",
                schema=TableSchema(
                    fields={
                        "name": FieldDefinition(
                            name="name",
                            type=FieldType.STRING,
                            required=True
                        ),
                        "email": FieldDefinition(
                            name="email",
                            type=FieldType.STRING,
                            required=True
                        ),
                        "age": FieldDefinition(
                            name="age",
                            type=FieldType.INTEGER,
                            required=False
                        ),
                        "active": FieldDefinition(
                            name="active",
                            type=FieldType.BOOLEAN,
                            required=False,
                            default=True
                        ),
                    }
                ),
                created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Table(
                id="tbl_demo_002",
                name="transactions",
                description="Financial transaction records",
                project_id="proj_demo_u1_001",
                schema=TableSchema(
                    fields={
                        "amount": FieldDefinition(
                            name="amount",
                            type=FieldType.FLOAT,
                            required=True
                        ),
                        "currency": FieldDefinition(
                            name="currency",
                            type=FieldType.STRING,
                            required=True
                        ),
                        "timestamp": FieldDefinition(
                            name="timestamp",
                            type=FieldType.DATETIME,
                            required=False
                        ),
                        "metadata": FieldDefinition(
                            name="metadata",
                            type=FieldType.JSON,
                            required=False
                        ),
                    }
                ),
                created_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # Tables for user_1 project 2
            Table(
                id="tbl_demo_003",
                name="agents_config",
                description="Agent configuration data",
                project_id="proj_demo_u1_002",
                schema=TableSchema(
                    fields={
                        "agent_name": FieldDefinition(
                            name="agent_name",
                            type=FieldType.STRING,
                            required=True
                        ),
                        "config": FieldDefinition(
                            name="config",
                            type=FieldType.JSON,
                            required=False
                        ),
                    }
                ),
                created_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # Tables for user_2 project 1
            Table(
                id="tbl_demo_004",
                name="analytics",
                description="Analytics and metrics data",
                project_id="proj_demo_u2_001",
                schema=TableSchema(
                    fields={
                        "metric_name": FieldDefinition(
                            name="metric_name",
                            type=FieldType.STRING,
                            required=True
                        ),
                        "value": FieldDefinition(
                            name="value",
                            type=FieldType.FLOAT,
                            required=True
                        ),
                        "tags": FieldDefinition(
                            name="tags",
                            type=FieldType.ARRAY,
                            required=False
                        ),
                    }
                ),
                created_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
            ),
            # Schemaless table for flexible data
            Table(
                id="tbl_demo_005",
                name="flexible_data",
                description="Schemaless table for flexible data storage",
                project_id="proj_demo_u1_001",
                schema=None,  # No schema - accepts any data
                created_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for table in demo_tables:
            self._tables[table.id] = table

    def get_by_id(self, table_id: str) -> Optional[Table]:
        """Get table by ID."""
        return self._tables.get(table_id)

    def get_by_project_id(self, project_id: str) -> List[Table]:
        """
        Get all tables for a project.
        Returns empty list if no tables exist.
        """
        return [
            table for table in self._tables.values()
            if table.project_id == project_id
        ]

    def get_by_name(self, name: str, project_id: str) -> Optional[Table]:
        """
        Get table by name within a project.
        Table names should be unique within a project.
        """
        for table in self._tables.values():
            if table.name == name and table.project_id == project_id:
                return table
        return None

    def create(self, table: Table) -> Table:
        """
        Create a new table.
        For production, this would insert into ZeroDB.
        """
        self._tables[table.id] = table
        return table

    def update(self, table: Table) -> Table:
        """Update an existing table."""
        if table.id not in self._tables:
            raise ValueError(f"Table not found: {table.id}")
        table.updated_at = datetime.now(timezone.utc)
        self._tables[table.id] = table
        return table

    def delete(self, table_id: str) -> bool:
        """Delete a table by ID."""
        if table_id in self._tables:
            del self._tables[table_id]
            return True
        return False

    def count_by_project_id(self, project_id: str) -> int:
        """Count tables in a project."""
        return len(self.get_by_project_id(project_id))

    def exists_in_project(self, table_id: str, project_id: str) -> bool:
        """Check if a table exists in a specific project."""
        table = self.get_by_id(table_id)
        return table is not None and table.project_id == project_id


# Global singleton instance for demo
table_store = TableStore()
