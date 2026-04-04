"""
Schemas for OpenClaw Agent Bootstrap — Issues #229, #230, #231.

Provides Pydantic models for:
  - AgentTool — a capability tool definition
  - AgentConfig — full agent configuration
  - BootstrapResult — result of bootstrapping one or more agents

Built by AINative Dev Team.
Refs #229, #230, #231.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentTool(BaseModel):
    """A tool available to an OpenClaw agent."""

    name: str = Field(..., description="Machine-readable tool identifier")
    description: str = Field(..., description="Human-readable description of the tool")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-schema-style parameter definitions"
    )


class AgentConfig(BaseModel):
    """Complete configuration for an OpenClaw agent."""

    name: str = Field(..., description="Unique agent name (atlas, sage, lyra, …)")
    role: str = Field(..., description="Agent role category (infrastructure, backend, frontend, …)")
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of capability identifiers the agent possesses"
    )
    system_prompt: str = Field(
        ..., description="System-level instruction prompt for the agent"
    )
    tools: List[AgentTool] = Field(
        default_factory=list,
        description="Tools available to the agent during task execution"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the config was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key/value metadata"
    )


class BootstrapResult(BaseModel):
    """Result returned by bootstrap_all containing all bootstrapped agents."""

    agents: List[AgentConfig] = Field(
        default_factory=list,
        description="All successfully bootstrapped agent configurations"
    )
    bootstrapped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the bootstrap run"
    )

    @property
    def agent_count(self) -> int:
        """Number of agents in this result."""
        return len(self.agents)

    @property
    def agent_names(self) -> List[str]:
        """Names of all bootstrapped agents."""
        return [a.name for a in self.agents]
