"""
Comprehensive tests for Table Creation API (Epic 7, Issue 1).
Tests table creation, listing, retrieval, and deletion with schema validation.

Test Coverage:
- Create table with valid schema
- All field types: string, integer, float, boolean, json, timestamp
- Duplicate table name returns 409 TABLE_ALREADY_EXISTS
- List tables endpoint
- Get table by ID endpoint
- Delete table endpoint
- Table not found returns 404 TABLE_NOT_FOUND
- Authentication and authorization
- Schema validation with indexes
- Edge cases and error conditions
"""
import pytest
from fastapi import status
from datetime import datetime


class TestCreateTableEndpoint:
    """Test suite for POST /v1/public/{project_id}/tables endpoint."""

    def test_create_table_success_with_basic_schema(self, client, auth_headers_user1):
        """
        Test successful table creation with basic schema.
        Epic 7 Issue 1: Create table with schema definition.
        """
        request_body = {
            "table_name": "test_basic_table",
            "description": "Test table for basic schema",
            "schema": {
                "fields": {
                    "event_type": {"type": "string", "required": True},
                    "agent_id": {"type": "string", "required": True}
                },
                "indexes": ["event_type"]
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "id" in data
        assert data["id"].startswith("tbl_")
        assert data["table_name"] == "test_basic_table"
        assert data["description"] == "Test table for basic schema"
        assert data["project_id"] == "proj_demo_u1_001"
        assert data["row_count"] == 0
        assert "created_at" in data
        assert "schema" in data

        # Verify schema structure
        schema = data["schema"]
        assert "fields" in schema
        assert "indexes" in schema
        assert len(schema["fields"]) == 2
        assert "event_type" in schema["fields"]
        assert "agent_id" in schema["fields"]
        assert schema["indexes"] == ["event_type"]

    def test_create_table_with_all_field_types(self, client, auth_headers_user1):
        """
        Test table creation with all supported field types.
        Epic 7 Issue 1: Support string, integer, float, boolean, json, timestamp.
        """
        request_body = {
            "table_name": "test_all_types",
            "description": "Table with all field types",
            "schema": {
                "fields": {
                    "text_field": {"type": "string", "required": True},
                    "number_field": {"type": "integer", "required": True},
                    "decimal_field": {"type": "float", "required": False},
                    "flag_field": {"type": "boolean", "required": False},
                    "data_field": {"type": "json", "required": False},
                    "time_field": {"type": "timestamp", "required": True}
                },
                "indexes": ["text_field", "number_field"]
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["table_name"] == "test_all_types"

        # Verify all field types are present
        fields = data["schema"]["fields"]
        assert fields["text_field"]["type"] == "string"
        assert fields["text_field"]["required"] is True

        assert fields["number_field"]["type"] == "integer"
        assert fields["number_field"]["required"] is True

        assert fields["decimal_field"]["type"] == "float"
        assert fields["decimal_field"]["required"] is False

        assert fields["flag_field"]["type"] == "boolean"
        assert fields["flag_field"]["required"] is False

        assert fields["data_field"]["type"] == "json"
        assert fields["data_field"]["required"] is False

        assert fields["time_field"]["type"] == "timestamp"
        assert fields["time_field"]["required"] is True

    def test_create_table_with_field_defaults(self, client, auth_headers_user1):
        """
        Test table creation with default values for fields.
        """
        request_body = {
            "table_name": "test_defaults",
            "description": "Table with default values",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "status": {"type": "string", "required": False, "default": "pending"},
                    "count": {"type": "integer", "required": False, "default": 0},
                    "enabled": {"type": "boolean", "required": False, "default": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        fields = data["schema"]["fields"]
        assert fields["status"]["default"] == "pending"
        assert fields["count"]["default"] == 0
        assert fields["enabled"]["default"] is True

    def test_create_table_duplicate_name_returns_409(self, client, auth_headers_user1):
        """
        Test duplicate table name returns 409 TABLE_ALREADY_EXISTS.
        Epic 7 Issue 1: Return TABLE_ALREADY_EXISTS for duplicate names.
        """
        request_body = {
            "table_name": "duplicate_test",
            "description": "First table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        # Create first table
        response1 = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create second table with same name
        response2 = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response2.status_code == status.HTTP_409_CONFLICT

        data = response2.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "TABLE_ALREADY_EXISTS"
        assert "duplicate_test" in data["detail"]

    def test_create_table_without_description(self, client, auth_headers_user1):
        """
        Test table creation without description (optional field).
        """
        request_body = {
            "table_name": "no_description",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["description"] is None

    def test_create_table_with_multiple_indexes(self, client, auth_headers_user1):
        """
        Test table creation with multiple indexed fields.
        """
        request_body = {
            "table_name": "multi_index",
            "schema": {
                "fields": {
                    "user_id": {"type": "string", "required": True},
                    "event_type": {"type": "string", "required": True},
                    "timestamp": {"type": "timestamp", "required": True},
                    "data": {"type": "json", "required": False}
                },
                "indexes": ["user_id", "event_type", "timestamp"]
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["schema"]["indexes"]) == 3
        assert set(data["schema"]["indexes"]) == {"user_id", "event_type", "timestamp"}

    def test_create_table_invalid_table_name_uppercase(self, client, auth_headers_user1):
        """
        Test table name must be lowercase.
        Table name rules: Must start with lowercase letter, only lowercase letters/numbers/underscores.
        """
        request_body = {
            "table_name": "InvalidName",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_create_table_invalid_table_name_starts_with_number(self, client, auth_headers_user1):
        """
        Test table name must start with a letter.
        """
        request_body = {
            "table_name": "123_invalid",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_table_invalid_table_name_special_chars(self, client, auth_headers_user1):
        """
        Test table name cannot contain special characters (except underscore).
        """
        request_body = {
            "table_name": "invalid-name",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_table_valid_table_name_with_underscores_numbers(self, client, auth_headers_user1):
        """
        Test valid table name with underscores and numbers.
        """
        request_body = {
            "table_name": "valid_table_123",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["table_name"] == "valid_table_123"

    def test_create_table_empty_schema_fields_returns_422(self, client, auth_headers_user1):
        """
        Test that empty fields dict returns validation error.
        Schema must have at least one field.
        """
        request_body = {
            "table_name": "empty_fields",
            "schema": {
                "fields": {},
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_table_index_field_not_in_schema_returns_422(self, client, auth_headers_user1):
        """
        Test that indexing a non-existent field returns validation error.
        Epic 7 Issue 1: Validate index fields exist in schema.
        """
        request_body = {
            "table_name": "invalid_index",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": ["non_existent_field"]
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_create_table_missing_api_key_returns_401(self, client):
        """
        Test missing X-API-Key header returns 401.
        """
        request_body = {
            "table_name": "test_table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_table_invalid_api_key_returns_401(self, client, invalid_auth_headers):
        """
        Test invalid API key returns 401.
        """
        request_body = {
            "table_name": "test_table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_table_project_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test creating table in non-existent project returns 404.
        """
        request_body = {
            "table_name": "test_table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/nonexistent_project/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_create_table_unauthorized_project_access_returns_403(self, client, auth_headers_user1):
        """
        Test creating table in another user's project returns 403.
        User 1 should not be able to create tables in User 2's projects.
        """
        request_body = {
            "table_name": "test_table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        # User 1 trying to access User 2's project
        response = client.post(
            "/v1/public/proj_demo_u2_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"


class TestListTablesEndpoint:
    """Test suite for GET /v1/public/{project_id}/tables endpoint."""

    def test_list_tables_success_with_tables(self, client, auth_headers_user1):
        """
        Test successful table listing when tables exist.
        Epic 7 Issue 1: List all tables for a project.
        """
        # Create a table first
        request_body = {
            "table_name": "list_test_table",
            "description": "Table for list test",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        # List tables
        response = client.get(
            "/v1/public/proj_demo_u1_001/tables",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "tables" in data
        assert "total" in data
        assert isinstance(data["tables"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 1

        # Verify table structure
        for table in data["tables"]:
            assert "id" in table
            assert "table_name" in table
            assert "description" in table
            assert "schema" in table
            assert "project_id" in table
            assert "row_count" in table
            assert "created_at" in table

    def test_list_tables_empty_project(self, client, auth_headers_user2):
        """
        Test listing tables in project with no tables returns empty array.
        """
        # User 2's first project should have no tables initially
        response = client.get(
            "/v1/public/proj_demo_u2_001/tables",
            headers=auth_headers_user2
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["tables"] == []
        assert data["total"] == 0

    def test_list_tables_missing_api_key_returns_401(self, client):
        """
        Test missing X-API-Key header returns 401.
        """
        response = client.get("/v1/public/proj_demo_u1_001/tables")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_list_tables_invalid_api_key_returns_401(self, client, invalid_auth_headers):
        """
        Test invalid API key returns 401.
        """
        response = client.get(
            "/v1/public/proj_demo_u1_001/tables",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_list_tables_project_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test listing tables in non-existent project returns 404.
        """
        response = client.get(
            "/v1/public/nonexistent_project/tables",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_list_tables_unauthorized_project_access_returns_403(self, client, auth_headers_user1):
        """
        Test listing tables in another user's project returns 403.
        """
        response = client.get(
            "/v1/public/proj_demo_u2_001/tables",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_list_tables_multiple_tables_count(self, client, auth_headers_user1):
        """
        Test that total count matches number of tables returned.
        """
        # Create multiple tables
        for i in range(3):
            request_body = {
                "table_name": f"count_test_table_{i}",
                "schema": {
                    "fields": {
                        "id": {"type": "string", "required": True}
                    },
                    "indexes": []
                }
            }
            client.post(
                "/v1/public/proj_demo_u1_001/tables",
                json=request_body,
                headers=auth_headers_user1
            )

        # List tables
        response = client.get(
            "/v1/public/proj_demo_u1_001/tables",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == len(data["tables"])
        assert data["total"] >= 3


class TestGetTableEndpoint:
    """Test suite for GET /v1/public/{project_id}/tables/{table_id} endpoint."""

    def test_get_table_success(self, client, auth_headers_user1):
        """
        Test successful retrieval of table by ID.
        Epic 7 Issue 1: Get table details by ID.
        """
        # Create a table first
        request_body = {
            "table_name": "get_test_table",
            "description": "Table for get test",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": False}
                },
                "indexes": ["id"]
            }
        }

        create_response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )
        created_table = create_response.json()
        table_id = created_table["id"]

        # Get the table
        response = client.get(
            f"/v1/public/proj_demo_u1_001/tables/{table_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == table_id
        assert data["table_name"] == "get_test_table"
        assert data["description"] == "Table for get test"
        assert data["project_id"] == "proj_demo_u1_001"
        assert data["row_count"] == 0
        assert "created_at" in data
        assert "schema" in data
        assert len(data["schema"]["fields"]) == 2
        assert data["schema"]["indexes"] == ["id"]

    def test_get_table_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test getting non-existent table returns 404 TABLE_NOT_FOUND.
        Epic 7 Issue 1: Table not found returns 404.
        """
        response = client.get(
            "/v1/public/proj_demo_u1_001/tables/tbl_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "TABLE_NOT_FOUND"
        assert "tbl_nonexistent" in data["detail"]

    def test_get_table_from_different_project_returns_404(self, client, auth_headers_user1, auth_headers_user2):
        """
        Test that getting a table from a different project returns 404.
        Table IDs are scoped to projects.
        """
        # User 2 creates a table
        request_body = {
            "table_name": "user2_table",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        create_response = client.post(
            "/v1/public/proj_demo_u2_001/tables",
            json=request_body,
            headers=auth_headers_user2
        )
        table_id = create_response.json()["id"]

        # User 1 tries to get it from their project
        response = client.get(
            f"/v1/public/proj_demo_u1_001/tables/{table_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "TABLE_NOT_FOUND"

    def test_get_table_missing_api_key_returns_401(self, client):
        """
        Test missing X-API-Key header returns 401.
        """
        response = client.get("/v1/public/proj_demo_u1_001/tables/tbl_test")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_table_invalid_api_key_returns_401(self, client, invalid_auth_headers):
        """
        Test invalid API key returns 401.
        """
        response = client.get(
            "/v1/public/proj_demo_u1_001/tables/tbl_test",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_get_table_project_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test getting table from non-existent project returns 404.
        """
        response = client.get(
            "/v1/public/nonexistent_project/tables/tbl_test",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_get_table_unauthorized_project_access_returns_403(self, client, auth_headers_user1):
        """
        Test getting table from another user's project returns 403.
        """
        response = client.get(
            "/v1/public/proj_demo_u2_001/tables/tbl_test",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"


class TestDeleteTableEndpoint:
    """Test suite for DELETE /v1/public/{project_id}/tables/{table_id} endpoint."""

    def test_delete_table_success(self, client, auth_headers_user1):
        """
        Test successful table deletion.
        Epic 7 Issue 1: Delete a table from a project.
        """
        # Create a table first
        request_body = {
            "table_name": "delete_test_table",
            "description": "Table to be deleted",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        create_response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )
        table_id = create_response.json()["id"]

        # Delete the table
        response = client.delete(
            f"/v1/public/proj_demo_u1_001/tables/{table_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == table_id
        assert data["table_name"] == "delete_test_table"
        assert data["deleted"] is True
        assert "deleted_at" in data

        # Verify table is actually deleted
        get_response = client.get(
            f"/v1/public/proj_demo_u1_001/tables/{table_id}",
            headers=auth_headers_user1
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_table_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test deleting non-existent table returns 404 TABLE_NOT_FOUND.
        Epic 7 Issue 1: Table not found returns 404.
        """
        response = client.delete(
            "/v1/public/proj_demo_u1_001/tables/tbl_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "TABLE_NOT_FOUND"

    def test_delete_table_from_different_project_returns_404(self, client, auth_headers_user1, auth_headers_user2):
        """
        Test that deleting a table from a different project returns 404.
        """
        # User 2 creates a table
        request_body = {
            "table_name": "user2_delete_test",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        create_response = client.post(
            "/v1/public/proj_demo_u2_001/tables",
            json=request_body,
            headers=auth_headers_user2
        )
        table_id = create_response.json()["id"]

        # User 1 tries to delete it from their project
        response = client.delete(
            f"/v1/public/proj_demo_u1_001/tables/{table_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "TABLE_NOT_FOUND"

    def test_delete_table_allows_name_reuse(self, client, auth_headers_user1):
        """
        Test that after deleting a table, the name can be reused.
        """
        table_name = "reusable_name"
        request_body = {
            "table_name": table_name,
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        # Create first table
        create1 = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )
        table_id1 = create1.json()["id"]

        # Delete it
        delete_response = client.delete(
            f"/v1/public/proj_demo_u1_001/tables/{table_id1}",
            headers=auth_headers_user1
        )
        assert delete_response.status_code == status.HTTP_200_OK

        # Create second table with same name
        create2 = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )
        assert create2.status_code == status.HTTP_201_CREATED
        table_id2 = create2.json()["id"]
        assert table_id1 != table_id2

    def test_delete_table_missing_api_key_returns_401(self, client):
        """
        Test missing X-API-Key header returns 401.
        """
        response = client.delete("/v1/public/proj_demo_u1_001/tables/tbl_test")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_delete_table_invalid_api_key_returns_401(self, client, invalid_auth_headers):
        """
        Test invalid API key returns 401.
        """
        response = client.delete(
            "/v1/public/proj_demo_u1_001/tables/tbl_test",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_API_KEY"

    def test_delete_table_project_not_found_returns_404(self, client, auth_headers_user1):
        """
        Test deleting table from non-existent project returns 404.
        """
        response = client.delete(
            "/v1/public/nonexistent_project/tables/tbl_test",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error_code"] == "PROJECT_NOT_FOUND"

    def test_delete_table_unauthorized_project_access_returns_403(self, client, auth_headers_user1):
        """
        Test deleting table from another user's project returns 403.
        """
        response = client.delete(
            "/v1/public/proj_demo_u2_001/tables/tbl_test",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"


class TestTableSchemaEdgeCases:
    """Test suite for edge cases and boundary conditions in table schema."""

    def test_create_table_with_empty_indexes_array(self, client, auth_headers_user1):
        """
        Test that empty indexes array is valid.
        """
        request_body = {
            "table_name": "empty_indexes",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["schema"]["indexes"] == []

    def test_create_table_without_indexes_field(self, client, auth_headers_user1):
        """
        Test that indexes field can be omitted (defaults to empty).
        """
        request_body = {
            "table_name": "no_indexes_field",
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                }
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Should default to empty list
        assert "indexes" in data["schema"]
        assert data["schema"]["indexes"] == []

    def test_create_table_max_length_table_name(self, client, auth_headers_user1):
        """
        Test table name at maximum length (100 characters).
        """
        # Create a 100-character valid table name
        table_name = "a" + "_" * 98 + "z"
        assert len(table_name) == 100

        request_body = {
            "table_name": table_name,
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["table_name"] == table_name

    def test_create_table_exceeds_max_length_table_name(self, client, auth_headers_user1):
        """
        Test table name exceeding maximum length (100 characters) returns error.
        """
        # Create a 101-character table name
        table_name = "a" * 101
        assert len(table_name) == 101

        request_body = {
            "table_name": table_name,
            "schema": {
                "fields": {
                    "id": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_table_complex_schema(self, client, auth_headers_user1):
        """
        Test table creation with complex real-world schema.
        """
        request_body = {
            "table_name": "compliance_events",
            "description": "Stores compliance event records for audit trail",
            "schema": {
                "fields": {
                    "event_id": {"type": "string", "required": True},
                    "event_type": {"type": "string", "required": True},
                    "agent_id": {"type": "string", "required": True},
                    "timestamp": {"type": "timestamp", "required": True},
                    "payload": {"type": "json", "required": False},
                    "severity": {"type": "integer", "required": True, "default": 1},
                    "is_processed": {"type": "boolean", "required": False, "default": False},
                    "confidence_score": {"type": "float", "required": False}
                },
                "indexes": ["event_type", "agent_id", "timestamp"]
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["table_name"] == "compliance_events"
        assert len(data["schema"]["fields"]) == 8
        assert len(data["schema"]["indexes"]) == 3


class TestErrorResponseFormat:
    """Test suite for error response format consistency."""

    def test_all_errors_have_detail_and_error_code(self, client, auth_headers_user1):
        """
        Test that all error responses follow DX Contract format.
        All errors must return { detail, error_code }.
        """
        # Test various error scenarios
        error_scenarios = [
            # Missing API key
            (client.get("/v1/public/proj_demo_u1_001/tables"), "INVALID_API_KEY"),
            # Project not found
            (client.get("/v1/public/nonexistent/tables", headers=auth_headers_user1), "PROJECT_NOT_FOUND"),
            # Table not found
            (client.get("/v1/public/proj_demo_u1_001/tables/tbl_fake", headers=auth_headers_user1), "TABLE_NOT_FOUND"),
        ]

        for response, expected_error_code in error_scenarios:
            assert response.status_code >= 400
            data = response.json()
            assert "detail" in data
            assert "error_code" in data
            assert isinstance(data["detail"], str)
            assert isinstance(data["error_code"], str)
            assert data["error_code"] == expected_error_code
