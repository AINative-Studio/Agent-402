"""
Compliance Service for managing compliance events.
Implements Epic 12 Issue 3: Write outcomes to compliance_events.

Per PRD Section 6 (ZeroDB Integration):
- Store compliance events with full auditability
- Support filtering and querying of events
- Provide deterministic event IDs

Uses ZeroDB for persistence via the compliance_events table.
"""
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client
from app.schemas.compliance_events import (
    ComplianceEventType,
    ComplianceOutcome,
    ComplianceEventCreate,
    ComplianceEventResponse,
    ComplianceEventFilter
)

logger = logging.getLogger(__name__)

# Table name for compliance events
COMPLIANCE_EVENTS_TABLE = "compliance_events"


class ComplianceService:
    """
    Service for managing compliance events.

    Provides CRUD operations for compliance events with filtering
    and pagination support. Uses ZeroDB for persistence.
    """

    def __init__(self):
        """Initialize the compliance service."""
        # ZeroDB client will be retrieved lazily
        self._client = None

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    def _get_client(self):
        """Get the ZeroDB client singleton."""
        if self._client is None:
            self._client = None

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client
        return self._client

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

    async def create_event(
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

        # Prepare row data for ZeroDB
        # Note: Maps to compliance_events table schema
        row_data = {
            "event_id": event_id,
            "project_id": project_id,
            "agent_id": event_data.agent_id,
            "event_type": event_data.event_type.value,
            "action": event_data.outcome.value,  # Maps outcome to action column
            "risk_score": int(event_data.risk_score * 100),  # Scale to integer 0-100
            "risk_level": self._calculate_risk_level(event_data.risk_score),
            "passed": event_data.outcome == ComplianceOutcome.PASS,
            "details": json.dumps(event_data.details or {}),
            "run_id": event_data.run_id or "",
            "timestamp": timestamp,
            "created_at": timestamp
        }

        try:
            client = self._get_client()
            result = await client.insert_row(COMPLIANCE_EVENTS_TABLE, row_data)
            logger.info(f"Created compliance event {event_id} for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to create compliance event: {e}")
            raise APIError(
                message=f"Failed to create compliance event: {str(e)}",
                status_code=500,
                error_code="COMPLIANCE_EVENT_CREATE_FAILED"
            )

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

    def _calculate_risk_level(self, risk_score: float) -> str:
        """Calculate risk level from risk score."""
        if risk_score <= 0.25:
            return "low"
        elif risk_score <= 0.5:
            return "medium"
        elif risk_score <= 0.75:
            return "high"
        else:
            return "critical"

    async def get_event(
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
        try:
            client = self._get_client()
            # Query by event_id and project_id
            filter_query = {
                "event_id": {"$eq": event_id},
                "project_id": {"$eq": project_id}
            }
            result = await client.query_rows(COMPLIANCE_EVENTS_TABLE, filter_query, limit=1)

            rows = result.get("rows", [])
            if not rows:
                return None

            event_record = rows[0]
            return self._row_to_response(event_record)
        except Exception as e:
            logger.error(f"Failed to get compliance event {event_id}: {e}")
            return None

    def _row_to_response(self, row: Dict[str, Any]) -> ComplianceEventResponse:
        """Convert a database row to a ComplianceEventResponse."""
        # Parse details if it's a string
        details = row.get("details", {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except json.JSONDecodeError:
                details = {}

        # Convert risk_score back from integer (0-100) to float (0.0-1.0)
        risk_score = row.get("risk_score", 0)
        if isinstance(risk_score, int) and risk_score > 1:
            risk_score = risk_score / 100.0

        # Map action back to outcome
        action = row.get("action", "PASS")
        try:
            outcome = ComplianceOutcome(action)
        except ValueError:
            outcome = ComplianceOutcome.PASS

        # Map event_type
        event_type_str = row.get("event_type", "AUDIT_LOG")
        try:
            event_type = ComplianceEventType(event_type_str)
        except ValueError:
            event_type = ComplianceEventType.AUDIT_LOG

        return ComplianceEventResponse(
            event_id=row.get("event_id", ""),
            project_id=row.get("project_id", ""),
            agent_id=row.get("agent_id", ""),
            event_type=event_type,
            outcome=outcome,
            risk_score=risk_score,
            details=details,
            run_id=row.get("run_id") or None,
            timestamp=row.get("timestamp", "")
        )

    async def list_events(
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
        try:
            client = self._get_client()

            # Build MongoDB-style filter
            filter_query = self._build_filter_query(project_id, filters)

            # Query with pagination
            result = await client.query_rows(
                COMPLIANCE_EVENTS_TABLE,
                filter_query,
                limit=filters.limit,
                skip=filters.offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            # Convert to response objects
            response_events = [self._row_to_response(row) for row in rows]

            return response_events, total
        except Exception as e:
            logger.error(f"Failed to list compliance events: {e}")
            return [], 0

    def _build_filter_query(
        self,
        project_id: str,
        filters: ComplianceEventFilter
    ) -> Dict[str, Any]:
        """
        Build MongoDB-style filter query from ComplianceEventFilter.

        Args:
            project_id: Project identifier
            filters: Filter parameters

        Returns:
            MongoDB-style filter dictionary
        """
        query: Dict[str, Any] = {
            "project_id": {"$eq": project_id}
        }

        # Filter by agent_id
        if filters.agent_id:
            query["agent_id"] = {"$eq": filters.agent_id}

        # Filter by event_type
        if filters.event_type:
            query["event_type"] = {"$eq": filters.event_type.value}

        # Filter by outcome (maps to action column)
        if filters.outcome:
            query["action"] = {"$eq": filters.outcome.value}

        # Filter by run_id
        if filters.run_id:
            query["run_id"] = {"$eq": filters.run_id}

        # Filter by min_risk_score (convert to integer 0-100)
        if filters.min_risk_score is not None:
            min_score_int = int(filters.min_risk_score * 100)
            query["risk_score"] = query.get("risk_score", {})
            query["risk_score"]["$gte"] = min_score_int

        # Filter by max_risk_score (convert to integer 0-100)
        if filters.max_risk_score is not None:
            max_score_int = int(filters.max_risk_score * 100)
            if "risk_score" not in query:
                query["risk_score"] = {}
            query["risk_score"]["$lte"] = max_score_int

        # Filter by start_time
        if filters.start_time:
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$gte"] = filters.start_time

        # Filter by end_time
        if filters.end_time:
            if "timestamp" not in query:
                query["timestamp"] = {}
            query["timestamp"]["$lte"] = filters.end_time

        return query

    async def delete_event(
        self,
        project_id: str,
        event_id: str
    ) -> bool:
        """
        Delete a compliance event.

        Note: ZeroDB client doesn't have a direct delete_row_by_filter method.
        We query first to get the row_id, then delete by row_id.

        Args:
            project_id: Project identifier
            event_id: Event identifier

        Returns:
            True if deleted, False if not found
        """
        try:
            client = self._get_client()

            # First, find the row to get its row_id
            filter_query = {
                "event_id": {"$eq": event_id},
                "project_id": {"$eq": project_id}
            }
            result = await client.query_rows(COMPLIANCE_EVENTS_TABLE, filter_query, limit=1)

            rows = result.get("rows", [])
            if not rows:
                return False

            # Get the row_id (assuming the API returns it)
            row_id = rows[0].get("id") or rows[0].get("row_id")
            if not row_id:
                logger.warning(f"No row_id found for event {event_id}")
                return False

            # Delete the row
            await client.delete_row(COMPLIANCE_EVENTS_TABLE, str(row_id))
            logger.info(f"Deleted compliance event {event_id} for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete compliance event {event_id}: {e}")
            return False

    async def get_project_stats(
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
        try:
            client = self._get_client()

            # Get all events for the project (with a reasonable limit)
            filter_query = {"project_id": {"$eq": project_id}}
            result = await client.query_rows(
                COMPLIANCE_EVENTS_TABLE,
                filter_query,
                limit=10000  # Reasonable limit for stats
            )

            rows = result.get("rows", [])

            if not rows:
                return {
                    "project_id": project_id,
                    "total_events": 0,
                    "events_by_type": {},
                    "events_by_outcome": {},
                    "average_risk_score": 0.0
                }

            # Count by type
            events_by_type: Dict[str, int] = {}
            for row in rows:
                event_type = row.get("event_type", "UNKNOWN")
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            # Count by outcome (action column)
            events_by_outcome: Dict[str, int] = {}
            for row in rows:
                outcome = row.get("action", "UNKNOWN")
                events_by_outcome[outcome] = events_by_outcome.get(outcome, 0) + 1

            # Calculate average risk score
            risk_scores = []
            for row in rows:
                score = row.get("risk_score", 0)
                # Convert from integer (0-100) to float (0.0-1.0) if needed
                if isinstance(score, int) and score > 1:
                    score = score / 100.0
                risk_scores.append(score)

            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

            return {
                "project_id": project_id,
                "total_events": len(rows),
                "events_by_type": events_by_type,
                "events_by_outcome": events_by_outcome,
                "average_risk_score": round(avg_risk, 4)
            }
        except Exception as e:
            logger.error(f"Failed to get project stats for {project_id}: {e}")
            return {
                "project_id": project_id,
                "total_events": 0,
                "events_by_type": {},
                "events_by_outcome": {},
                "average_risk_score": 0.0
            }


# Singleton instance
compliance_service = ComplianceService()
