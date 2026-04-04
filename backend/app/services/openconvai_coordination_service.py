"""
OpenConvAI HCS-10 Coordination Service.

Issue #205: CrewAI Multi-Agent Coordination via HCS-10.

Provides:
- coordinate_workflow  — orchestrate Analyst→Compliance→Transaction via HCS-10
- submit_stage_result  — record stage completion and broadcast result
- get_workflow_status  — retrieve status of all stages

Stage progression: analyst_review → compliance_check → transaction_execute

Built by AINative Dev Team
Refs #205
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Canonical stage order for the standard workflow
CANONICAL_STAGES = ["analyst_review", "compliance_check", "transaction_execute"]


class OpenConvAICoordinationService:
    """
    Orchestrates CrewAI multi-agent workflows via HCS-10 messages.

    Maintains in-memory workflow state keyed by workflow_id. Each stage
    starts as "pending" and transitions to "completed" via submit_stage_result.
    Every state transition sends an HCS-10 coordination message.
    """

    def __init__(self, messaging_service: Any = None):
        """
        Initialise the coordination service.

        Args:
            messaging_service: OpenConvAIMessagingService instance (injected
                               for testability). If None, a default is created.
        """
        if messaging_service is not None:
            self._messaging = messaging_service
        else:
            from app.services.openconvai_messaging_service import (
                get_openconvai_messaging_service,
            )
            self._messaging = get_openconvai_messaging_service()

        # In-memory workflow store: workflow_id -> WorkflowRecord
        self._workflows: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def coordinate_workflow(
        self,
        workflow_id: str,
        stages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Initialise and orchestrate a multi-agent workflow via HCS-10.

        Creates a workflow record, marks every stage as "pending", and
        broadcasts a coordination message to each stage's agent_did.

        Args:
            workflow_id: Unique workflow identifier.
            stages:      Ordered list of stage definitions, each with:
                           name, agent_did, inputs.

        Returns:
            WorkflowStatus dict with workflow_id, status, and stages map.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build initial stage map
        stages_map: Dict[str, Any] = {}
        for stage in stages:
            stage_name = stage["name"]
            stages_map[stage_name] = {
                "status": "pending",
                "agent_did": stage.get("agent_did"),
                "inputs": stage.get("inputs", {}),
                "result": None,
                "completed_at": None,
            }

        # Persist workflow record
        record: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "status": "initiated",
            "stages": stages_map,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        self._workflows[workflow_id] = record

        # Broadcast a coordination message to each stage agent
        for stage in stages:
            await self._messaging.send_message(
                sender_did="did:hedera:testnet:orchestrator",
                recipient_did=stage.get("agent_did", "did:hedera:testnet:unknown"),
                message_type="coordination",
                payload={
                    "action": "stage_assigned",
                    "workflow_id": workflow_id,
                    "stage_name": stage["name"],
                    "inputs": stage.get("inputs", {}),
                },
                conversation_id=f"wf-{workflow_id}",
            )

        logger.info(
            "Workflow initiated",
            extra={"workflow_id": workflow_id, "stage_count": len(stages)},
        )

        return {
            "workflow_id": record["workflow_id"],
            "status": record["status"],
            "stages": record["stages"],
            "created_at": record["created_at"],
        }

    async def submit_stage_result(
        self,
        workflow_id: str,
        stage_name: str,
        agent_did: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Record the completion of a workflow stage.

        Updates the stage status to "completed", persists the result, and
        broadcasts an HCS-10 coordination message to announce completion.

        Args:
            workflow_id:  Parent workflow identifier.
            stage_name:   Name of the stage that finished.
            agent_did:    DID of the agent that completed the stage.
            result:       Output produced by the stage.

        Returns:
            StageResult dict with stage_name, status, and result.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        timestamp = datetime.now(timezone.utc).isoformat()
        workflow = self._workflows[workflow_id]

        if stage_name not in workflow["stages"]:
            raise ValueError(
                f"Stage '{stage_name}' not found in workflow '{workflow_id}'"
            )

        # Mark stage complete
        workflow["stages"][stage_name].update(
            {
                "status": "completed",
                "result": result,
                "completed_at": timestamp,
            }
        )
        workflow["updated_at"] = timestamp

        # Check if all stages are complete and advance workflow status
        all_done = all(
            s["status"] == "completed"
            for s in workflow["stages"].values()
        )
        if all_done:
            workflow["status"] = "completed"

        # Broadcast stage completion message
        await self._messaging.send_message(
            sender_did=agent_did,
            recipient_did="did:hedera:testnet:orchestrator",
            message_type="coordination",
            payload={
                "action": "stage_completed",
                "workflow_id": workflow_id,
                "stage_name": stage_name,
                "result": result,
            },
            conversation_id=f"wf-{workflow_id}",
        )

        logger.info(
            "Stage result submitted",
            extra={
                "workflow_id": workflow_id,
                "stage_name": stage_name,
                "agent_did": agent_did,
            },
        )

        return {
            "workflow_id": workflow_id,
            "stage_name": stage_name,
            "agent_did": agent_did,
            "result": result,
            "status": "completed",
            "completed_at": timestamp,
        }

    async def get_workflow_status(
        self, workflow_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve the current status of a workflow and all its stages.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            WorkflowStatus dict.

        Raises:
            ValueError: If the workflow_id is unknown.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        record = self._workflows[workflow_id]
        return {
            "workflow_id": record["workflow_id"],
            "status": record["status"],
            "stages": record["stages"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_coordination_service: Optional[OpenConvAICoordinationService] = None


def get_openconvai_coordination_service() -> OpenConvAICoordinationService:
    """Return the shared OpenConvAICoordinationService singleton."""
    global _coordination_service
    if _coordination_service is None:
        _coordination_service = OpenConvAICoordinationService()
    return _coordination_service
