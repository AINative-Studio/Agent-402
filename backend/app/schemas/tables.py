"""
Table API schemas for request/response validation.
These schemas define the contract with API consumers per DX Contract.
Epic 7, Issue 1: Table creation with schema definitions.
Per PRD Section 6 (ZeroDB Integration): Compliance records storage.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator


class FieldType(str, Enum):
    """
    Supported field types for table schema definitions.
    Per Epic 7, Issue 1: string, integer, float, boolean, json, timestamp.
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    TIMESTAMP = "timestamp"


class FieldDefinition(BaseModel):
    """
    Definition for a single field in the table schema.
    """
    type: FieldType = Field(
        ...,
        description="Field data type (string, integer, float, boolean, json, timestamp)"
    )
    required: bool = Field(
        default=False,
        description="Whether this field is required when inserting rows"
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default value for this field if not provided"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "string",
                "required": True,
                "default": None
            }
        }


class TableSchema(BaseModel):
    """
    Schema definition for a table.
    Contains field definitions and index specifications.
    """
    fields: Dict[str, FieldDefinition] = Field(
        ...,
        description="Field definitions mapping field names to their type and constraints",
        min_length=1
    )
    indexes: Optional[List[str]] = Field(
        default_factory=list,
        description="List of field names to index for faster queries"
    )

    @validator('indexes')
    def validate_indexes_reference_valid_fields(cls, v, values):
        """
        Ensure all indexed fields exist in the schema.
        """
        if not v:
            return v

        fields = values.get('fields', {})
        for index_field in v:
            if index_field not in fields:
                raise ValueError(
                    f"Index field '{index_field}' does not exist in schema fields. "
                    f"Available fields: {list(fields.keys())}"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "fields": {
                    "event_type": {"type": "string", "required": True},
                    "agent_id": {"type": "string", "required": True},
                    "payload": {"type": "json", "required": False},
                    "timestamp": {"type": "timestamp", "required": True}
                },
                "indexes": ["event_type", "agent_id"]
            }
        }


class TableCreateRequest(BaseModel):
    """
    Request schema for POST /v1/public/{project_id}/tables.
    Creates a new table with the specified schema.
    """
    table_name: str = Field(
        ...,
        description="Unique table name within the project",
        min_length=1,
        max_length=100,
        pattern="^[a-z][a-z0-9_]*$",
        examples=["compliance_events"]
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of the table's purpose",
        max_length=500,
        examples=["Stores compliance event records for audit trail"]
    )
    schema: TableSchema = Field(
        ...,
        description="Table schema definition with fields and indexes"
    )

    @validator('table_name')
    def validate_table_name(cls, v):
        """
        Validate table name follows naming conventions.
        Must start with lowercase letter, contain only lowercase letters, numbers, underscores.
        """
        if not v:
            raise ValueError("table_name cannot be empty")
        if not v[0].isalpha() or not v[0].islower():
            raise ValueError("table_name must start with a lowercase letter")
        if not all(c.islower() or c.isdigit() or c == '_' for c in v):
            raise ValueError(
                "table_name can only contain lowercase letters, numbers, and underscores"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "compliance_events",
                "description": "Stores compliance event records for audit trail",
                "schema": {
                    "fields": {
                        "event_type": {"type": "string", "required": True},
                        "agent_id": {"type": "string", "required": True},
                        "payload": {"type": "json", "required": False},
                        "timestamp": {"type": "timestamp", "required": True}
                    },
                    "indexes": ["event_type", "agent_id"]
                }
            }
        }


class TableResponse(BaseModel):
    """
    Response schema for table operations.
    Returns full table details with schema information.
    """
    id: str = Field(..., description="Unique table identifier")
    table_name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    schema: TableSchema = Field(..., description="Table schema definition")
    project_id: str = Field(..., description="Project this table belongs to")
    row_count: int = Field(default=0, description="Number of rows in the table")
    created_at: datetime = Field(..., description="Timestamp of table creation")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last schema update")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "tbl_abc123",
                "table_name": "compliance_events",
                "description": "Stores compliance event records for audit trail",
                "schema": {
                    "fields": {
                        "event_type": {"type": "string", "required": True},
                        "agent_id": {"type": "string", "required": True},
                        "payload": {"type": "json", "required": False},
                        "timestamp": {"type": "timestamp", "required": True}
                    },
                    "indexes": ["event_type", "agent_id"]
                },
                "project_id": "proj_demo_u1_001",
                "row_count": 0,
                "created_at": "2026-01-11T00:00:00Z",
                "updated_at": None
            }
        }


class TableListResponse(BaseModel):
    """
    Response schema for listing tables.
    Returns array of tables for a project.
    """
    tables: List[TableResponse] = Field(
        default_factory=list,
        description="List of tables in the project"
    )
    total: int = Field(..., description="Total number of tables")

    class Config:
        json_schema_extra = {
            "example": {
                "tables": [
                    {
                        "id": "tbl_abc123",
                        "table_name": "compliance_events",
                        "description": "Stores compliance event records",
                        "schema": {
                            "fields": {
                                "event_type": {"type": "string", "required": True}
                            },
                            "indexes": []
                        },
                        "project_id": "proj_demo_u1_001",
                        "row_count": 150,
                        "created_at": "2026-01-11T00:00:00Z",
                        "updated_at": None
                    }
                ],
                "total": 1
            }
        }


class TableDeleteResponse(BaseModel):
    """
    Response schema for table deletion.
    Confirms successful deletion with table details.
    """
    id: str = Field(..., description="ID of the deleted table")
    table_name: str = Field(..., description="Name of the deleted table")
    deleted: bool = Field(default=True, description="Confirmation of deletion")
    deleted_at: datetime = Field(..., description="Timestamp of deletion")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "tbl_abc123",
                "table_name": "compliance_events",
                "deleted": True,
                "deleted_at": "2026-01-11T12:00:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response per DX Contract.
    All errors return { detail, error_code }.
    """
    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Table 'compliance_events' already exists in project",
                "error_code": "TABLE_ALREADY_EXISTS"
            }
        }
