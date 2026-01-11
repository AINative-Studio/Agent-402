"""
CrewAI Task Definitions for Sequential Workflow.
Implements Issue #72: Task definitions for Analyst, Compliance, Transaction agents.

Per PRD Section 4, 6, 9:
- Sequential workflow: Analyst -> Compliance -> Transaction
- Each task accepts context from previous task
- Store decisions in agent_memory
- Log events for audit trail
- Return structured output

Architecture:
- create_analysis_task: Market analysis and data gathering
- create_compliance_task: KYC/KYT checks and risk assessment
- create_transaction_task: X402 request execution
- create_all_tasks: Helper to create all tasks in sequence
"""

import logging
from typing import List
from crewai import Task, Agent

logger = logging.getLogger(__name__)


def create_analysis_task(agent: Agent) -> Task:
    """
    Create market analysis task for Analyst agent.

    Per Issue #72:
    - First task in sequential workflow
    - Analyzes market data and provides investment recommendations
    - Output feeds into compliance task

    Args:
        agent: Analyst agent instance

    Returns:
        CrewAI Task for market analysis
    """
    task = Task(
        description="""
        Analyze the current market conditions and transaction request.

        Steps:
        1. Review market data for relevant assets
        2. Assess market volatility and liquidity
        3. Evaluate transaction timing and feasibility
        4. Provide investment recommendation with risk assessment

        Context: You are reviewing a financial transaction request and must provide
        a comprehensive market analysis to support decision-making.

        Your analysis should include:
        - Market conditions summary
        - Risk level assessment (low, medium, high)
        - Investment recommendation (approve, reject, hold)
        - Supporting data points and rationale
        """,
        agent=agent,
        expected_output="""
        A structured market analysis report containing:
        - Market conditions: Current state of relevant markets
        - Risk assessment: Overall risk level with justification
        - Recommendation: Clear approve/reject/hold decision
        - Rationale: Data-driven reasoning for recommendation
        - Next steps: Actions required for compliance review
        """
    )

    return task


def create_compliance_task(agent: Agent) -> Task:
    """
    Create compliance check task for Compliance agent.

    Per Issue #72:
    - Second task in sequential workflow
    - Receives context from analysis task
    - Performs KYC/KYT checks and risk assessment
    - Output feeds into transaction task

    Args:
        agent: Compliance agent instance

    Returns:
        CrewAI Task for compliance verification
    """
    task = Task(
        description="""
        Perform comprehensive compliance checks on the transaction request.

        Steps:
        1. Review analysis task output and recommendation
        2. Verify KYC (Know Your Customer) requirements
        3. Conduct KYT (Know Your Transaction) checks
        4. Assess regulatory compliance for jurisdiction
        5. Check against sanctions lists and blacklists
        6. Evaluate AML (Anti-Money Laundering) risk
        7. Provide compliance approval or rejection

        Context: You are reviewing the analyst's recommendation and must ensure
        all regulatory requirements are met before transaction execution.

        Your compliance review should verify:
        - Customer identity and verification status
        - Transaction legitimacy and pattern analysis
        - Regulatory requirements for jurisdiction
        - Sanctions and blacklist screening
        - AML risk score and mitigation
        """,
        agent=agent,
        expected_output="""
        A structured compliance report containing:
        - KYC status: Customer verification results
        - KYT analysis: Transaction pattern and legitimacy assessment
        - Regulatory compliance: All applicable requirements checked
        - Risk score: Compliance risk level (0-100)
        - Approval decision: Approved, Rejected, or Requires Manual Review
        - Compliance notes: Any flags, warnings, or required actions
        """
    )

    return task


def create_transaction_task(agent: Agent) -> Task:
    """
    Create transaction execution task for Transaction agent.

    Per Issue #72:
    - Third task in sequential workflow
    - Receives context from compliance task
    - Executes approved X402 transactions
    - Stores final execution results

    Args:
        agent: Transaction agent instance

    Returns:
        CrewAI Task for transaction execution
    """
    task = Task(
        description="""
        Execute the approved financial transaction securely.

        Steps:
        1. Review compliance task output and approval status
        2. Verify all prerequisites are met (analysis approved, compliance passed)
        3. Prepare X402 protocol request payload
        4. Execute transaction via secure payment rails
        5. Verify transaction confirmation and settlement
        6. Store transaction metadata and audit trail
        7. Generate execution summary

        Context: You are executing a transaction that has been approved by both
        the analyst and compliance teams. Execute only if all approvals are present.

        Your execution should include:
        - Pre-execution validation checks
        - Secure transaction submission
        - Confirmation and settlement verification
        - Audit trail and metadata storage
        - Error handling and rollback capability
        """,
        agent=agent,
        expected_output="""
        A structured transaction execution report containing:
        - Execution status: Success, Failed, or Pending
        - Transaction ID: Unique identifier for transaction
        - Confirmation details: Settlement and confirmation data
        - Timestamp: Execution timestamp in ISO format
        - Metadata: All relevant transaction metadata
        - Audit trail: Complete execution log for compliance
        - Error details: If failed, detailed error information
        """
    )

    return task


def create_all_tasks(
    analyst_agent: Agent,
    compliance_agent: Agent,
    transaction_agent: Agent
) -> List[Task]:
    """
    Create all tasks for sequential workflow.

    Per Issue #72:
    - Helper function to create all tasks in correct order
    - Ensures sequential workflow: Analyst -> Compliance -> Transaction

    Args:
        analyst_agent: Analyst agent instance
        compliance_agent: Compliance agent instance
        transaction_agent: Transaction agent instance

    Returns:
        List of tasks in sequential execution order
    """
    analysis_task = create_analysis_task(analyst_agent)
    compliance_task = create_compliance_task(compliance_agent)
    transaction_task = create_transaction_task(transaction_agent)

    tasks = [
        analysis_task,
        compliance_task,
        transaction_task
    ]

    logger.info(f"Created {len(tasks)} tasks for sequential workflow")

    return tasks


def get_task_metadata(task: Task) -> dict:
    """
    Extract metadata from a task for logging and tracking.

    Args:
        task: CrewAI Task instance

    Returns:
        Dictionary with task metadata
    """
    return {
        "description": task.description[:100] + "..." if len(task.description) > 100 else task.description,
        "agent_role": task.agent.role if task.agent else "Unknown",
        "expected_output": task.expected_output[:100] + "..." if len(task.expected_output) > 100 else task.expected_output
    }
