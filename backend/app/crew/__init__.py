"""
CrewAI-inspired agent orchestration for Agent-402.
Implements 3-agent workflow: Analyst -> Compliance -> Transaction

This module provides:
- Agent persona definitions (Analyst, Compliance, Transaction)
- Sequential task orchestration
- Integration with ZeroDB agent_memory
- X402 request submission
"""

from app.crew.agents import (
    create_analyst_agent,
    create_compliance_agent,
    create_transaction_agent
)
from app.crew.tasks import (
    create_analyst_task,
    create_compliance_task,
    create_transaction_task
)
from app.crew.crew import X402Crew

__all__ = [
    "create_analyst_agent",
    "create_compliance_agent",
    "create_transaction_agent",
    "create_analyst_task",
    "create_compliance_task",
    "create_transaction_task",
    "X402Crew"
]
