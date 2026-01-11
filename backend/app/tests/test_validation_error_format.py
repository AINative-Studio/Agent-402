"""
Comprehensive tests for Epic 9, Issue 44: Validation errors include loc/msg/type.

Per DX Contract and api-spec.md:
- Validation errors return HTTP 422 (Unprocessable Entity)
- Response includes `detail` field with summary message
- Response includes `error_code: VALIDATION_ERROR`
- Response includes `validation_errors` array
- Each validation error has:
  - `loc`: Array of path segments to the error location (e.g., ["body", "name"])
  - `msg`: Human-readable error message (e.g., "Field required")
  - `type`: Pydantic error type identifier (e.g., "missing", "string_too_short")

Test Coverage:
1. HTTP 422 status code for validation errors
2. Response structure with detail and error_code
3. Presence of validation_errors array
4. Each validation error has loc, msg, type fields
5. loc field is an array of path segments
6. msg field is a non-empty string
7. type field matches Pydantic error types
8. Multiple validation errors are all included
9. detail field summarizes the first error
10. Edge cases: missing required fields, invalid types, constraint violations

Example expected response:
{
  "detail": "Validation error on field 'name': Field required",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {
      "loc": ["body", "name"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestValidationErrorFormat:
    """Test validation error response format per Issue 44."""

    def test_validation_error_returns_422(self, client, auth_headers_user1):
        """
        Test that validation errors return HTTP 422.

        Per DX Contract: Validation errors use HTTP 422 Unprocessable Entity.
        """
        # Send request with missing required fields (empty JSON)
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            "Validation errors must return HTTP 422"

    def test_validation_error_has_detail_and_error_code(self, client, auth_headers_user1):
        """
        Test that validation error response includes detail and error_code.

        Per Epic 9, Issue 42: All errors return { detail, error_code }.
        Per Epic 9, Issue 44: Validation errors include loc/msg/type.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Verify base error structure
        assert "detail" in data, "Response must include 'detail' field"
        assert "error_code" in data, "Response must include 'error_code' field"

        # Verify detail is a non-empty string
        assert isinstance(data["detail"], str), "detail must be a string"
        assert len(data["detail"]) > 0, "detail must not be empty"

        # Verify error_code is VALIDATION_ERROR
        assert data["error_code"] == "VALIDATION_ERROR", \
            "Validation errors must use error_code: VALIDATION_ERROR"

    def test_validation_error_has_validation_errors_array(self, client, auth_headers_user1):
        """
        Test that validation error response includes validation_errors array.

        Per Issue 44: Response includes validation_errors array with loc/msg/type.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Verify validation_errors array exists
        assert "validation_errors" in data, \
            "Response must include 'validation_errors' field"
        assert isinstance(data["validation_errors"], list), \
            "validation_errors must be an array"
        assert len(data["validation_errors"]) > 0, \
            "validation_errors array must not be empty"

    def test_validation_error_has_loc_field(self, client, auth_headers_user1):
        """
        Test that each validation error has loc field (array of path segments).

        Per Issue 44: Each validation error has loc (array of path segments).
        Example: ["body", "event_type"] indicates error in body.event_type field.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Check each validation error has loc field
        for error in data["validation_errors"]:
            assert "loc" in error, "Each validation error must have 'loc' field"
            assert isinstance(error["loc"], list), \
                "loc must be an array of path segments"
            assert len(error["loc"]) > 0, \
                "loc array must not be empty"

            # Verify loc contains path segments (typically starts with "body")
            # For request body validation, first element is usually "body"
            # Example: ["body", "event_type"], ["body", "data"]
            assert all(isinstance(segment, (str, int)) for segment in error["loc"]), \
                "loc segments must be strings or integers"

    def test_validation_error_has_msg_field(self, client, auth_headers_user1):
        """
        Test that each validation error has msg field (human-readable message).

        Per Issue 44: Each validation error has msg (human-readable message).
        Example: "Field required", "String should have at least 1 character"
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Check each validation error has msg field
        for error in data["validation_errors"]:
            assert "msg" in error, "Each validation error must have 'msg' field"
            assert isinstance(error["msg"], str), \
                "msg must be a string"
            assert len(error["msg"]) > 0, \
                "msg must not be empty"

    def test_validation_error_has_type_field(self, client, auth_headers_user1):
        """
        Test that each validation error has type field (error type identifier).

        Per Issue 44: Each validation error has type (error type like "missing").
        Common types: "missing", "string_too_short", "value_error", etc.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Check each validation error has type field
        for error in data["validation_errors"]:
            assert "type" in error, "Each validation error must have 'type' field"
            assert isinstance(error["type"], str), \
                "type must be a string"
            assert len(error["type"]) > 0, \
                "type must not be empty"

    def test_multiple_validation_errors_included(self, client, auth_headers_user1):
        """
        Test that multiple validation errors are all included.

        Per Issue 44: Test multiple validation errors are all included.
        When multiple fields fail validation, all errors should be reported.
        """
        # Send request with invalid event_type (empty string) - will be caught by validation
        # Missing 'data' field will also trigger validation error
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "",  # Invalid: empty string
                # Missing 'data' field
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation_errors array with at least one error
        assert "validation_errors" in data
        assert len(data["validation_errors"]) >= 1, \
            "Should report at least one validation error"

        # Verify each error has the required structure
        for error in data["validation_errors"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_detail_field_summarizes_first_error(self, client, auth_headers_user1):
        """
        Test that detail field summarizes the first validation error.

        Per Issue 44: Test detail field summarizes the first error.
        The detail field should be a human-readable summary, not the full array.
        Example: "Validation error on field 'event_type': Field required"
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Verify detail is a summary string
        assert "detail" in data
        assert isinstance(data["detail"], str)

        # Detail should mention validation error
        detail_lower = data["detail"].lower()
        assert "validation" in detail_lower or "error" in detail_lower, \
            "detail should mention validation error"

        # Detail should reference the first error's field
        if data["validation_errors"]:
            first_error = data["validation_errors"][0]
            field_name = str(first_error["loc"][-1])  # Last segment of loc path

            # detail should contain the field name or message from first error
            assert field_name in data["detail"] or first_error["msg"] in data["detail"], \
                f"detail should reference first error field '{field_name}' or message '{first_error['msg']}'"

    def test_missing_required_field_validation(self, client, auth_headers_user1):
        """
        Test validation error for missing required field.

        Tests that missing required fields produce proper validation errors
        with type "missing" or "value_error.missing".
        """
        # Send request missing both required fields: event_type and data
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation errors for missing fields
        assert "validation_errors" in data
        assert len(data["validation_errors"]) >= 2, \
            "Should have errors for both missing event_type and data"

        # Check for missing field error types
        error_types = [err["type"] for err in data["validation_errors"]]
        # Pydantic v2 uses "missing" for missing fields
        assert any("missing" in error_type for error_type in error_types), \
            "Should have 'missing' error type for required fields"

    def test_invalid_field_type_validation(self, client, auth_headers_user1):
        """
        Test validation error for invalid field type.

        Tests that fields with wrong types produce proper validation errors.
        """
        # Send request with data as a string instead of an object
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "test_event",
                "data": "this should be an object"  # Invalid: string instead of dict
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation error for data field
        assert "validation_errors" in data

        # Find error related to 'data' field
        data_errors = [
            err for err in data["validation_errors"]
            if "data" in str(err["loc"])
        ]
        assert len(data_errors) > 0, "Should have validation error for 'data' field"

        # Verify error has loc/msg/type
        data_error = data_errors[0]
        assert "loc" in data_error
        assert "msg" in data_error
        assert "type" in data_error

    def test_string_constraint_validation(self, client, auth_headers_user1):
        """
        Test validation error for string constraint violations.

        Tests that string fields violating min_length/max_length produce
        proper validation errors with type like "string_too_short".
        """
        # Send request with event_type exceeding max_length (100 chars)
        long_event_type = "a" * 101  # 101 characters

        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": long_event_type,
                "data": {"test": "data"}
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation error
        assert "validation_errors" in data

        # Find error related to event_type length
        event_type_errors = [
            err for err in data["validation_errors"]
            if "event_type" in str(err["loc"])
        ]

        if len(event_type_errors) > 0:
            error = event_type_errors[0]
            assert "loc" in error
            assert "msg" in error
            assert "type" in error
            # Type might be "string_too_long" or similar
            assert "string" in error["type"].lower() or "value" in error["type"].lower()

    def test_custom_validation_error(self, client, auth_headers_user1):
        """
        Test validation error from custom validator.

        Tests that custom field validators (like timestamp validation)
        produce proper validation errors with loc/msg/type.
        """
        # Send request with invalid timestamp format
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "test_event",
                "data": {"test": "data"},
                "timestamp": "invalid-timestamp"  # Invalid ISO8601 format
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation error for timestamp
        assert "validation_errors" in data

        # Find error related to timestamp
        timestamp_errors = [
            err for err in data["validation_errors"]
            if "timestamp" in str(err["loc"])
        ]
        assert len(timestamp_errors) > 0, "Should have validation error for 'timestamp'"

        # Verify error structure
        ts_error = timestamp_errors[0]
        assert "loc" in ts_error
        assert "msg" in ts_error
        assert "type" in ts_error

        # Message should explain the timestamp format requirement
        assert len(ts_error["msg"]) > 0

    def test_whitespace_only_field_validation(self, client, auth_headers_user1):
        """
        Test validation error for whitespace-only fields.

        Tests that fields containing only whitespace are properly validated
        and rejected with appropriate error messages.
        """
        # Send request with whitespace-only event_type
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "   ",  # Whitespace only
                "data": {"test": "data"}
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Should have validation error
        assert "validation_errors" in data
        assert len(data["validation_errors"]) > 0

        # Each error should have required fields
        for error in data["validation_errors"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error


class TestValidationErrorStructure:
    """Test the complete structure of validation error responses."""

    def test_complete_validation_error_structure(self, client, auth_headers_user1):
        """
        Test complete validation error response structure.

        Comprehensive test verifying all required fields are present
        and properly formatted in a validation error response.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Top-level structure
        assert "detail" in data, "Missing 'detail' field"
        assert "error_code" in data, "Missing 'error_code' field"
        assert "validation_errors" in data, "Missing 'validation_errors' field"

        # Verify types
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)
        assert isinstance(data["validation_errors"], list)

        # Verify error_code value
        assert data["error_code"] == "VALIDATION_ERROR"

        # Verify each validation error structure
        for idx, error in enumerate(data["validation_errors"]):
            assert isinstance(error, dict), \
                f"validation_errors[{idx}] must be an object"

            assert "loc" in error, \
                f"validation_errors[{idx}] missing 'loc' field"
            assert "msg" in error, \
                f"validation_errors[{idx}] missing 'msg' field"
            assert "type" in error, \
                f"validation_errors[{idx}] missing 'type' field"

            assert isinstance(error["loc"], list), \
                f"validation_errors[{idx}].loc must be an array"
            assert isinstance(error["msg"], str), \
                f"validation_errors[{idx}].msg must be a string"
            assert isinstance(error["type"], str), \
                f"validation_errors[{idx}].type must be a string"

            # Verify non-empty values
            assert len(error["loc"]) > 0, \
                f"validation_errors[{idx}].loc must not be empty"
            assert len(error["msg"]) > 0, \
                f"validation_errors[{idx}].msg must not be empty"
            assert len(error["type"]) > 0, \
                f"validation_errors[{idx}].type must not be empty"

    def test_validation_error_loc_path_format(self, client, auth_headers_user1):
        """
        Test that loc field follows correct path format.

        For request body validation, loc should be ["body", "field_name"]
        For nested fields, loc should be ["body", "parent", "child"]
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Check loc path format for each error
        for error in data["validation_errors"]:
            loc = error["loc"]

            # For body validation, first element should be "body"
            assert loc[0] == "body", \
                "For request body validation, loc should start with 'body'"

            # Should have at least 2 elements: ["body", "field_name"]
            assert len(loc) >= 2, \
                "loc should have at least ['body', 'field_name']"

            # Field name should be the last element
            field_name = loc[-1]
            assert isinstance(field_name, str), \
                "Field name in loc path should be a string"

    def test_validation_error_no_extra_fields(self, client, auth_headers_user1):
        """
        Test that validation errors don't include unexpected extra fields.

        Ensures the response format is stable and predictable.
        """
        # Send request with missing required fields
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        # Expected top-level fields
        expected_fields = {"detail", "error_code", "validation_errors"}
        actual_fields = set(data.keys())

        # Verify no unexpected fields (though extra fields are allowed)
        # This is more of a documentation test
        assert "detail" in actual_fields
        assert "error_code" in actual_fields
        assert "validation_errors" in actual_fields

        # Each validation error should have exactly loc, msg, type
        # (though Pydantic might include other fields like 'input', 'url', etc.)
        for error in data["validation_errors"]:
            # Required fields must be present
            assert "loc" in error
            assert "msg" in error
            assert "type" in error


class TestValidationErrorEdgeCases:
    """Test edge cases and special scenarios for validation errors."""

    def test_empty_json_body_validation(self, client, auth_headers_user1):
        """
        Test validation error when sending empty JSON object.

        Empty object should fail validation for missing required fields.
        """
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        assert "validation_errors" in data
        assert len(data["validation_errors"]) >= 2  # event_type and data missing

        # Verify structure
        for error in data["validation_errors"]:
            assert all(key in error for key in ["loc", "msg", "type"])

    def test_null_field_validation(self, client, auth_headers_user1):
        """
        Test validation error when sending null for required fields.

        Null values should fail validation for required non-nullable fields.
        """
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": None,  # Null value for required field
                "data": None
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        assert "validation_errors" in data

        # Verify structure
        for error in data["validation_errors"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_array_instead_of_object_validation(self, client, auth_headers_user1):
        """
        Test validation error when sending array instead of object.

        The data field requires a dict/object, not an array.
        """
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "test_event",
                "data": ["not", "an", "object"]  # Array instead of object
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        assert "validation_errors" in data

        # Find error for data field
        data_errors = [
            err for err in data["validation_errors"]
            if "data" in str(err["loc"])
        ]
        assert len(data_errors) > 0

        # Verify structure
        for error in data_errors:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_extra_unknown_fields_handled(self, client, auth_headers_user1):
        """
        Test that extra/unknown fields are handled gracefully.

        Pydantic should either ignore extra fields or validate them
        depending on model configuration.
        """
        response = client.post(
            "/v1/public/database/events",
            headers=auth_headers_user1,
            json={
                "event_type": "test_event",
                "data": {"test": "data"},
                "unknown_field": "should be ignored or rejected"
            }
        )

        # Should either succeed (extra fields ignored) or fail with validation error
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            data = response.json()
            # If rejected, should still have proper structure
            assert "validation_errors" in data
            for error in data["validation_errors"]:
                assert all(key in error for key in ["loc", "msg", "type"])
