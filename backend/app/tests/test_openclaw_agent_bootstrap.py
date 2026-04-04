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
    """Tests for OpenClawAgentBootstrap.bootstrap_all."""

    @pytest.mark.asyncio
    async def it_returns_a_list_of_three_configs(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        assert len(configs) == 3

    @pytest.mark.asyncio
    async def it_includes_all_three_agent_names(self, bootstrap):
        configs = await bootstrap.bootstrap_all()
        names = {c.name for c in configs}
        assert names == {"atlas", "sage", "lyra"}

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
        assert result.agent_count == 3

    @pytest.mark.asyncio
    async def it_exposes_agent_names_list(self, bootstrap):
        from app.schemas.openclaw_agents import BootstrapResult
        configs = await bootstrap.bootstrap_all()
        result = BootstrapResult(agents=configs)
        assert set(result.agent_names) == {"atlas", "sage", "lyra"}


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
