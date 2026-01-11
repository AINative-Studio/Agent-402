#!/usr/bin/env python3
"""
Demo script for Events API (Issue #37)

Demonstrates posting events for audit trail and system tracking.
"""
import json
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "demo-api-key"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def post_event(event_type, data, timestamp=None):
    """Post an event to the API."""
    url = f"{BASE_URL}/v1/public/database/events"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "event_type": event_type,
        "data": data
    }

    if timestamp:
        payload["timestamp"] = timestamp

    response = requests.post(url, headers=headers, json=payload)

    print(f"\n📤 Request: POST /v1/public/database/events")
    print(f"Event Type: {event_type}")
    print(f"Status: {response.status_code}")

    if response.status_code == 201:
        event = response.json()
        print(f"✅ Event Created:")
        print(f"   ID: {event['id']}")
        print(f"   Type: {event['event_type']}")
        print(f"   Timestamp: {event['timestamp']}")
        print(f"   Data: {json.dumps(event['data'], indent=6)}")
        return event
    else:
        print(f"❌ Error: {response.json()}")
        return None

def main():
    print("\n" + "="*60)
    print("  🎯 Events API Demo - Issue #37")
    print("  POST /database/events for audit trail and tracking")
    print("="*60)

    # Example 1: Agent Decision Event
    print_section("1. Agent Decision Event")
    post_event(
        event_type="agent_decision",
        data={
            "agent_id": "analyst-001",
            "decision": "approve_transaction",
            "confidence": 0.95,
            "reasoning": "All compliance checks passed",
            "run_id": "demo-run-001"
        },
        timestamp="2025-01-11T22:00:00Z"
    )

    # Example 2: Compliance Check Event
    print_section("2. Compliance Check Event")
    post_event(
        event_type="compliance_check",
        data={
            "subject": "user-12345",
            "check_type": "kyc",
            "status": "passed",
            "risk_score": 0.15,
            "reviewer": "compliance-agent-002"
        },
        timestamp="2025-01-11T22:01:00Z"
    )

    # Example 3: X402 Request Event
    print_section("3. X402 Request Tracking")
    post_event(
        event_type="x402_request",
        data={
            "did": "did:example:agent-123",
            "signature": "0x1234abcd5678ef90",
            "payload": {
                "action": "transfer",
                "amount": 1000,
                "currency": "USD"
            },
            "verified": True
        },
        timestamp="2025-01-11T22:02:00Z"
    )

    # Example 4: Agent Tool Call
    print_section("4. Agent Tool Call Event")
    post_event(
        event_type="agent_tool_call",
        data={
            "agent_id": "transaction-agent",
            "tool_name": "x402.request",
            "parameters": {
                "endpoint": "/api/transaction",
                "method": "POST"
            },
            "result": "success",
            "execution_time_ms": 145
        }
    )  # No timestamp - will auto-generate

    # Example 5: Workflow Sequence
    print_section("5. Multi-Event Workflow (for replay)")
    workflow_run_id = "workflow-demo-001"

    # Step 1: Analysis
    post_event(
        event_type="agent_decision",
        data={
            "agent_id": "analyst-001",
            "run_id": workflow_run_id,
            "step": 1,
            "decision": "initiate_compliance_check"
        },
        timestamp="2025-01-11T23:00:00Z"
    )

    # Step 2: Compliance
    post_event(
        event_type="compliance_check",
        data={
            "run_id": workflow_run_id,
            "step": 2,
            "check_type": "kyt",
            "status": "passed"
        },
        timestamp="2025-01-11T23:00:15Z"
    )

    # Step 3: Execution
    post_event(
        event_type="agent_tool_call",
        data={
            "agent_id": "transaction-agent",
            "run_id": workflow_run_id,
            "step": 3,
            "tool_name": "x402.request",
            "result": "success"
        },
        timestamp="2025-01-11T23:00:30Z"
    )

    print_section("Demo Complete!")
    print("\n✅ All events posted successfully")
    print("📊 Events are now available for:")
    print("   - Audit trail review")
    print("   - Compliance reporting")
    print("   - Workflow replay")
    print("   - System observability")
    print()

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")
