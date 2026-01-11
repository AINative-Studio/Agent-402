"""
Comprehensive tests for row_data field validation (Epic 7, Issue 3).

Tests the RowInsertRequest schema validation:
- Missing row_data field returns 422 with MISSING_ROW_DATA error code
- Using 'data' field returns 422 with INVALID_FIELD_NAME error code
- Using 'rows' field returns 422 with INVALID_FIELD_NAME error code
- Using 'items' field returns 422 with INVALID_FIELD_NAME error code
- Using 'records' field returns 422 with INVALID_FIELD_NAME error code
- Error messages are helpful and guide developers to use row_data

Test Strategy:
1. Unit tests for Pydantic schema validation
2. Edge cases for malformed requests
3. Verification of error codes and messages
4. Behavioral tests for developer experience

Per PRD Section 10 (Contract Stability):
- Field name MUST be row_data (not data, rows, items, or records)
- Errors are deterministic and helpful
"""
import pytest
from pydantic import ValidationError
from app.schemas.rows import RowInsertRequest, INVALID_FIELD_NAMES
from app.core.errors import MissingRowDataError, InvalidFieldNameError


class TestRowDataFieldValidation:
    """Test row_data field validation in RowInsertRequest schema."""

    def test_valid_single_row_data(self):
        """
        Test that valid single row data is accepted.

        Given: A request with row_data containing a single dictionary
        When: The schema is validated
        Then: Validation should succeed
        """
        request_data = {
            "row_data": {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30
            }
        }

        # Should not raise any exception
        request = RowInsertRequest(**request_data)
        assert request.row_data == request_data["row_data"]
        assert isinstance(request.row_data, dict)

    def test_valid_batch_row_data(self):
        """
        Test that valid batch row data is accepted.

        Given: A request with row_data containing an array of dictionaries
        When: The schema is validated
        Then: Validation should succeed
        """
        request_data = {
            "row_data": [
                {"name": "Alice", "email": "alice@example.com", "age": 25},
                {"name": "Bob", "email": "bob@example.com", "age": 35}
            ]
        }

        # Should not raise any exception
        request = RowInsertRequest(**request_data)
        assert request.row_data == request_data["row_data"]
        assert isinstance(request.row_data, list)
        assert len(request.row_data) == 2


