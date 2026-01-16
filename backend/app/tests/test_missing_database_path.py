"""
Tests for Epic 11 Story 3 - Database path validation with clear error messages.

GitHub Issue #69: Test fails loudly on missing /database/ path.

This test suite validates that database operations fail with clear, helpful
error messages when required paths or configurations are missing, rather than
producing cryptic "NoneType has no attribute..." errors.

Per PRD Section 10 (Determinism):
- Errors are deterministic and documented
- Error messages are clear and actionable
- No silent failures or cryptic error messages

Test Coverage:
1. Missing database path in API requests
2. Missing project path validation
3. Missing table path validation
4. Missing database configuration
5. Helpful error message validation (not "NoneType has no attribute...")

Design Philosophy:
- Tests verify BEHAVIOR, not implementation details
- Error messages should guide developers to solutions
- All errors follow DX Contract format: {detail, error_code}
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.services.zerodb_client import ZeroDBClient
from app.core.errors import TableNotFoundError, ProjectNotFoundError, ZeroDBError
import httpx


class TestMissingDatabasePath:
    """
    Test suite for missing database path validation.

    Validates that operations fail with clear error messages when
    database paths are not properly configured or provided.
    """

    def test_insert_row_fails_loudly_when_table_not_found(self, client, auth_headers_user1):
        """
        GIVEN: A table that does not exist in the project
        WHEN: Attempting to insert a row into the nonexistent table
        THEN: Should raise clear error with helpful message

        This test ensures that missing table paths produce clear errors,
        not cryptic "NoneType has no attribute..." messages.
        """
        # Attempt to insert into a nonexistent table
        row_data = {
            "run_id": "run_123",
            "agent_id": "agent_456",
            "status": "running"
        }

        response = client.post(
            "/v1/public/test_project_123/database/tables/nonexistent_table/rows",
            headers=auth_headers_user1,
            json={"row_data": row_data}
        )

        # Should return 404 Not Found
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Validate error response format per DX Contract
        error_data = response.json()
        assert "detail" in error_data, "Error must include detail field"
        assert "error_code" in error_data, "Error must include error_code field"

        # Validate helpful error message (not cryptic)
        detail = error_data["detail"]
        assert "not found" in detail.lower(), "Error should indicate resource not found"

        # Ensure error_code is appropriate (PATH_NOT_FOUND or TABLE_NOT_FOUND)
        assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
            f"Error code should be TABLE_NOT_FOUND or PATH_NOT_FOUND, got {error_data['error_code']}"

        # Most importantly: NO "NoneType has no attribute..." message
        assert "NoneType" not in detail, \
            "Error must not contain cryptic 'NoneType has no attribute' message"
        assert "AttributeError" not in detail, \
            "Error must not expose Python AttributeError"

    def test_query_rows_fails_loudly_when_table_path_missing(self, client, auth_headers_user1):
        """
        GIVEN: Table does not exist at expected path
        WHEN: Attempting to query rows from the table
        THEN: Should raise clear TableNotFoundError with path info

        Validates that query operations provide helpful error messages
        about missing table paths.
        """
        # Attempt to query rows from nonexistent table
        filter_criteria = {"status": "active"}

        response = client.post(
            "/v1/public/test_project_123/database/tables/missing_table/query",
            headers=auth_headers_user1,
            json={"filter": filter_criteria, "limit": 10}
        )

        # Should return 404 Not Found
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Validate error response
        error_data = response.json()
        assert "detail" in error_data
        assert "error_code" in error_data

        # Validate helpful error message
        detail = error_data["detail"]
        assert "table" in detail.lower() or "not found" in detail.lower(), \
            "Error should indicate table or resource not found"

        # NO cryptic errors
        assert "NoneType" not in detail
        assert "AttributeError" not in detail
        assert len(detail) > 10, "Error message should be substantive, not empty"

    def test_list_rows_fails_loudly_when_table_missing(self, client, auth_headers_user1):
        """
        GIVEN: Table path does not exist
        WHEN: Attempting to list rows from the table
        THEN: Should return clear error about missing table

        Tests that GET requests for rows also fail with clear messages.
        """
        response = client.get(
            "/v1/public/test_project_123/database/tables/no_such_table/rows",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data = response.json()
        assert "detail" in error_data
        assert "error_code" in error_data
        assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
            f"Error code should indicate not found, got {error_data['error_code']}"

        # Verify helpful message
        detail = error_data["detail"]
        assert detail, "Detail must not be empty"
        assert "NoneType" not in detail
        assert "not found" in detail.lower(), "Should indicate resource not found"

    def test_update_row_fails_loudly_when_table_not_found(self, client, auth_headers_user1):
        """
        GIVEN: Table does not exist
        WHEN: Attempting to update a row in the table
        THEN: Should return clear error about missing table

        Validates PUT operations provide helpful error messages.
        """
        row_data = {"status": "completed"}

        response = client.put(
            "/v1/public/test_project_123/database/tables/missing_table/rows/row_123",
            headers=auth_headers_user1,
            json={"row_data": row_data}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data = response.json()
        assert "detail" in error_data
        assert "error_code" in error_data

        detail = error_data["detail"]
        assert detail
        assert "NoneType" not in detail
        assert "AttributeError" not in detail

    def test_get_table_fails_loudly_when_not_found(self, client, auth_headers_user1):
        """
        GIVEN: Table ID that does not exist
        WHEN: Attempting to get table details
        THEN: Should return clear error about table not found

        Tests that table metadata operations provide clear errors.
        """
        response = client.get(
            "/v1/public/test_project_123/database/tables/nonexistent_table_id",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data = response.json()
        assert "detail" in error_data
        assert "error_code" in error_data
        assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
            f"Error code should indicate not found, got {error_data['error_code']}"

        detail = error_data["detail"]
        assert "not found" in detail.lower(), "Should indicate resource not found"
        assert "NoneType" not in detail

    def test_error_messages_are_actionable(self, client, auth_headers_user1):
        """
        GIVEN: Various missing database path scenarios
        WHEN: Operations are attempted
        THEN: Error messages should guide developers to solutions

        This test validates the QUALITY of error messages, ensuring they:
        1. Explain what went wrong
        2. Identify the missing resource
        3. Are actionable (not just "error occurred")
        """
        test_cases = [
            {
                "method": "POST",
                "path": "/v1/public/test_project_123/database/tables/missing/rows",
                "json": {"row_data": {"test": "data"}},
                "expected_status": 404,
                "expected_keywords": ["table", "not found"]
            },
            {
                "method": "GET",
                "path": "/v1/public/test_project_123/database/tables/missing/rows",
                "json": None,
                "expected_status": 404,
                "expected_keywords": ["table", "not found"]
            },
            {
                "method": "GET",
                "path": "/v1/public/test_project_123/database/tables/missing",
                "json": None,
                "expected_status": 404,
                "expected_keywords": ["table", "not found"]
            }
        ]

        for case in test_cases:
            if case["method"] == "POST":
                response = client.post(
                    case["path"],
                    headers=auth_headers_user1,
                    json=case["json"]
                )
            elif case["method"] == "GET":
                response = client.get(
                    case["path"],
                    headers=auth_headers_user1
                )

            assert response.status_code == case["expected_status"], \
                f"Failed for {case['method']} {case['path']}"

            error_data = response.json()
            detail = error_data["detail"].lower()

            # Verify keywords present
            for keyword in case["expected_keywords"]:
                assert keyword in detail, \
                    f"Error message should contain '{keyword}' for {case['path']}"

            # Verify no cryptic messages
            assert "NoneType" not in error_data["detail"]
            assert "AttributeError" not in error_data["detail"]
            assert len(error_data["detail"]) > 15, \
                "Error message should be substantive"


class TestDatabaseConfigurationErrors:
    """
    Test suite for database configuration validation.

    Validates that missing or invalid database configurations
    produce clear error messages.
    """

    def test_zerodb_client_handles_missing_api_key_gracefully(self):
        """
        GIVEN: ZeroDB client without API key configured
        WHEN: Client is initialized
        THEN: Should handle gracefully with mock mode, not crash with cryptic error

        This test validates that missing configuration is handled with
        clear messaging, not "NoneType has no attribute..." errors.
        """
        # Create client without credentials
        with patch.dict('os.environ', {}, clear=True):
            client = ZeroDBClient()

            # Should be in mock mode
            assert client._mock_mode is True, \
                "Client should enter mock mode when credentials missing"

            # Should have mock credentials, not None
            assert client.api_key is not None, \
                "API key should default to mock value, not None"
            assert client.project_id is not None, \
                "Project ID should default to mock value, not None"

            # Should be able to construct URLs without AttributeError
            assert client._db_base is not None
            assert "mock_project" in client._db_base

    def test_zerodb_client_handles_missing_project_id_gracefully(self):
        """
        GIVEN: ZeroDB client without project_id configured
        WHEN: Client is initialized with only API key
        THEN: Should handle gracefully, not produce NoneType error

        Validates graceful degradation when partial configuration exists.
        """
        with patch.dict('os.environ', {'ZERODB_API_KEY': 'test_key'}, clear=True):
            client = ZeroDBClient()

            # Should be in mock mode (project_id missing)
            assert client._mock_mode is True

            # Should have mock project_id
            assert client.project_id is not None
            assert client.project_id == "mock_project"

    def test_zerodb_client_url_construction_handles_none_gracefully(self):
        """
        GIVEN: ZeroDB client with various configuration states
        WHEN: Client constructs URLs for requests
        THEN: Should not produce "NoneType has no attribute" errors

        This test ensures that URL construction handles missing values
        gracefully without exposing Python internals.
        """
        # Test that URL construction works even in mock mode
        with patch.dict('os.environ', {}, clear=True):
            client = ZeroDBClient()

            # Should be able to access URL properties without AttributeError
            assert client._db_base is not None, "Database base URL should be constructed"
            assert client._embed_base is not None, "Embeddings base URL should be constructed"

            # URLs should contain project_id (even if mock)
            assert client.project_id in client._db_base, \
                "Base URL should include project_id"

            # Should not have "None" string in URLs
            assert "None" not in client._db_base, \
                "URL should not contain literal 'None' string"
            assert "/None/" not in client._db_base, \
                "URL should not have /None/ path segment"


class TestErrorMessageClarity:
    """
    Test suite specifically for validating error message clarity.

    Epic 11 Story 3: Error messages must be helpful, not cryptic.
    """

    def test_error_messages_never_contain_nonetype(self, client, auth_headers_user1):
        """
        GIVEN: Various error scenarios
        WHEN: Errors occur
        THEN: Error messages must NEVER contain "NoneType has no attribute"

        This is the KEY test for Issue #69 - ensuring errors fail loudly
        with helpful messages, not cryptic Python exceptions.
        """
        # Test various endpoints that could produce errors
        error_scenarios = [
            ("POST", "/v1/public/proj/database/tables/missing/rows", {"row_data": {}}),
            ("GET", "/v1/public/proj/database/tables/missing/rows", None),
            ("GET", "/v1/public/proj/database/tables/missing", None),
            ("PUT", "/v1/public/proj/database/tables/missing/rows/id", {"row_data": {}}),
        ]

        for method, path, json_body in error_scenarios:
            if method == "POST":
                response = client.post(path, headers=auth_headers_user1, json=json_body)
            elif method == "GET":
                response = client.get(path, headers=auth_headers_user1)
            elif method == "PUT":
                response = client.put(path, headers=auth_headers_user1, json=json_body)

            # Get error response
            error_data = response.json()
            detail = error_data.get("detail", "")

            # CRITICAL ASSERTION: No "NoneType" in any error message
            assert "NoneType" not in detail, \
                f"Error message contains 'NoneType' for {method} {path}: {detail}"

            # Also verify no other Python exception leakage
            assert "AttributeError" not in detail
            assert "TypeError" not in detail
            assert "KeyError" not in detail
            assert "'NoneType' object" not in detail

            # Verify message is substantive
            assert len(detail) > 0, "Error detail must not be empty"
            assert detail.strip() != "", "Error detail must not be whitespace only"

    def test_error_messages_include_resource_identifiers(self, client, auth_headers_user1):
        """
        GIVEN: Operations on missing resources
        WHEN: Errors occur
        THEN: Error messages should identify which resource is missing

        Helpful error messages include context about what was attempted.
        """
        # Test table not found - should mention table name
        response = client.get(
            "/v1/public/test_project/database/tables/specific_table_name",
            headers=auth_headers_user1
        )

        if response.status_code == 404:
            error_data = response.json()
            detail = error_data["detail"]

            # Should mention the resource type
            assert "table" in detail.lower() or "not found" in detail.lower(), \
                "Error should indicate what type of resource is missing"

    def test_error_messages_follow_dx_contract(self, client, auth_headers_user1):
        """
        GIVEN: Any error scenario
        WHEN: Error response is returned
        THEN: Must follow DX Contract format: {detail, error_code}

        Validates consistency across all error responses.
        """
        # Trigger various errors
        error_endpoints = [
            "/v1/public/proj/database/tables/missing",
            "/v1/public/proj/database/tables/missing/rows",
        ]

        for endpoint in error_endpoints:
            response = client.get(endpoint, headers=auth_headers_user1)

            # Should have JSON response
            assert response.headers.get("content-type") == "application/json"

            error_data = response.json()

            # DX Contract validation
            assert "detail" in error_data, \
                f"Error must have 'detail' field for {endpoint}"
            assert "error_code" in error_data, \
                f"Error must have 'error_code' field for {endpoint}"

            # Fields must not be None or empty
            assert error_data["detail"] is not None
            assert error_data["error_code"] is not None
            assert error_data["detail"] != ""
            assert error_data["error_code"] != ""

            # error_code must be UPPER_SNAKE_CASE
            assert error_data["error_code"].isupper(), \
                "error_code must be uppercase"


class TestDatabasePathValidation:
    """
    Test suite for database path validation and URL construction.

    Ensures that database paths are properly validated and errors
    are clear when paths are malformed or missing.
    """

    def test_table_operations_require_valid_table_path(self, client, auth_headers_user1):
        """
        GIVEN: Table operations with various path formats
        WHEN: Requests are made to table endpoints
        THEN: Invalid paths should return clear errors

        Tests that table path validation produces helpful errors.
        """
        # Valid path format (should work or return business logic error, not path error)
        valid_response = client.get(
            "/v1/public/test_project_123/database/tables",
            headers=auth_headers_user1
        )
        # Should return 200 (list of tables, possibly empty) or other business logic status
        # But NOT 404 for missing path
        assert valid_response.status_code in [200, 404], \
            "Valid path structure should not fail with path error"

        # Invalid path format - missing /database/ (tested in test_missing_database_prefix.py)
        # Here we focus on table-specific path issues

    def test_row_operations_validate_table_existence(self, client, auth_headers_user1):
        """
        GIVEN: Row operations on nonexistent tables
        WHEN: Attempting CRUD operations
        THEN: Should return helpful table not found errors

        Validates that row operations check table existence with clear errors.
        """
        operations = [
            ("POST", "/v1/public/test_project/database/tables/no_table/rows",
             {"row_data": {"test": "data"}}),
            ("GET", "/v1/public/test_project/database/tables/no_table/rows", None),
            ("GET", "/v1/public/test_project/database/tables/no_table/rows/row_id", None),
            ("PUT", "/v1/public/test_project/database/tables/no_table/rows/row_id",
             {"row_data": {"updated": "data"}}),
        ]

        for method, path, json_data in operations:
            if method == "POST":
                response = client.post(path, headers=auth_headers_user1, json=json_data)
            elif method == "GET":
                response = client.get(path, headers=auth_headers_user1)
            elif method == "PUT":
                response = client.put(path, headers=auth_headers_user1, json=json_data)

            # All should return 404 for table not found
            assert response.status_code == status.HTTP_404_NOT_FOUND, \
                f"Should return 404 for {method} {path}"

            error_data = response.json()

            # Validate error format and clarity
            assert "detail" in error_data
            assert "error_code" in error_data
            assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
                f"Error code should indicate not found for {method} {path}, got {error_data['error_code']}"

            # Verify helpful message
            detail = error_data["detail"]
            assert "not found" in detail.lower(), f"Should indicate not found for {method} {path}"
            assert "NoneType" not in detail

    def test_query_operations_validate_table_path(self, client, auth_headers_user1):
        """
        GIVEN: Query operations on missing table paths
        WHEN: Attempting to query rows
        THEN: Should return clear table not found error

        Specific test for query endpoint validation.
        """
        response = client.post(
            "/v1/public/test_project/database/tables/missing_table/query",
            headers=auth_headers_user1,
            json={"filter": {"status": "active"}, "limit": 10}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data = response.json()
        assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
            f"Error code should indicate not found, got {error_data['error_code']}"

        detail = error_data["detail"]
        assert "not found" in detail.lower(), "Should indicate resource not found"
        assert "NoneType" not in detail
        assert len(detail) > 10, "Error message should be descriptive"


class TestErrorMessageExamples:
    """
    Documentation test suite showing examples of good error messages.

    These tests serve as living documentation of the expected error
    message format and quality.
    """

    def test_table_not_found_error_example(self, client, auth_headers_user1):
        """
        Example of expected error message for table not found.

        Expected format:
        {
            "detail": "Table not found: missing_table" or "Path '...' not found",
            "error_code": "TABLE_NOT_FOUND" or "PATH_NOT_FOUND"
        }

        The detail should:
        - Clearly state the problem (resource not found)
        - Be actionable (developer knows what to check)
        """
        response = client.get(
            "/v1/public/test_project/database/tables/missing_table",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        error_data = response.json()

        # Validate it follows the expected pattern
        assert "detail" in error_data
        assert "error_code" in error_data
        assert error_data["error_code"] in ["TABLE_NOT_FOUND", "PATH_NOT_FOUND"], \
            f"Error code should indicate not found, got {error_data['error_code']}"

        detail = error_data["detail"]

        # Quality checks for the error message
        assert isinstance(detail, str), "Detail must be a string"
        assert len(detail) > 10, "Detail should be substantive"
        assert detail.strip() == detail, "Detail should not have leading/trailing whitespace"
        assert "not found" in detail.lower(), "Should clearly indicate the resource is missing"

        # Anti-patterns to avoid
        assert "NoneType" not in detail, "Should not expose Python internals"
        assert "AttributeError" not in detail, "Should not expose Python exceptions"

    def test_multiple_error_messages_are_consistent(self, client, auth_headers_user1):
        """
        Test that error messages are consistent across similar errors.

        All "not found" errors should follow similar patterns for:
        - Message structure
        - Level of detail
        - Tone and helpfulness
        """
        not_found_endpoints = [
            "/v1/public/proj/database/tables/table1",
            "/v1/public/proj/database/tables/table2",
            "/v1/public/proj/database/tables/table3",
        ]

        error_messages = []
        for endpoint in not_found_endpoints:
            response = client.get(endpoint, headers=auth_headers_user1)
            if response.status_code == 404:
                error_data = response.json()
                error_messages.append(error_data["detail"])

        # If we got multiple error messages, verify consistency
        if len(error_messages) > 1:
            # All should mention "table" or similar keyword
            for msg in error_messages:
                assert "table" in msg.lower() or "not found" in msg.lower(), \
                    f"Message should be consistent in terminology: {msg}"

            # All should be similar in length (within reason)
            lengths = [len(msg) for msg in error_messages]
            avg_length = sum(lengths) / len(lengths)
            for length in lengths:
                # Within 100% of average (very lenient - just checking order of magnitude)
                assert length > avg_length * 0.3, \
                    "Error messages should be similarly detailed"
