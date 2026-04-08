"""
Decision Logger Service — Issue #163

Contextual logging for agent decisions persisted to ZeroDB.

Decision types:
- task_selection
- payment_approval
- compliance_check
- memory_recall
- agent_selection

Built by AINative Dev Team
Refs #163
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

DECISIONS_TABLE = "agent_decisions"

VALID_DECISION_TYPES = {
    "task_selection",
    "payment_approval",
    "compliance_check",
    "memory_recall",
    "agent_selection",
}


class DecisionLoggerService:
    """
    Persists and retrieves structured agent decision logs.

    Each decision is stored as a row in ZeroDB with full context,
    outcome, confidence score, and reasoning chain.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    async def log_decision(
        self,
        agent_id: str,
        decision_type: str,
        context: Dict[str, Any],
        outcome: str,
        confidence: float,
        reasoning: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log a structured agent decision to ZeroDB.

        Args:
            agent_id: Identifier of the agent making the decision.
            decision_type: One of the defined decision type constants.
            context: Contextual data at time of decision.
            outcome: The decision outcome.
            confidence: Confidence score [0.0, 1.0].
            reasoning: Human-readable reasoning chain.
            run_id: Optional run identifier for grouping decisions.

        Returns:
            The stored decision log record.
        """
        log_id = f"log-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract run_id from context if not supplied directly
        effective_run_id = run_id or context.get("run_id")

        row_data: Dict[str, Any] = {
            "log_id": log_id,
            "agent_id": agent_id,
            "decision_type": decision_type,
            "context": context,
            "outcome": outcome,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": timestamp,
            "run_id": effective_run_id,
        }

        await self.client.insert_row(DECISIONS_TABLE, row_data)

        return row_data

    async def get_decision_history(
        self,
        agent_id: str,
        decision_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve paginated decision history for an agent.

        Args:
            agent_id: Agent to query.
            decision_type: Optional filter by decision type.
            limit: Maximum number of records to return.

        Returns:
            List of decision log records ordered by timestamp descending.
        """
        query_filter: Dict[str, Any] = {"agent_id": agent_id}
        if decision_type:
            query_filter["decision_type"] = decision_type

        result = await self.client.query_rows(
            DECISIONS_TABLE,
            filter=query_filter,
            limit=limit,
        )

        rows: List[Dict[str, Any]] = result.get("rows", [])
        # Sort descending by timestamp
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return rows

    async def get_decision_chain(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all decisions belonging to a specific run, ordered chronologically.

        Args:
            run_id: Run identifier.

        Returns:
            Ordered list of decision log records for the run.
        """
        result = await self.client.query_rows(
            DECISIONS_TABLE,
            filter={"run_id": run_id},
            limit=1000,
        )

        rows: List[Dict[str, Any]] = result.get("rows", [])
        rows.sort(key=lambda r: r.get("timestamp", ""))
        return rows


decision_logger_service = DecisionLoggerService()
