"""
Integration test for PROJECT_LIMIT_EXCEEDED error.

This test can be added to the smoke test suite to verify
the project limit validation is working correctly.
"""
import os

import pytest
import requests


ZERODB_BASE_URL = os.getenv("ZERODB_BASE_URL", "http://127.0.0.1:8000/v1/public")


@pytest.fixture
def api_key():
    """Get or generate a test API key."""
    return os.getenv("TEST_API_KEY", "test-integration-key-789")


@pytest.fixture
def headers(api_key):
    """Create headers with API key."""
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def test_project_limit_exceeded_integration(headers):
    """
    Integration test for PROJECT_LIMIT_EXCEEDED error handling.

    Verifies:
    1. Can create projects up to tier limit
    2. Exceeding limit returns HTTP 429
    3. Error response includes error_code: "PROJECT_LIMIT_EXCEEDED"
    4. Error response includes detail field with tier and limit info
    5. Error message suggests upgrade path
    """
    # Clean start - use unique API key for isolation
    test_headers = headers.copy()

    # Create projects up to free tier limit (3)
    created_projects = []
    for i in range(3):
        response = requests.post(
            f"{ZERODB_BASE_URL}/projects",
            json={
                "name": f"integration-test-project-{i}",
                "description": f"Integration test project {i}",
                "tier": "free",
                "database_enabled": True
            },
            headers=test_headers,
            timeout=10
        )

        # Should succeed
        assert response.status_code == 201, f"Failed to create project {i}: {response.text}"

        project = response.json()
        created_projects.append(project)

        # Verify response structure
        assert "id" in project
        assert project["name"] == f"integration-test-project-{i}"
        assert project["tier"] == "free"
        assert project["status"] == "ACTIVE"

    # Attempt to create 4th project (should fail)
    response = requests.post(
        f"{ZERODB_BASE_URL}/projects",
        json={
            "name": "integration-test-project-4",
            "tier": "free",
            "database_enabled": True
        },
        headers=test_headers,
        timeout=10
    )

    # Verify HTTP 429 status code
    assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.text}"

    # Verify error response structure
    error_data = response.json()

    # Must have error_code field
    assert "error_code" in error_data, "Missing error_code in error response"
    assert error_data["error_code"] == "PROJECT_LIMIT_EXCEEDED"

    # Must have detail field
    assert "detail" in error_data, "Missing detail in error response"
    detail = error_data["detail"]

    # Verify detail contains required information
    assert "Project limit exceeded" in detail, "Detail missing 'Project limit exceeded'"
    assert "tier 'free'" in detail, "Detail missing tier information"
    assert "3/3" in detail, "Detail missing current count and limit"

    # Verify upgrade suggestion or support contact
    assert (
        "upgrade to 'starter'" in detail or "contact support" in detail
    ), "Detail missing upgrade suggestion or support contact"

    assert "support@ainative.studio" in detail, "Detail missing support email"

    print("✅ PROJECT_LIMIT_EXCEEDED integration test passed")
    print(f"   - Created {len(created_projects)} projects successfully")
    print(f"   - 4th project correctly rejected with HTTP 429")
    print(f"   - Error response: {error_data}")


def test_tier_validation_returns_422(headers):
    """
    Test that invalid tier returns HTTP 422 with INVALID_TIER error code.

    This is a complementary test to verify tier validation.
    """
    response = requests.post(
        f"{ZERODB_BASE_URL}/projects",
        json={
            "name": "test-invalid-tier",
            "tier": "premium",  # Invalid tier
            "database_enabled": True
        },
        headers=headers,
        timeout=10
    )

    # Verify HTTP 422 status code
    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

    # Verify error response
    error_data = response.json()
    assert error_data["error_code"] == "INVALID_TIER"
    assert "detail" in error_data
    assert "premium" in error_data["detail"]

    print("✅ INVALID_TIER validation test passed")


if __name__ == "__main__":
    # Run tests directly
    import sys

    # Set default test URL if not set
    if "ZERODB_BASE_URL" not in os.environ:
        os.environ["ZERODB_BASE_URL"] = "http://127.0.0.1:8000/v1/public"

    # Run pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
