#!/usr/bin/env python3
"""
Example script demonstrating PROJECT_LIMIT_EXCEEDED error handling.

This script shows how the API behaves when project limits are exceeded.
Run this after starting the API server with: python3 app/main.py

⚠️ SECURITY WARNING:
This is a demonstration script using a hardcoded API key for LOCAL TESTING ONLY.
NEVER use hardcoded API keys in production or commit them to version control.
Always use environment variables: API_KEY = os.getenv('ZERODB_API_KEY')
See /SECURITY.md for production best practices.
"""
import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000/v1/public"
API_KEY = "example-demo-key-123"  # ⚠️ DEMO ONLY - Use os.getenv('API_KEY') in production


def create_project(name: str, tier: str = "free") -> Dict[str, Any]:
    """Create a project via the API."""
    response = requests.post(
        f"{BASE_URL}/projects",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={"name": name, "tier": tier, "database_enabled": True}
    )

    return {
        "status_code": response.status_code,
        "body": response.json()
    }


def list_projects() -> Dict[str, Any]:
    """List all projects."""
    response = requests.get(
        f"{BASE_URL}/projects",
        headers={"X-API-Key": API_KEY}
    )

    return {
        "status_code": response.status_code,
        "body": response.json()
    }


def main():
    """Demonstrate project limit error handling."""

    print("=" * 70)
    print("PROJECT LIMIT EXCEEDED - Example Demonstration")
    print("=" * 70)
    print()

    print("Free tier allows 3 projects maximum.")
    print()

    # Create projects within limit
    print("Creating projects within limit...")
    print("-" * 70)

    for i in range(1, 4):
        print(f"\n{i}. Creating project 'demo-project-{i}'...")
        result = create_project(f"demo-project-{i}", tier="free")

        if result["status_code"] == 201:
            print(f"   ✅ SUCCESS (HTTP {result['status_code']})")
            print(f"   Project ID: {result['body']['id']}")
            print(f"   Status: {result['body']['status']}")
        else:
            print(f"   ❌ FAILED (HTTP {result['status_code']})")
            print(f"   Error: {result['body']}")

    print()
    print("=" * 70)

    # List projects
    print("\nListing all projects...")
    print("-" * 70)
    projects = list_projects()
    print(f"Total projects: {projects['body']['total']}")
    for p in projects['body']['items']:
        print(f"  - {p['name']} (ID: {p['id']}, Tier: {p['tier']})")

    print()
    print("=" * 70)

    # Attempt to create 4th project (should fail)
    print("\n4. Attempting to create 4th project (should trigger limit error)...")
    print("-" * 70)

    result = create_project("demo-project-4", tier="free")

    if result["status_code"] == 429:
        print(f"   ❌ LIMIT EXCEEDED (HTTP {result['status_code']}) - Expected behavior!")
        print()
        print("   Error Response:")
        print(f"   {json.dumps(result['body'], indent=2)}")
        print()
        print("   Key observations:")
        print(f"   ✅ HTTP Status: {result['status_code']} (Too Many Requests)")
        print(f"   ✅ Error Code: {result['body'].get('error_code')}")
        print(f"   ✅ Detail: {result['body'].get('detail')}")
        print()

        detail = result['body'].get('detail', '')
        print("   The error message includes:")
        if "tier 'free'" in detail:
            print("   ✅ Current tier ('free')")
        if "3/3" in detail:
            print("   ✅ Current usage (3/3)")
        if "upgrade to" in detail:
            print("   ✅ Upgrade suggestion")
        if "support@ainative.studio" in detail:
            print("   ✅ Support contact")
    else:
        print(f"   ⚠️  Unexpected status code: {result['status_code']}")
        print(f"   Response: {result['body']}")

    print()
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review the error message clarity")
    print("  2. Check OpenAPI docs at http://localhost:8000/docs")
    print("  3. Try different tiers (starter: 10, pro: 50, enterprise: unlimited)")
    print("  4. Run comprehensive tests: pytest tests/test_project_limits.py -v")
    print()


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API server")
        print("   Please start the server first:")
        print("   python3 app/main.py")
        exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)
