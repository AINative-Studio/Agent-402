"""
Comprehensive tests for Row Insertion API (Epic 7, Issue 2).

Tests the POST /v1/public/{project_id}/tables/{table_id}/rows endpoint:
- Single row insertion with valid row_data
- Batch insert with array of row_data
- Schema validation for wrong types
- Required field validation
- TABLE_NOT_FOUND error handling
- SCHEMA_VALIDATION_ERROR handling

Test Strategy:
1. Unit tests for single row insertion
2. Unit tests for batch row insertion
3. Schema validation tests (type mismatches)
4. Required field validation tests
5. Edge cases and error conditions
6. Behavioral tests for deterministic errors
7. Mutation testing suggestions for critical paths

Test Data Pattern:
- Uses hard-coded project IDs (proj_test_XXX) following existing test pattern
- Tests assume project service provides access to these project IDs
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Test project IDs (using pre-initialized demo projects for user_1)
# Per project_store.py initialization, these projects exist for demo API key users
TEST_PROJECT_1 = "proj_demo_u1_001"  # Agent Finance Demo project for user_1


def create_test_table(client, project_id, table_name, schema, headers):
    """
    Helper function to create a test table.

    Args:
        client: TestClient instance
        project_id: Project ID
        table_name: Name for the table
        schema: Table schema dict
        headers: Authentication headers

    Returns:
        table_id if successful, None otherwise
    """
    import uuid
    # Make table name unique to avoid conflicts in tests
    unique_table_name = f"{table_name}_{uuid.uuid4().hex[:8]}"

    response = client.post(
        f"/v1/public/{project_id}/tables",
        json={
            "table_name": unique_table_name,
            "schema": schema
        },
        headers=headers
    )
    if response.status_code == status.HTTP_201_CREATED:
        # Table API returns 'id' not 'table_id'
        return response.json()["id"]
    # Debug: print response for failed table creation
    print(f"Table creation failed: {response.status_code} - {response.text}")
    return None


class TestSingleRowInsertion:
    """Test single row insertion with valid row_data."""

    def test_insert_single_row_with_valid_data(self, client, auth_headers_user1):
        """
        Test inserting a single row with valid row_data.

        Given: A table exists with a schema
        When: POST request with valid single row_data
        Then: Row is created successfully with row_id and created_at
        """
        project_id = TEST_PROJECT_1

        # Create a table with schema
        table_id = create_test_table(
            client, project_id, "users",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                    "age": {"type": "integer", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert a single row
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                }
            },
            headers=auth_headers_user1
        )

        # Verify response
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert "rows" in data
        assert "inserted_count" in data
        assert data["inserted_count"] == 1
        assert len(data["rows"]) == 1

        # Verify row structure
        row = data["rows"][0]
        assert "row_id" in row
        assert "created_at" in row
        assert "row_data" in row
        assert row["row_data"]["name"] == "John Doe"
        assert row["row_data"]["email"] == "john@example.com"
        assert row["row_data"]["age"] == 30

    def test_insert_row_with_minimal_required_fields(self, client, auth_headers_user1):
        """
        Test inserting a row with only required fields.

        Given: A table with required and optional fields
        When: POST request with only required fields
        Then: Row is created successfully
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "products",
            {
                "fields": {
                    "product_name": {"type": "string", "required": True},
                    "price": {"type": "float", "required": True},
                    "description": {"type": "string", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with only required fields
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "product_name": "Widget",
                    "price": 19.99
                }
            },
            headers=auth_headers_user1
        )

        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 1
        assert data["rows"][0]["row_data"]["product_name"] == "Widget"
        assert data["rows"][0]["row_data"]["price"] == 19.99


