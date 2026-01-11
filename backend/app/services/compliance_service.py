"""
Compliance Service for managing compliance events.
Implements Epic 12 Issue 3: Write outcomes to compliance_events.

Per PRD Section 6 (ZeroDB Integration):
- Store compliance events with full auditability
- Support filtering and querying of events
- Provide deterministic event IDs

For MVP: Uses in-memory storage simulation
For Production: Will use actual ZeroDB table storage
"""
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.errors import APIError
from app.schemas.compliance_events import (
    ComplianceEventType,
    ComplianceOutcome,
    ComplianceEventCreate,
    ComplianceEventResponse,
    ComplianceEventFilter
)


class ComplianceService:
    """
    Service for managing compliance events.

    Provides CRUD operations for compliance events with filtering
    and pagination support. Integrates with ZeroDB for persistence.

    For MVP: Uses in-memory storage
    For Production: Uses ZeroDB table storage via MCP
    """

    def __init__(self):
        """Initialize the compliance service."""
        # In-memory store for MVP (project_id -> event_id -> event_data)
        self._event_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def generate_event_id(self) -> str:
        """
        Generate a unique event ID.

        Per PRD Section 10 (Determinism):
        - IDs are unique and non-colliding
        - Format: evt_{uuid}

        Returns:
            str: Unique event identifier
        """
        return f"evt_{uuid.uuid4().hex[:16]}"

    def create_event(
        self,
        project_id: str,
        event_data: ComplianceEventCreate
    ) -> ComplianceEventResponse:
        """
        Create a new compliance event.

        Per Epic 12 Issue 3: Compliance agents write outcomes to compliance_events.

        Args:
            project_id: Project identifier
            event_data: Event data from request

        Returns:
            ComplianceEventResponse with full event data

        Raises:
            APIError: If event creation fails
        """
        # Generate unique event ID
        event_id = self.generate_event_id()

        # Generate timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Prepare event record
        event_record = {
            "event_id": event_id,
            "project_id": project_id,
            "agent_id": event_data.agent_id,
            "event_type": event_data.event_type.value,
            "outcome": event_data.outcome.value,
            "risk_score": event_data.risk_score,
            "details": event_data.details or {},
            "run_id": event_data.run_id,
            "timestamp": timestamp,
            "created_at": time.time()
        }

        # Initialize project store if needed
        if project_id not in self._event_store:
            self._event_store[project_id] = {}

        # Store event
        self._event_store[project_id][event_id] = event_record

        return ComplianceEventResponse(
            event_id=event_id,
            project_id=project_id,
            agent_id=event_data.agent_id,
            event_type=event_data.event_type,
            outcome=event_data.outcome,
            risk_score=event_data.risk_score,
            details=event_data.details or {},
            run_id=event_data.run_id,
            timestamp=timestamp
        )

    def get_event(
        self,
        project_id: str,
        event_id: str
    ) -> Optional[ComplianceEventResponse]:
        """
        Get a single compliance event by ID.

        Args:
            project_id: Project identifier
            event_id: Event identifier

        Returns:
            ComplianceEventResponse or None if not found
        """
        if project_id not in self._event_store:
            return None

        event_record = self._event_store[project_id].get(event_id)
        if not event_record:
            return None

        return ComplianceEventResponse(
            event_id=event_record["event_id"],
            project_id=event_record["project_id"],
            agent_id=event_record["agent_id"],
            event_type=ComplianceEventType(event_record["event_type"]),
            outcome=ComplianceOutcome(event_record["outcome"]),
            risk_score=event_record["risk_score"],
            details=event_record["details"],
            run_id=event_record["run_id"],
            timestamp=event_record["timestamp"]
        )

    def list_events(
        self,
        project_id: str,
        filters: ComplianceEventFilter
    ) -> Tuple[List[ComplianceEventResponse], int]:
        """
        List compliance events with filtering and pagination.

        Args:
            project_id: Project identifier
            filters: Filter parameters

        Returns:
            Tuple of (list of events, total count)
        """
        if project_id not in self._event_store:
            return [], 0

        # Get all events for project
        all_events = list(self._event_store[project_id].values())

        # Apply filters
        filtered_events = self._apply_filters(all_events, filters)

        # Sort by timestamp descending (most recent first)
        filtered_events.sort(key=lambda x: x["created_at"], reverse=True)

        # Get total count before pagination
        total = len(filtered_events)

        # Apply pagination
        paginated_events = filtered_events[filters.offset:filters.offset + filters.limit]

        # Convert to response objects
        response_events = [
            ComplianceEventResponse(
                event_id=event["event_id"],
                project_id=event["project_id"],
                agent_id=event["agent_id"],
                event_type=ComplianceEventType(event["event_type"]),
                outcome=ComplianceOutcome(event["outcome"]),
                risk_score=event["risk_score"],
                details=event["details"],
                run_id=event["run_id"],
                timestamp=event["timestamp"]
            )
            for event in paginated_events
        ]

        return response_events, total

    def _apply_filters(
        self,
        events: List[Dict[str, Any]],
        filters: ComplianceEventFilter
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to event list.

        Args:
            events: List of event records
            filters: Filter parameters

        Returns:
            Filtered list of events
        """
        result = events

        # Filter by agent_id
        if filters.agent_id:
            result = [e for e in result if e["agent_id"] == filters.agent_id]

        # Filter by event_type
        if filters.event_type:
            result = [e for e in result if e["event_type"] == filters.event_type.value]

        # Filter by outcome
        if filters.outcome:
            result = [e for e in result if e["outcome"] == filters.outcome.value]

        # Filter by run_id
        if filters.run_id:
            result = [e for e in result if e["run_id"] == filters.run_id]

        # Filter by min_risk_score
        if filters.min_risk_score is not None:
            result = [e for e in result if e["risk_score"] >= filters.min_risk_score]

        # Filter by max_risk_score
        if filters.max_risk_score is not None:
            result = [e for e in result if e["risk_score"] <= filters.max_risk_score]

        # Filter by start_time
        if filters.start_time:
            result = [e for e in result if e["timestamp"] >= filters.start_time]

        # Filter by end_time
        if filters.end_time:
            result = [e for e in result if e["timestamp"] <= filters.end_time]

        return result

    def delete_event(
        self,
        project_id: str,
        event_id: str
    ) -> bool:
        """
        Delete a compliance event.

        Args:
            project_id: Project identifier
            event_id: Event identifier

        Returns:
            True if deleted, False if not found
        """
        if project_id not in self._event_store:
            return False

        if event_id in self._event_store[project_id]:
            del self._event_store[project_id][event_id]
            return True

        return False

    def get_project_stats(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get compliance event statistics for a project.

        Args:
            project_id: Project identifier

        Returns:
            Dictionary with event statistics
        """
        if project_id not in self._event_store:
            return {
                "project_id": project_id,
                "total_events": 0,
                "events_by_type": {},
                "events_by_outcome": {},
                "average_risk_score": 0.0
            }

        events = list(self._event_store[project_id].values())

        # Count by type
        events_by_type = {}
        for event in events:
            event_type = event["event_type"]
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

        # Count by outcome
        events_by_outcome = {}
        for event in events:
            outcome = event["outcome"]
            events_by_outcome[outcome] = events_by_outcome.get(outcome, 0) + 1

        # Calculate average risk score
        if events:
            avg_risk = sum(e["risk_score"] for e in events) / len(events)
        else:
            avg_risk = 0.0

        return {
            "project_id": project_id,
            "total_events": len(events),
            "events_by_type": events_by_type,
            "events_by_outcome": events_by_outcome,
            "average_risk_score": round(avg_risk, 4)
        }


# Singleton instance
compliance_service = ComplianceService()
