"""
Governance Policy Service.
Manages agent self-governance policies and policy evaluation.

Issue #236: Agent Self-Governance Policies.

Supported policy types:
- spend_limit:           daily_limit_usd, per_call_limit_usd
- interaction_whitelist: allowed_dids
- task_scope:            allowed_tasks
- data_access:           allowed_tables, read_only

Built by AINative Dev Team
Refs #236
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

GOVERNANCE_POLICIES_TABLE = "governance_policies"

SUPPORTED_POLICY_TYPES = {
    "spend_limit",
    "interaction_whitelist",
    "task_scope",
    "data_access",
}


class GovernancePolicyService:
    """
    Creates, stores, and evaluates agent governance policies.

    Policies are persisted in ZeroDB and evaluated in-memory during
    agent action checks.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-init ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    async def create_policy(
        self,
        agent_did: str,
        policy_type: str,
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Define a governance policy for an agent.

        Args:
            agent_did: Agent DID that owns this policy
            policy_type: One of spend_limit, interaction_whitelist, task_scope, data_access
            rules: Policy-type-specific rule definitions

        Returns:
            Policy dict with policy_id

        Raises:
            ValueError: If policy_type is not supported
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(
                f"Unsupported policy type '{policy_type}'. "
                f"Supported: {sorted(SUPPORTED_POLICY_TYPES)}"
            )

        policy_id = f"pol_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        row = {
            "policy_id": policy_id,
            "agent_did": agent_did,
            "policy_type": policy_type,
            "rules": rules,
            "active": True,
            "created_at": now,
        }

        await self.client.insert_row(GOVERNANCE_POLICIES_TABLE, row)
        logger.info(
            f"Created policy {policy_id} ({policy_type}) for agent {agent_did}"
        )
        return self._policy_from_row(row)

    async def evaluate_policy(
        self,
        agent_did: str,
        action: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check whether an action is permitted under the agent's governance policies.

        When no policies exist for the agent, all actions are allowed.
        If any active policy blocks the action, the result is denied.

        Args:
            agent_did: Agent whose policies to evaluate
            action: Action identifier (e.g. 'spend', 'call_agent', 'execute_task')
            context: Contextual data used for rule evaluation

        Returns:
            Dict with allowed (bool), agent_did, action, violated_policies, reason
        """
        policies = await self.get_policies(agent_did)

        if not policies:
            return {
                "allowed": True,
                "agent_did": agent_did,
                "action": action,
                "violated_policies": [],
                "reason": "No governance policies defined — action allowed by default",
            }

        violated: List[str] = []

        for policy in policies:
            violation = self._check_policy(policy, action, context)
            if violation:
                violated.append(policy["policy_id"])

        allowed = len(violated) == 0
        return {
            "allowed": allowed,
            "agent_did": agent_did,
            "action": action,
            "violated_policies": violated,
            "reason": (
                "All policies passed"
                if allowed
                else f"Violated {len(violated)} policy/policies"
            ),
        }

    async def get_policies(self, agent_did: str) -> List[Dict[str, Any]]:
        """
        List all governance policies for an agent.

        Args:
            agent_did: Agent DID to look up

        Returns:
            List of policy dicts
        """
        result = await self.client.query_rows(
            GOVERNANCE_POLICIES_TABLE,
            filter={"agent_did": agent_did, "active": True},
            limit=1_000,
        )
        rows = result.get("rows", [])
        return [self._policy_from_row(r) for r in rows]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_policy(
        self,
        policy: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Evaluate a single policy against an action and context.

        Returns True if the policy is VIOLATED (action denied), False if allowed.
        """
        policy_type = policy.get("policy_type")
        rules = policy.get("rules") or {}

        if policy_type == "spend_limit":
            return self._check_spend_limit(rules, action, context)
        elif policy_type == "interaction_whitelist":
            return self._check_interaction_whitelist(rules, action, context)
        elif policy_type == "task_scope":
            return self._check_task_scope(rules, action, context)
        elif policy_type == "data_access":
            return self._check_data_access(rules, action, context)
        return False

    def _check_spend_limit(
        self,
        rules: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Violated if action is 'spend' and amount exceeds per_call_limit_usd."""
        if action != "spend":
            return False
        amount = context.get("amount_usd", 0.0)
        per_call_limit = rules.get("per_call_limit_usd")
        if per_call_limit is not None and amount > per_call_limit:
            return True
        daily_limit = rules.get("daily_limit_usd")
        if daily_limit is not None and amount > daily_limit:
            return True
        return False

    def _check_interaction_whitelist(
        self,
        rules: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Violated if action is 'call_agent' and target_did is not whitelisted."""
        if action != "call_agent":
            return False
        allowed_dids = rules.get("allowed_dids") or []
        target_did = context.get("target_did", "")
        return target_did not in allowed_dids

    def _check_task_scope(
        self,
        rules: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Violated if action is 'execute_task' and task is not in allowed_tasks."""
        if action != "execute_task":
            return False
        allowed_tasks = rules.get("allowed_tasks") or []
        task = context.get("task", "")
        return task not in allowed_tasks

    def _check_data_access(
        self,
        rules: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Violated if action is 'read_data' or 'write_data' and table not allowed."""
        if action not in ("read_data", "write_data"):
            return False
        allowed_tables = rules.get("allowed_tables") or []
        table = context.get("table", "")
        if table and table not in allowed_tables:
            return True
        if action == "write_data" and rules.get("read_only"):
            return True
        return False

    def _policy_from_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw ZeroDB row to a clean policy dict."""
        return {
            "policy_id": row.get("policy_id"),
            "agent_did": row.get("agent_did"),
            "policy_type": row.get("policy_type"),
            "rules": row.get("rules") or {},
            "active": row.get("active", True),
            "created_at": row.get("created_at", ""),
        }


governance_policy_service = GovernancePolicyService()
