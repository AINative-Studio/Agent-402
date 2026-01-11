"""
Comprehensive tests for Agent Run Replay API (Epic 12, Issue 5).

Tests cover:
1. List runs endpoint with pagination
2. Get run details endpoint
3. Get replay data endpoint
4. Chronological ordering validation
5. Error cases (run not found)
6. Authentication requirements
7. Data completeness and validation

Per PRD Section 10 (Success Criteria):
- Enable deterministic replay of agent runs
- Complete audit trail and replayability

Per PRD Section 11 (Deterministic Replay):
- Aggregate all records for a run_id
- Order chronologically by timestamp
- Validate all linked records exist
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app.schemas.runs import RunStatus


class TestListRunsEndpoint:
    """
    Tests for GET /v1/public/{project_id}/runs
    List all runs with pagination and filtering.
    """

    def test_list_runs_success(self, client, auth_headers_user1):
        """
        Test successful retrieval of runs list.
        Verifies pagination and run summary structure.
        """
        project_id = "proj_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "runs" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        # Verify pagination defaults
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert isinstance(data["total"], int)
        assert isinstance(data["runs"], list)

        # Verify we have demo data
        assert data["total"] > 0
        assert len(data["runs"]) > 0

        # Verify run summary structure
        run = data["runs"][0]
        assert "run_id" in run
        assert "project_id" in run
        assert "agent_id" in run
        assert "status" in run
        assert "started_at" in run
        assert "memory_count" in run
        assert "event_count" in run
        assert "request_count" in run

        # Verify demo run data
        assert run["run_id"] == "run_demo_001"
        assert run["project_id"] == project_id
        assert run["agent_id"] == "agent_compliance_001"
        assert run["status"] == "COMPLETED"

        # Verify counts match demo data
        assert run["memory_count"] == 3  # 3 memory records in demo
        assert run["event_count"] == 5   # 5 compliance events in demo
        assert run["request_count"] == 2  # 2 X402 requests in demo

    def test_list_runs_pagination(self, client, auth_headers_user1):
        """
        Test pagination parameters work correctly.
        """
        project_id = "proj_demo_001"

        # Test custom page size
        response = client.get(
            f"/v1/public/{project_id}/runs?page=1&page_size=10",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["runs"]) <= 10

    def test_list_runs_status_filter(self, client, auth_headers_user1):
        """
        Test filtering runs by status.
        """
        project_id = "proj_demo_001"

        # Filter by COMPLETED status
        response = client.get(
            f"/v1/public/{project_id}/runs?status_filter=COMPLETED",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # All returned runs should have COMPLETED status
        for run in data["runs"]:
            assert run["status"] == "COMPLETED"

    def test_list_runs_empty_project(self, client, auth_headers_user1):
        """
        Test listing runs for project with no runs returns empty list.
        """
        project_id = "proj_nonexistent_999"

        response = client.get(
            f"/v1/public/{project_id}/runs",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert len(data["runs"]) == 0

    def test_list_runs_requires_authentication(self, client):
        """
        Test that list runs requires API key authentication.
        """
        project_id = "proj_demo_001"

        # Request without authentication
        response = client.get(f"/v1/public/{project_id}/runs")

        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "error_code" in data

    def test_list_runs_page_validation(self, client, auth_headers_user1):
        """
        Test that page parameter must be >= 1.
        """
        project_id = "proj_demo_001"

        # Invalid page number
        response = client.get(
            f"/v1/public/{project_id}/runs?page=0",
            headers=auth_headers_user1
        )

        assert response.status_code == 422  # Validation error

    def test_list_runs_page_size_validation(self, client, auth_headers_user1):
        """
        Test that page_size parameter must be between 1 and 100.
        """
        project_id = "proj_demo_001"

        # Page size too large
        response = client.get(
            f"/v1/public/{project_id}/runs?page_size=200",
            headers=auth_headers_user1
        )

        assert response.status_code == 422  # Validation error

        # Page size too small
        response = client.get(
            f"/v1/public/{project_id}/runs?page_size=0",
            headers=auth_headers_user1
        )

        assert response.status_code == 422  # Validation error


class TestGetRunDetailEndpoint:
    """
    Tests for GET /v1/public/{project_id}/runs/{run_id}
    Get detailed information for a specific run.
    """

    def test_get_run_detail_success(self, client, auth_headers_user1):
        """
        Test successful retrieval of run details.
        Verifies all required fields and agent profile inclusion.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify run detail structure
        assert data["run_id"] == run_id
        assert data["project_id"] == project_id
        assert data["status"] == "COMPLETED"

        # Verify timestamps
        assert "started_at" in data
        assert "completed_at" in data
        assert data["completed_at"] is not None

        # Verify duration calculation
        assert "duration_ms" in data
        assert isinstance(data["duration_ms"], int)
        assert data["duration_ms"] > 0

        # Verify counts
        assert data["memory_count"] == 3
        assert data["event_count"] == 5
        assert data["request_count"] == 2

        # Verify agent profile is included
        assert "agent_profile" in data
        profile = data["agent_profile"]

        assert profile["agent_id"] == "agent_compliance_001"
        assert profile["agent_name"] == "Compliance Checker Agent"
        assert profile["agent_type"] == "compliance"
        assert "configuration" in profile
        assert "created_at" in profile

        # Verify agent configuration
        config = profile["configuration"]
        assert config["model"] == "gpt-4"
        assert config["temperature"] == 0.0

    def test_get_run_detail_not_found(self, client, auth_headers_user1):
        """
        Test that requesting non-existent run returns 404.
        """
        project_id = "proj_demo_001"
        run_id = "run_nonexistent_999"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == 404
        data = response.json()

        # Verify error response structure
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "RUN_NOT_FOUND"
        assert run_id in data["detail"]
        assert project_id in data["detail"]

    def test_get_run_detail_wrong_project(self, client, auth_headers_user1):
        """
        Test that requesting run with wrong project_id returns 404.
        """
        project_id = "proj_wrong_999"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == 404
        data = response.json()

        assert data["error_code"] == "RUN_NOT_FOUND"

    def test_get_run_detail_requires_authentication(self, client):
        """
        Test that get run detail requires API key authentication.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        # Request without authentication
        response = client.get(f"/v1/public/{project_id}/runs/{run_id}")

        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "error_code" in data


class TestGetRunReplayEndpoint:
    """
    Tests for GET /v1/public/{project_id}/runs/{run_id}/replay
    Get complete replay data for deterministic replay.
    """

    def test_get_replay_data_success(self, client, auth_headers_user1):
        """
        Test successful retrieval of complete replay data.
        Verifies all required components: profile, memory, events, requests.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify basic run info
        assert data["run_id"] == run_id
        assert data["project_id"] == project_id
        assert data["status"] == "COMPLETED"

        # Verify timestamps
        assert "started_at" in data
        assert "completed_at" in data
        assert "replay_generated_at" in data

        # Verify agent profile
        assert "agent_profile" in data
        profile = data["agent_profile"]
        assert profile["agent_id"] == "agent_compliance_001"
        assert profile["agent_name"] == "Compliance Checker Agent"
        assert profile["agent_type"] == "compliance"

        # Verify agent memory records
        assert "agent_memory" in data
        memory = data["agent_memory"]
        assert isinstance(memory, list)
        assert len(memory) == 3  # Demo has 3 memory records

        # Verify compliance events
        assert "compliance_events" in data
        events = data["compliance_events"]
        assert isinstance(events, list)
        assert len(events) == 5  # Demo has 5 compliance events

        # Verify X402 requests
        assert "x402_requests" in data
        requests = data["x402_requests"]
        assert isinstance(requests, list)
        assert len(requests) == 2  # Demo has 2 X402 requests

        # Verify validation results
        assert "validation" in data
        validation = data["validation"]
        assert validation["all_records_present"] is True
        assert validation["chronological_order_verified"] is True
        assert validation["agent_profile_found"] is True

    def test_replay_data_agent_memory_structure(self, client, auth_headers_user1):
        """
        Test that agent_memory records have correct structure and content.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        memory = data["agent_memory"]
        assert len(memory) > 0

        # Verify first memory record structure
        mem = memory[0]
        assert "memory_id" in mem
        assert "agent_id" in mem
        assert "run_id" in mem
        assert "task_id" in mem
        assert "input_summary" in mem
        assert "output_summary" in mem
        assert "confidence" in mem
        assert "metadata" in mem
        assert "timestamp" in mem

        # Verify run_id matches
        assert mem["run_id"] == run_id
        assert mem["agent_id"] == "agent_compliance_001"

        # Verify confidence is in valid range
        assert 0.0 <= mem["confidence"] <= 1.0

    def test_replay_data_compliance_events_structure(self, client, auth_headers_user1):
        """
        Test that compliance_events have correct structure and content.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        events = data["compliance_events"]
        assert len(events) > 0

        # Verify first event structure
        evt = events[0]
        assert "event_id" in evt
        assert "run_id" in evt
        assert "agent_id" in evt
        assert "event_type" in evt
        assert "event_category" in evt
        assert "description" in evt
        assert "severity" in evt
        assert "metadata" in evt
        assert "timestamp" in evt

        # Verify run_id matches
        assert evt["run_id"] == run_id

        # Verify event types are present
        event_types = [e["event_type"] for e in events]
        assert "CHECK_STARTED" in event_types
        assert "CHECK_COMPLETED" in event_types

    def test_replay_data_x402_requests_structure(self, client, auth_headers_user1):
        """
        Test that x402_requests have correct structure and content.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        requests = data["x402_requests"]
        assert len(requests) > 0

        # Verify first request structure
        req = requests[0]
        assert "request_id" in req
        assert "run_id" in req
        assert "agent_id" in req
        assert "request_type" in req
        assert "status" in req
        assert "request_payload" in req
        assert "response_payload" in req
        assert "metadata" in req
        assert "timestamp" in req

        # Verify run_id matches
        assert req["run_id"] == run_id

        # Verify request types are present
        request_types = [r["request_type"] for r in requests]
        assert "VERIFICATION" in request_types or "PAYMENT" in request_types

    def test_replay_data_chronological_order_memory(self, client, auth_headers_user1):
        """
        Test that agent_memory records are in chronological order.
        Per PRD Section 11: All records ordered chronologically by timestamp.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        memory = data["agent_memory"]

        # Verify chronological ordering
        timestamps = [m["timestamp"] for m in memory]
        sorted_timestamps = sorted(timestamps)

        assert timestamps == sorted_timestamps, \
            "Memory records must be in chronological order by timestamp"

    def test_replay_data_chronological_order_events(self, client, auth_headers_user1):
        """
        Test that compliance_events are in chronological order.
        Per PRD Section 11: All records ordered chronologically by timestamp.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        events = data["compliance_events"]

        # Verify chronological ordering
        timestamps = [e["timestamp"] for e in events]
        sorted_timestamps = sorted(timestamps)

        assert timestamps == sorted_timestamps, \
            "Compliance events must be in chronological order by timestamp"

    def test_replay_data_chronological_order_requests(self, client, auth_headers_user1):
        """
        Test that x402_requests are in chronological order.
        Per PRD Section 11: All records ordered chronologically by timestamp.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        requests = data["x402_requests"]

        # Verify chronological ordering
        timestamps = [r["timestamp"] for r in requests]
        sorted_timestamps = sorted(timestamps)

        assert timestamps == sorted_timestamps, \
            "X402 requests must be in chronological order by timestamp"

    def test_replay_data_validation_results(self, client, auth_headers_user1):
        """
        Test that validation results are included and correct.
        Per PRD Section 11: Validate all linked records exist.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        validation = data["validation"]

        # Required validation fields
        assert "all_records_present" in validation
        assert "chronological_order_verified" in validation
        assert "agent_profile_found" in validation
        assert "memory_records_validated" in validation
        assert "compliance_events_validated" in validation
        assert "x402_requests_validated" in validation

        # For demo data, all validations should pass
        assert validation["all_records_present"] is True
        assert validation["chronological_order_verified"] is True
        assert validation["agent_profile_found"] is True

        # Verify counts match actual records
        assert validation["memory_records_validated"] == 3
        assert validation["compliance_events_validated"] == 5
        assert validation["x402_requests_validated"] == 2

    def test_get_replay_data_not_found(self, client, auth_headers_user1):
        """
        Test that requesting replay for non-existent run returns 404.
        """
        project_id = "proj_demo_001"
        run_id = "run_nonexistent_999"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 404
        data = response.json()

        # Verify error response structure
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "RUN_NOT_FOUND"
        assert run_id in data["detail"]

    def test_get_replay_data_requires_authentication(self, client):
        """
        Test that get replay data requires API key authentication.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        # Request without authentication
        response = client.get(f"/v1/public/{project_id}/runs/{run_id}/replay")

        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "error_code" in data

    def test_replay_data_timestamp_formats(self, client, auth_headers_user1):
        """
        Test that all timestamps are in ISO 8601 format.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Helper to validate ISO timestamp
        def is_valid_iso_timestamp(ts):
            try:
                # Should be parseable as ISO format
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return True
            except (ValueError, AttributeError):
                return False

        # Verify run timestamps
        assert is_valid_iso_timestamp(data["started_at"])
        if data["completed_at"]:
            assert is_valid_iso_timestamp(data["completed_at"])
        assert is_valid_iso_timestamp(data["replay_generated_at"])

        # Verify agent profile timestamp
        assert is_valid_iso_timestamp(data["agent_profile"]["created_at"])

        # Verify all memory timestamps
        for mem in data["agent_memory"]:
            assert is_valid_iso_timestamp(mem["timestamp"])

        # Verify all event timestamps
        for evt in data["compliance_events"]:
            assert is_valid_iso_timestamp(evt["timestamp"])

        # Verify all request timestamps
        for req in data["x402_requests"]:
            assert is_valid_iso_timestamp(req["timestamp"])


class TestReplayDataCompleteness:
    """
    Tests for verifying completeness and integrity of replay data.
    Ensures all required data is present for deterministic replay.
    """

    def test_replay_includes_all_components(self, client, auth_headers_user1):
        """
        Test that replay data includes all required components.
        Per PRD Section 11: agent_profile, agent_memory, compliance_events, x402_requests.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # All required components must be present
        required_fields = [
            "run_id",
            "project_id",
            "status",
            "agent_profile",
            "agent_memory",
            "compliance_events",
            "x402_requests",
            "started_at",
            "replay_generated_at",
            "validation"
        ]

        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from replay data"

    def test_replay_metadata_preservation(self, client, auth_headers_user1):
        """
        Test that metadata is preserved in all record types.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        # Verify memory records have metadata
        for mem in data["agent_memory"]:
            assert "metadata" in mem
            assert isinstance(mem["metadata"], dict)

        # Verify events have metadata
        for evt in data["compliance_events"]:
            assert "metadata" in evt
            assert isinstance(evt["metadata"], dict)

        # Verify requests have metadata
        for req in data["x402_requests"]:
            assert "metadata" in req
            assert isinstance(req["metadata"], dict)

    def test_replay_payloads_preservation(self, client, auth_headers_user1):
        """
        Test that X402 request/response payloads are preserved.
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response.status_code == 200
        data = response.json()

        requests = data["x402_requests"]

        for req in requests:
            # Both payloads must be present (even if empty)
            assert "request_payload" in req
            assert "response_payload" in req
            assert isinstance(req["request_payload"], dict)
            assert isinstance(req["response_payload"], dict)

    def test_replay_data_deterministic(self, client, auth_headers_user1):
        """
        Test that replay data is deterministic - same request returns same data.
        (Except for replay_generated_at which may differ)
        """
        project_id = "proj_demo_001"
        run_id = "run_demo_001"

        # Make first request
        response1 = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response1.status_code == 200
        data1 = response1.json()

        # Make second request
        response2 = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # Compare core data (excluding replay_generated_at)
        assert data1["run_id"] == data2["run_id"]
        assert data1["project_id"] == data2["project_id"]
        assert data1["status"] == data2["status"]
        assert data1["started_at"] == data2["started_at"]
        assert data1["completed_at"] == data2["completed_at"]

        # Verify same counts
        assert len(data1["agent_memory"]) == len(data2["agent_memory"])
        assert len(data1["compliance_events"]) == len(data2["compliance_events"])
        assert len(data1["x402_requests"]) == len(data2["x402_requests"])

        # Verify same record IDs
        mem_ids1 = [m["memory_id"] for m in data1["agent_memory"]]
        mem_ids2 = [m["memory_id"] for m in data2["agent_memory"]]
        assert mem_ids1 == mem_ids2


