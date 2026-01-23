"""
CrewAI-inspired agent orchestration for Agent-402.
Implements 3-agent workflow: Analyst -> Compliance -> Transaction

This module provides:
- Agent persona definitions (Analyst, Compliance, Transaction)
- Sequential task orchestration
- Integration with ZeroDB agent_memory
- X402 request submission
- Tool definitions for Circle APIs

Issues #117 + #118: Enhanced CrewAI and Agent Memory System
"""

from app.crew.agents import (
    Agent,
    AgentTool,
    create_analyst_agent,
    create_compliance_agent,
    create_transaction_agent,
    create_all_agents,
    create_circle_api_tools,
    create_market_data_tools,
    create_compliance_tools,
    create_transaction_tools
)
from app.crew.tasks import (
    Task,
    create_analyst_task,
    create_compliance_task,
    create_transaction_task
)
from app.crew.crew import X402Crew, Crew, Process

__all__ = [
    # Agent classes
    "Agent",
    "AgentTool",
    # Agent factory functions
    "create_analyst_agent",
    "create_compliance_agent",
    "create_transaction_agent",
    "create_all_agents",
    # Tool factory functions
    "create_circle_api_tools",
    "create_market_data_tools",
    "create_compliance_tools",
    "create_transaction_tools",
    # Task classes and factories
    "Task",
    "create_analyst_task",
    "create_compliance_task",
    "create_transaction_task",
    # Crew classes
    "X402Crew",
    "Crew",
    "Process"
]
