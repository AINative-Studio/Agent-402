"""
Event service layer - Business logic for event operations.

Implements event storage for audit trails and system tracking.
Per PRD §6 (ZeroDB Integration) and §10 (Success Criteria - Replayability).
"""
from datetime import datetime
from typing import Dict, List
from uuid import UUID, uuid4

from app.models.event import EventCreate, EventResponse


class EventService:
    """
    Service layer for event operations.

    Implements event storage for audit trails, compliance tracking,
    and agent workflow replayability.

    In production, this would interface with ZeroDB tables or event streams.
    For MVP, uses in-memory storage to demonstrate functionality.
    """

    def __init__(self):
        # In-memory storage: event_id -> event
        # In production, this would be replaced with ZeroDB event stream or tables
        self._events: Dict[UUID, EventResponse] = {}
        # Index by user for multi-tenancy
        self._user_events: Dict[str, List[UUID]] = {}

    def create_event(self, user_id: str, event_data: EventCreate) -> EventResponse:
        """
        Create a new event for audit trail and system tracking.

        Per PRD §6: Events support compliance auditability and workflow replay.
        Per PRD §10: Events are append-only for non-repudiation.

        Args:
            user_id: User identifier (from API key)
            event_data: Event creation data

        Returns:
            Created event with generated ID and timestamps
        """
        # Generate event ID
        event_id = uuid4()

        # Use provided timestamp or default to current time
        event_timestamp = event_data.timestamp if event_data.timestamp else datetime.utcnow().isoformat() + "Z"

        # Create the event response
        event = EventResponse(
            id=event_id,
            event_type=event_data.event_type,
            data=event_data.data,
            timestamp=event_timestamp,
            created_at=datetime.utcnow()
        )

        # Store the event (append-only)
        self._events[event_id] = event

        # Index by user
        if user_id not in self._user_events:
            self._user_events[user_id] = []
        self._user_events[user_id].append(event_id)

        return event

    def get_event(self, user_id: str, event_id: UUID) -> EventResponse | None:
        """
        Get a specific event by ID.

        Args:
            user_id: User identifier
            event_id: Event identifier

        Returns:
            Event if found and owned by user, None otherwise
        """
        # Check if event exists and belongs to user
        if event_id not in self._events:
            return None

        user_event_ids = self._user_events.get(user_id, [])
        if event_id not in user_event_ids:
            return None

        return self._events[event_id]

    def list_events(
        self,
        user_id: str,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[EventResponse], int]:
        """
        List events for a user with optional filtering.

        Args:
            user_id: User identifier
            event_type: Optional event type filter
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            Tuple of (events list, total count)
        """
        # Get user's event IDs
        user_event_ids = self._user_events.get(user_id, [])

        # Get events
        events = [self._events[eid] for eid in user_event_ids if eid in self._events]

        # Filter by event type if specified
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Sort by created_at descending (newest first)
        events.sort(key=lambda e: e.created_at, reverse=True)

        total = len(events)

        # Apply pagination
        start = offset
        end = offset + limit
        paginated = events[start:end]

        return paginated, total

    def count_events(self, user_id: str, event_type: str | None = None) -> int:
        """
        Count events for a user with optional filtering.

        Args:
            user_id: User identifier
            event_type: Optional event type filter

        Returns:
            Number of events
        """
        user_event_ids = self._user_events.get(user_id, [])
        events = [self._events[eid] for eid in user_event_ids if eid in self._events]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return len(events)


# Global service instance
event_service = EventService()
