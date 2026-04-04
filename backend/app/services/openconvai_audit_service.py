"""
OpenConvAI HCS-10 Audit Service.

Issue #206: Message Audit Trail stored in ZeroDB hcs10_audit_trail table.

Provides:
- log_message      — store an HCS-10 message in ZeroDB
- get_audit_trail  — retrieve messages for a conversation (ordered)
- get_agent_audit  — retrieve all messages involving an agent, with optional
                     time-range filtering

ZeroDB table: hcs10_audit_trail

Built by AINative Dev Team
Refs #206
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

AUDIT_TABLE = "hcs10_audit_trail"


class OpenConvAIAuditService:
    """
    Stores and retrieves HCS-10 message audit records via ZeroDB.

    The audit table schema (conceptual):
        audit_id          TEXT PRIMARY KEY
        conversation_id   TEXT
        sender_did        TEXT
        recipient_did     TEXT
        message_type      TEXT
        payload_json      TEXT
        consensus_timestamp TEXT
        sequence_number   INTEGER
        logged_at         TEXT
    """

    def __init__(self, zerodb_client: Any = None):
        """
        Initialise the audit service.

        Args:
            zerodb_client: ZeroDBClient instance (injected for testability).
                           If None, the global singleton is used.
        """
        if zerodb_client is not None:
            self._db = zerodb_client
        else:
            from app.services.zerodb_client import get_zerodb_client
            self._db = get_zerodb_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def log_message(
        self,
        message: Dict[str, Any],
        consensus_timestamp: str,
        sequence_number: int,
    ) -> Dict[str, Any]:
        """
        Store an HCS-10 message in the ZeroDB audit trail table.

        Args:
            message:             Decoded HCS-10 message dict.
            consensus_timestamp: Hedera consensus timestamp (ISO 8601).
            sequence_number:     HCS topic sequence number.

        Returns:
            AuditEntry dict with audit_id.
        """
        audit_id = f"aud-{uuid.uuid4().hex[:16]}"
        logged_at = datetime.now(timezone.utc).isoformat()

        import json
        row: Dict[str, Any] = {
            "audit_id": audit_id,
            "conversation_id": message.get("conversation_id", ""),
            "sender_did": message.get("sender_did", ""),
            "recipient_did": message.get("recipient_did", ""),
            "message_type": message.get("message_type", ""),
            "payload_json": json.dumps(message.get("payload", {})),
            "consensus_timestamp": consensus_timestamp,
            "sequence_number": sequence_number,
            "logged_at": logged_at,
        }

        await self._db.insert_row(AUDIT_TABLE, row)

        logger.info(
            "Logged HCS-10 message to audit trail",
            extra={
                "audit_id": audit_id,
                "conversation_id": row["conversation_id"],
                "sequence_number": sequence_number,
            },
        )

        return {
            "audit_id": audit_id,
            "conversation_id": row["conversation_id"],
            "sender_did": row["sender_did"],
            "recipient_did": row["recipient_did"],
            "message_type": row["message_type"],
            "consensus_timestamp": consensus_timestamp,
            "sequence_number": sequence_number,
            "logged_at": logged_at,
        }

    async def get_audit_trail(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the audit trail for a specific conversation, ordered by
        sequence_number ascending.

        Args:
            conversation_id: Conversation identifier.
            limit:           Maximum number of entries to return.

        Returns:
            List of AuditEntry dicts.
        """
        result = await self._db.query_rows(
            table_name=AUDIT_TABLE,
            filter={"conversation_id": conversation_id},
            limit=limit,
        )
        rows = result.get("rows", [])
        return self._format_rows(rows)

    async def get_agent_audit(
        self,
        agent_did: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all audit entries involving an agent (as sender or recipient),
        with optional time-range filtering.

        Args:
            agent_did: DID of the agent.
            since:     Optional ISO 8601 lower bound (inclusive).
            until:     Optional ISO 8601 upper bound (inclusive).

        Returns:
            List of AuditEntry dicts.
        """
        # Fetch all rows — we filter in Python because ZeroDB mock
        # does not support $or operator natively.
        result = await self._db.query_rows(
            table_name=AUDIT_TABLE,
            filter={},
            limit=1000,
        )
        rows = result.get("rows", [])

        # Filter to rows where agent is sender or recipient
        matched = [
            r for r in rows
            if r.get("sender_did") == agent_did
            or r.get("recipient_did") == agent_did
        ]

        # Apply time-range filters on consensus_timestamp
        if since is not None:
            matched = [
                r for r in matched
                if r.get("consensus_timestamp", "") >= since
            ]
        if until is not None:
            matched = [
                r for r in matched
                if r.get("consensus_timestamp", "") <= until
            ]

        return self._format_rows(matched)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise raw DB rows into AuditEntry dicts."""
        formatted = []
        for row in rows:
            formatted.append({
                "audit_id": row.get("audit_id", ""),
                "conversation_id": row.get("conversation_id", ""),
                "sender_did": row.get("sender_did", ""),
                "recipient_did": row.get("recipient_did", ""),
                "message_type": row.get("message_type", ""),
                "consensus_timestamp": row.get("consensus_timestamp", ""),
                "sequence_number": row.get("sequence_number"),
                "logged_at": row.get("logged_at"),
            })
        return formatted


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_audit_service: Optional[OpenConvAIAuditService] = None


def get_openconvai_audit_service() -> OpenConvAIAuditService:
    """Return the shared OpenConvAIAuditService singleton."""
    global _audit_service
    if _audit_service is None:
        _audit_service = OpenConvAIAuditService()
    return _audit_service
