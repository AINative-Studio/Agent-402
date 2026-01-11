"""
Comprehensive tests for Row Pagination API (Epic 7, Issue 4).

Tests the following endpoints:
- GET /v1/public/{project_id}/tables/{table_id}/rows - List rows with pagination
- GET /v1/public/{project_id}/tables/{table_id}/rows/{row_id} - Get single row
- DELETE /v1/public/{project_id}/tables/{table_id}/rows/{row_id} - Delete row

Test Coverage:
1. Listing rows with default pagination
2. Custom limit and offset pagination
3. has_more flag correctness
4. Filtering by field value
5. Sorting ascending and descending
6. Get single row
7. Delete row
8. ROW_NOT_FOUND error handling
9. Edge cases and boundary conditions

Implementation Files:
- backend/app/api/rows.py
- backend/app/services/row_service.py
"""
import pytest
from fastapi import status


class TestListRowsDefaultPagination:
    """Test listing rows with default pagination parameters."""

    def test_list_rows_empty_table(self, client, auth_headers_user1):
        """
        Test listing rows from an empty table.
        Should return empty array with correct pagination metadata.
        """
        project_id = "proj_demo_u1_001"

        # Create table first
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "empty_table",
                "description": "Table with no rows",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # List rows
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "rows" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

        # Verify values
        assert data["rows"] == []
        assert data["total"] == 0
        assert data["limit"] == 100  # Default limit
        assert data["offset"] == 0  # Default offset
        assert data["has_more"] is False

    def test_list_rows_default_pagination(self, client, auth_headers_user1):
        """
        Test listing rows with default pagination (limit=100, offset=0).
        Should use default values when not specified.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "users",
                "description": "User data table",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "email": {"type": "string", "required": True},
                        "age": {"type": "integer", "required": False}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert test rows
        rows_to_insert = [
            {"name": f"User{i}", "email": f"user{i}@example.com", "age": 20 + i}
            for i in range(10)
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED
        assert insert_response.json()["inserted_count"] == 10

        # List rows without pagination parameters
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify pagination metadata
        assert data["total"] == 10
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert data["has_more"] is False
        assert len(data["rows"]) == 10

        # Verify row structure
        for row in data["rows"]:
            assert "row_id" in row
            assert "table_id" in row
            assert "row_data" in row
            assert "created_at" in row
            assert row["table_id"] == table_id

    def test_list_rows_sorted_by_created_at_desc(self, client, auth_headers_user1):
        """
        Test that rows are sorted by created_at descending by default.
        Most recent rows should appear first.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "events",
                "description": "Event log table",
                "schema": {
                    "fields": {
                        "event": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows one by one to ensure different timestamps
        inserted_rows = []
        for i in range(5):
            insert_response = client.post(
                f"/v1/public/{project_id}/tables/{table_id}/rows",
                json={"row_data": {"event": f"event_{i}"}},
                headers=auth_headers_user1
            )
            assert insert_response.status_code == status.HTTP_201_CREATED
            inserted_rows.append(insert_response.json()["rows"][0])

        # List rows
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify default sorting (created_at descending)
        rows = data["rows"]
        assert len(rows) == 5

        # Most recent should be first
        for i in range(len(rows) - 1):
            assert rows[i]["created_at"] >= rows[i + 1]["created_at"]


class TestCustomLimitAndOffset:
    """Test custom limit and offset pagination parameters."""

    def test_list_rows_custom_limit(self, client, auth_headers_user1):
        """
        Test pagination with custom limit parameter.
        Should return only specified number of rows.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 50 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "products",
                "description": "Product catalog",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "price": {"type": "float", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [
            {"name": f"Product{i}", "price": 10.0 + i}
            for i in range(50)
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test with limit=10
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=10",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 50
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["has_more"] is True
        assert len(data["rows"]) == 10

    def test_list_rows_custom_offset(self, client, auth_headers_user1):
        """
        Test pagination with custom offset parameter.
        Should skip specified number of rows.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 30 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "articles",
                "description": "Article collection",
                "schema": {
                    "fields": {
                        "title": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [
            {"title": f"Article {i}"}
            for i in range(30)
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test with offset=20, limit=10
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?offset=20&limit=10",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 30
        assert data["limit"] == 10
        assert data["offset"] == 20
        assert data["has_more"] is False  # 20 + 10 = 30, no more rows
        assert len(data["rows"]) == 10

    def test_list_rows_offset_beyond_total(self, client, auth_headers_user1):
        """
        Test pagination with offset beyond total row count.
        Should return empty result set but correct total.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 10 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "tasks",
                "description": "Task list",
                "schema": {
                    "fields": {
                        "task": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"task": f"Task {i}"} for i in range(10)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test with offset=100 (beyond total)
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?offset=100",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 10
        assert data["offset"] == 100
        assert data["has_more"] is False
        assert len(data["rows"]) == 0

    def test_list_rows_max_limit(self, client, auth_headers_user1):
        """
        Test pagination with maximum allowed limit (1000).
        Should accept and use the maximum limit value.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 50 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "records",
                "description": "Record collection",
                "schema": {
                    "fields": {
                        "value": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"value": i} for i in range(50)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test with limit=1000 (maximum allowed)
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=1000",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["limit"] == 1000
        assert data["total"] == 50
        assert len(data["rows"]) == 50
        assert data["has_more"] is False


class TestHasMoreFlag:
    """Test has_more flag correctness in various pagination scenarios."""

    def test_has_more_true_when_more_rows_exist(self, client, auth_headers_user1):
        """
        Test has_more flag is True when more rows exist beyond current page.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 150 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "items",
                "description": "Item collection",
                "schema": {
                    "fields": {
                        "item_name": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"item_name": f"Item {i}"} for i in range(150)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test first page (offset=0, limit=100)
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=0",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 150
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert data["has_more"] is True  # 0 + 100 < 150

    def test_has_more_false_when_no_more_rows(self, client, auth_headers_user1):
        """
        Test has_more flag is False when no more rows exist.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert 150 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "entries",
                "description": "Entry collection",
                "schema": {
                    "fields": {
                        "value": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"value": f"Value {i}"} for i in range(150)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test last page (offset=100, limit=100)
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=100",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 150
        assert data["limit"] == 100
        assert data["offset"] == 100
        assert data["has_more"] is False  # 100 + 100 >= 150
        assert len(data["rows"]) == 50  # Only 50 rows remaining

    def test_has_more_exact_boundary(self, client, auth_headers_user1):
        """
        Test has_more flag at exact boundary (offset + limit == total).
        Should be False when exactly at the end.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert exactly 100 rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "boundary_test",
                "description": "Boundary test table",
                "schema": {
                    "fields": {
                        "num": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"num": i} for i in range(100)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Test with offset=0, limit=100 (exactly at boundary)
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=0",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 100
        assert data["has_more"] is False  # 0 + 100 = 100, not < 100


class TestFilteringByFieldValue:
    """Test filtering rows by field values."""

    def test_filter_by_string_field(self, client, auth_headers_user1):
        """
        Test filtering rows by string field value.
        Should return only matching rows.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "users_filter",
                "description": "User data for filtering",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "status": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows with different statuses
        rows_to_insert = [
            {"name": "Alice", "status": "active"},
            {"name": "Bob", "status": "inactive"},
            {"name": "Charlie", "status": "active"},
            {"name": "Diana", "status": "pending"},
            {"name": "Eve", "status": "active"}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by status=active
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?status=active",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 3  # 3 active users
        assert len(data["rows"]) == 3

        # Verify all returned rows have status=active
        for row in data["rows"]:
            assert row["row_data"]["status"] == "active"

    def test_filter_by_integer_field(self, client, auth_headers_user1):
        """
        Test filtering rows by integer field value.
        Query parameter should be parsed as integer.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "products_filter",
                "description": "Products for filtering",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "category_id": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows with different category IDs
        rows_to_insert = [
            {"name": "Product A", "category_id": 1},
            {"name": "Product B", "category_id": 2},
            {"name": "Product C", "category_id": 1},
            {"name": "Product D", "category_id": 3},
            {"name": "Product E", "category_id": 1}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by category_id=1
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?category_id=1",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 3
        assert len(data["rows"]) == 3

        # Verify all returned rows have category_id=1
        for row in data["rows"]:
            assert row["row_data"]["category_id"] == 1

    def test_filter_by_boolean_field(self, client, auth_headers_user1):
        """
        Test filtering rows by boolean field value.
        Query parameter should be parsed as boolean.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "features_filter",
                "description": "Features for filtering",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "enabled": {"type": "boolean", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows with different enabled states
        rows_to_insert = [
            {"name": "Feature A", "enabled": True},
            {"name": "Feature B", "enabled": False},
            {"name": "Feature C", "enabled": True},
            {"name": "Feature D", "enabled": False},
            {"name": "Feature E", "enabled": True}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by enabled=true
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?enabled=true",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 3
        assert len(data["rows"]) == 3

        # Verify all returned rows have enabled=true
        for row in data["rows"]:
            assert row["row_data"]["enabled"] is True

    def test_filter_by_multiple_fields(self, client, auth_headers_user1):
        """
        Test filtering rows by multiple field values (AND logic).
        All filter conditions must match.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "employees_filter",
                "description": "Employees for filtering",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "department": {"type": "string", "required": True},
                        "active": {"type": "boolean", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows with various combinations
        rows_to_insert = [
            {"name": "Alice", "department": "Engineering", "active": True},
            {"name": "Bob", "department": "Sales", "active": True},
            {"name": "Charlie", "department": "Engineering", "active": False},
            {"name": "Diana", "department": "Engineering", "active": True},
            {"name": "Eve", "department": "Sales", "active": False}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by department=Engineering AND active=true
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?department=Engineering&active=true",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 2  # Alice and Diana
        assert len(data["rows"]) == 2

        # Verify all returned rows match both filters
        for row in data["rows"]:
            assert row["row_data"]["department"] == "Engineering"
            assert row["row_data"]["active"] is True

    def test_filter_no_matches(self, client, auth_headers_user1):
        """
        Test filtering with no matching rows.
        Should return empty result set with total=0.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "orders_filter",
                "description": "Orders for filtering",
                "schema": {
                    "fields": {
                        "order_id": {"type": "string", "required": True},
                        "status": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"order_id": "O1", "status": "pending"},
            {"order_id": "O2", "status": "shipped"},
            {"order_id": "O3", "status": "pending"}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by non-existent status
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?status=cancelled",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 0
        assert len(data["rows"]) == 0
        assert data["has_more"] is False


class TestSortingAscendingDescending:
    """Test sorting rows in ascending and descending order."""

    def test_sort_by_string_field_ascending(self, client, auth_headers_user1):
        """
        Test sorting rows by string field in ascending order.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "names_sort",
                "description": "Names for sorting",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows in random order
        rows_to_insert = [
            {"name": "Charlie"},
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Diana"}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Sort by name ascending
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?sort_by=name&order=asc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["rows"]) == 4

        # Verify ascending order
        names = [row["row_data"]["name"] for row in data["rows"]]
        assert names == ["Alice", "Bob", "Charlie", "Diana"]

    def test_sort_by_string_field_descending(self, client, auth_headers_user1):
        """
        Test sorting rows by string field in descending order.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "cities_sort",
                "description": "Cities for sorting",
                "schema": {
                    "fields": {
                        "city": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"city": "Boston"},
            {"city": "Denver"},
            {"city": "Atlanta"},
            {"city": "Chicago"}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Sort by city descending
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?sort_by=city&order=desc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["rows"]) == 4

        # Verify descending order
        cities = [row["row_data"]["city"] for row in data["rows"]]
        assert cities == ["Denver", "Chicago", "Boston", "Atlanta"]

    def test_sort_by_integer_field_ascending(self, client, auth_headers_user1):
        """
        Test sorting rows by integer field in ascending order.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "scores_sort",
                "description": "Scores for sorting",
                "schema": {
                    "fields": {
                        "player": {"type": "string", "required": True},
                        "score": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"player": "Alice", "score": 95},
            {"player": "Bob", "score": 78},
            {"player": "Charlie", "score": 88},
            {"player": "Diana", "score": 92}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Sort by score ascending
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?sort_by=score&order=asc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["rows"]) == 4

        # Verify ascending order
        scores = [row["row_data"]["score"] for row in data["rows"]]
        assert scores == [78, 88, 92, 95]

    def test_sort_by_integer_field_descending(self, client, auth_headers_user1):
        """
        Test sorting rows by integer field in descending order.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "ages_sort",
                "description": "Ages for sorting",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "age": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 40},
            {"name": "Charlie", "age": 30},
            {"name": "Diana", "age": 35}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Sort by age descending
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?sort_by=age&order=desc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["rows"]) == 4

        # Verify descending order
        ages = [row["row_data"]["age"] for row in data["rows"]]
        assert ages == [40, 35, 30, 25]

    def test_sort_combined_with_filter(self, client, auth_headers_user1):
        """
        Test sorting combined with filtering.
        Should filter first, then sort the filtered results.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "products_sort_filter",
                "description": "Products for sort and filter",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "category": {"type": "string", "required": True},
                        "price": {"type": "float", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"name": "Laptop", "category": "Electronics", "price": 999.99},
            {"name": "Desk", "category": "Furniture", "price": 299.99},
            {"name": "Mouse", "category": "Electronics", "price": 29.99},
            {"name": "Chair", "category": "Furniture", "price": 199.99},
            {"name": "Keyboard", "category": "Electronics", "price": 79.99}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by category=Electronics and sort by price descending
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?category=Electronics&sort_by=price&order=desc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 3  # Only Electronics category
        assert len(data["rows"]) == 3

        # Verify all are Electronics and sorted by price descending
        prices = []
        for row in data["rows"]:
            assert row["row_data"]["category"] == "Electronics"
            prices.append(row["row_data"]["price"])

        assert prices == [999.99, 79.99, 29.99]


class TestGetSingleRow:
    """Test getting a single row by ID."""

    def test_get_row_success(self, client, auth_headers_user1):
        """
        Test successfully retrieving a single row by ID.
        Should return full row data with all fields.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "documents",
                "description": "Document collection",
                "schema": {
                    "fields": {
                        "title": {"type": "string", "required": True},
                        "content": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert a row
        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={
                "row_data": {
                    "title": "Test Document",
                    "content": "This is test content"
                }
            },
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED
        row_id = insert_response.json()["rows"][0]["row_id"]

        # Get the row
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{row_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify structure
        assert "row_id" in data
        assert "table_id" in data
        assert "project_id" in data
        assert "row_data" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify values
        assert data["row_id"] == row_id
        assert data["table_id"] == table_id
        assert data["project_id"] == project_id
        assert data["row_data"]["title"] == "Test Document"
        assert data["row_data"]["content"] == "This is test content"

    def test_get_row_not_found(self, client, auth_headers_user1):
        """
        Test getting a non-existent row.
        Should return 404 with ROW_NOT_FOUND error code.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "empty_table_get",
                "description": "Empty table for get test",
                "schema": {
                    "fields": {
                        "data": {"type": "string", "required": False}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Try to get non-existent row
        non_existent_row_id = "row_nonexistent123"
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{non_existent_row_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error structure
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "ROW_NOT_FOUND"
        assert non_existent_row_id in data["detail"]


class TestDeleteRow:
    """Test deleting a row by ID."""

    def test_delete_row_success(self, client, auth_headers_user1):
        """
        Test successfully deleting a row.
        Should return confirmation with row_id and timestamp.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "temp_data",
                "description": "Temporary data for deletion",
                "schema": {
                    "fields": {
                        "value": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert a row
        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": {"value": "temporary"}},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED
        row_id = insert_response.json()["rows"][0]["row_id"]

        # Delete the row
        response = client.delete(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{row_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "row_id" in data
        assert "table_id" in data
        assert "deleted" in data
        assert "deleted_at" in data

        # Verify values
        assert data["row_id"] == row_id
        assert data["table_id"] == table_id
        assert data["deleted"] is True
        assert data["deleted_at"].endswith("Z")  # ISO 8601 format

    def test_delete_row_verify_removed(self, client, auth_headers_user1):
        """
        Test that deleted row is actually removed.
        Attempting to get deleted row should return 404.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert row
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "verify_delete",
                "description": "Table to verify deletion",
                "schema": {
                    "fields": {
                        "data": {"type": "string", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": {"data": "test"}},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED
        row_id = insert_response.json()["rows"][0]["row_id"]

        # Delete the row
        delete_response = client.delete(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{row_id}",
            headers=auth_headers_user1
        )
        assert delete_response.status_code == status.HTTP_200_OK

        # Try to get the deleted row
        get_response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{row_id}",
            headers=auth_headers_user1
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND
        assert get_response.json()["error_code"] == "ROW_NOT_FOUND"

    def test_delete_row_not_found(self, client, auth_headers_user1):
        """
        Test deleting a non-existent row.
        Should return 404 with ROW_NOT_FOUND error code.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "delete_test",
                "description": "Table for delete test",
                "schema": {
                    "fields": {
                        "data": {"type": "string", "required": False}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Try to delete non-existent row
        non_existent_row_id = "row_doesnotexist456"
        response = client.delete(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{non_existent_row_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error structure
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "ROW_NOT_FOUND"
        assert non_existent_row_id in data["detail"]

    def test_delete_row_decreases_total(self, client, auth_headers_user1):
        """
        Test that deleting a row decreases the total count.
        List rows should show reduced count.
        """
        project_id = "proj_demo_u1_001"

        # Create table and insert multiple rows
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "count_test",
                "description": "Table for count test",
                "schema": {
                    "fields": {
                        "value": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        rows_to_insert = [{"value": i} for i in range(5)]
        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED
        row_id_to_delete = insert_response.json()["rows"][0]["row_id"]

        # Verify initial count
        list_response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            headers=auth_headers_user1
        )
        assert list_response.json()["total"] == 5

        # Delete one row
        delete_response = client.delete(
            f"/v1/public/{project_id}/tables/{table_id}/rows/{row_id_to_delete}",
            headers=auth_headers_user1
        )
        assert delete_response.status_code == status.HTTP_200_OK

        # Verify count decreased
        list_response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            headers=auth_headers_user1
        )
        assert list_response.json()["total"] == 4


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_pagination_with_filtering_and_sorting(self, client, auth_headers_user1):
        """
        Test combining pagination, filtering, and sorting together.
        Should apply all operations correctly.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "combined_test",
                "description": "Test combined operations",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "category": {"type": "string", "required": True},
                        "score": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows
        rows_to_insert = [
            {"name": "Item1", "category": "A", "score": 10},
            {"name": "Item2", "category": "B", "score": 20},
            {"name": "Item3", "category": "A", "score": 30},
            {"name": "Item4", "category": "A", "score": 15},
            {"name": "Item5", "category": "B", "score": 25},
            {"name": "Item6", "category": "A", "score": 35},
            {"name": "Item7", "category": "A", "score": 5}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by category=A, sort by score descending, limit=3, offset=1
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?category=A&sort_by=score&order=desc&limit=3&offset=1",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have 5 category A items total
        assert data["total"] == 5
        assert data["limit"] == 3
        assert data["offset"] == 1
        assert data["has_more"] is True  # 1 + 3 < 5
        assert len(data["rows"]) == 3

        # Verify they're sorted by score descending and skip first one
        # Expected order: 35, 30, 15, 10, 5
        # With offset=1 and limit=3: 30, 15, 10
        scores = [row["row_data"]["score"] for row in data["rows"]]
        assert scores == [30, 15, 10]

        # Verify all are category A
        for row in data["rows"]:
            assert row["row_data"]["category"] == "A"

    def test_empty_string_filter(self, client, auth_headers_user1):
        """
        Test filtering by empty string value.
        Should match rows with empty string in that field.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "empty_string_test",
                "description": "Test empty string filtering",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "description": {"type": "string", "required": False}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert rows with empty and non-empty descriptions
        rows_to_insert = [
            {"name": "Item1", "description": ""},
            {"name": "Item2", "description": "Has description"},
            {"name": "Item3", "description": ""},
            {"name": "Item4", "description": "Another description"}
        ]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Filter by empty description
        response = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?description=",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 2
        assert len(data["rows"]) == 2

        # Verify all have empty description
        for row in data["rows"]:
            assert row["row_data"]["description"] == ""

    def test_large_result_set_pagination(self, client, auth_headers_user1):
        """
        Test pagination with a larger result set.
        Verify correct behavior across multiple pages.
        """
        project_id = "proj_demo_u1_001"

        # Create table
        table_response = client.post(
            f"/v1/public/{project_id}/tables",
            json={
                "table_name": "large_dataset",
                "description": "Large dataset for pagination",
                "schema": {
                    "fields": {
                        "id": {"type": "integer", "required": True}
                    }
                }
            },
            headers=auth_headers_user1
        )
        assert table_response.status_code == status.HTTP_201_CREATED
        table_id = table_response.json()["id"]

        # Insert 250 rows
        rows_to_insert = [{"id": i} for i in range(250)]

        insert_response = client.post(
            f"/v1/public/{project_id}/tables/{table_id}/rows",
            json={"row_data": rows_to_insert},
            headers=auth_headers_user1
        )
        assert insert_response.status_code == status.HTTP_201_CREATED

        # Page 1: offset=0, limit=100
        response_1 = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=0",
            headers=auth_headers_user1
        )
        assert response_1.status_code == status.HTTP_200_OK
        data_1 = response_1.json()
        assert data_1["total"] == 250
        assert len(data_1["rows"]) == 100
        assert data_1["has_more"] is True

        # Page 2: offset=100, limit=100
        response_2 = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=100",
            headers=auth_headers_user1
        )
        assert response_2.status_code == status.HTTP_200_OK
        data_2 = response_2.json()
        assert data_2["total"] == 250
        assert len(data_2["rows"]) == 100
        assert data_2["has_more"] is True

        # Page 3: offset=200, limit=100
        response_3 = client.get(
            f"/v1/public/{project_id}/tables/{table_id}/rows?limit=100&offset=200",
            headers=auth_headers_user1
        )
        assert response_3.status_code == status.HTTP_200_OK
        data_3 = response_3.json()
        assert data_3["total"] == 250
        assert len(data_3["rows"]) == 50  # Only 50 remaining
        assert data_3["has_more"] is False