class TestBatchRowInsertion:
    """Test batch insert with array of row_data."""

    def test_insert_multiple_rows_batch(self, client, auth_headers_user1):
        """
        Test batch insertion of multiple rows.

        Given: A table exists with schema
        When: POST request with array of row_data
        Then: All rows are inserted successfully
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "employees",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "department": {"type": "string", "required": True},
                    "salary": {"type": "integer", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert multiple rows in batch
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": [
                    {"name": "Alice", "department": "Engineering", "salary": 120000},
                    {"name": "Bob", "department": "Sales", "salary": 80000},
                    {"name": "Charlie", "department": "Marketing"}
                ]
            },
            headers=auth_headers_user1
        )

        # Verify batch insertion
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 3
        assert len(data["rows"]) == 3

        # Verify each row has unique row_id and created_at
        row_ids = set()
        for row in data["rows"]:
            assert "row_id" in row
            assert "created_at" in row
            assert row["row_id"] not in row_ids
            row_ids.add(row["row_id"])

    def test_batch_insert_empty_array(self, client, auth_headers_user1):
        """
        Test batch insertion with empty array.

        Given: A table exists
        When: POST request with empty row_data array
        Then: No rows are inserted (inserted_count = 0)
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "test_table",
            {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert with empty array
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": []},
            headers=auth_headers_user1
        )

        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 0
        assert len(data["rows"]) == 0


class TestSchemaValidation:
    """Test schema validation for wrong types."""

    def test_schema_validation_wrong_type_integer(self, client, auth_headers_user1):
        """
        Test schema validation when integer field receives string.

        Given: A table with integer field
        When: POST request with string value for integer field
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_age_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "age": {"type": "integer", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with wrong type for age
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "age": "thirty"  # String instead of integer
                }
            },
            headers=auth_headers_user1
        )

        # Verify schema validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"
        assert "detail" in data
        assert "age" in data["detail"]

    def test_schema_validation_wrong_type_string(self, client, auth_headers_user1):
        """
        Test schema validation when string field receives non-string.

        Given: A table with string field
        When: POST request with integer value for string field
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "products_sku_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "sku": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with integer for string field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "Widget",
                    "sku": 12345  # Integer instead of string
                }
            },
            headers=auth_headers_user1
        )

        # Verify schema validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"
        assert "detail" in data

    def test_schema_validation_wrong_type_boolean(self, client, auth_headers_user1):
        """
        Test schema validation when boolean field receives non-boolean.

        Given: A table with boolean field
        When: POST request with string value for boolean field
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_active_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "active": {"type": "boolean", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with string for boolean field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "active": "true"  # String instead of boolean
                }
            },
            headers=auth_headers_user1
        )

        # Verify schema validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"

    def test_schema_validation_wrong_type_float(self, client, auth_headers_user1):
        """
        Test schema validation for float field type.

        Given: A table with float field
        When: POST request with string value for float field
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "products_price_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "price": {"type": "float", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with string for float field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "Widget",
                    "price": "nineteen ninety-nine"  # String instead of float
                }
            },
            headers=auth_headers_user1
        )

        # Verify schema validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"


