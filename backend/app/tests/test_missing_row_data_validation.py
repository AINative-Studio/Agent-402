"""
Comprehensive tests for missing row_data validation (Epic 11, Story 4).

Tests validate proper error handling when developers use wrong field names
instead of row_data, as specified in Issue #70.

Test Coverage:
- POST /v1/public/{project_id}/tables/{table_id}/rows without row_data
- HTTP 422 response validation
- error_code: MISSING_ROW_DATA validation
- error_code: INVALID_FIELD_NAME validation for common mistakes
- Detail message validation that mentions row_data
- Common mistakes: 'data', 'rows', 'items', 'records'
- Successful insert with correct row_data field

Per PRD Section 10 (Contract Stability):
- Field name MUST be row_data (not data, rows, items, or records)
- Errors are deterministic with proper error codes
- Error messages guide developers to use correct field name

Test Strategy:
1. Test missing row_data field (empty body)
2. Test each common field name mistake individually
3. Test successful case with correct row_data
4. Verify error response structure matches DX Contract
5. Ensure error messages are helpful and actionable
"""
import pytest
from fastapi import status


class TestMissingRowDataValidation:
    """
    Test suite for validating missing row_data field errors.

    Epic 11 Story 4: As a maintainer, tests validate 422 for missing row_data.
    GitHub Issue #70: Test validates 422 for missing row_data.
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1):
        """
        Create a test table and return its ID.

        Creates a table with basic schema for row insertion testing.
        """
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_row_validation_{unique_suffix}",
            "description": "Table for row_data validation testing",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": False},
                    "age": {"type": "integer", "required": False}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    def test_missing_row_data_field_empty_body(self, client, auth_headers_user1, test_table_id):
        """
        Test POST /tables/{table_id}/rows with empty body returns 422 MISSING_ROW_DATA.

        Given: POST request with empty JSON body {}
        When: Attempting to insert rows
        Then: Should return HTTP 422 with MISSING_ROW_DATA error code
        And: Detail message should mention row_data
        """
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={},
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Response has required error fields
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # Assert: Error code is MISSING_ROW_DATA
        assert data["error_code"] == "MISSING_ROW_DATA"

        # Assert: Detail message mentions row_data
        assert "row_data" in data["detail"].lower()

    def test_missing_row_data_field_no_body(self, client, auth_headers_user1, test_table_id):
        """
        Test POST /tables/{table_id}/rows with no row_data field returns 422.

        Given: POST request with fields but missing row_data
        When: Attempting to insert rows
        Then: Should return HTTP 422 with MISSING_ROW_DATA error code
        """
        # Request with unrelated fields but no row_data
        request_body = {
            "some_field": "value",
            "another_field": 123
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Error code is MISSING_ROW_DATA
        data = response.json()
        assert data["error_code"] == "MISSING_ROW_DATA"

        # Assert: Detail message is helpful
        assert "row_data" in data["detail"].lower()


class TestInvalidFieldNameValidation:
    """
    Test suite for validating INVALID_FIELD_NAME errors for common mistakes.

    Tests each common field name mistake individually:
    - 'data' instead of 'row_data'
    - 'rows' instead of 'row_data'
    - 'items' instead of 'row_data'
    - 'records' instead of 'row_data'
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1):
        """
        Create a test table and return its ID.

        Creates a table with basic schema for row insertion testing.
        """
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_invalid_field_names_{unique_suffix}",
            "description": "Table for testing invalid field name errors",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "value": {"type": "integer", "required": False}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    def test_invalid_field_name_data(self, client, auth_headers_user1, test_table_id):
        """
        Test using 'data' field instead of 'row_data' returns 422 INVALID_FIELD_NAME.

        Given: POST request with 'data' field instead of 'row_data'
        When: Attempting to insert rows
        Then: Should return HTTP 422 with INVALID_FIELD_NAME error code
        And: Detail message should mention 'data' and 'row_data'
        """
        request_body = {
            "data": {
                "name": "Test User",
                "value": 42
            }
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Response has required error fields
        data = response.json()
        assert "detail" in data
        assert "error_code" in data

        # Assert: Error code is INVALID_FIELD_NAME
        assert data["error_code"] == "INVALID_FIELD_NAME"

        # Assert: Detail message mentions the invalid field and correct field
        assert "data" in data["detail"].lower()
        assert "row_data" in data["detail"].lower()

    def test_invalid_field_name_rows(self, client, auth_headers_user1, test_table_id):
        """
        Test using 'rows' field instead of 'row_data' returns 422 INVALID_FIELD_NAME.

        Given: POST request with 'rows' field instead of 'row_data'
        When: Attempting to insert rows
        Then: Should return HTTP 422 with INVALID_FIELD_NAME error code
        And: Detail message should mention 'rows' and 'row_data'
        """
        request_body = {
            "rows": [
                {"name": "User 1", "value": 10},
                {"name": "User 2", "value": 20}
            ]
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Error code is INVALID_FIELD_NAME
        data = response.json()
        assert data["error_code"] == "INVALID_FIELD_NAME"

        # Assert: Detail message is helpful
        assert "rows" in data["detail"].lower()
        assert "row_data" in data["detail"].lower()

    def test_invalid_field_name_items(self, client, auth_headers_user1, test_table_id):
        """
        Test using 'items' field instead of 'row_data' returns 422 INVALID_FIELD_NAME.

        Given: POST request with 'items' field instead of 'row_data'
        When: Attempting to insert rows
        Then: Should return HTTP 422 with INVALID_FIELD_NAME error code
        And: Detail message should mention 'items' and 'row_data'
        """
        request_body = {
            "items": [
                {"name": "Item 1", "value": 100},
                {"name": "Item 2", "value": 200}
            ]
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Error code is INVALID_FIELD_NAME
        data = response.json()
        assert data["error_code"] == "INVALID_FIELD_NAME"

        # Assert: Detail message is helpful
        assert "items" in data["detail"].lower()
        assert "row_data" in data["detail"].lower()

    def test_invalid_field_name_records(self, client, auth_headers_user1, test_table_id):
        """
        Test using 'records' field instead of 'row_data' returns 422 INVALID_FIELD_NAME.

        Given: POST request with 'records' field instead of 'row_data'
        When: Attempting to insert rows
        Then: Should return HTTP 422 with INVALID_FIELD_NAME error code
        And: Detail message should mention 'records' and 'row_data'
        """
        request_body = {
            "records": [
                {"name": "Record 1", "value": 111},
                {"name": "Record 2", "value": 222}
            ]
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Assert: Error code is INVALID_FIELD_NAME
        data = response.json()
        assert data["error_code"] == "INVALID_FIELD_NAME"

        # Assert: Detail message is helpful
        assert "records" in data["detail"].lower()
        assert "row_data" in data["detail"].lower()


class TestCorrectRowDataField:
    """
    Test suite for validating successful row insertion with correct row_data field.

    Ensures that when developers use the correct field name, insertion works properly.
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1):
        """
        Create a test table and return its ID.

        Creates a table with basic schema for row insertion testing.
        """
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_correct_row_data_{unique_suffix}",
            "description": "Table for testing correct row_data usage",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": False},
                    "active": {"type": "boolean", "required": False}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    def test_correct_row_data_single_row(self, client, auth_headers_user1, test_table_id):
        """
        Test successful row insertion with correct row_data field (single row).

        Given: POST request with correct 'row_data' field containing single object
        When: Attempting to insert row
        Then: Should return HTTP 201 with inserted row data
        And: Response should include row_id and created_at
        """
        request_body = {
            "row_data": {
                "name": "John Doe",
                "email": "john@example.com",
                "active": True
            }
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 201 Created
        assert response.status_code == status.HTTP_201_CREATED

        # Assert: Response has required fields
        data = response.json()
        assert "rows" in data
        assert "inserted_count" in data

        # Assert: One row was inserted
        assert data["inserted_count"] == 1
        assert len(data["rows"]) == 1

        # Assert: Inserted row has generated fields
        inserted_row = data["rows"][0]
        assert "row_id" in inserted_row
        assert "created_at" in inserted_row
        assert "row_data" in inserted_row

        # Assert: Row data matches what was sent
        assert inserted_row["row_data"]["name"] == "John Doe"
        assert inserted_row["row_data"]["email"] == "john@example.com"
        assert inserted_row["row_data"]["active"] is True

    def test_correct_row_data_batch_insert(self, client, auth_headers_user1, test_table_id):
        """
        Test successful row insertion with correct row_data field (batch insert).

        Given: POST request with correct 'row_data' field containing array of objects
        When: Attempting to insert multiple rows
        Then: Should return HTTP 201 with all inserted rows
        And: Response should include row_id and created_at for each row
        """
        request_body = {
            "row_data": [
                {"name": "Alice Smith", "email": "alice@example.com", "active": True},
                {"name": "Bob Johnson", "email": "bob@example.com", "active": False},
                {"name": "Carol White", "email": "carol@example.com", "active": True}
            ]
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Assert: HTTP 201 Created
        assert response.status_code == status.HTTP_201_CREATED

        # Assert: Response has required fields
        data = response.json()
        assert "rows" in data
        assert "inserted_count" in data

        # Assert: Three rows were inserted
        assert data["inserted_count"] == 3
        assert len(data["rows"]) == 3

        # Assert: Each row has generated fields
        for i, inserted_row in enumerate(data["rows"]):
            assert "row_id" in inserted_row
            assert "created_at" in inserted_row
            assert "row_data" in inserted_row

            # Verify row data matches
            original_row = request_body["row_data"][i]
            assert inserted_row["row_data"]["name"] == original_row["name"]
            assert inserted_row["row_data"]["email"] == original_row["email"]
            assert inserted_row["row_data"]["active"] == original_row["active"]


class TestErrorResponseStructure:
    """
    Test suite for validating error response structure consistency.

    Ensures all error responses follow the DX Contract format:
    - All errors return { detail, error_code }
    - Error codes are stable and documented
    - Detail messages are helpful and actionable
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1):
        """
        Create a test table and return its ID.
        """
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_error_structure_{unique_suffix}",
            "description": "Table for testing error response structure",
            "schema": {
                "fields": {
                    "field1": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    def test_missing_row_data_error_structure(self, client, auth_headers_user1, test_table_id):
        """
        Test that MISSING_ROW_DATA error follows DX Contract structure.

        Given: Request with missing row_data field
        When: Error is returned
        Then: Response should have exactly { detail, error_code } fields
        And: Both fields should be non-empty strings
        """
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={},
            headers=auth_headers_user1
        )

        data = response.json()

        # Assert: Response has exactly the required fields
        assert "detail" in data
        assert "error_code" in data

        # Assert: Fields are non-empty strings
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0
        assert len(data["error_code"]) > 0

        # Assert: Error code is correct
        assert data["error_code"] == "MISSING_ROW_DATA"

    def test_invalid_field_name_error_structure(self, client, auth_headers_user1, test_table_id):
        """
        Test that INVALID_FIELD_NAME error follows DX Contract structure.

        Given: Request with invalid field name (e.g., 'data')
        When: Error is returned
        Then: Response should have exactly { detail, error_code } fields
        And: Both fields should be non-empty strings
        """
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={"data": {"field1": "value"}},
            headers=auth_headers_user1
        )

        data = response.json()

        # Assert: Response has exactly the required fields
        assert "detail" in data
        assert "error_code" in data

        # Assert: Fields are non-empty strings
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert len(data["detail"]) > 0
        assert len(data["error_code"]) > 0

        # Assert: Error code is correct
        assert data["error_code"] == "INVALID_FIELD_NAME"

    def test_all_invalid_field_names_return_consistent_errors(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test that all invalid field names return consistent error structure.

        Given: Requests with different invalid field names
        When: Errors are returned
        Then: All should have same structure but mention specific field name
        """
        invalid_fields = ["data", "rows", "items", "records"]

        for field_name in invalid_fields:
            request_body = {field_name: {"field1": "value"}}

            response = client.post(
                f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
                json=request_body,
                headers=auth_headers_user1
            )

            # Assert: HTTP 422
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Assert: Consistent structure
            data = response.json()
            assert "detail" in data
            assert "error_code" in data
            assert data["error_code"] == "INVALID_FIELD_NAME"

            # Assert: Error message mentions the specific invalid field
            assert field_name in data["detail"].lower()
            assert "row_data" in data["detail"].lower()
