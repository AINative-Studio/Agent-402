"""
Manual verification test for GitHub Issue #40: Stable response format for event writes.

Run this script to manually verify the implementation:
    python3 test_issue40_manual.py

This script demonstrates:
1. Successful event creation with HTTP 201 status
2. Stable response format with all required fields
3. Field order consistency
4. Timestamp normalization
5. Server-side created_at timestamp
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import json

client = TestClient(app)

# Use a valid API key from settings
API_KEY = settings.demo_api_key_1
PROJECT_ID = "test_project_001"

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_response(response):
    """Print formatted response details."""
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2))

def test_successful_event_creation():
    """Test successful event creation with stable response format."""
    print_header("TEST 1: Successful Event Creation")

    response = client.post(
        f"/v1/public/{PROJECT_ID}/database/events",
        json={
            "event_type": "agent_decision",
            "data": {
                "agent_id": "agent_001",
                "decision": "approve_transaction",
                "confidence": 0.95,
                "reasoning": "All compliance checks passed"
            }
        },
        headers={"X-API-Key": API_KEY}
    )

    print_response(response)

    # Verify HTTP 201 status
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    print("\n✓ HTTP 201 (Created) status confirmed")

    # Verify all required fields present
    data = response.json()
    required_fields = ["id", "event_type", "data", "timestamp", "created_at"]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    print("✓ All required fields present:", required_fields)

    # Verify field order
    field_names = list(data.keys())
    assert field_names == required_fields, f"Field order mismatch: {field_names}"
    print("✓ Field order is stable:", field_names)

    # Verify field values
    assert data["id"].startswith("evt_"), "ID should start with 'evt_'"
    print(f"✓ Event ID format correct: {data['id']}")

    assert data["event_type"] == "agent_decision", "event_type should match request"
    print(f"✓ event_type echoed from request: {data['event_type']}")

    assert data["data"]["agent_id"] == "agent_001", "data should match request"
    print("✓ data echoed from request")

    assert data["timestamp"].endswith("Z"), "timestamp should be ISO8601 with Z suffix"
    print(f"✓ timestamp normalized to ISO8601: {data['timestamp']}")

    assert data["created_at"].endswith("Z"), "created_at should be ISO8601 with Z suffix"
    print(f"✓ created_at is server-side timestamp: {data['created_at']}")

    print("\n✓✓✓ TEST PASSED: Stable response format verified ✓✓✓")

def test_custom_timestamp():
    """Test event creation with custom timestamp."""
    print_header("TEST 2: Custom Timestamp Normalization")

    custom_timestamp = "2024-01-15T10:30:00Z"

    response = client.post(
        f"/v1/public/{PROJECT_ID}/database/events",
        json={
            "event_type": "agent_tool_call",
            "data": {
                "agent_id": "agent_002",
                "tool": "x402.request",
                "parameters": {"endpoint": "/compliance/kyc"}
            },
            "timestamp": custom_timestamp
        },
        headers={"X-API-Key": API_KEY}
    )

    print_response(response)

    assert response.status_code == 201
    data = response.json()

    # Verify timestamp was normalized
    assert data["timestamp"].startswith("2024-01-15T10:30:00")
    print(f"✓ Custom timestamp normalized: {data['timestamp']}")

    print("\n✓✓✓ TEST PASSED: Timestamp normalization verified ✓✓✓")

def test_nested_data_structure():
    """Test that nested data structures are preserved."""
    print_header("TEST 3: Nested Data Structure Preservation")

    complex_data = {
        "agent_id": "compliance_agent",
        "decision": {
            "action": "approve",
            "reasons": ["kyc_passed", "risk_low", "sanctions_clear"],
            "metadata": {
                "risk_score": 0.15,
                "confidence": 0.95,
                "processing_time_ms": 234
            }
        },
        "context": {
            "transaction_id": "txn_abc123",
            "amount": 1000.00,
            "currency": "USD"
        }
    }

    response = client.post(
        f"/v1/public/{PROJECT_ID}/database/events",
        json={
            "event_type": "compliance_check",
            "data": complex_data
        },
        headers={"X-API-Key": API_KEY}
    )

    print_response(response)

    assert response.status_code == 201
    data = response.json()

    # Verify nested structure preserved
    assert data["data"] == complex_data
    print("✓ Nested data structure preserved exactly")

    print("\n✓✓✓ TEST PASSED: Nested data preservation verified ✓✓✓")

def test_multiple_events_consistency():
    """Test that multiple events return consistent format."""
    print_header("TEST 4: Multiple Events Format Consistency")

    event_types = ["agent_decision", "agent_tool_call", "agent_error"]
    responses = []

    for event_type in event_types:
        response = client.post(
            f"/v1/public/{PROJECT_ID}/database/events",
            json={
                "event_type": event_type,
                "data": {"type": event_type, "test": "value"}
            },
            headers={"X-API-Key": API_KEY}
        )
        responses.append(response.json())
        print(f"Created event: {event_type}")

    # Verify all have same field structure
    expected_fields = ["id", "event_type", "data", "timestamp", "created_at"]

    for idx, resp in enumerate(responses):
        field_names = list(resp.keys())
        assert field_names == expected_fields, \
            f"Event {idx} has inconsistent fields: {field_names}"

    print(f"✓ All {len(responses)} events have consistent format")
    print("✓ Field order stable across multiple events")

    print("\n✓✓✓ TEST PASSED: Format consistency verified ✓✓✓")

def main():
    """Run all manual verification tests."""
    print("\n")
    print("╔═════════════════════════════════════════════════════════╗")
    print("║  GitHub Issue #40: Stable Response Format Verification  ║")
    print("╚═════════════════════════════════════════════════════════╝")

    try:
        test_successful_event_creation()
        test_custom_timestamp()
        test_nested_data_structure()
        test_multiple_events_consistency()

        print("\n")
        print("╔═════════════════════════════════════════════════════════╗")
        print("║              ✓ ALL TESTS PASSED ✓                      ║")
        print("║  Issue #40 implementation verified successfully!        ║")
        print("╚═════════════════════════════════════════════════════════╝")
        print("\n")

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
