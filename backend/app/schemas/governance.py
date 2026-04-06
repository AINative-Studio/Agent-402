"""
Governance policy API schemas.

Issue #236: Agent Self-Governance Policies.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyType(str, Enum):
    """Supported governance policy types."""

    SPEND_LIMIT = "spend_limit"
    INTERACTION_WHITELIST = "interaction_whitelist"
    TASK_SCOPE = "task_scope"
    DATA_ACCESS = "data_access"


class CreatePolicyRequest(BaseModel):
    """Request body for creating a governance policy."""

    agent_did: str
    policy_type: PolicyType
    rules: Dict[str, Any] = Field(description="Policy-type-specific rule definitions")


class PolicyResponse(BaseModel):
    """Response representing a governance policy."""

    policy_id: str
    agent_did: str
    policy_type: str
    rules: Dict[str, Any]
    created_at: str
    active: bool


class EvaluatePolicyRequest(BaseModel):
    """Request body for evaluating whether an action is permitted."""

    agent_did: str
    action: str = Field(description="Action identifier (e.g. 'spend', 'call_agent', 'read_file')")
    context: Dict[str, Any] = Field(description="Contextual data for policy evaluation")


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation."""

    allowed: bool
    agent_did: str
    action: str
    violated_policies: List[str] = Field(default_factory=list)
    reason: str