class TestRequiredFieldValidation:
    """Test required field validation."""

    def test_missing_required_field(self, client, auth_headers_user1):
        """
        Test that missing required field triggers validation error.

        Given: A table with required fields
        When: POST request missing a required field
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_required_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                    "age": {"type": "integer", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row missing required email field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe"
                    # Missing required "email" field
                }
            },
            headers=auth_headers_user1
        )

        # Verify required field validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"
        assert "detail" in data
        assert "email" in data["detail"]

    def test_multiple_missing_required_fields(self, client, auth_headers_user1):
        """
        Test validation error when multiple required fields are missing.

        Given: A table with multiple required fields
        When: POST request missing multiple required fields
        Then: Returns 422 SCHEMA_VALIDATION_ERROR
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "products_multi_required_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "sku": {"type": "string", "required": True},
                    "price": {"type": "float", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row missing multiple required fields
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "Widget"
                    # Missing "sku" and "price"
                }
            },
            headers=auth_headers_user1
        )

        # Verify validation error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"

    def test_optional_field_can_be_omitted(self, client, auth_headers_user1):
        """
        Test that optional fields can be omitted without error.

        Given: A table with optional fields
        When: POST request omitting optional fields
        Then: Row is created successfully
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_optional_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                    "phone": {"type": "string", "required": False},
                    "address": {"type": "string", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row omitting optional fields
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "email": "john@example.com"
                    # Omitting optional phone and address
                }
            },
            headers=auth_headers_user1
        )

        # Verify successful creation
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 1


class TestTableNotFoundError:
    """Test TABLE_NOT_FOUND error handling."""

    def test_insert_row_into_nonexistent_table(self, client, auth_headers_user1):
        """
        Test inserting row into non-existent table.

        Given: A project exists but table does not
        When: POST request to non-existent table
        Then: Returns 404 TABLE_NOT_FOUND
        """
        project_id = TEST_PROJECT_1

        # Attempt to insert into non-existent table
        row_response = client.post(
            f"/v1/public/{project_id}/tables/nonexistent_table/rows",
            json={
                "row_data": {
                    "name": "John Doe"
                }
            },
            headers=auth_headers_user1
        )

        # Verify TABLE_NOT_FOUND error
        assert row_response.status_code == status.HTTP_404_NOT_FOUND
        data = row_response.json()
        assert data["error_code"] == "TABLE_NOT_FOUND"
        assert "detail" in data
        assert "nonexistent_table" in data["detail"]

    def test_insert_row_with_invalid_table_id_format(self, client, auth_headers_user1):
        """
        Test inserting row with malformed table ID.

        Given: A project exists
        When: POST request with invalid table ID format
        Then: Returns 404 TABLE_NOT_FOUND
        """
        project_id = TEST_PROJECT_1

        # Attempt to insert with invalid table ID
        row_response = client.post(
            f"/v1/public/{project_id}/tables/invalid-table-id-123/rows",
            json={
                "row_data": {
                    "field1": "value1"
                }
            },
            headers=auth_headers_user1
        )

        # Verify error (404 TABLE_NOT_FOUND)
        assert row_response.status_code == status.HTTP_404_NOT_FOUND
        data = row_response.json()
        assert data["error_code"] == "TABLE_NOT_FOUND"


class TestMissingRowDataError:
    """Test MISSING_ROW_DATA error handling (Epic 7, Issue 3)."""

    def test_missing_row_data_field(self, client, auth_headers_user1):
        """
        Test that missing row_data field returns MISSING_ROW_DATA error.

        Given: A table exists
        When: POST request without row_data field
        Then: Returns 422 MISSING_ROW_DATA
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "test_missing_row_data",
            {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # POST without row_data field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={},  # Empty object, no row_data
            headers=auth_headers_user1
        )

        # Verify MISSING_ROW_DATA error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "MISSING_ROW_DATA"
        assert "detail" in data
        assert "row_data" in data["detail"]

    def test_invalid_field_name_data(self, client, auth_headers_user1):
        """
        Test that using 'data' instead of 'row_data' returns INVALID_FIELD_NAME.

        Given: A table exists
        When: POST request with 'data' field instead of 'row_data'
        Then: Returns 422 INVALID_FIELD_NAME
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "test_invalid_field_data",
            {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # POST with 'data' instead of 'row_data'
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "data": {"field1": "value1"}  # Wrong field name
            },
            headers=auth_headers_user1
        )

        # Verify INVALID_FIELD_NAME error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "INVALID_FIELD_NAME"
        assert "detail" in data
        assert "data" in data["detail"]

    def test_invalid_field_name_rows(self, client, auth_headers_user1):
        """
        Test that using 'rows' instead of 'row_data' returns INVALID_FIELD_NAME.

        Given: A table exists
        When: POST request with 'rows' field instead of 'row_data'
        Then: Returns 422 INVALID_FIELD_NAME
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "test_invalid_field_rows",
            {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # POST with 'rows' instead of 'row_data'
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "rows": [{"field1": "value1"}]  # Wrong field name
            },
            headers=auth_headers_user1
        )

        # Verify INVALID_FIELD_NAME error
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "INVALID_FIELD_NAME"
        assert "detail" in data
        assert "rows" in data["detail"]


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_insert_row_with_null_values_for_optional_fields(self, client, auth_headers_user1):
        """
        Test inserting row with explicit null values for optional fields.

        Given: A table with optional fields
        When: POST request with null values for optional fields
        Then: Row is created successfully
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_null_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": False}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with null for optional field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "email": None
                }
            },
            headers=auth_headers_user1
        )

        # Verify successful creation
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 1

    def test_insert_row_with_extra_fields_not_in_schema(self, client, auth_headers_user1):
        """
        Test inserting row with extra fields not defined in schema.

        Given: A table with defined schema
        When: POST request with additional fields not in schema
        Then: Row is created successfully (flexible schema approach)
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_extra_fields_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with extra field
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "name": "John Doe",
                    "extra_field": "extra_value"  # Not in schema
                }
            },
            headers=auth_headers_user1
        )

        # Verify successful creation (flexible schema allows extra fields)
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 1
        assert data["rows"][0]["row_data"]["extra_field"] == "extra_value"

    def test_insert_row_with_very_long_string(self, client, auth_headers_user1):
        """
        Test inserting row with very long string value.

        Given: A table with string field
        When: POST request with very long string value
        Then: Row is created successfully
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "documents_long_test",
            {
                "fields": {
                    "title": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert row with very long string
        long_content = "A" * 10000  # 10,000 character string
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "title": "Long Document",
                    "content": long_content
                }
            },
            headers=auth_headers_user1
        )

        # Verify successful creation
        assert row_response.status_code == status.HTTP_201_CREATED
        data = row_response.json()
        assert data["inserted_count"] == 1
        assert len(data["rows"][0]["row_data"]["content"]) == 10000

    def test_batch_insert_with_mixed_valid_and_invalid_rows(self, client, auth_headers_user1):
        """
        Test batch insertion where some rows are valid and others are invalid.

        Given: A table with schema
        When: POST batch request with mix of valid and invalid rows
        Then: All rows should fail validation (atomic operation)
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "users_batch_validation_test",
            {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "age": {"type": "integer", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Batch insert with one invalid row
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": [
                    {"name": "Alice", "age": 25},  # Valid
                    {"name": "Bob", "age": "thirty"},  # Invalid - string for integer
                    {"name": "Charlie", "age": 35}  # Valid
                ]
            },
            headers=auth_headers_user1
        )

        # Verify that validation fails for the batch
        assert row_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = row_response.json()
        assert data["error_code"] == "SCHEMA_VALIDATION_ERROR"


