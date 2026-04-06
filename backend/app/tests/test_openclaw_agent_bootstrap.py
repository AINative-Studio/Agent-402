"""
Tests for OpenClaw Agent Bootstrap — Issues #229, #230, #231.

Covers:
  - atlas agent config (infrastructure role)
  - sage agent config (backend role)
  - lyra agent config (frontend role)
  - bootstrap_all returns all three configs
  - get_agent_config retrieval by name

BDD-style: DescribeX / it_does_something naming convention.
"""
from __future__ import annotations

import pytest
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Issue #229 — Bootstrap atlas
# ---------------------------------------------------------------------------

class DescribeBootstrapAtlas:
    """Tests for OpenClawAgentBootstrap.bootstrap_atlas."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_atlas(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        assert config.name == "atlas"

    @pytest.mark.asyncio
    async def it_sets_role_to_infrastructure(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        assert config.role == "infrastructure"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        expected = {"deployment", "monitoring", "scaling", "networking"}
        assert expected == set(config.capabilities)

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_references_infrastructure_technologies_in_system_prompt(
        self, bootstrap
    ):
        config = await bootstrap.bootstrap_atlas()
        prompt_lower = config.system_prompt.lower()
        # At least one of Railway, Docker, CI/CD should appear
        assert any(kw in prompt_lower for kw in ["railway", "docker", "ci/cd", "cicd"])

    @pytest.mark.asyncio
    async def it_includes_required_tools(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        tool_names = {t.name for t in config.tools}
        expected = {"deployment_check", "service_status", "log_query", "resource_monitor"}
        assert expected == tool_names

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_atlas()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# Issue #230 — Bootstrap sage
# ---------------------------------------------------------------------------

class DescribeBootstrapSage:
    """Tests for OpenClawAgentBootstrap.bootstrap_sage."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_sage(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        assert config.name == "sage"

    @pytest.mark.asyncio
    async def it_sets_role_to_backend(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        assert config.role == "backend"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        expected = {"api_development", "database", "testing", "security"}
        assert expected == set(config.capabilities)

    @pytest.mark.asyncio
    async def it_references_backend_technologies_in_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        prompt_lower = config.system_prompt.lower()
        assert any(kw in prompt_lower for kw in ["fastapi", "postgresql", "zerodb"])

    @pytest.mark.asyncio
    async def it_includes_required_tools(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        tool_names = {t.name for t in config.tools}
        expected = {"code_review", "test_runner", "schema_validator", "api_tester"}
        assert expected == tool_names

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_sage()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# Issue #231 — Bootstrap lyra
# ---------------------------------------------------------------------------

class DescribeBootstrapLyra:
    """Tests for OpenClawAgentBootstrap.bootstrap_lyra."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_lyra(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        assert config.name == "lyra"

    @pytest.mark.asyncio
    async def it_sets_role_to_frontend(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        assert config.role == "frontend"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        expected = {"ui_development", "accessibility", "performance", "design_system"}
        assert expected == set(config.capabilities)

    @pytest.mark.asyncio
    async def it_references_frontend_technologies_in_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        prompt_lower = config.system_prompt.lower()
        assert any(kw in prompt_lower for kw in ["react", "next.js", "nextjs", "tailwind"])

    @pytest.mark.asyncio
    async def it_includes_required_tools(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        tool_names = {t.name for t in config.tools}
        expected = {
            "component_builder", "a11y_checker",
            "lighthouse_audit", "design_token_extractor"
        }
        assert expected == tool_names

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_lyra()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# bootstrap_all
# ---------------------------------------------------------------------------

class DescribeBootstrapAll:
    """Tests for OpenClawAgentBootstrap.bootstrap_all (Sprint 3 agents)."""

    @pytest.mark.asyncio
    async def it_returns_a_list_of_at_least_three_configs(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        assert len(configs) >= 3

    @pytest.mark.asyncio
    async def it_includes_sprint3_agent_names(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        names = {c.name for c in configs}
        assert {"atlas", "sage", "lyra"}.issubset(names)

    @pytest.mark.asyncio
    async def it_returns_valid_agent_config_objects(self, bootstrap):
        from app.schemas.openclaw_agents import AgentConfig
        configs = await bootstrap.bootstrap_all()
        for config in configs:
            assert isinstance(config, AgentConfig)


# ---------------------------------------------------------------------------
# get_agent_config
# ---------------------------------------------------------------------------

class DescribeGetAgentConfig:
    """Tests for OpenClawAgentBootstrap.get_agent_config."""

    @pytest.mark.asyncio
    async def it_retrieves_atlas_by_name(self, bootstrap_with_agents):
        config = await bootstrap_with_agents.get_agent_config("atlas")
        assert config is not None
        assert config.name == "atlas"

    @pytest.mark.asyncio
    async def it_retrieves_sage_by_name(self, bootstrap_with_agents):
        config = await bootstrap_with_agents.get_agent_config("sage")
        assert config is not None
        assert config.name == "sage"

    @pytest.mark.asyncio
    async def it_retrieves_lyra_by_name(self, bootstrap_with_agents):
        config = await bootstrap_with_agents.get_agent_config("lyra")
        assert config is not None
        assert config.name == "lyra"

    @pytest.mark.asyncio
    async def it_returns_none_for_unknown_agent(self, bootstrap_with_agents):
        config = await bootstrap_with_agents.get_agent_config("unknown_agent")
        assert config is None


# ---------------------------------------------------------------------------
# BootstrapResult schema
# ---------------------------------------------------------------------------

class DescribeBootstrapResult:
    """Tests for the BootstrapResult schema object returned by bootstrap_all."""

    @pytest.mark.asyncio
    async def it_exposes_agent_count(self, bootstrap):
        from app.schemas.openclaw_agents import BootstrapResult
        configs = await bootstrap.bootstrap_all()
        result = BootstrapResult(agents=configs)
        assert result.agent_count == 8

    @pytest.mark.asyncio
    async def it_exposes_agent_names_list(self, bootstrap):
        from app.schemas.openclaw_agents import BootstrapResult
        configs = await bootstrap.bootstrap_all()
        result = BootstrapResult(agents=configs)
        expected = {"atlas", "sage", "lyra", "aurora", "nova", "luma", "vega", "helios"}
        assert set(result.agent_names) == expected


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bootstrap():
    """Fresh OpenClawAgentBootstrap instance."""
    from app.services.openclaw_agent_bootstrap import OpenClawAgentBootstrap
    return OpenClawAgentBootstrap()


@pytest.fixture
async def bootstrap_with_agents():
    """Bootstrap instance that has already bootstrapped all agents."""
    from app.services.openclaw_agent_bootstrap import OpenClawAgentBootstrap
    instance = OpenClawAgentBootstrap()
    await instance.bootstrap_all()
    return instance


# ---------------------------------------------------------------------------
# Issue #232 — Bootstrap aurora (QA)
# ---------------------------------------------------------------------------

class DescribeBootstrapAurora:
    """Tests for OpenClawAgentBootstrap.bootstrap_aurora."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_aurora(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        assert config.name == "aurora"

    @pytest.mark.asyncio
    async def it_sets_role_to_qa(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        assert config.role == "qa"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        expected = {"test_planning", "test_execution", "bug_reporting", "coverage_analysis"}
        assert expected == set(config.capabilities)

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_includes_required_tools(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        tool_names = {t.name for t in config.tools}
        expected = {"test_runner", "coverage_reporter", "bug_tracker", "regression_detector"}
        assert expected == tool_names

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_aurora()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def it_registers_aurora_in_registry(self, bootstrap):
        await bootstrap.bootstrap_aurora()
        config = await bootstrap.get_agent_config("aurora")
        assert config is not None
        assert config.name == "aurora"


# ---------------------------------------------------------------------------
# Issue #233 — Bootstrap nova (Security)
# ---------------------------------------------------------------------------

class DescribeBootstrapNova:
    """Tests for OpenClawAgentBootstrap.bootstrap_nova."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_nova(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        assert config.name == "nova"

    @pytest.mark.asyncio
    async def it_sets_role_to_security(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        assert config.role == "security"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        expected = {
            "vulnerability_scanning", "code_audit",
            "dependency_check", "threat_modeling",
        }
        assert expected == set(config.capabilities)

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_includes_required_tools(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        tool_names = {t.name for t in config.tools}
        expected = {
            "dependency_scanner", "owasp_checker",
            "secret_detector", "cve_lookup",
        }
        assert expected == tool_names

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_nova()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def it_registers_nova_in_registry(self, bootstrap):
        await bootstrap.bootstrap_nova()
        config = await bootstrap.get_agent_config("nova")
        assert config is not None
        assert config.name == "nova"


# ---------------------------------------------------------------------------
# Issue #234 — Bootstrap luma (Data)
# ---------------------------------------------------------------------------

class DescribeBootstrapLuma:
    """Tests for OpenClawAgentBootstrap.bootstrap_luma."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_luma(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        assert config.name == "luma"

    @pytest.mark.asyncio
    async def it_sets_role_to_data(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        assert config.role == "data"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        expected = {"data_pipeline", "etl", "analytics"}
        assert expected.issubset(set(config.capabilities))

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_has_at_least_one_tool(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        assert len(config.tools) >= 1

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_luma()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# Issue #234 — Bootstrap vega (DevOps)
# ---------------------------------------------------------------------------

class DescribeBootstrapVega:
    """Tests for OpenClawAgentBootstrap.bootstrap_vega."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_vega(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        assert config.name == "vega"

    @pytest.mark.asyncio
    async def it_sets_role_to_devops(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        assert config.role == "devops"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        expected = {"ci_cd", "monitoring", "deployment"}
        assert expected.issubset(set(config.capabilities))

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_has_at_least_one_tool(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        assert len(config.tools) >= 1

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_vega()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# Issue #234 — Bootstrap helios (Documentation)
# ---------------------------------------------------------------------------

class DescribeBootstrapHelios:
    """Tests for OpenClawAgentBootstrap.bootstrap_helios."""

    @pytest.mark.asyncio
    async def it_returns_an_agent_config(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        assert config is not None

    @pytest.mark.asyncio
    async def it_sets_agent_name_to_helios(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        assert config.name == "helios"

    @pytest.mark.asyncio
    async def it_sets_role_to_docs(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        assert config.role == "docs"

    @pytest.mark.asyncio
    async def it_includes_required_capabilities(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        expected = {"api_docs", "guides", "changelog"}
        assert expected.issubset(set(config.capabilities))

    @pytest.mark.asyncio
    async def it_sets_a_non_empty_system_prompt(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    @pytest.mark.asyncio
    async def it_has_at_least_one_tool(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        assert len(config.tools) >= 1

    @pytest.mark.asyncio
    async def it_gives_each_tool_a_description(self, bootstrap):
        config = await bootstrap.bootstrap_helios()
        for tool in config.tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


# ---------------------------------------------------------------------------
# Updated bootstrap_all — all 8 agents
# ---------------------------------------------------------------------------

class DescribeBootstrapAllExtended:
    """Tests for bootstrap_all after adding aurora, nova, luma, vega, helios."""

    @pytest.mark.asyncio
    async def it_returns_eight_configs(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        assert len(configs) == 8

    @pytest.mark.asyncio
    async def it_includes_all_eight_agent_names(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        names = {c.name for c in configs}
        expected = {"atlas", "sage", "lyra", "aurora", "nova", "luma", "vega", "helios"}
        assert names == expected

    @pytest.mark.asyncio
    async def it_returns_valid_agent_config_objects(self, bootstrap):
        from app.schemas.openclaw_agents import AgentConfig
        configs = await bootstrap.bootstrap_all()
        for config in configs:
            assert isinstance(config, AgentConfig)

    @pytest.mark.asyncio
    async def it_registers_all_agents_in_registry(self, bootstrap):
        await bootstrap.bootstrap_all()
        for name in ("atlas", "sage", "lyra", "aurora", "nova", "luma", "vega", "helios"):
            config = await bootstrap.get_agent_config(name)
            assert config is not None, f"Agent '{name}' not found in registry"

    @pytest.mark.asyncio
    async def it_returns_bootstrap_result_with_count_eight(self, bootstrap):
        from app.schemas.openclaw_agents import BootstrapResult
        configs = await bootstrap.bootstrap_all()
        result = BootstrapResult(agents=configs)
        assert result.agent_count == 8
