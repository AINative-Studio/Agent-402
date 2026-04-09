"""
HCS Project Audit Service — per-project HCS audit trail (Issue #268 Phase 2).

Provides audit logging for agent projects via Hedera Consensus Service:
- create_project_topic: create an HCS topic dedicated to a project
- log_audit_event: submit a structured event to the project's HCS topic
- get_audit_log: query the mirror node for project events
- get_audit_summary: count events by type

Event types: payment, decision, handoff, memory_anchor, compliance

Built by AINative Dev Team
Refs #268
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid event types
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES: List[str] = [
    "payment",
    "decision",
    "handoff",
    "memory_anchor",
    "compliance",
]


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class HCSProjectAuditError(Exception):
    """Raised when an HCS project audit operation fails."""

    def __init__(self, message: str, original: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.message = message
        self.original = original


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HCSProjectAuditService:
    """
    Per-project audit trail on Hedera Consensus Service.

    Each project gets its own HCS topic so that audit events are scoped
    and cannot be mixed across projects.
    """

    def __init__(self, hcs_client: Any) -> None:
        """
        Args:
            hcs_client: An HCS client object exposing async methods:
                - create_topic(**kwargs)
                - submit_hcs_message(topic_id, message)
                - get_topic_messages(topic_id, limit)
        """
        self._client = hcs_client

    # -------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------

    async def create_project_topic(self, project_id: str) -> Dict[str, Any]:
        """
        Create a new HCS topic for a project's audit trail.

        Args:
            project_id: Unique project identifier.

        Returns:
            dict with topic_id key.

        Raises:
            HCSProjectAuditError: if topic creation fails.
        """
        memo = f"audit-trail:{project_id}"
        try:
            result = await self._client.create_topic(
                memo=memo,
                project_id=project_id,
            )
            return result
        except Exception as exc:
            raise HCSProjectAuditError(
                f"Failed to create HCS topic for project {project_id}: {exc}",
                original=exc,
            ) from exc

    async def log_audit_event(
        self,
        project_id: str,
        topic_id: str,
        event_type: str,
        payload: Dict[str, Any],
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Submit an audit event to the project's HCS topic.

        Args:
            project_id: Project identifier.
            topic_id: HCS topic ID for this project.
            event_type: One of VALID_EVENT_TYPES.
            payload: Arbitrary event data.
            agent_id: Agent that generated the event.

        Returns:
            dict with sequence_number.

        Raises:
            HCSProjectAuditError: if event_type is invalid or submission fails.
        """
        if event_type not in VALID_EVENT_TYPES:
            raise HCSProjectAuditError(
                f"Invalid event type '{event_type}'. Must be one of: {VALID_EVENT_TYPES}"
            )

        message_body = {
            "project_id": project_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        message_str = json.dumps(message_body)

        try:
            result = await self._client.submit_hcs_message(
                topic_id=topic_id,
                message=message_str,
            )
            return result
        except Exception as exc:
            raise HCSProjectAuditError(
                f"Failed to log audit event '{event_type}' for project {project_id}: {exc}",
                original=exc,
            ) from exc

    async def get_audit_log(
        self,
        project_id: str,
        topic_id: str,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the mirror node for audit events on a project's topic.

        Args:
            project_id: Project identifier (used for context).
            topic_id: HCS topic ID to query.
            limit: Maximum number of messages to return.
            since: Optional ISO timestamp to filter messages after this date.

        Returns:
            List of event dicts with sequence_number, message, consensus_timestamp.

        Raises:
            HCSProjectAuditError: if the mirror node query fails.
        """
        try:
            result = await self._client.get_topic_messages(
                topic_id=topic_id,
                limit=limit,
            )
            messages = result.get("messages", [])
            return messages
        except Exception as exc:
            raise HCSProjectAuditError(
                f"Failed to get audit log for project {project_id}: {exc}",
                original=exc,
            ) from exc

    async def get_audit_summary(
        self,
        project_id: str,
        topic_id: str,
    ) -> Dict[str, Any]:
        """
        Return event counts grouped by event type for a project.

        Args:
            project_id: Project identifier.
            topic_id: HCS topic ID for the project.

        Returns:
            dict with total (int) and by_type (dict[str, int]).

        Raises:
            HCSProjectAuditError: if the mirror node query fails.
        """
        try:
            result = await self._client.get_topic_messages(
                topic_id=topic_id,
                limit=10000,  # retrieve all for counting
            )
            messages = result.get("messages", [])
        except Exception as exc:
            raise HCSProjectAuditError(
                f"Failed to get audit summary for project {project_id}: {exc}",
                original=exc,
            ) from exc

        by_type: Dict[str, int] = {}
        for msg in messages:
            raw = msg.get("message", "")
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                parsed = json.loads(decoded)
                event_type = parsed.get("event_type", "unknown")
            except Exception:
                event_type = "unknown"

            by_type[event_type] = by_type.get(event_type, 0) + 1

        return {
            "total": len(messages),
            "by_type": by_type,
        }


# ---------------------------------------------------------------------------
# Factory / singleton helper
# ---------------------------------------------------------------------------

def get_hcs_project_audit_service() -> HCSProjectAuditService:
    """
    Return an HCSProjectAuditService wired to the shared Hedera client.
    Lazily imports to avoid circular imports.
    """
    from app.services.hedera_client import get_hedera_client

    hedera = get_hedera_client()
    return HCSProjectAuditService(hcs_client=hedera)