class TestMissingRowDataError:
    """Test missing row_data field returns MISSING_ROW_DATA error."""

    def test_missing_row_data_field(self):
        """
        Test that missing row_data field raises MissingRowDataError.

        Given: A request without row_data field
        When: The schema is validated
        Then: MissingRowDataError should be raised with error_code MISSING_ROW_DATA
        """
        request_data = {}

        with pytest.raises(MissingRowDataError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "MISSING_ROW_DATA"
        assert error.status_code == 422
        assert "row_data" in error.detail.lower()

    def test_missing_row_data_with_other_fields(self):
        """
        Test that request with other fields but no row_data raises error.

        Given: A request with unrelated fields but no row_data
        When: The schema is validated
        Then: MissingRowDataError should be raised
        """
        request_data = {
            "some_field": "value",
            "another_field": 123
        }

        with pytest.raises(MissingRowDataError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "MISSING_ROW_DATA"
        assert "row_data" in error.detail

    def test_none_value_for_row_data(self):
        """
        Test that None value for row_data field is caught.

        Given: A request with row_data set to None
        When: The schema is validated
        Then: Pydantic ValidationError should be raised
        """
        request_data = {
            "row_data": None
        }

        # Pydantic catches None value for required field
        with pytest.raises(ValidationError):
            RowInsertRequest(**request_data)

    def test_empty_dict(self):
        """
        Test that empty dictionary raises MissingRowDataError.

        Given: An empty dictionary
        When: The schema is validated
        Then: MissingRowDataError should be raised
        """
        request_data = {}

        with pytest.raises(MissingRowDataError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "MISSING_ROW_DATA"


class TestInvalidFieldNameErrors:
    """Test using invalid field names instead of row_data."""

    def test_using_data_field(self):
        """
        Test that using 'data' field returns INVALID_FIELD_NAME error.

        Given: A request using 'data' instead of 'row_data'
        When: The schema is validated
        Then: InvalidFieldNameError should be raised with error_code INVALID_FIELD_NAME
        And: Error message should guide user to use row_data
        """
        request_data = {
            "data": {"name": "John Doe", "email": "john@example.com"}
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        assert error.status_code == 422
        assert error.field_name == "data"
        assert "data" in error.detail.lower()
        assert "row_data" in error.detail.lower()

    def test_using_rows_field(self):
        """
        Test that using 'rows' field returns INVALID_FIELD_NAME error.

        Given: A request using 'rows' instead of 'row_data'
        When: The schema is validated
        Then: InvalidFieldNameError should be raised
        And: Error message should guide user to use row_data
        """
        request_data = {
            "rows": [{"name": "Alice"}, {"name": "Bob"}]
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        assert error.status_code == 422
        assert error.field_name == "rows"
        assert "rows" in error.detail.lower()
        assert "row_data" in error.detail.lower()

    def test_using_items_field(self):
        """
        Test that using 'items' field returns INVALID_FIELD_NAME error.

        Given: A request using 'items' instead of 'row_data'
        When: The schema is validated
        Then: InvalidFieldNameError should be raised
        And: Error message should guide user to use row_data
        """
        request_data = {
            "items": [{"name": "Item 1"}, {"name": "Item 2"}]
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        assert error.status_code == 422
        assert error.field_name == "items"
        assert "items" in error.detail.lower()
        assert "row_data" in error.detail.lower()

    def test_using_records_field(self):
        """
        Test that using 'records' field returns INVALID_FIELD_NAME error.

        Given: A request using 'records' instead of 'row_data'
        When: The schema is validated
        Then: InvalidFieldNameError should be raised
        And: Error message should guide user to use row_data
        """
        request_data = {
            "records": [{"id": 1}, {"id": 2}]
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        assert error.status_code == 422
        assert error.field_name == "records"
        assert "records" in error.detail.lower()
        assert "row_data" in error.detail.lower()


class TestInvalidFieldNameDetection:
    """Test that all invalid field names are detected correctly."""

    def test_all_invalid_field_names_defined(self):
        """
        Test that all expected invalid field names are in the constant.

        Given: The INVALID_FIELD_NAMES constant
        When: Checking its contents
        Then: It should contain data, rows, items, records
        """
        expected_invalid_names = {"data", "rows", "items", "records"}
        assert INVALID_FIELD_NAMES == expected_invalid_names

    def test_invalid_field_priority_over_missing(self):
        """
        Test that invalid field name error takes priority over missing row_data.

        Given: A request with invalid field name but no row_data
        When: The schema is validated
        Then: InvalidFieldNameError should be raised (not MissingRowDataError)

        This ensures developers get more helpful guidance about the specific
        field name mistake they made.
        """
        request_data = {
            "data": {"name": "Test"}
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        assert error.field_name == "data"

    def test_multiple_invalid_fields_first_detected(self):
        """
        Test behavior when multiple invalid field names are present.

        Given: A request with multiple invalid field names
        When: The schema is validated
        Then: One InvalidFieldNameError should be raised

        Note: The specific field detected first depends on iteration order,
        but at least one should be caught.
        """
        request_data = {
            "data": {"test": 1},
            "rows": [{"test": 2}],
            "items": [{"test": 3}]
        }

        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"
        # Should be one of the invalid field names
        assert error.field_name in INVALID_FIELD_NAMES


class TestErrorMessageQuality:
    """Test that error messages are helpful for developers."""

    def test_missing_row_data_message_is_helpful(self):
        """
        Test that MISSING_ROW_DATA error message is helpful.

        Given: A MissingRowDataError
        When: Reading the error detail
        Then: Message should mention row_data and explain to use it
        """
        error = MissingRowDataError()

        assert "row_data" in error.detail.lower()
        # Should suggest using row_data instead of common alternatives
        assert ("data" in error.detail.lower() or
                "rows" in error.detail.lower())

    def test_invalid_field_name_message_format(self):
        """
        Test that INVALID_FIELD_NAME error messages are well-formatted.

        Given: InvalidFieldNameError for each invalid field
        When: Reading error details
        Then: Each should mention the wrong field and suggest row_data
        """
        invalid_fields = ["data", "rows", "items", "records"]

        for field in invalid_fields:
            error = InvalidFieldNameError(field)

            # Should mention the invalid field name
            assert field in error.detail.lower()
            # Should suggest the correct field name
            assert "row_data" in error.detail.lower()
            # Should have error_code
            assert error.error_code == "INVALID_FIELD_NAME"
            # Should have correct status code
            assert error.status_code == 422

    def test_error_messages_guide_to_correct_field(self):
        """
        Test that error messages explicitly guide to use row_data.

        Given: Any validation error (missing or invalid field)
        When: Reading the error detail
        Then: Message should mention 'row_data' as the correct field name
        """
        # Test missing row_data error
        missing_error = MissingRowDataError()
        assert "row_data" in missing_error.detail

        # Test invalid field name errors
        for invalid_field in ["data", "rows", "items", "records"]:
            invalid_error = InvalidFieldNameError(invalid_field)
            assert "row_data" in invalid_error.detail.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_row_data_with_null_value(self):
        """
        Test that row_data with null value is handled.

        Given: A request with row_data set to null
        When: The schema is validated
        Then: Should raise ValidationError (Pydantic validation)
        """
        request_data = {
            "row_data": None
        }

        # Pydantic should catch this as row_data is required
        with pytest.raises(ValidationError):
            RowInsertRequest(**request_data)

    def test_row_data_with_empty_dict(self):
        """
        Test that row_data with empty dictionary is accepted.

        Given: A request with row_data as empty dict
        When: The schema is validated
        Then: Should be valid (schema allows empty row data)
        """
        request_data = {
            "row_data": {}
        }

        # Should be valid - empty row data is allowed
        request = RowInsertRequest(**request_data)
        assert request.row_data == {}

    def test_row_data_with_empty_array(self):
        """
        Test that row_data with empty array is accepted.

        Given: A request with row_data as empty array
        When: The schema is validated
        Then: Should be valid (schema allows empty array)
        """
        request_data = {
            "row_data": []
        }

        # Should be valid - empty array is allowed
        request = RowInsertRequest(**request_data)
        assert request.row_data == []

    def test_case_sensitivity_of_field_names(self):
        """
        Test that field names are case-sensitive.

        Given: A request with ROW_DATA (uppercase)
        When: The schema is validated
        Then: Should raise MissingRowDataError (field names are case-sensitive)
        """
        request_data = {
            "ROW_DATA": {"name": "Test"}
        }

        with pytest.raises(MissingRowDataError):
            RowInsertRequest(**request_data)

    def test_invalid_field_with_valid_row_data(self):
        """
        Test that having both invalid field and valid row_data succeeds.

        Given: A request with both 'data' field and 'row_data' field
        When: The schema is validated
        Then: InvalidFieldNameError should be raised (invalid fields detected first)
        """
        request_data = {
            "data": {"wrong": "field"},
            "row_data": {"correct": "field"}
        }

        # Invalid field is detected first in validation
        with pytest.raises(InvalidFieldNameError) as exc_info:
            RowInsertRequest(**request_data)

        error = exc_info.value
        assert error.error_code == "INVALID_FIELD_NAME"


class TestContractStability:
    """Test that error codes and formats are stable per PRD Section 10."""

    def test_missing_row_data_error_code_stable(self):
        """
        Test that MISSING_ROW_DATA error code is stable.

        Given: Multiple instances of MissingRowDataError
        When: Checking error codes
        Then: All should have the same error_code
        """
        error1 = MissingRowDataError()
        error2 = MissingRowDataError()

        assert error1.error_code == error2.error_code
        assert error1.error_code == "MISSING_ROW_DATA"

    def test_invalid_field_name_error_code_stable(self):
        """
        Test that INVALID_FIELD_NAME error code is stable.

        Given: Multiple instances of InvalidFieldNameError with different fields
        When: Checking error codes
        Then: All should have the same error_code
        """
        errors = [
            InvalidFieldNameError("data"),
            InvalidFieldNameError("rows"),
            InvalidFieldNameError("items"),
            InvalidFieldNameError("records")
        ]

        for error in errors:
            assert error.error_code == "INVALID_FIELD_NAME"

    def test_http_status_codes_stable(self):
        """
        Test that HTTP status codes are stable (422 for validation errors).

        Given: Validation errors
        When: Checking status codes
        Then: All should return 422 Unprocessable Entity
        """
        missing_error = MissingRowDataError()
        invalid_error = InvalidFieldNameError("data")

        assert missing_error.status_code == 422
        assert invalid_error.status_code == 422

    def test_error_format_consistency(self):
        """
        Test that all errors follow consistent format.

        Given: Different validation errors
        When: Checking their attributes
        Then: All should have detail, error_code, and status_code
        """
        errors = [
            MissingRowDataError(),
            InvalidFieldNameError("data"),
            InvalidFieldNameError("rows"),
            InvalidFieldNameError("items"),
            InvalidFieldNameError("records")
        ]

        for error in errors:
            # All should have these attributes
            assert hasattr(error, "detail")
            assert hasattr(error, "error_code")
            assert hasattr(error, "status_code")
            # Detail and error_code should not be empty
            assert error.detail
            assert error.error_code
            # Status code should be valid HTTP code
            assert 400 <= error.status_code < 600
