"""
CrewAI Runtime Implementation with 3 Agent Personas.
Implements Issue #72: CrewAI integration for Agent-402 backend.

Per PRD Section 4, 6, 9:
- 3 Agent Personas: Analyst, Compliance, Transaction
- Sequential workflow execution
- Integration with agent_memory API
- Tool integration from backend/tools/

Architecture:
- create_analyst_agent: Market analysis and decision support
- create_compliance_agent: KYC/KYT checks and risk assessment
- create_transaction_agent: X402 request execution
- create_crew: Orchestrate all agents in sequential workflow
"""

import logging
from typing import List, Optional, Dict, Any
from crewai import Agent, Crew, Process
try:
    from langchain_community.llms.fake import FakeListLLM
except ImportError:
    # Fallback for older versions
    try:
        from langchain.llms.fake import FakeListLLM
    except ImportError:
        # If neither works, we'll handle it later
        FakeListLLM = None

from app.services.agent_service import agent_service
from app.services.agent_memory_service import agent_memory_service
from tasks import create_analysis_task, create_compliance_task, create_transaction_task

logger = logging.getLogger(__name__)


async def create_analyst_agent(project_id: str) -> Agent:
    """
    Create Financial Analyst agent.

    Per Issue #72:
    - DID: did:ethr:0xanalyst001
    - Role: Financial Analyst
    - Goal: Analyze market data and provide investment recommendations
    - Backstory: Expert financial analyst with deep market knowledge

    Args:
        project_id: Project identifier for agent registration

    Returns:
        CrewAI Agent instance for market analysis
    """
    did = "did:ethr:0xanalyst001"
    role = "Financial Analyst"
    goal = "Analyze market data and provide investment recommendations"
    backstory = "Expert financial analyst with deep market knowledge and years of experience in fintech markets"

    # Register agent with agent_service for metadata tracking
    try:
        agent_record = await agent_service.create_agent(
            project_id=project_id,
            did=did,
            role=role,
            name="Analyst Agent",
            description=backstory,
            scope="PROJECT"
        )
        logger.info(f"Registered analyst agent: {agent_record.id}")
    except Exception as e:
        logger.warning(f"Failed to register analyst agent: {e}")
        # Continue anyway - agent can still function without registration

    # Create CrewAI agent with mock LLM for testing
    # In production, replace with actual LLM (OpenAI, Anthropic, etc.)
    llm_config = None
    if FakeListLLM:
        llm_config = FakeListLLM(responses=[
            "Market analysis complete. Recommendation: Proceed with transaction.",
            "Analysis shows positive market conditions.",
            "Risk assessment: Low to moderate risk level."
        ])

    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=[],  # Tools from backend/tools/ will be added here
        llm=llm_config
    )

    return agent


async def create_compliance_agent(project_id: str) -> Agent:
    """
    Create Compliance Officer agent.

    Per Issue #72:
    - DID: did:ethr:0xcompliance001
    - Role: Compliance Officer
    - Goal: Ensure all transactions meet regulatory requirements
    - Backstory: Regulatory compliance expert specializing in fintech

    Args:
        project_id: Project identifier for agent registration

    Returns:
        CrewAI Agent instance for compliance checks
    """
    did = "did:ethr:0xcompliance001"
    role = "Compliance Officer"
    goal = "Ensure all transactions meet regulatory requirements"
    backstory = "Regulatory compliance expert specializing in fintech with extensive KYC/KYT experience"

    # Register agent with agent_service
    try:
        agent_record = await agent_service.create_agent(
            project_id=project_id,
            did=did,
            role=role,
            name="Compliance Agent",
            description=backstory,
            scope="PROJECT"
        )
        logger.info(f"Registered compliance agent: {agent_record.id}")
    except Exception as e:
        logger.warning(f"Failed to register compliance agent: {e}")

    # Create CrewAI agent
    llm_config = None
    if FakeListLLM:
        llm_config = FakeListLLM(responses=[
            "Compliance check complete. All regulatory requirements met.",
            "KYC verification passed. No red flags detected.",
            "Transaction approved from compliance perspective."
        ])

    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=[],  # Tools from backend/tools/ will be added here
        llm=llm_config
    )

    return agent


