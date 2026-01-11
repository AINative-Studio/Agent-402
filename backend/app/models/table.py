"""
Table domain model.
Represents NoSQL tables with schema definition.
Epic 7, Issue 2: Row insertion support.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Any


class FieldType(str, Enum):
    """
    Supported field types for table schema.
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"


@dataclass
class FieldDefinition:
    """
    Schema field definition.

    Attributes:
        name: Field name
        type: Field data type
        required: Whether field is required
        default: Default value if not provided
    """
    name: str
    type: FieldType
    required: bool = False
    default: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type.value,
            "required": self.required,
            "default": self.default,
        }


@dataclass
class TableSchema:
    """
    Table schema definition.

    Attributes:
        fields: Dictionary of field name to field definition
    """
    fields: Dict[str, FieldDefinition] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "fields": {
                name: field_def.to_dict()
                for name, field_def in self.fields.items()
            }
        }


@dataclass
class Table:
    """
    Internal table model.
    Represents a NoSQL table within a project.

    Attributes:
        id: Unique table identifier
        name: Table name
        description: Table description
        schema: Table schema definition
        project_id: Project this table belongs to
        created_at: Timestamp of table creation
        updated_at: Timestamp of last update
    """
    id: str
    name: str
    project_id: str
    description: Optional[str] = None
    schema: Optional[TableSchema] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schema": self.schema.to_dict() if self.schema else None,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
