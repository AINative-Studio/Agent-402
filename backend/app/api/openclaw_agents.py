"""
OpenClaw Agents API Router — Issues #229, #230, #231.

Endpoints:
  POST /openclaw/bootstrap/{agent_name}  — bootstrap a single named agent
  POST /openclaw/bootstrap/all           — bootstrap all three agents
  GET  /openclaw/agents/{name}/config    — retrieve a bootstrapped agent config

NOTE: This router is NOT registered in main.py.
      Wire it up explicitly when ready to expose these endpoints.

Built by AINative Dev Team.
Refs #229, #230, #231.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.openclaw_agents import AgentConfig, BootstrapResult
from app.services.openclaw_agent_bootstrap import OpenClawAgentBootstrap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openclaw", tags=["openclaw-agents"])

# Shared bootstrap instance — maintains an in-process agent registry
_bootstrap = OpenClawAgentBootstrap()

# Map of known agent names to their bootstrap coroutine
_AGENT_BOOTSTRAPPERS = {
    "atlas": "_bootstrap_atlas",
    "sage": "_bootstrap_sage",
    "lyra": "_bootstrap_lyra",
}


@router.post(
    "/bootstrap/all",
    response_model=BootstrapResult,
    status_code=201,
    summary="Bootstrap all OpenClaw agents",
)
async def bootstrap_all() -> BootstrapResult:
    """
    Bootstrap atlas, sage, and lyra agents and return their configurations.
    """
    try:
        configs = await _bootstrap.bootstrap_all()
        return BootstrapResult(agents=configs)
    except Exception as exc:
        logger.error("bootstrap_all failed: %s", exc)
        raise HTTPException(status_code=500, detail="Agent bootstrap failed") from exc


@router.post(
    "/bootstrap/{agent_name}",
    response_model=AgentConfig,
    status_code=201,
    summary="Bootstrap a single named OpenClaw agent",
)
async def bootstrap_agent(agent_name: str) -> AgentConfig:
    """
    Bootstrap a specific agent by name (atlas, sage, or lyra).
    """
    dispatch: Dict[str, Any] = {
        "atlas": _bootstrap.bootstrap_atlas,
        "sage": _bootstrap.bootstrap_sage,
        "lyra": _bootstrap.bootstrap_lyra,
    }
    handler = dispatch.get(agent_name)
    if handler is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent '{agent_name}'. Valid names: atlas, sage, lyra.",
        )
    try:
        config = await handler()
        return config
    except Exception as exc:
        logger.error("bootstrap_agent(%s) failed: %s", agent_name, exc)
        raise HTTPException(
            status_code=500, detail=f"Bootstrap failed for agent '{agent_name}'"
        ) from exc


@router.get(
    "/agents/{name}/config",
    response_model=AgentConfig,
    summary="Retrieve a bootstrapped agent configuration by name",
)
async def get_agent_config(name: str) -> AgentConfig:
    """
    Return the configuration for a previously bootstrapped agent.

    Returns 404 if the agent has not been bootstrapped in this session.
    """
    config = await _bootstrap.get_agent_config(name)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent '{name}' not found. "
                "Call POST /openclaw/bootstrap/{name} first."
            ),
        )
    return config