async def create_transaction_agent(project_id: str) -> Agent:
    """
    Create Transaction Executor agent.

    Per Issue #72:
    - DID: did:ethr:0xtransaction001
    - Role: Transaction Executor
    - Goal: Execute approved financial transactions securely
    - Backstory: Payment systems specialist with blockchain expertise

    Args:
        project_id: Project identifier for agent registration

    Returns:
        CrewAI Agent instance for transaction execution
    """
    did = "did:ethr:0xtransaction001"
    role = "Transaction Executor"
    goal = "Execute approved financial transactions securely"
    backstory = "Payment systems specialist with blockchain expertise and secure transaction processing experience"

    # Register agent with agent_service
    try:
        agent_record = await agent_service.create_agent(
            project_id=project_id,
            did=did,
            role=role,
            name="Transaction Agent",
            description=backstory,
            scope="PROJECT"
        )
        logger.info(f"Registered transaction agent: {agent_record.id}")
    except Exception as e:
        logger.warning(f"Failed to register transaction agent: {e}")

    # Create CrewAI agent
    llm_config = None
    if FakeListLLM:
        llm_config = FakeListLLM(responses=[
            "Transaction executed successfully. ID: TX-001",
            "Payment processed securely via blockchain.",
            "Transaction complete. Confirmation sent."
        ])

    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=[],  # Tools from backend/tools/ will be added here
        llm=llm_config
    )

    return agent


async def create_crew(
    project_id: str,
    run_id: str,
    verbose: bool = False
) -> Crew:
    """
    Create and configure CrewAI crew with all three agents.

    Per Issue #72:
    - Sequential workflow: Analyst -> Compliance -> Transaction
    - Integration with agent_memory for decision tracking
    - Tool integration from backend/tools/

    Args:
        project_id: Project identifier
        run_id: Execution run identifier
        verbose: Enable verbose output for debugging

    Returns:
        Configured CrewAI Crew instance

    Raises:
        Exception: If agent creation or crew configuration fails
    """
    logger.info(f"Creating crew for project {project_id}, run {run_id}")

    # Create all three agents
    analyst_agent = await create_analyst_agent(project_id)
    compliance_agent = await create_compliance_agent(project_id)
    transaction_agent = await create_transaction_agent(project_id)

    # Create tasks for sequential workflow
    analysis_task = create_analysis_task(analyst_agent)
    compliance_task = create_compliance_task(compliance_agent)
    transaction_task = create_transaction_task(transaction_agent)

    # Configure crew with sequential process
    crew = Crew(
        agents=[analyst_agent, compliance_agent, transaction_agent],
        tasks=[analysis_task, compliance_task, transaction_task],
        process=Process.sequential,  # Sequential workflow required
        verbose=verbose
    )

    # Store crew metadata for tracking
    # Note: Crew is a Pydantic model, so we can't add arbitrary fields
    # Store metadata in a dict accessible via crew.__dict__
    crew.__dict__['project_id'] = project_id
    crew.__dict__['run_id'] = run_id

    # Log crew creation in agent_memory
    try:
        await agent_memory_service.store_memory(
            project_id=project_id,
            agent_id="crew_orchestrator",
            run_id=run_id,
            memory_type="state",
            content=f"Crew initialized with 3 agents: Analyst, Compliance, Transaction",
            metadata={
                "agent_count": 3,
                "process": "sequential",
                "agents": ["analyst", "compliance", "transaction"]
            }
        )
        logger.info(f"Crew metadata stored in agent_memory for run {run_id}")
    except Exception as e:
        logger.warning(f"Failed to store crew metadata: {e}")

    return crew


def get_agent_tools() -> List:
    """
    Get tools from backend/tools/ for agent configuration.

    Per Issue #72:
    - Tools are shared across all agents
    - Integration with existing tools framework

    Returns:
        List of tool instances for agent use
    """
    # Import tools when they are implemented
    # from tools import tool_registry
    # return tool_registry.list_tools()

    # For now, return empty list
    # Tools will be added as they are implemented
    return []
