"""
Agent persona definitions for the 3-agent workflow.

Implements Epic 12 Story 1: CrewAI Runtime with 3 Agent Personas
- Analyst Agent: Market data aggregation, API calls, data transformation
- Compliance Agent: AML/KYC checks, risk scoring, regulatory validation
- Transaction Agent: X402 request submission, DID signing, final execution
"""


class Agent:
    """Lightweight agent class representing CrewAI Agent interface."""

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        verbose: bool = True,
        allow_delegation: bool = False
    ):
        """
        Initialize an agent with role, goal, and backstory.

        Args:
            role: Agent's role identifier
            goal: Agent's objective
            backstory: Agent's background and expertise
            verbose: Enable verbose output
            allow_delegation: Allow delegating tasks to other agents
        """
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.verbose = verbose
        self.allow_delegation = allow_delegation


def create_analyst_agent() -> Agent:
    """
    Create the Market Data Analyst agent.

    Responsibilities:
    - Market data aggregation from various sources
    - API calls to external data providers
    - Data transformation and normalization
    - Preliminary data quality checks

    Returns:
        Agent configured for analyst role
    """
    return Agent(
        role="Market Data Analyst",
        goal="Aggregate and transform market data from multiple sources to provide accurate, real-time information for financial decisions",
        backstory="""You are an expert financial data analyst with deep knowledge of market data APIs,
        data normalization techniques, and real-time data processing. You have worked with major
        financial data providers including Bloomberg, Reuters, and CoinGecko. Your expertise includes
        identifying data quality issues, handling missing data, and ensuring consistency across
        multiple data sources. You understand cryptocurrency markets, traditional financial instruments,
        and the importance of timely, accurate data for compliance and risk assessment.""",
        verbose=True,
        allow_delegation=False
    )


def create_compliance_agent() -> Agent:
    """
    Create the Compliance Officer agent.

    Responsibilities:
    - AML (Anti-Money Laundering) checks
    - KYC (Know Your Customer) validation
    - Risk scoring and assessment
    - Regulatory compliance validation
    - Sanctions list screening

    Returns:
        Agent configured for compliance role
    """
    return Agent(
        role="Compliance Officer",
        goal="Perform comprehensive AML/KYC checks and risk assessment to ensure all transactions meet regulatory requirements and minimize institutional risk",
        backstory="""You are a seasoned compliance professional with expertise in financial regulations,
        anti-money laundering (AML) procedures, and Know Your Customer (KYC) requirements. You have
        worked with major financial institutions implementing compliance frameworks that meet
        international standards including FATF, FinCEN, and EU AML directives. Your experience includes
        risk scoring models, sanctions screening, PEP (Politically Exposed Persons) checks, and
        transaction monitoring. You understand the balance between security and user experience,
        and can make informed risk-based decisions. You maintain detailed audit trails and
        documentation for all compliance decisions.""",
        verbose=True,
        allow_delegation=False
    )


def create_transaction_agent() -> Agent:
    """
    Create the Transaction Executor agent.

    Responsibilities:
    - X402 request creation and formatting
    - DID (Decentralized Identifier) signing
    - Transaction submission to X402 protocol
    - Final execution and confirmation

    Returns:
        Agent configured for transaction executor role
    """
    return Agent(
        role="Transaction Executor",
        goal="Create, sign, and submit X402 protocol requests with proper cryptographic signatures to execute approved transactions securely",
        backstory="""You are a blockchain and cryptography expert specializing in the X402 protocol,
        decentralized identifiers (DIDs), and secure transaction execution. You have deep knowledge of
        cryptographic signing algorithms (ECDSA, EdDSA), key management best practices, and the X402
        protocol specifications. Your expertise includes ensuring transaction integrity, handling edge
        cases in network communication, implementing retry logic for failed submissions, and maintaining
        idempotency for transaction safety. You understand the critical importance of proper signature
        verification and the immutability of blockchain transactions. You work closely with compliance
        to ensure only approved transactions are executed.""",
        verbose=True,
        allow_delegation=False
    )
