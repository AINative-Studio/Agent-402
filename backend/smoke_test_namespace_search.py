"""
Smoke test for Issue #23: Namespace scoping in search endpoint.

This smoke test verifies that:
1. Search accepts namespace parameter
2. Search returns only vectors from the specified namespace
3. Complete isolation between namespaces is enforced
4. Default namespace behavior works correctly

Usage:
    python smoke_test_namespace_search.py
"""
import requests
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test_api_key_abc123"
PROJECT_ID = "proj_smoke_test_ns_search"

headers = {"X-API-Key": API_KEY}


def test_namespace_search_isolation():
    """
    Test that search properly scopes results by namespace.

    Stores vectors in different namespaces and verifies complete isolation.
    """
    print("\n" + "=" * 70)
    print("Issue #23 Smoke Test: Search Namespace Scoping")
    print("=" * 70)

    # Store vector in namespace "team_alpha"
    print("\n1. Storing vector in namespace 'team_alpha'...")
    alpha_response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
        json={
            "text": "Alpha team quarterly financial report Q4 2025",
            "namespace": "team_alpha",
            "metadata": {"team": "alpha", "type": "report"}
        },
        headers=headers
    )

    if alpha_response.status_code != 200:
        print(f"   ERROR: Failed to store alpha vector: {alpha_response.status_code}")
        print(f"   Response: {alpha_response.json()}")
        return False

    alpha_data = alpha_response.json()
    print(f"   SUCCESS: Stored vector {alpha_data['vector_id']} in namespace '{alpha_data['namespace']}'")

    # Store vector in namespace "team_beta"
    print("\n2. Storing vector in namespace 'team_beta'...")
    beta_response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
        json={
            "text": "Beta team product roadmap and engineering milestones",
            "namespace": "team_beta",
            "metadata": {"team": "beta", "type": "roadmap"}
        },
        headers=headers
    )

    if beta_response.status_code != 200:
        print(f"   ERROR: Failed to store beta vector: {beta_response.status_code}")
        print(f"   Response: {beta_response.json()}")
        return False

    beta_data = beta_response.json()
    print(f"   SUCCESS: Stored vector {beta_data['vector_id']} in namespace '{beta_data['namespace']}'")

    # Store vector in default namespace
    print("\n3. Storing vector in default namespace...")
    default_response = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/embed-and-store",
        json={
            "text": "Company-wide general announcement and updates",
            "metadata": {"scope": "company-wide"}
        },
        headers=headers
    )

    if default_response.status_code != 200:
        print(f"   ERROR: Failed to store default vector: {default_response.status_code}")
        print(f"   Response: {default_response.json()}")
        return False

    default_data = default_response.json()
    print(f"   SUCCESS: Stored vector {default_data['vector_id']} in namespace '{default_data['namespace']}'")

    # Test 1: Search in team_alpha namespace
    print("\n4. Searching in namespace 'team_alpha'...")
    search_alpha = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        json={
            "query": "financial report",
            "namespace": "team_alpha",
            "top_k": 10
        },
        headers=headers
    )

    if search_alpha.status_code != 200:
        print(f"   ERROR: Search failed: {search_alpha.status_code}")
        print(f"   Response: {search_alpha.json()}")
        return False

    alpha_results = search_alpha.json()
    print(f"   Namespace searched: {alpha_results['namespace']}")
    print(f"   Total results: {alpha_results['total_results']}")

    if alpha_results['namespace'] != 'team_alpha':
        print(f"   ERROR: Expected namespace 'team_alpha', got '{alpha_results['namespace']}'")
        return False

    if alpha_results['total_results'] != 1:
        print(f"   ERROR: Expected 1 result, got {alpha_results['total_results']}")
        return False

    result = alpha_results['results'][0]
    if result['namespace'] != 'team_alpha':
        print(f"   ERROR: Result namespace is '{result['namespace']}', expected 'team_alpha'")
        return False

    if result['metadata']['team'] != 'alpha':
        print(f"   ERROR: Result is not from alpha team")
        return False

    print(f"   SUCCESS: Found only alpha team vector")
    print(f"   - Vector ID: {result['vector_id']}")
    print(f"   - Text: {result['text'][:50]}...")
    print(f"   - Similarity: {result['similarity']:.4f}")

    # Test 2: Search in team_beta namespace
    print("\n5. Searching in namespace 'team_beta'...")
    search_beta = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        json={
            "query": "roadmap milestones",
            "namespace": "team_beta",
            "top_k": 10
        },
        headers=headers
    )

    if search_beta.status_code != 200:
        print(f"   ERROR: Search failed: {search_beta.status_code}")
        return False

    beta_results = search_beta.json()
    print(f"   Namespace searched: {beta_results['namespace']}")
    print(f"   Total results: {beta_results['total_results']}")

    if beta_results['namespace'] != 'team_beta':
        print(f"   ERROR: Expected namespace 'team_beta', got '{beta_results['namespace']}'")
        return False

    if beta_results['total_results'] != 1:
        print(f"   ERROR: Expected 1 result, got {beta_results['total_results']}")
        return False

    result = beta_results['results'][0]
    if result['metadata']['team'] != 'beta':
        print(f"   ERROR: Result is not from beta team")
        return False

    print(f"   SUCCESS: Found only beta team vector")
    print(f"   - Vector ID: {result['vector_id']}")
    print(f"   - Text: {result['text'][:50]}...")

    # Test 3: Search in default namespace
    print("\n6. Searching in default namespace (no namespace parameter)...")
    search_default = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        json={
            "query": "announcement updates",
            "top_k": 10
        },
        headers=headers
    )

    if search_default.status_code != 200:
        print(f"   ERROR: Search failed: {search_default.status_code}")
        return False

    default_results = search_default.json()
    print(f"   Namespace searched: {default_results['namespace']}")
    print(f"   Total results: {default_results['total_results']}")

    if default_results['namespace'] != 'default':
        print(f"   ERROR: Expected namespace 'default', got '{default_results['namespace']}'")
        return False

    if default_results['total_results'] != 1:
        print(f"   ERROR: Expected 1 result, got {default_results['total_results']}")
        return False

    result = default_results['results'][0]
    if result['metadata']['scope'] != 'company-wide':
        print(f"   ERROR: Result is not from default namespace")
        return False

    print(f"   SUCCESS: Found only default namespace vector")
    print(f"   - Vector ID: {result['vector_id']}")
    print(f"   - Text: {result['text'][:50]}...")

    # Test 4: Verify cross-namespace isolation
    print("\n7. Verifying cross-namespace isolation...")
    print("   Searching for 'financial report' in team_beta (should find 0 results)...")
    search_cross = requests.post(
        f"{BASE_URL}/v1/public/{PROJECT_ID}/embeddings/search",
        json={
            "query": "financial report",  # This is in team_alpha
            "namespace": "team_beta",  # But searching in team_beta
            "top_k": 10
        },
        headers=headers
    )

    if search_cross.status_code != 200:
        print(f"   ERROR: Search failed: {search_cross.status_code}")
        return False

    cross_results = search_cross.json()
    if cross_results['total_results'] != 0:
        print(f"   ERROR: Expected 0 results, got {cross_results['total_results']}")
        print(f"   ISOLATION FAILURE: Found vectors from other namespace!")
        return False

    print(f"   SUCCESS: Complete isolation verified - 0 results found")

    return True


if __name__ == "__main__":
    print("\nStarting Issue #23 smoke test...")
    print(f"Base URL: {BASE_URL}")
    print(f"Project ID: {PROJECT_ID}")

    try:
        success = test_namespace_search_isolation()

        if success:
            print("\n" + "=" * 70)
            print("SUCCESS: Issue #23 smoke test passed!")
            print("=" * 70)
            print("\nVerified capabilities:")
            print("  - Search accepts namespace parameter")
            print("  - Namespace scoping works correctly")
            print("  - Complete isolation between namespaces")
            print("  - Default namespace behavior works")
            print("  - Cross-namespace searches return empty results")
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("FAILED: Issue #23 smoke test failed!")
            print("=" * 70)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to API server")
        print(f"Make sure the server is running at {BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
