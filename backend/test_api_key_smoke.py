#!/usr/bin/env python3
"""
Smoke test for X-API-Key authentication.
Tests Issue #6 implementation manually.
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_missing_api_key():
    """Test that missing X-API-Key returns 401."""
    print("Test 1: Missing X-API-Key...")
    response = requests.get(f"{BASE_URL}/v1/public/projects")

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    data = response.json()
    assert "error_code" in data, "Missing error_code in response"
    assert data["error_code"] == "INVALID_API_KEY", f"Expected INVALID_API_KEY, got {data['error_code']}"
    assert "detail" in data, "Missing detail in response"
    print("✅ PASS: Missing API key returns 401 with correct error format")

def test_invalid_api_key():
    """Test that invalid X-API-Key returns 401."""
    print("\nTest 2: Invalid X-API-Key...")
    response = requests.get(
        f"{BASE_URL}/v1/public/projects",
        headers={"X-API-Key": "invalid_key_xyz"}
    )

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    data = response.json()
    assert data["error_code"] == "INVALID_API_KEY", f"Expected INVALID_API_KEY, got {data['error_code']}"
    print("✅ PASS: Invalid API key returns 401")

def test_valid_api_key():
    """Test that valid X-API-Key allows access."""
    print("\nTest 3: Valid X-API-Key...")
    response = requests.get(
        f"{BASE_URL}/v1/public/projects",
        headers={"X-API-Key": "demo_key_user1_abc123"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "projects" in data, "Missing projects in response"
    assert "total" in data, "Missing total in response"
    print("✅ PASS: Valid API key allows access")

def test_health_endpoint():
    """Test that health endpoint doesn't require auth."""
    print("\nTest 4: Health endpoint without auth...")
    response = requests.get(f"{BASE_URL}/health")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy", "Health check failed"
    print("✅ PASS: Health endpoint works without authentication")

def test_docs_endpoint():
    """Test that docs endpoint doesn't require auth."""
    print("\nTest 5: Docs endpoint without auth...")
    response = requests.get(f"{BASE_URL}/openapi.json")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✅ PASS: Docs endpoint works without authentication")

if __name__ == "__main__":
    print("=" * 60)
    print("X-API-Key Authentication Smoke Test")
    print("Issue #6: Authenticate all public endpoints using X-API-Key")
    print("=" * 60)

    try:
        test_missing_api_key()
        test_invalid_api_key()
        test_valid_api_key()
        test_health_endpoint()
        test_docs_endpoint()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Please start the server with: cd backend && python3 -m uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
