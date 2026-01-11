"""
Comprehensive tests for Compliance Events API.
Tests Epic 12 Issue 3: Write outcomes to compliance_events.

Test Coverage:
- All endpoints: create, list, get single event
- All event types: KYC_CHECK, KYT_CHECK, RISK_ASSESSMENT, COMPLIANCE_DECISION, AUDIT_LOG
- All outcomes: PASS, FAIL, PENDING, ESCALATED, ERROR
- Filtering by agent_id, event_type, outcome, risk_score range
- Error cases: event not found, invalid event_type
- Authentication requirements
- Response schema validation
- Edge cases and boundary conditions
"""
import pytest
from fastapi import status


class TestCreateComplianceEvent:
    """Test suite for POST /v1/public/{project_id}/compliance-events."""

    def test_create_event_kyc_check_pass(self, client, auth_headers_user1):
        """
        Test creating a KYC_CHECK event with PASS outcome.
        Epic 12 Issue 3: Compliance agents write outcomes to compliance_events.
        """
        payload = {
            "agent_id": "kyc_agent_001",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.15,
            "details": {
                "customer_id": "cust_12345",
                "verification_method": "document",
                "documents_verified": ["passport", "utility_bill"]
            },
            "run_id": "run_abc123"
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "event_id" in data
        assert data["event_id"].startswith("evt_")
        assert data["project_id"] == "test_project_1"
        assert data["agent_id"] == "kyc_agent_001"
        assert data["event_type"] == "KYC_CHECK"
        assert data["outcome"] == "PASS"
        assert data["risk_score"] == 0.15
        assert data["details"] == payload["details"]
        assert data["run_id"] == "run_abc123"
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")  # ISO 8601 with UTC timezone

    def test_create_event_kyt_check_fail(self, client, auth_headers_user1):
        """Test creating a KYT_CHECK event with FAIL outcome."""
        payload = {
            "agent_id": "kyt_agent_002",
            "event_type": "KYT_CHECK",
            "outcome": "FAIL",
            "risk_score": 0.92,
            "details": {
                "transaction_id": "txn_98765",
                "suspicious_patterns": ["rapid_transfers", "round_amounts"],
                "flagged_countries": ["XX"]
            }
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["event_type"] == "KYT_CHECK"
        assert data["outcome"] == "FAIL"
        assert data["risk_score"] == 0.92

    def test_create_event_risk_assessment_pending(self, client, auth_headers_user1):
        """Test creating a RISK_ASSESSMENT event with PENDING outcome."""
        payload = {
            "agent_id": "risk_agent_003",
            "event_type": "RISK_ASSESSMENT",
            "outcome": "PENDING",
            "risk_score": 0.55,
            "details": {
                "assessment_id": "risk_001",
                "factors": ["high_value", "new_customer"],
                "requires_manual_review": True
            }
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["event_type"] == "RISK_ASSESSMENT"
        assert data["outcome"] == "PENDING"
        assert data["risk_score"] == 0.55

    def test_create_event_compliance_decision_escalated(self, client, auth_headers_user1):
        """Test creating a COMPLIANCE_DECISION event with ESCALATED outcome."""
        payload = {
            "agent_id": "decision_agent_004",
            "event_type": "COMPLIANCE_DECISION",
            "outcome": "ESCALATED",
            "risk_score": 0.78,
            "details": {
                "decision_id": "dec_456",
                "escalation_reason": "high_risk_profile",
                "assigned_to": "senior_analyst_02"
            },
            "run_id": "run_xyz789"
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["event_type"] == "COMPLIANCE_DECISION"
        assert data["outcome"] == "ESCALATED"
        assert data["risk_score"] == 0.78

    def test_create_event_audit_log_error(self, client, auth_headers_user1):
        """Test creating an AUDIT_LOG event with ERROR outcome."""
        payload = {
            "agent_id": "audit_agent_005",
            "event_type": "AUDIT_LOG",
            "outcome": "ERROR",
            "risk_score": 0.0,
            "details": {
                "error_code": "TIMEOUT",
                "error_message": "External API timeout",
                "retry_count": 3
            }
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["event_type"] == "AUDIT_LOG"
        assert data["outcome"] == "ERROR"
        assert data["risk_score"] == 0.0

    def test_create_event_minimal_payload(self, client, auth_headers_user1):
        """Test creating event with minimal required fields (no run_id, empty details)."""
        payload = {
            "agent_id": "minimal_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.25
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["agent_id"] == "minimal_agent"
        assert data["details"] == {}
        assert data["run_id"] is None

    def test_create_event_risk_score_boundary_min(self, client, auth_headers_user1):
        """Test creating event with minimum risk score (0.0)."""
        payload = {
            "agent_id": "boundary_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.0
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["risk_score"] == 0.0

    def test_create_event_risk_score_boundary_max(self, client, auth_headers_user1):
        """Test creating event with maximum risk score (1.0)."""
        payload = {
            "agent_id": "boundary_agent",
            "event_type": "KYT_CHECK",
            "outcome": "FAIL",
            "risk_score": 1.0
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["risk_score"] == 1.0

    def test_create_event_invalid_risk_score_negative(self, client, auth_headers_user1):
        """Test creating event with negative risk score returns 422."""
        payload = {
            "agent_id": "invalid_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": -0.1
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_invalid_risk_score_too_high(self, client, auth_headers_user1):
        """Test creating event with risk score > 1.0 returns 422."""
        payload = {
            "agent_id": "invalid_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 1.1
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_invalid_event_type(self, client, auth_headers_user1):
        """Test creating event with invalid event_type returns 422."""
        payload = {
            "agent_id": "test_agent",
            "event_type": "INVALID_TYPE",
            "outcome": "PASS",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_invalid_outcome(self, client, auth_headers_user1):
        """Test creating event with invalid outcome returns 422."""
        payload = {
            "agent_id": "test_agent",
            "event_type": "KYC_CHECK",
            "outcome": "INVALID_OUTCOME",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_empty_agent_id(self, client, auth_headers_user1):
        """Test creating event with empty agent_id returns 422."""
        payload = {
            "agent_id": "",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_whitespace_agent_id(self, client, auth_headers_user1):
        """Test creating event with whitespace-only agent_id returns 422."""
        payload = {
            "agent_id": "   ",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_empty_run_id(self, client, auth_headers_user1):
        """Test creating event with empty run_id returns 422."""
        payload = {
            "agent_id": "test_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.5,
            "run_id": ""
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_missing_required_fields(self, client, auth_headers_user1):
        """Test creating event without required fields returns 422."""
        payload = {
            "agent_id": "test_agent"
            # Missing event_type, outcome, risk_score
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_missing_api_key(self, client):
        """Test creating event without X-API-Key returns 401."""
        payload = {
            "agent_id": "test_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "INVALID_API_KEY"

    def test_create_event_invalid_api_key(self, client, invalid_auth_headers):
        """Test creating event with invalid API key returns 401."""
        payload = {
            "agent_id": "test_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.5
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_API_KEY"

    def test_create_event_response_schema(self, client, auth_headers_user1):
        """Test response schema matches documented contract."""
        payload = {
            "agent_id": "schema_test_agent",
            "event_type": "KYC_CHECK",
            "outcome": "PASS",
            "risk_score": 0.33,
            "details": {"test": "data"},
            "run_id": "run_123"
        }

        response = client.post(
            "/v1/public/test_project_1/compliance-events",
            json=payload,
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        # Verify all required fields
        expected_fields = {
            "event_id", "project_id", "agent_id", "event_type",
            "outcome", "risk_score", "details", "run_id", "timestamp"
        }
        assert set(data.keys()) == expected_fields

        # Verify field types
        assert isinstance(data["event_id"], str)
        assert isinstance(data["project_id"], str)
        assert isinstance(data["agent_id"], str)
        assert isinstance(data["event_type"], str)
        assert isinstance(data["outcome"], str)
        assert isinstance(data["risk_score"], (int, float))
        assert isinstance(data["details"], dict)
        assert isinstance(data["timestamp"], str)


class TestListComplianceEvents:
    """Test suite for GET /v1/public/{project_id}/compliance-events."""

    def setup_method(self):
        """Setup test events for each test."""
        # Events will be created in each test as needed

    def test_list_events_empty_project(self, client, auth_headers_user1):
        """Test listing events for project with no events."""
        response = client.get(
            "/v1/public/empty_project/compliance-events",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_list_events_multiple_events(self, client, auth_headers_user1):
        """Test listing multiple events."""
        # Create 3 events
        events_to_create = [
            {
                "agent_id": "agent_1",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.1
            },
            {
                "agent_id": "agent_2",
                "event_type": "KYT_CHECK",
                "outcome": "FAIL",
                "risk_score": 0.8
            },
            {
                "agent_id": "agent_3",
                "event_type": "RISK_ASSESSMENT",
                "outcome": "PENDING",
                "risk_score": 0.5
            }
        ]

        for event_payload in events_to_create:
            client.post(
                "/v1/public/test_list_project/compliance-events",
                json=event_payload,
                headers=auth_headers_user1
            )

        # List events
        response = client.get(
            "/v1/public/test_list_project/compliance-events",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3
        assert len(data["events"]) == 3

    def test_list_events_filter_by_agent_id(self, client, auth_headers_user1):
        """Test filtering events by agent_id."""
        # Create events with different agent_ids
        client.post(
            "/v1/public/filter_test_project/compliance-events",
            json={
                "agent_id": "agent_alpha",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.2
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/filter_test_project/compliance-events",
            json={
                "agent_id": "agent_beta",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.3
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/filter_test_project/compliance-events",
            json={
                "agent_id": "agent_alpha",
                "event_type": "KYT_CHECK",
                "outcome": "FAIL",
                "risk_score": 0.7
            },
            headers=auth_headers_user1
        )

        # Filter by agent_alpha
        response = client.get(
            "/v1/public/filter_test_project/compliance-events?agent_id=agent_alpha",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2
        for event in data["events"]:
            assert event["agent_id"] == "agent_alpha"

    def test_list_events_filter_by_event_type(self, client, auth_headers_user1):
        """Test filtering events by event_type."""
        # Create events with different types
        event_types = ["KYC_CHECK", "KYT_CHECK", "KYC_CHECK"]
        for event_type in event_types:
            client.post(
                "/v1/public/type_filter_project/compliance-events",
                json={
                    "agent_id": "test_agent",
                    "event_type": event_type,
                    "outcome": "PASS",
                    "risk_score": 0.3
                },
                headers=auth_headers_user1
            )

        # Filter by KYC_CHECK
        response = client.get(
            "/v1/public/type_filter_project/compliance-events?event_type=KYC_CHECK",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2
        for event in data["events"]:
            assert event["event_type"] == "KYC_CHECK"

    def test_list_events_filter_by_outcome(self, client, auth_headers_user1):
        """Test filtering events by outcome."""
        # Create events with different outcomes
        outcomes = ["PASS", "FAIL", "PASS", "PENDING"]
        for outcome in outcomes:
            client.post(
                "/v1/public/outcome_filter_project/compliance-events",
                json={
                    "agent_id": "test_agent",
                    "event_type": "KYC_CHECK",
                    "outcome": outcome,
                    "risk_score": 0.4
                },
                headers=auth_headers_user1
            )

        # Filter by PASS
        response = client.get(
            "/v1/public/outcome_filter_project/compliance-events?outcome=PASS",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2
        for event in data["events"]:
            assert event["outcome"] == "PASS"

    def test_list_events_filter_by_run_id(self, client, auth_headers_user1):
        """Test filtering events by run_id."""
        # Create events with different run_ids
        client.post(
            "/v1/public/run_filter_project/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.2,
                "run_id": "run_abc"
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/run_filter_project/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.3,
                "run_id": "run_xyz"
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/run_filter_project/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.4,
                "run_id": "run_abc"
            },
            headers=auth_headers_user1
        )

        # Filter by run_abc
        response = client.get(
            "/v1/public/run_filter_project/compliance-events?run_id=run_abc",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 2
        for event in data["events"]:
            assert event["run_id"] == "run_abc"

    def test_list_events_filter_by_min_risk_score(self, client, auth_headers_user1):
        """Test filtering events by minimum risk score."""
        # Create events with different risk scores
        risk_scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        for score in risk_scores:
            client.post(
                "/v1/public/risk_min_filter_project/compliance-events",
                json={
                    "agent_id": "test_agent",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": score
                },
                headers=auth_headers_user1
            )

        # Filter by min_risk_score >= 0.5
        response = client.get(
            "/v1/public/risk_min_filter_project/compliance-events?min_risk_score=0.5",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3
        for event in data["events"]:
            assert event["risk_score"] >= 0.5

    def test_list_events_filter_by_max_risk_score(self, client, auth_headers_user1):
        """Test filtering events by maximum risk score."""
        # Create events with different risk scores
        risk_scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        for score in risk_scores:
            client.post(
                "/v1/public/risk_max_filter_project/compliance-events",
                json={
                    "agent_id": "test_agent",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": score
                },
                headers=auth_headers_user1
            )

        # Filter by max_risk_score <= 0.5
        response = client.get(
            "/v1/public/risk_max_filter_project/compliance-events?max_risk_score=0.5",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3
        for event in data["events"]:
            assert event["risk_score"] <= 0.5

    def test_list_events_filter_by_risk_score_range(self, client, auth_headers_user1):
        """Test filtering events by risk score range (min and max)."""
        # Create events with different risk scores
        risk_scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        for score in risk_scores:
            client.post(
                "/v1/public/risk_range_filter_project/compliance-events",
                json={
                    "agent_id": "test_agent",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": score
                },
                headers=auth_headers_user1
            )

        # Filter by risk score range [0.3, 0.7]
        response = client.get(
            "/v1/public/risk_range_filter_project/compliance-events?min_risk_score=0.3&max_risk_score=0.7",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 3
        for event in data["events"]:
            assert 0.3 <= event["risk_score"] <= 0.7

    def test_list_events_filter_multiple_criteria(self, client, auth_headers_user1):
        """Test filtering events with multiple criteria."""
        # Create various events
        client.post(
            "/v1/public/multi_filter_project/compliance-events",
            json={
                "agent_id": "agent_1",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.2
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/multi_filter_project/compliance-events",
            json={
                "agent_id": "agent_1",
                "event_type": "KYC_CHECK",
                "outcome": "FAIL",
                "risk_score": 0.8
            },
            headers=auth_headers_user1
        )
        client.post(
            "/v1/public/multi_filter_project/compliance-events",
            json={
                "agent_id": "agent_2",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.3
            },
            headers=auth_headers_user1
        )

        # Filter by agent_1 + KYC_CHECK + PASS
        response = client.get(
            "/v1/public/multi_filter_project/compliance-events?agent_id=agent_1&event_type=KYC_CHECK&outcome=PASS",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        event = data["events"][0]
        assert event["agent_id"] == "agent_1"
        assert event["event_type"] == "KYC_CHECK"
        assert event["outcome"] == "PASS"

    def test_list_events_pagination_limit(self, client, auth_headers_user1):
        """Test pagination with custom limit."""
        # Create 5 events
        for i in range(5):
            client.post(
                "/v1/public/pagination_project/compliance-events",
                json={
                    "agent_id": f"agent_{i}",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": 0.1
                },
                headers=auth_headers_user1
            )

        # Request with limit=2
        response = client.get(
            "/v1/public/pagination_project/compliance-events?limit=2",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 5
        assert len(data["events"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_events_pagination_offset(self, client, auth_headers_user1):
        """Test pagination with offset."""
        # Create 5 events
        for i in range(5):
            client.post(
                "/v1/public/offset_project/compliance-events",
                json={
                    "agent_id": f"agent_{i}",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": 0.1
                },
                headers=auth_headers_user1
            )

        # Request with offset=2, limit=2
        response = client.get(
            "/v1/public/offset_project/compliance-events?limit=2&offset=2",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["total"] == 5
        assert len(data["events"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 2

    def test_list_events_pagination_limit_max(self, client, auth_headers_user1):
        """Test pagination limit cannot exceed 1000."""
        response = client.get(
            "/v1/public/test_project/compliance-events?limit=1001",
            headers=auth_headers_user1
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_events_pagination_limit_min(self, client, auth_headers_user1):
        """Test pagination limit cannot be less than 1."""
        response = client.get(
            "/v1/public/test_project/compliance-events?limit=0",
            headers=auth_headers_user1
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_events_pagination_offset_negative(self, client, auth_headers_user1):
        """Test pagination offset cannot be negative."""
        response = client.get(
            "/v1/public/test_project/compliance-events?offset=-1",
            headers=auth_headers_user1
        )

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_events_sorted_by_timestamp_descending(self, client, auth_headers_user1):
        """Test events are returned in descending order by timestamp (most recent first)."""
        # Create events with small delay to ensure different timestamps
        import time

        event_ids = []
        for i in range(3):
            response = client.post(
                "/v1/public/sort_project/compliance-events",
                json={
                    "agent_id": f"agent_{i}",
                    "event_type": "KYC_CHECK",
                    "outcome": "PASS",
                    "risk_score": 0.1
                },
                headers=auth_headers_user1
            )
            event_ids.append(response.json()["event_id"])
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # List events
        response = client.get(
            "/v1/public/sort_project/compliance-events",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["events"]) == 3

        # Events should be in reverse order (most recent first)
        assert data["events"][0]["event_id"] == event_ids[2]
        assert data["events"][1]["event_id"] == event_ids[1]
        assert data["events"][2]["event_id"] == event_ids[0]

    def test_list_events_missing_api_key(self, client):
        """Test listing events without X-API-Key returns 401."""
        response = client.get("/v1/public/test_project/compliance-events")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_API_KEY"

    def test_list_events_invalid_api_key(self, client, invalid_auth_headers):
        """Test listing events with invalid API key returns 401."""
        response = client.get(
            "/v1/public/test_project/compliance-events",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_API_KEY"

    def test_list_events_response_schema(self, client, auth_headers_user1):
        """Test response schema matches documented contract."""
        response = client.get(
            "/v1/public/test_project/compliance-events",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Verify top-level schema
        expected_fields = {"events", "total", "limit", "offset"}
        assert set(data.keys()) == expected_fields

        # Verify field types
        assert isinstance(data["events"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)


class TestGetComplianceEvent:
    """Test suite for GET /v1/public/{project_id}/compliance-events/{event_id}."""

    def test_get_event_success(self, client, auth_headers_user1):
        """Test getting a single event by ID."""
        # Create an event first
        create_response = client.post(
            "/v1/public/get_test_project/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.25,
                "details": {"test_data": "value"},
                "run_id": "run_123"
            },
            headers=auth_headers_user1
        )

        event_id = create_response.json()["event_id"]

        # Get the event
        response = client.get(
            f"/v1/public/get_test_project/compliance-events/{event_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["event_id"] == event_id
        assert data["project_id"] == "get_test_project"
        assert data["agent_id"] == "test_agent"
        assert data["event_type"] == "KYC_CHECK"
        assert data["outcome"] == "PASS"
        assert data["risk_score"] == 0.25
        assert data["details"] == {"test_data": "value"}
        assert data["run_id"] == "run_123"
        assert "timestamp" in data

    def test_get_event_not_found(self, client, auth_headers_user1):
        """Test getting non-existent event returns 404."""
        response = client.get(
            "/v1/public/test_project/compliance-events/evt_nonexistent123",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "EVENT_NOT_FOUND"
        assert "evt_nonexistent123" in data["detail"]

    def test_get_event_from_different_project(self, client, auth_headers_user1):
        """Test getting event from different project returns 404."""
        # Create event in project A
        create_response = client.post(
            "/v1/public/project_a/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "KYC_CHECK",
                "outcome": "PASS",
                "risk_score": 0.3
            },
            headers=auth_headers_user1
        )

        event_id = create_response.json()["event_id"]

        # Try to get it from project B
        response = client.get(
            f"/v1/public/project_b/compliance-events/{event_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_event_missing_api_key(self, client):
        """Test getting event without X-API-Key returns 401."""
        response = client.get(
            "/v1/public/test_project/compliance-events/evt_123"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_API_KEY"

    def test_get_event_invalid_api_key(self, client, invalid_auth_headers):
        """Test getting event with invalid API key returns 401."""
        response = client.get(
            "/v1/public/test_project/compliance-events/evt_123",
            headers=invalid_auth_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error_code"] == "INVALID_API_KEY"

    def test_get_event_response_schema(self, client, auth_headers_user1):
        """Test response schema matches documented contract."""
        # Create an event
        create_response = client.post(
            "/v1/public/schema_test_project/compliance-events",
            json={
                "agent_id": "schema_agent",
                "event_type": "RISK_ASSESSMENT",
                "outcome": "PENDING",
                "risk_score": 0.55,
                "details": {"key": "value"}
            },
            headers=auth_headers_user1
        )

        event_id = create_response.json()["event_id"]

        # Get the event
        response = client.get(
            f"/v1/public/schema_test_project/compliance-events/{event_id}",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Verify all required fields
        expected_fields = {
            "event_id", "project_id", "agent_id", "event_type",
            "outcome", "risk_score", "details", "run_id", "timestamp"
        }
        assert set(data.keys()) == expected_fields

        # Verify field types
        assert isinstance(data["event_id"], str)
        assert isinstance(data["project_id"], str)
        assert isinstance(data["agent_id"], str)
        assert isinstance(data["event_type"], str)
        assert isinstance(data["outcome"], str)
        assert isinstance(data["risk_score"], (int, float))
        assert isinstance(data["details"], dict)
        assert isinstance(data["timestamp"], str)


class TestComplianceEventsAllEventTypes:
    """Test all supported event types can be created and retrieved."""

    def test_all_event_types(self, client, auth_headers_user1):
        """Test creating events with all supported event types."""
        event_types = [
            "KYC_CHECK",
            "KYT_CHECK",
            "RISK_ASSESSMENT",
            "COMPLIANCE_DECISION",
            "AUDIT_LOG"
        ]

        for event_type in event_types:
            response = client.post(
                "/v1/public/all_types_project/compliance-events",
                json={
                    "agent_id": f"agent_{event_type}",
                    "event_type": event_type,
                    "outcome": "PASS",
                    "risk_score": 0.4
                },
                headers=auth_headers_user1
            )

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["event_type"] == event_type


class TestComplianceEventsAllOutcomes:
    """Test all supported outcomes can be created and retrieved."""

    def test_all_outcomes(self, client, auth_headers_user1):
        """Test creating events with all supported outcomes."""
        outcomes = ["PASS", "FAIL", "PENDING", "ESCALATED", "ERROR"]

        for outcome in outcomes:
            response = client.post(
                "/v1/public/all_outcomes_project/compliance-events",
                json={
                    "agent_id": f"agent_{outcome}",
                    "event_type": "KYC_CHECK",
                    "outcome": outcome,
                    "risk_score": 0.5
                },
                headers=auth_headers_user1
            )

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["outcome"] == outcome


class TestComplianceEventsErrorHandling:
    """Test error handling and edge cases."""

    def test_error_response_format(self, client, auth_headers_user1):
        """Test error responses follow DX Contract format."""
        # Trigger a 404 error
        response = client.get(
            "/v1/public/test_project/compliance-events/evt_nonexistent",
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        # Must have exactly detail and error_code per DX Contract
        assert "detail" in data
        assert "error_code" in data
        assert isinstance(data["detail"], str)
        assert isinstance(data["error_code"], str)

    def test_validation_error_format(self, client, auth_headers_user1):
        """Test validation errors return 422 with proper format."""
        # Send invalid data
        response = client.post(
            "/v1/public/test_project/compliance-events",
            json={
                "agent_id": "test_agent",
                "event_type": "INVALID_TYPE",
                "outcome": "PASS",
                "risk_score": 0.5
            },
            headers=auth_headers_user1
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "detail" in data
