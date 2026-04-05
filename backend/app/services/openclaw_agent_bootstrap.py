"""
OpenClaw Agent Bootstrap — Issues #229, #230, #231, #232, #233, #234.

Bootstraps eight specialised OpenClaw agents:
  - atlas  : Infrastructure (Railway, Docker, CI/CD)
  - sage   : Backend (FastAPI, PostgreSQL, ZeroDB)
  - lyra   : Frontend (React, Next.js, Tailwind)
  - aurora : QA (test planning, execution, bug reporting, coverage)
  - nova   : Security (vulnerability scanning, code audit, CVE lookup)
  - luma   : Data (data pipeline, ETL, analytics)
  - vega   : DevOps (CI/CD, monitoring, deployment)
  - helios : Documentation (API docs, guides, changelog)

Built by AINative Dev Team.
Refs #229, #230, #231, #232, #233, #234.
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
    # Issue #232 — aurora: QA Agent
    # ------------------------------------------------------------------

    async def bootstrap_aurora(self) -> AgentConfig:
        """
        Create and register the aurora QA agent configuration.

        Returns:
            AgentConfig for aurora.
        """
        config = AgentConfig(
            name="aurora",
            role="qa",
            capabilities=[
                "test_planning", "test_execution", "bug_reporting", "coverage_analysis"
            ],
            system_prompt=(
                "You are aurora, the quality assurance specialist for AINative projects. "
                "Your expertise covers end-to-end test planning, automated test execution, "
                "structured bug reporting, and test coverage analysis. "
                "You design comprehensive test plans that cover happy paths, edge cases, "
                "and regression scenarios. When a bug is detected, you produce a complete "
                "reproduction case with expected vs actual behaviour, environment details, "
                "and severity assessment. "
                "Coverage targets: minimum 80% line coverage, 100% for critical payment paths."
            ),
            tools=[
                AgentTool(
                    name="test_runner",
                    description=(
                        "Execute a pytest or unittest test suite for a given module "
                        "or directory and return pass/fail counts with error details."
                    ),
                ),
                AgentTool(
                    name="coverage_reporter",
                    description=(
                        "Analyse test coverage for a codebase or module and produce "
                        "a report highlighting uncovered lines and branches."
                    ),
                ),
                AgentTool(
                    name="bug_tracker",
                    description=(
                        "Create, update, and query bug reports in the issue tracker, "
                        "including severity, reproduction steps, and resolution status."
                    ),
                ),
                AgentTool(
                    name="regression_detector",
                    description=(
                        "Compare test results across two revisions to identify newly "
                        "failing tests and potential regressions introduced by a change."
                    ),
                ),
            ],
        )
        self._registry["aurora"] = config
        logger.info("Bootstrapped aurora agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #233 — nova: Security Agent
    # ------------------------------------------------------------------

    async def bootstrap_nova(self) -> AgentConfig:
        """
        Create and register the nova security agent configuration.

        Returns:
            AgentConfig for nova.
        """
        config = AgentConfig(
            name="nova",
            role="security",
            capabilities=[
                "vulnerability_scanning", "code_audit",
                "dependency_check", "threat_modeling",
            ],
            system_prompt=(
                "You are nova, the security specialist for AINative projects. "
                "Your domain covers vulnerability scanning, static code auditing, "
                "third-party dependency health checks, and threat modelling. "
                "You identify OWASP Top 10 risks, exposed secrets, and CVE-affected "
                "dependencies before they reach production. "
                "Every recommendation follows the principle of least privilege and "
                "defence-in-depth. Always produce actionable remediation steps with "
                "effort estimates and risk ratings."
            ),
            tools=[
                AgentTool(
                    name="dependency_scanner",
                    description=(
                        "Scan project dependencies (requirements.txt, package.json, etc.) "
                        "for known vulnerabilities and out-of-date packages."
                    ),
                ),
                AgentTool(
                    name="owasp_checker",
                    description=(
                        "Audit source code and API definitions against the OWASP Top 10 "
                        "checklist and return findings with severity levels."
                    ),
                ),
                AgentTool(
                    name="secret_detector",
                    description=(
                        "Scan git history and source files for accidentally committed "
                        "secrets, API keys, and credentials using pattern matching."
                    ),
                ),
                AgentTool(
                    name="cve_lookup",
                    description=(
                        "Query the NVD CVE database for vulnerability details, "
                        "CVSS scores, and available patches for a given package or CVE ID."
                    ),
                ),
            ],
        )
        self._registry["nova"] = config
        logger.info("Bootstrapped nova agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #234 — luma: Data Agent
    # ------------------------------------------------------------------

    async def bootstrap_luma(self) -> AgentConfig:
        """
        Create and register the luma data agent configuration.

        Returns:
            AgentConfig for luma.
        """
        config = AgentConfig(
            name="luma",
            role="data",
            capabilities=["data_pipeline", "etl", "analytics"],
            system_prompt=(
                "You are luma, the data engineering specialist for AINative projects. "
                "Your expertise covers designing and maintaining data pipelines, "
                "ETL processes, and analytical workloads. "
                "You build reliable, idempotent data flows from raw sources to "
                "analytics-ready datasets, validate data quality at every stage, "
                "and surface actionable insights through clear visualisation and "
                "summary statistics."
            ),
            tools=[
                AgentTool(
                    name="pipeline_builder",
                    description=(
                        "Scaffold or modify a data pipeline definition, including "
                        "source connectors, transformation steps, and sink targets."
                    ),
                ),
                AgentTool(
                    name="etl_runner",
                    description=(
                        "Execute an ETL job, track progress, and report row counts "
                        "and error rates for each pipeline stage."
                    ),
                ),
                AgentTool(
                    name="data_quality_checker",
                    description=(
                        "Run data quality assertions (nullability, uniqueness, range checks) "
                        "on a dataset and return a pass/fail quality report."
                    ),
                ),
                AgentTool(
                    name="analytics_query",
                    description=(
                        "Execute an analytical query against a data warehouse or "
                        "ZeroDB table and return summarised results."
                    ),
                ),
            ],
        )
        self._registry["luma"] = config
        logger.info("Bootstrapped luma agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #234 — vega: DevOps Agent
    # ------------------------------------------------------------------

    async def bootstrap_vega(self) -> AgentConfig:
        """
        Create and register the vega DevOps agent configuration.

        Returns:
            AgentConfig for vega.
        """
        config = AgentConfig(
            name="vega",
            role="devops",
            capabilities=["ci_cd", "monitoring", "deployment"],
            system_prompt=(
                "You are vega, the DevOps specialist for AINative projects. "
                "Your expertise covers CI/CD pipeline management, service monitoring, "
                "and reliable deployment strategies. "
                "You design zero-downtime deployment workflows, manage environment "
                "configuration, and respond to production incidents by correlating "
                "metrics, logs, and traces. "
                "Prefer blue/green and canary deployments to reduce risk, and always "
                "ensure rollback plans are tested before going live."
            ),
            tools=[
                AgentTool(
                    name="pipeline_trigger",
                    description=(
                        "Trigger a CI/CD pipeline run for a given repository branch "
                        "and return the build status and test results."
                    ),
                ),
                AgentTool(
                    name="deployment_manager",
                    description=(
                        "Manage service deployments including rolling updates, "
                        "canary releases, and rollbacks on Railway or Kubernetes."
                    ),
                ),
                AgentTool(
                    name="metrics_dashboard",
                    description=(
                        "Query real-time and historical service metrics (CPU, memory, "
                        "latency, error rate) and surface anomalies."
                    ),
                ),
                AgentTool(
                    name="alert_manager",
                    description=(
                        "Create, update, and acknowledge alerting rules and on-call "
                        "incidents for production services."
                    ),
                ),
            ],
        )
        self._registry["vega"] = config
        logger.info("Bootstrapped vega agent configuration")
        return config

    # ------------------------------------------------------------------
    # Issue #234 — helios: Documentation Agent
    # ------------------------------------------------------------------

    async def bootstrap_helios(self) -> AgentConfig:
        """
        Create and register the helios documentation agent configuration.

        Returns:
            AgentConfig for helios.
        """
        config = AgentConfig(
            name="helios",
            role="docs",
            capabilities=["api_docs", "guides", "changelog"],
            system_prompt=(
                "You are helios, the documentation specialist for AINative projects. "
                "Your expertise covers generating accurate API reference docs from "
                "OpenAPI specifications, writing developer guides and tutorials, "
                "and maintaining structured changelogs. "
                "You ensure documentation stays in sync with the codebase, flags "
                "undocumented endpoints, and produces clear, concise prose aimed at "
                "developers integrating with AINative APIs. "
                "Every guide includes working code examples and troubleshooting sections."
            ),
            tools=[
                AgentTool(
                    name="openapi_doc_generator",
                    description=(
                        "Generate human-readable API reference documentation from an "
                        "OpenAPI 3.x specification, including examples and schemas."
                    ),
                ),
                AgentTool(
                    name="guide_writer",
                    description=(
                        "Produce a step-by-step developer guide or tutorial for a "
                        "feature, including prerequisites, code samples, and next steps."
                    ),
                ),
                AgentTool(
                    name="changelog_generator",
                    description=(
                        "Generate a structured changelog entry from git commit history "
                        "or pull request descriptions, grouped by change type."
                    ),
                ),
                AgentTool(
                    name="doc_coverage_checker",
                    description=(
                        "Identify undocumented API endpoints, parameters, and schemas "
                        "by diffing the OpenAPI spec against existing documentation."
                    ),
                ),
            ],
        )
        self._registry["helios"] = config
        logger.info("Bootstrapped helios agent configuration")
        return config

    # ------------------------------------------------------------------
    # bootstrap_all / get_agent_config
    # ------------------------------------------------------------------

    async def bootstrap_all(self) -> List[AgentConfig]:
        """
        Bootstrap all eight OpenClaw agents and return their configs.

        Includes the original Sprint 3 agents (atlas, sage, lyra) and the
        Sprint 4 agents (aurora, nova, luma, vega, helios).

        Returns:
            List of AgentConfig objects for all eight agents.
        """
        atlas = await self.bootstrap_atlas()
        sage = await self.bootstrap_sage()
        lyra = await self.bootstrap_lyra()
        aurora = await self.bootstrap_aurora()
        nova = await self.bootstrap_nova()
        luma = await self.bootstrap_luma()
        vega = await self.bootstrap_vega()
        helios = await self.bootstrap_helios()
        configs = [atlas, sage, lyra, aurora, nova, luma, vega, helios]
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
