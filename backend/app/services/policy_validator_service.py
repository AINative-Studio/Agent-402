"""
Policy Validator Service — Issue #171

Policy schema validation, dry-run simulation, and policy diffing.

Supports policy types: spend_limit, interaction_whitelist, task_scope, data_access.

Returns: {valid: bool, errors: [], warnings: []}

Built by AINative Dev Team
Refs #171
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any

from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

SUPPORTED_POLICY_TYPES = {
    "spend_limit",
    "interaction_whitelist",
    "task_scope",
    "data_access",
}

# Spend limit thresholds (USD)
DAILY_LIMIT_WARNING_THRESHOLD = 100_000.0


class PolicyValidatorService:
    """
    Validates, dry-runs, and diffs governance policies.

    Validation checks:
    - Required fields presence (policy_type, rules)
    - Negative spend limits
    - Unusually high limits (warnings)
    - Unknown policy types
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    # ------------------------------------------------------------------ #
    # validate_policy
    # ------------------------------------------------------------------ #

    async def validate_policy(
        self, policy_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a policy dict for schema correctness and rule consistency.

        Args:
            policy_dict: Policy configuration to validate.

        Returns:
            Dict with valid (bool), errors (list), warnings (list).
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Required: policy_type
        policy_type = policy_dict.get("policy_type")
        if not policy_type:
            errors.append("Field 'policy_type' is required.")
        elif policy_type not in SUPPORTED_POLICY_TYPES:
            errors.append(
                f"Unknown policy_type '{policy_type}'. "
                f"Supported: {sorted(SUPPORTED_POLICY_TYPES)}"
            )

        # Required: rules
        rules = policy_dict.get("rules")
        if rules is None:
            errors.append("Field 'rules' is required.")
        elif not isinstance(rules, dict):
            errors.append("Field 'rules' must be a dict.")
        else:
            self._validate_rules(policy_type, rules, errors, warnings)

        valid = len(errors) == 0
        return {"valid": valid, "errors": errors, "warnings": warnings}

    def _validate_rules(
        self,
        policy_type: Optional[str],
        rules: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Validate rule-level constraints for a given policy type."""
        if policy_type == "spend_limit":
            daily = rules.get("daily_limit_usd")
            per_call = rules.get("per_call_limit_usd")

            if daily is not None:
                if not isinstance(daily, (int, float)):
                    errors.append("Rule 'daily_limit_usd' must be a number.")
                elif daily < 0:
                    errors.append(
                        "Rule 'daily_limit_usd' must be non-negative; "
                        f"got {daily}."
                    )
                elif daily > DAILY_LIMIT_WARNING_THRESHOLD:
                    warnings.append(
                        f"Rule 'daily_limit_usd' is unusually high ({daily}). "
                        "Verify this is intentional."
                    )

            if per_call is not None:
                if not isinstance(per_call, (int, float)):
                    errors.append("Rule 'per_call_limit_usd' must be a number.")
                elif per_call < 0:
                    errors.append(
                        "Rule 'per_call_limit_usd' must be non-negative; "
                        f"got {per_call}."
                    )

    # ------------------------------------------------------------------ #
    # dry_run_policy
    # ------------------------------------------------------------------ #

    async def dry_run_policy(
        self,
        policy_dict: Dict[str, Any],
        test_actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Simulate how a policy would evaluate a list of test actions.

        Args:
            policy_dict: Policy to simulate.
            test_actions: List of action dicts with 'action' and associated fields.

        Returns:
            Dict with results (per-action pass/fail+reason) and summary.
        """
        rules = policy_dict.get("rules", {})
        policy_type = policy_dict.get("policy_type", "")
        results: List[Dict[str, Any]] = []

        for action in test_actions:
            action_type = action.get("action", "unknown")
            result_entry = await self._evaluate_action(
                action_type, action, policy_type, rules
            )
            results.append(result_entry)

        passed = sum(1 for r in results if r["result"] == "pass")
        failed = sum(1 for r in results if r["result"] == "fail")

        return {
            "results": results,
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
            },
        }

    async def _evaluate_action(
        self,
        action_type: str,
        action: Dict[str, Any],
        policy_type: str,
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate a single action against policy rules."""
        if policy_type == "spend_limit" and action_type == "spend":
            amount = float(action.get("amount", 0.0))
            daily_limit = rules.get("daily_limit_usd")
            per_call_limit = rules.get("per_call_limit_usd")

            if daily_limit is not None and amount > daily_limit:
                return {
                    "action": action,
                    "result": "fail",
                    "reason": (
                        f"Amount ${amount:.2f} exceeds daily_limit_usd "
                        f"${daily_limit:.2f}."
                    ),
                }
            if per_call_limit is not None and amount > per_call_limit:
                return {
                    "action": action,
                    "result": "fail",
                    "reason": (
                        f"Amount ${amount:.2f} exceeds per_call_limit_usd "
                        f"${per_call_limit:.2f}."
                    ),
                }
            return {
                "action": action,
                "result": "pass",
                "reason": "Amount is within all configured limits.",
            }

        # Default: unknown action type or policy type — pass through
        return {
            "action": action,
            "result": "pass",
            "reason": f"No specific rule for action '{action_type}' under policy '{policy_type}'.",
        }

    # ------------------------------------------------------------------ #
    # diff_policies
    # ------------------------------------------------------------------ #

    async def diff_policies(
        self,
        policy_a: Dict[str, Any],
        policy_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare two policies and return a list of differences.

        Args:
            policy_a: Original policy.
            policy_b: New/modified policy.

        Returns:
            Dict with changes list. Each change: {field, change_type, old, new}.
        """
        changes: List[Dict[str, Any]] = []
        self._diff_dicts("", policy_a, policy_b, changes)
        return {"changes": changes}

    def _diff_dicts(
        self,
        prefix: str,
        a: Dict[str, Any],
        b: Dict[str, Any],
        changes: List[Dict[str, Any]],
    ) -> None:
        """Recursively diff two dicts, appending changes."""
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            full_key = f"{prefix}.{key}" if prefix else key
            in_a = key in a
            in_b = key in b

            if in_a and not in_b:
                changes.append({
                    "field": full_key,
                    "change_type": "removed",
                    "old": a[key],
                    "new": None,
                })
            elif in_b and not in_a:
                changes.append({
                    "field": full_key,
                    "change_type": "added",
                    "old": None,
                    "new": b[key],
                })
            elif isinstance(a[key], dict) and isinstance(b[key], dict):
                self._diff_dicts(full_key, a[key], b[key], changes)
            elif a[key] != b[key]:
                changes.append({
                    "field": full_key,
                    "change_type": "changed",
                    "old": a[key],
                    "new": b[key],
                })


policy_validator_service = PolicyValidatorService()
