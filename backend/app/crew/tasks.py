"""
Task definitions for the sequential 3-agent workflow.

Implements Epic 12 Story 1: Sequential task orchestration
Tasks execute in order: Analyst -> Compliance -> Transaction
"""
from typing import Dict, Any
from app.crew.agents import Agent


class Task:
    """Lightweight task class representing CrewAI Task interface."""

    def __init__(
        self,
        description: str,
        agent: Agent,
        expected_output: str,
        context: Dict[str, Any] = None
    ):
        """
        Initialize a task with description, assigned agent, and expected output.

        Args:
            description: Detailed task description
            agent: Agent responsible for this task
            expected_output: Description of expected task output
            context: Additional context data for task execution
        """
        self.description = description
        self.agent = agent
        self.expected_output = expected_output
        self.context = context or {}


def create_analyst_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """
    Create the market data analysis task.

    This is the first task in the sequential workflow.

    Args:
        agent: Analyst agent to assign this task
        context: Context including query, project_id, etc.

    Returns:
        Task configured for market data analysis
    """
    query = context.get("query", "")

    description = f"""
    Analyze and aggregate market data based on the following query:
    {query}

    Your responsibilities:
    1. Identify required data sources (exchanges, price feeds, market data APIs)
    2. Fetch real-time or recent market data
    3. Normalize data formats across different sources
    4. Validate data quality and consistency
    5. Calculate derived metrics (averages, spreads, volatility)
    6. Prepare structured output for compliance review

    Focus on accuracy, timeliness, and completeness of data.
    """

    expected_output = """
    Structured market data report containing:
    - Source identification and timestamps
    - Raw data values with units
    - Normalized/transformed data
    - Data quality indicators
    - Any anomalies or warnings
    - Recommended action based on data analysis
    """

    return Task(
        description=description.strip(),
        agent=agent,
        expected_output=expected_output.strip(),
        context=context
    )


def create_compliance_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """
    Create the compliance validation task.

    This is the second task in the sequential workflow.
    Depends on output from analyst task.

    Args:
        agent: Compliance agent to assign this task
        context: Context including analyst_output, project_id, etc.

    Returns:
        Task configured for compliance checks
    """
    analyst_output = context.get("analyst_output", "")

    description = f"""
    Perform comprehensive compliance and risk assessment based on the analyst's findings:

    Analyst Output:
    {analyst_output}

    Your responsibilities:
    1. Review transaction details against AML/KYC requirements
    2. Perform sanctions list screening
    3. Calculate risk score (0.0 = lowest, 1.0 = highest)
    4. Check regulatory compliance for jurisdiction
    5. Validate transaction limits and thresholds
    6. Review counterparty information if available
    7. Make PASS/FAIL determination with justification

    Document all checks performed and maintain audit trail.
    """

    expected_output = """
    Compliance report containing:
    - AML/KYC check results
    - Risk score (0.0-1.0) with breakdown
    - Sanctions screening status
    - Regulatory compliance status
    - PASS or FAIL determination
    - Detailed justification for decision
    - Recommendations for risk mitigation
    - Audit trail of checks performed
    """

    return Task(
        description=description.strip(),
        agent=agent,
        expected_output=expected_output.strip(),
        context=context
    )


def create_transaction_task(agent: Agent, context: Dict[str, Any]) -> Task:
    """
    Create the transaction execution task.

    This is the third and final task in the sequential workflow.
    Depends on outputs from both analyst and compliance tasks.

    Args:
        agent: Transaction agent to assign this task
        context: Context including compliance_output, project_id, etc.

    Returns:
        Task configured for X402 transaction execution
    """
    compliance_output = context.get("compliance_output", "")

    description = f"""
    Execute the X402 transaction based on approved compliance status:

    Compliance Decision:
    {compliance_output}

    Your responsibilities:
    1. Verify compliance PASS status before proceeding
    2. Construct X402 protocol request payload
    3. Generate DID (Decentralized Identifier) signature
    4. Validate signature correctness
    5. Submit X402 request to protocol endpoint
    6. Handle any submission errors with retry logic
    7. Record request_id and transaction details
    8. Store execution metadata in agent_memory

    CRITICAL: Only execute if compliance status is PASS. If FAIL, log the rejection.
    """

    expected_output = """
    Transaction execution report containing:
    - Execution status (SUCCESS/FAILED/REJECTED)
    - X402 request_id (if successful)
    - DID signature details
    - Submission timestamp
    - Any error messages or retry attempts
    - Links to memory_id for audit trail
    - Next steps or follow-up actions
    """

    return Task(
        description=description.strip(),
        agent=agent,
        expected_output=expected_output.strip(),
        context=context
    )
