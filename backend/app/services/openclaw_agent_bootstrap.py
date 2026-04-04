"""
OpenClaw Agent Bootstrap — Issues #229, #230, #231.

Bootstraps three specialised OpenClaw agents:
  - atlas : Infrastructure (Railway, Docker, CI/CD)
  - sage  : Backend (FastAPI, PostgreSQL, ZeroDB)
  - lyra  : Frontend (React, Next.js, Tailwind)

Built by AINative Dev Team.
Refs #229, #230, #231.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.schemas.openclaw_agents import AgentConfig, AgentTool, BootstrapResult

logger = logging.getLogger(__name__)


class OpenClawAgentBootstrap:
    """
    Bootstraps OpenClaw agent configurations and maintains an in-process
    registry for retrieval.

    Configs are pure data objects — no external I/O is performed here.
    Persistence is the responsibility of the calling layer.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, AgentConfig] = {}

    # ------------------------------------------------------------------
    # Issue #229 — atlas: Infrastructure Agent
    # ------------------------------------------------------------------

    async def bootstrap_atlas(self) -> AgentConfig:
        """
        Create and register the atlas infrastructure agent configuration.

        Returns:
            AgentConfig for atlas.
        """
        config = AgentConfig(
            name="atlas",
            role="infrastructure",
            capabilities=["deployment", "monitoring", "scaling", "networking"],
            system_prompt=(
                "You are atlas, the infrastructure specialist for AINative projects. "
                "Your domain expertise covers Railway deployments, Docker containerisation, "
                "CI/CD pipeline management, and cloud networking. "
                "You monitor service health, manage scaling decisions, and ensure "
                "deployment reliability across all environments. "
                "When diagnosing issues, examine logs, resource metrics, and service status "
                "before recommending changes. Always prefer incremental, reversible actions."
            ),
            tools=[
                AgentTool(
                    name="deployment_check",
                    description=(
                        "Verify the current deployment status of a service, "
                        "including revision, health checks, and rollout progress."
                    ),
                ),
                AgentTool(
                    name="service_status",
                    description=(
                        "Query real-time status of a running service, including "
                        "uptime, replica count, and recent restart events."
                    ),
                ),
                AgentTool(
                    name="log_query",
                    description=(
                        "Retrieve and filter structured logs from a service or "
                        "infrastructure component within a given time window."
                    ),
                ),
                AgentTool(
                    name="resource_monitor",
                    description=(
                        "Inspect CPU, memory, and network utilisation metrics "
                        "for a target service or host to identify bottlenecks."
                    ),
                ),
            ],
        )
        self._registry["atlas"] = config
        logger.info("Bootstrapped atlas agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #230 — sage: Backend Agent
    # ------------------------------------------------------------------

    async def bootstrap_sage(self) -> AgentConfig:
        """
        Create and register the sage backend agent configuration.

        Returns:
            AgentConfig for sage.
        """
        config = AgentConfig(
            name="sage",
            role="backend",
            capabilities=["api_development", "database", "testing", "security"],
            system_prompt=(
                "You are sage, the backend engineering specialist for AINative projects. "
                "Your expertise spans FastAPI service design, PostgreSQL schema management, "
                "ZeroDB integration for vectors and memory, and API security best practices. "
                "You review code for correctness, run test suites, validate API schemas, "
                "and ensure database migrations are safe. "
                "Prioritise test coverage, idempotent operations, and least-privilege access "
                "in every recommendation."
            ),
            tools=[
                AgentTool(
                    name="code_review",
                    description=(
                        "Perform a static analysis code review of a Python module or "
                        "pull request diff, reporting issues by severity."
                    ),
                ),
                AgentTool(
                    name="test_runner",
                    description=(
                        "Execute the pytest test suite for a given module or directory "
                        "and return pass/fail counts with coverage metrics."
                    ),
                ),
                AgentTool(
                    name="schema_validator",
                    description=(
                        "Validate a Pydantic model schema or OpenAPI specification "
                        "against defined contracts and report any violations."
                    ),
                ),
                AgentTool(
                    name="api_tester",
                    description=(
                        "Send HTTP requests to an API endpoint and assert response "
                        "status, headers, and body against expected values."
                    ),
                ),
            ],
        )
        self._registry["sage"] = config
        logger.info("Bootstrapped sage agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #231 — lyra: Frontend Agent
    # ------------------------------------------------------------------

    async def bootstrap_lyra(self) -> AgentConfig:
        """
        Create and register the lyra frontend agent configuration.

        Returns:
            AgentConfig for lyra.
        """
        config = AgentConfig(
            name="lyra",
            role="frontend",
            capabilities=[
                "ui_development", "accessibility", "performance", "design_system"
            ],
            system_prompt=(
                "You are lyra, the frontend engineering specialist for AINative projects. "
                "Your expertise covers React component architecture, Next.js app routing, "
                "Tailwind CSS design systems, and web accessibility (WCAG 2.1 AA). "
                "You build performant, accessible UI components, audit Lighthouse scores, "
                "and ensure design token consistency across the product surface. "
                "Every UI change should pass accessibility checks and maintain or improve "
                "Core Web Vitals benchmarks."
            ),
            tools=[
                AgentTool(
                    name="component_builder",
                    description=(
                        "Scaffold a new React component with TypeScript types, "
                        "Tailwind styling, and a corresponding test file."
                    ),
                ),
                AgentTool(
                    name="a11y_checker",
                    description=(
                        "Run an automated accessibility audit (axe-core) against a "
                        "rendered component or page URL and report WCAG violations."
                    ),
                ),
                AgentTool(
                    name="lighthouse_audit",
                    description=(
                        "Execute a Lighthouse performance, accessibility, and SEO audit "
                        "for a given URL and return the scored report."
                    ),
                ),
                AgentTool(
                    name="design_token_extractor",
                    description=(
                        "Extract design tokens (colours, spacing, typography) from a "
                        "Figma file or Tailwind config and generate a token manifest."
                    ),
                ),
            ],
        )
        self._registry["lyra"] = config
        logger.info("Bootstrapped lyra agent configuration")
        return config

    # ------------------------------------------------------------------
    # bootstrap_all / get_agent_config
    # ------------------------------------------------------------------

    async def bootstrap_all(self) -> List[AgentConfig]:
        """
        Bootstrap all three OpenClaw agents and return their configs.

        Returns:
            List of AgentConfig objects for atlas, sage, and lyra.
        """
        atlas = await self.bootstrap_atlas()
        sage = await self.bootstrap_sage()
        lyra = await self.bootstrap_lyra()
        configs = [atlas, sage, lyra]
        logger.info("Bootstrapped all OpenClaw agents: %s", [c.name for c in configs])
        return configs

    async def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        Retrieve a bootstrapped agent configuration by name.

        Args:
            agent_name: Name of the agent (e.g. "atlas", "sage", "lyra").

        Returns:
            AgentConfig if found, None otherwise.
        """
        config = self._registry.get(agent_name)
        if config is None:
            logger.debug("Agent config not found for name: %s", agent_name)
        return config
