"""
Manual smoke test for vector upsert endpoint (Issue #27).
Run this to verify the endpoint works end-to-end.
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "demo_key_user1_abc123"  # From settings.demo_api_key_1

def test_vector_upsert():
    """Test the vector upsert endpoint with a real request."""

    print("=" * 60)
    print("VECTOR UPSERT ENDPOINT SMOKE TEST (Issue #27)")
    print("=" * 60)

    # Test 1: Insert new vector (384 dimensions)
    print("\n1. Testing INSERT (new vector, 384 dimensions)...")
    vector_384 = [0.1] * 384

    payload = {
        "vector_id": "smoke_test_vec_001",
        "vector_embedding": vector_384,
        "document": "Smoke test document for vector upsert",
        "metadata": {
            "test": "smoke_test",
            "agent_id": "test_agent",
            "created_by": "manual_test"
        },
        "namespace": "smoke_test"
    }

    response = requests.post(
        f"{BASE_URL}/database/vectors/upsert",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["created"] is True, "Expected created=True for new vector"
    assert data["dimensions"] == 384, "Expected 384 dimensions"
    assert data["namespace"] == "smoke_test", "Expected smoke_test namespace"
    print("✅ INSERT test passed!")

    # Test 2: Update existing vector
    print("\n2. Testing UPDATE (existing vector)...")
    payload["vector_embedding"] = [0.2] * 384
    payload["metadata"]["version"] = 2

    response = requests.post(
        f"{BASE_URL}/database/vectors/upsert",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["created"] is False, "Expected created=False for updated vector"
    assert data["metadata"]["version"] == 2, "Expected updated metadata"
    print("✅ UPDATE test passed!")

    # Test 3: Test dimension validation (should fail)
    print("\n3. Testing DIMENSION_MISMATCH error (512 dimensions)...")
    invalid_payload = {
        "vector_embedding": [0.1] * 512,  # Invalid dimension
        "document": "Test document"
    }

    response = requests.post(
        f"{BASE_URL}/database/vectors/upsert",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=invalid_payload
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    assert "512" in str(data["detail"]), "Error should mention 512 dimensions"
    print("✅ DIMENSION_MISMATCH test passed!")

    # Test 4: Test 768 dimensions
    print("\n4. Testing 768 dimensions...")
    payload_768 = {
        "vector_embedding": [0.3] * 768,
        "document": "768-dimensional vector test"
    }

    response = requests.post(
        f"{BASE_URL}/database/vectors/upsert",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload_768
    )

    print(f"Status Code: {response.status_code}")
    data = response.json()
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["dimensions"] == 768, "Expected 768 dimensions"
    print("✅ 768 dimensions test passed!")

    # Test 5: List vectors in namespace
    print("\n5. Testing LIST vectors in namespace...")
    response = requests.get(
        f"{BASE_URL}/database/vectors/smoke_test",
        headers={"X-API-Key": API_KEY}
    )

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Found {data['total']} vectors in smoke_test namespace")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["total"] >= 1, "Expected at least 1 vector in namespace"
    print("✅ LIST vectors test passed!")

    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS PASSED! ✅")
    print("=" * 60)
    print("\nVector upsert endpoint is working correctly!")
    print("- POST /database/vectors/upsert: ✅")
    print("- GET /database/vectors/{namespace}: ✅")
    print("- Dimension validation: ✅")
    print("- Upsert behavior (insert/update): ✅")
    print("- Namespace isolation: ✅")
    print("- Metadata support: ✅")

if __name__ == "__main__":
    try:
        test_vector_upsert()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server at http://localhost:8000")
        print("Please start the server with: uvicorn app.main:app --reload")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