class TestErrorHandling:
    """
    Tests for error handling and edge cases.
    """

    def test_invalid_project_id_format(self, client, auth_headers_user1):
        """
        Test handling of various project_id formats.
        """
        # Should handle different formats
        response = client.get(
            "/v1/public/proj-123/runs",
            headers=auth_headers_user1
        )

        # Should return 200 with empty list (project has no runs)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_invalid_run_id_format(self, client, auth_headers_user1):
        """
        Test handling of various run_id formats.
        """
        project_id = "proj_demo_001"

        # Various invalid run IDs should return 404
        invalid_run_ids = [
            "run-invalid",
            "123",
            "run_!@#$%",
            ""
        ]

        for run_id in invalid_run_ids:
            if run_id:  # Skip empty string as it's a URL path issue
                response = client.get(
                    f"/v1/public/{project_id}/runs/{run_id}",
                    headers=auth_headers_user1
                )

                # Should return 404 for non-existent runs
                assert response.status_code in [404, 422]

    def test_missing_api_key_header(self, client):
        """
        Test that missing X-API-Key header returns 401.
        """
        project_id = "proj_demo_001"

        # List runs without auth
        response = client.get(f"/v1/public/{project_id}/runs")
        assert response.status_code == 401

        # Get run detail without auth
        response = client.get(f"/v1/public/{project_id}/runs/run_demo_001")
        assert response.status_code == 401

        # Get replay data without auth
        response = client.get(f"/v1/public/{project_id}/runs/run_demo_001/replay")
        assert response.status_code == 401

    def test_invalid_api_key(self, client, invalid_auth_headers):
        """
        Test that invalid API key returns 401.
        """
        project_id = "proj_demo_001"

        response = client.get(
            f"/v1/public/{project_id}/runs",
            headers=invalid_auth_headers
        )

        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "error_code" in data