class TestDeterministicBehavior:
    """Test deterministic error responses and behavior."""

    def test_repeated_inserts_generate_unique_row_ids(self, client, auth_headers_user1):
        """
        Test that repeated inserts generate unique row IDs.

        Given: A table exists
        When: Multiple POST requests with same row_data
        Then: Each insertion generates unique row_id
        """
        project_id = TEST_PROJECT_1

        table_id = create_test_table(
            client, project_id, "test_unique_ids",
            {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Insert same data multiple times
        row_ids = set()
        for i in range(5):
            row_response = client.post(
                f"/v1/public/{project_id}/tables/{table_id}/rows",
                json={
                    "row_data": {"field1": "same_value"}
                },
                headers=auth_headers_user1
            )
            assert row_response.status_code == status.HTTP_201_CREATED
            row_id = row_response.json()["rows"][0]["row_id"]
            row_ids.add(row_id)

        # Verify all row_ids are unique
        assert len(row_ids) == 5

    def test_error_response_format_consistency(self, client, auth_headers_user1):
        """
        Test that all error responses follow consistent format.

        Given: Various error scenarios
        When: Errors occur
        Then: All errors return { detail, error_code } format
        """
        project_id = TEST_PROJECT_1

        # Test TABLE_NOT_FOUND format
        row_response = client.post(
            f"/v1/public/{project_id}/tables/nonexistent/rows",
            json={"row_data": {"field": "value"}},
            headers=auth_headers_user1
        )
        data = row_response.json()
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

        # Create table for schema validation test
        table_id = create_test_table(
            client, project_id, "test_error_format",
            {
                "fields": {
                    "age": {"type": "integer", "required": True}
                },
                "indexes": []
            },
            auth_headers_user1
        )
        assert table_id is not None

        # Test SCHEMA_VALIDATION_ERROR format
        row_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": {"age": "not_a_number"}},
            headers=auth_headers_user1
        )
        data = row_response.json()
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)


# Mutation Testing Suggestions
"""
MUTATION TESTING RECOMMENDATIONS:

1. Schema Validation Mutations:
   - Change type comparison operators (== to !=)
   - Remove required field checks
   - Invert boolean conditions in validation
   - Test boundary conditions for numeric types

2. Error Handling Mutations:
   - Change error codes to different values
   - Remove error throwing statements
   - Change HTTP status codes
   - Mutate error message strings

3. Row ID Generation Mutations:
   - Remove uniqueness check
   - Change UUID generation logic
   - Test collision handling

4. Batch Processing Mutations:
   - Change loop boundaries (off-by-one)
   - Remove validation for individual rows
   - Change atomic transaction behavior

Critical Paths to Test with Mutations:
- Row data validation against schema
- Required field enforcement
- Type checking logic
- Error code assignment
- Batch vs single row code paths
"""
