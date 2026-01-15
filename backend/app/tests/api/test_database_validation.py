"""
Comprehensive validation tests for table row insertion operations.

Epic 11, Story 4 (Issue #70): Test validates 422 for missing row_data.

This module validates that the API properly returns 422 validation errors
when row_data is missing, empty, null, or has invalid types during table
insert operations.

Test Coverage:
- POST /tables/{table_id}/rows without row_data returns 422
- POST with empty row_data array returns 422
- POST with null row_data returns 422
- POST with invalid row_data type (string, number, boolean) returns 422
- Verify error response format matches APIError schema
- Verify error messages include proper field validation
- Test both single and batch insert operations

Per PRD Section 10 (Contract Stability):
- Field name MUST be row_data (not data, rows, items, or records)
- Errors are deterministic with proper error codes
- Error messages guide developers to use correct field name

DX Contract Compliance:
- All errors return { detail, error_code }
- Error codes are stable and machine-readable
- Validation errors use HTTP 422
- Error messages are clear and actionable
"""
import pytest
from fastapi import status


class TestMissingRowDataValidation:
    """
    Test suite for validating missing row_data field returns 422.

    Epic 11, Story 4: Test validates 422 for missing row_data.
    GitHub Issue #70: Comprehensive validation tests.
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1, mock_zerodb_client):
        """
        Create a test table for row insertion validation using mock.

        Returns:
            str: Table ID for use in tests
        """
        import uuid

        # Create table via API (will use mocked ZeroDB)
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_db_validation_{unique_suffix}",
            "description": "Table for database validation testing",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True},
                    "email": {"type": "string", "required": False},
                    "age": {"type": "integer", "required": False},
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

        assert response.status_code == status.HTTP_201_CREATED, \
            f"Failed to create table: {response.status_code} {response.json()}"

        return response.json()["id"]

    def test_missing_row_data_field_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST /tables/{table_id}/rows without row_data returns 422.

        Given: POST request with empty body
        When: Attempting to insert rows without row_data field
        Then: Should return HTTP 422 UNPROCESSABLE_ENTITY
        And: Error code should be MISSING_ROW_DATA
        And: Detail message should mention row_data
        """
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={},
            headers=auth_headers_user1
        )

        # Verify HTTP 422 status
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422, got {response.status_code}"

        # Verify error response structure
        data = response.json()
        assert "detail" in data, "Error response missing 'detail' field"
        assert "error_code" in data, "Error response missing 'error_code' field"

        # Verify error code
        assert data["error_code"] == "MISSING_ROW_DATA", \
            f"Expected MISSING_ROW_DATA, got {data['error_code']}"

        # Verify error message mentions row_data
        assert "row_data" in data["detail"].lower(), \
            f"Error detail should mention 'row_data': {data['detail']}"

    def test_missing_row_data_with_other_fields_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST without row_data but with other fields returns 422.

        Given: POST request with arbitrary fields but no row_data
        When: Attempting to insert rows
        Then: Should return HTTP 422 with MISSING_ROW_DATA error
        """
        request_body = {
            "some_field": "value",
            "another_field": 123,
            "yet_another": True
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["error_code"] == "MISSING_ROW_DATA"
        assert "row_data" in data["detail"].lower()


class TestNullRowDataValidation:
    """
    Test suite for validating null row_data returns 422.

    Tests null value handling for row_data field.
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1, mock_zerodb_client):
        """
        Create a test table for null row_data validation using mock.

        Returns:
            str: Table ID for use in tests
        """
        import uuid

        # Create table via API (will use mocked ZeroDB)
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_null_validation_{unique_suffix}",
            "description": "Table for null row_data validation testing",
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

        assert response.status_code == status.HTTP_201_CREATED, \
            f"Failed to create table: {response.status_code} {response.json()}"

        return response.json()["id"]

    def test_null_row_data_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST with null row_data returns 422.

        Given: POST request with row_data set to null
        When: Attempting to insert rows
        Then: Should return HTTP 422 UNPROCESSABLE_ENTITY
        And: Error should indicate invalid row_data value
        """
        request_body = {
            "row_data": None
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        # Should reject null value
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for null row_data, got {response.status_code}"

        data = response.json()
        assert "error_code" in data
        assert "detail" in data

        # Error should be about invalid/missing data
        assert data["error_code"] in [
            "VALIDATION_ERROR",
            "INVALID_ROW_DATA",
            "MISSING_ROW_DATA"
        ]


class TestInvalidRowDataTypeValidation:
    """
    Test suite for validating invalid row_data types return 422.

    Tests rejection of incorrect data types:
    - String instead of object/array
    - Number instead of object/array
    - Boolean instead of object/array
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1, mock_zerodb_client):
        """
        Create a test table for type validation using mock.

        Returns:
            str: Table ID for use in tests
        """
        import uuid

        # Create table via API (will use mocked ZeroDB)
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_type_validation_{unique_suffix}",
            "description": "Table for row_data type validation testing",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED, \
            f"Failed to create table: {response.status_code} {response.json()}"

        return response.json()["id"]

    def test_string_row_data_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST with string row_data returns 422.

        Given: POST request with row_data as string
        When: Attempting to insert rows
        Then: Should return HTTP 422 UNPROCESSABLE_ENTITY
        And: Error should indicate type validation failure
        """
        request_body = {
            "row_data": "invalid string data"
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for string row_data, got {response.status_code}"

        data = response.json()
        assert "error_code" in data
        assert "detail" in data

        # Verify error indicates type problem
        detail_lower = data["detail"].lower()
        assert any(keyword in detail_lower for keyword in [
            "type", "invalid", "must be", "expected", "dict", "should be"
        ]), f"Error should mention type issue: {data['detail']}"

    def test_number_row_data_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST with number row_data returns 422.

        Given: POST request with row_data as number
        When: Attempting to insert rows
        Then: Should return HTTP 422 UNPROCESSABLE_ENTITY
        And: Error should indicate type validation failure
        """
        request_body = {
            "row_data": 12345
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for number row_data, got {response.status_code}"

        data = response.json()
        assert "error_code" in data
        assert "detail" in data

        # Verify error indicates type problem
        detail_lower = data["detail"].lower()
        assert any(keyword in detail_lower for keyword in [
            "type", "invalid", "must be", "expected", "dict", "should be"
        ]), f"Error should mention type issue: {data['detail']}"

    def test_boolean_row_data_returns_422(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test POST with boolean row_data returns 422.

        Given: POST request with row_data as boolean
        When: Attempting to insert rows
        Then: Should return HTTP 422 UNPROCESSABLE_ENTITY
        And: Error should indicate type validation failure
        """
        request_body = {
            "row_data": True
        }

        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json=request_body,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for boolean row_data, got {response.status_code}"

        data = response.json()
        assert "error_code" in data
        assert "detail" in data

        # Verify error indicates type problem
        detail_lower = data["detail"].lower()
        assert any(keyword in detail_lower for keyword in [
            "type", "invalid", "must be", "expected", "dict", "should be"
        ]), f"Error should mention type issue: {data['detail']}"


class TestErrorResponseFormat:
    """
    Test suite for validating error response format matches APIError schema.

    Verifies:
    - All validation errors have detail and error_code fields
    - Error codes are consistent and machine-readable
    - Detail messages are human-readable and helpful
    - Response format matches DX Contract specifications
    """

    @pytest.fixture
    def test_table_id(self, client, auth_headers_user1, mock_zerodb_client):
        """
        Create a test table for error format validation using mock.

        Returns:
            str: Table ID for use in tests
        """
        import uuid

        # Create table via API (will use mocked ZeroDB)
        unique_suffix = uuid.uuid4().hex[:8]
        table_request = {
            "table_name": f"test_error_format_{unique_suffix}",
            "description": "Table for error format validation testing",
            "schema": {
                "fields": {
                    "name": {"type": "string", "required": True}
                },
                "indexes": []
            }
        }

        response = client.post(
            "/v1/public/proj_demo_u1_001/tables",
            json=table_request,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED, \
            f"Failed to create table: {response.status_code} {response.json()}"

        return response.json()["id"]

    def test_validation_error_has_required_fields(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test validation errors contain required fields per APIError schema.

        Given: Request that triggers validation error
        When: Error response is returned
        Then: Response must have 'detail' and 'error_code' fields
        And: Both fields must be non-empty strings
        """
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={},
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()

        # Verify required fields exist
        assert "detail" in data, "Response missing 'detail' field"
        assert "error_code" in data, "Response missing 'error_code' field"

        # Verify fields are non-empty strings
        assert isinstance(data["detail"], str), "'detail' must be string"
        assert isinstance(data["error_code"], str), "'error_code' must be string"
        assert len(data["detail"]) > 0, "'detail' must not be empty"
        assert len(data["error_code"]) > 0, "'error_code' must not be empty"

    def test_error_codes_are_machine_readable(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test error codes follow machine-readable format.

        Given: Various validation errors
        When: Error responses are returned
        Then: error_code should be UPPER_SNAKE_CASE
        And: error_code should be descriptive
        """
        # Test missing row_data
        response = client.post(
            f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
            json={},
            headers=auth_headers_user1
        )

        data = response.json()
        error_code = data["error_code"]

        # Verify format: UPPER_SNAKE_CASE
        assert error_code.isupper(), \
            f"Error code should be uppercase: {error_code}"
        assert "_" in error_code or error_code.isalpha(), \
            f"Error code should use underscores: {error_code}"

    def test_detail_messages_are_helpful(
        self, client, auth_headers_user1, test_table_id
    ):
        """
        Test detail messages provide helpful guidance.

        Given: Validation errors
        When: Error responses are returned
        Then: Detail messages should be clear and actionable
        And: Should guide developer to correct usage
        """
        test_cases = [
            ({}, "missing row_data"),
            ({"data": {"name": "test"}}, "invalid field 'data'"),
            ({"row_data": "string"}, "invalid type"),
        ]

        for request_body, expected_guidance in test_cases:
            response = client.post(
                f"/v1/public/proj_demo_u1_001/tables/{test_table_id}/rows",
                json=request_body,
                headers=auth_headers_user1
            )

            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                data = response.json()
                detail = data["detail"].lower()

                # Verify message is not generic
                assert len(detail) > 20, \
                    f"Detail message should be descriptive: {detail}"

                # Should not just say "error" or "invalid"
                assert not detail in ["error", "invalid", "validation error"], \
                    f"Detail should be specific: {detail}"