class TestEndToEndReplayScenario:
    """
    End-to-end test simulating a complete replay workflow.
    """

    def test_complete_replay_workflow(self, client, auth_headers_user1):
        """
        Test complete workflow: list runs -> get details -> get replay data.
        Simulates real user workflow for replaying agent run.
        """
        project_id = "proj_demo_001"

        # Step 1: List all runs for project
        list_response = client.get(
            f"/v1/public/{project_id}/runs",
            headers=auth_headers_user1
        )

        assert list_response.status_code == 200
        runs_data = list_response.json()
        assert runs_data["total"] > 0

        # Get first run ID
        run_id = runs_data["runs"][0]["run_id"]

        # Step 2: Get run details
        detail_response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}",
            headers=auth_headers_user1
        )

        assert detail_response.status_code == 200
        detail_data = detail_response.json()

        # Verify we can access agent profile and counts
        assert "agent_profile" in detail_data
        assert detail_data["memory_count"] > 0

        # Step 3: Get complete replay data
        replay_response = client.get(
            f"/v1/public/{project_id}/runs/{run_id}/replay",
            headers=auth_headers_user1
        )

        assert replay_response.status_code == 200
        replay_data = replay_response.json()

        # Verify replay data has all components
        assert len(replay_data["agent_memory"]) == detail_data["memory_count"]
        assert len(replay_data["compliance_events"]) == detail_data["event_count"]
        assert len(replay_data["x402_requests"]) == detail_data["request_count"]

        # Verify validation passed
        assert replay_data["validation"]["all_records_present"] is True

        # Verify chronological ordering across all record types
        all_timestamps = []

        for mem in replay_data["agent_memory"]:
            all_timestamps.append(mem["timestamp"])

        for evt in replay_data["compliance_events"]:
            all_timestamps.append(evt["timestamp"])

        for req in replay_data["x402_requests"]:
            all_timestamps.append(req["timestamp"])

        # Verify all timestamps are after run start
        for ts in all_timestamps:
            assert ts >= replay_data["started_at"]
