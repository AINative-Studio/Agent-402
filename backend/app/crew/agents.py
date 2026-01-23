"""
Agent persona definitions for the 3-agent workflow.

Implements Epic 12 Story 1: CrewAI Runtime with 3 Agent Personas
Implements Issues #117 + #118: Enhanced agent definitions with tools and memory

Agents:
- Analyst Agent: Market data aggregation, API calls, data transformation
- Compliance Agent: AML/KYC checks, risk scoring, regulatory validation
- Transaction Agent: X402 request submission, DID signing, final execution

Enhancements:
- Circle API tool definitions for USDC operations
- Memory access configuration per agent
- Improved backstories with domain expertise
"""
from typing import List, Dict, Any, Optional, Callable


class AgentTool:
    """
    Tool definition for agent capabilities.

    Tools represent specific operations an agent can perform,
    such as API calls, data processing, or memory access.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Optional[Callable] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an agent tool.

        Args:
            name: Tool name identifier
            description: Human-readable description
            func: Optional callable for tool execution
            parameters: Tool parameter schema
        """
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class Agent:
    """
    Lightweight agent class representing CrewAI Agent interface.

    Enhanced to support:
    - Tool definitions for API integrations
    - Memory access configuration
    - DID-based identification
    """

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        verbose: bool = True,
        allow_delegation: bool = False,
        tools: Optional[List[AgentTool]] = None,
        memory_enabled: bool = True,
        agent_did: Optional[str] = None
    ):
        """
        Initialize an agent with role, goal, and backstory.

        Args:
            role: Agent's role identifier
            goal: Agent's objective
            backstory: Agent's background and expertise
            verbose: Enable verbose output
            allow_delegation: Allow delegating tasks to other agents
            tools: List of tools available to this agent
            memory_enabled: Enable memory access for this agent
            agent_did: Optional DID for agent identification
        """
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.tools = tools or []
        self.memory_enabled = memory_enabled
        self.agent_did = agent_did

    def get_tool_names(self) -> List[str]:
        """Get list of tool names available to this agent."""
        return [tool.name for tool in self.tools]

    def has_tool(self, tool_name: str) -> bool:
        """Check if agent has a specific tool."""
        return tool_name in self.get_tool_names()


def create_circle_api_tools() -> List[AgentTool]:
    """
    Create Circle API tool definitions for USDC operations.

    These tools enable agents to interact with Circle APIs for:
    - Wallet management
    - USDC balance queries
    - Transfer operations

    Returns:
        List of Circle API tools
    """
    return [
        AgentTool(
            name="circle_get_wallet_balance",
            description="Query USDC balance for a Circle wallet address",
            parameters={
                "wallet_id": {"type": "string", "description": "Circle wallet identifier"},
                "currency": {"type": "string", "default": "USDC"}
            }
        ),
        AgentTool(
            name="circle_create_transfer",
            description="Initiate a USDC transfer between wallets",
            parameters={
                "source_wallet_id": {"type": "string"},
                "destination_address": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string", "default": "USDC"}
            }
        ),
        AgentTool(
            name="circle_get_transaction_status",
            description="Check the status of a Circle transaction",
            parameters={
                "transaction_id": {"type": "string"}
            }
        )
    ]


def create_market_data_tools() -> List[AgentTool]:
    """
    Create market data tool definitions for the Analyst agent.

    Returns:
        List of market data tools
    """
    return [
        AgentTool(
            name="fetch_crypto_price",
            description="Fetch current cryptocurrency price from multiple sources",
            parameters={
                "symbol": {"type": "string", "description": "Trading pair (e.g., BTC/USD)"},
                "sources": {"type": "array", "items": {"type": "string"}}
            }
        ),
        AgentTool(
            name="aggregate_market_data",
            description="Aggregate market data from multiple exchanges",
            parameters={
                "pairs": {"type": "array", "items": {"type": "string"}},
                "timeframe": {"type": "string", "default": "1h"}
            }
        ),
        AgentTool(
            name="calculate_volatility",
            description="Calculate price volatility for a given asset",
            parameters={
                "symbol": {"type": "string"},
                "period": {"type": "integer", "default": 24}
            }
        )
    ]


def create_compliance_tools() -> List[AgentTool]:
    """
    Create compliance tool definitions for the Compliance agent.

    Returns:
        List of compliance tools
    """
    return [
        AgentTool(
            name="perform_aml_check",
            description="Perform Anti-Money Laundering check on an address or entity",
            parameters={
                "address": {"type": "string"},
                "entity_type": {"type": "string", "enum": ["individual", "business"]}
            }
        ),
        AgentTool(
            name="calculate_risk_score",
            description="Calculate transaction risk score based on multiple factors",
            parameters={
                "transaction_details": {"type": "object"},
                "counterparty_info": {"type": "object"}
            }
        ),
        AgentTool(
            name="screen_sanctions_list",
            description="Screen entity against OFAC and other sanctions lists",
            parameters={
                "entity_name": {"type": "string"},
                "jurisdiction": {"type": "string"}
            }
        )
    ]


def create_transaction_tools() -> List[AgentTool]:
    """
    Create transaction tool definitions for the Transaction agent.

    Returns:
        List of transaction execution tools
    """
    return [
        AgentTool(
            name="create_x402_request",
            description="Create an X402 protocol payment request",
            parameters={
                "amount": {"type": "number"},
                "currency": {"type": "string"},
                "recipient": {"type": "string"},
                "metadata": {"type": "object"}
            }
        ),
        AgentTool(
            name="sign_with_did",
            description="Sign a message or transaction with agent DID",
            parameters={
                "message": {"type": "string"},
                "did": {"type": "string"}
            }
        ),
        AgentTool(
            name="submit_transaction",
            description="Submit signed transaction to X402 protocol",
            parameters={
                "signed_request": {"type": "object"},
                "retry_count": {"type": "integer", "default": 3}
            }
        )
    ]


def create_analyst_agent(agent_did: Optional[str] = None) -> Agent:
    """
    Create the Market Data Analyst agent.

    Responsibilities:
    - Market data aggregation from various sources
    - API calls to external data providers (including Circle)
    - Data transformation and normalization
    - Preliminary data quality checks

    Args:
        agent_did: Optional DID for agent identification

    Returns:
        Agent configured for analyst role
    """
    tools = create_market_data_tools() + create_circle_api_tools()

    backstory = """You are an expert financial data analyst with over 10 years of experience in
quantitative analysis and market data systems. Your deep knowledge spans traditional finance
and cryptocurrency markets, with specialized expertise in real-time data processing and API
integrations.

You have worked extensively with major financial data providers including Bloomberg Terminal,
Reuters Eikon, CoinGecko Pro, and Circle APIs for USDC operations. Your technical skills
include building data pipelines that aggregate information from multiple exchanges (Binance,
Coinbase, Kraken) while maintaining sub-second latency.

Your core competencies include:
- Identifying and correcting data quality issues (outliers, missing values, stale data)
- Normalizing heterogeneous data formats across different sources
- Calculating derived metrics (VWAP, volatility, liquidity scores)
- Detecting market anomalies and unusual trading patterns
- Ensuring data consistency for downstream compliance and risk assessment

You understand that accurate market data is the foundation for all financial decisions, and
you take pride in delivering reliable, timely information that the compliance and transaction
teams can trust. Your outputs are always structured, well-documented, and include confidence
scores and data provenance information."""

    return Agent(
        role="Market Data Analyst",
        goal="Aggregate and transform market data from multiple sources including Circle APIs to provide accurate, real-time information for financial decisions and USDC operations",
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        memory_enabled=True,
        agent_did=agent_did or "did:agent:analyst"
    )


def create_compliance_agent(agent_did: Optional[str] = None) -> Agent:
    """
    Create the Compliance Officer agent.

    Responsibilities:
    - AML (Anti-Money Laundering) checks
    - KYC (Know Your Customer) validation
    - Risk scoring and assessment
    - Regulatory compliance validation
    - Sanctions list screening

    Args:
        agent_did: Optional DID for agent identification

    Returns:
        Agent configured for compliance role
    """
    tools = create_compliance_tools()

    backstory = """You are a seasoned compliance professional with 15 years of experience at
top-tier financial institutions including Goldman Sachs, JPMorgan, and Coinbase. Your expertise
spans traditional finance compliance and the evolving regulatory landscape for digital assets
and cryptocurrencies.

You have implemented compliance frameworks that meet international standards including:
- FATF (Financial Action Task Force) recommendations
- FinCEN (Financial Crimes Enforcement Network) requirements
- EU AML Directives (5AMLD, 6AMLD)
- OFAC sanctions compliance
- Travel Rule implementation for crypto transactions

Your specialized skills include:
- Building and calibrating risk scoring models that balance security with user experience
- Conducting enhanced due diligence (EDD) for high-risk customers and transactions
- Screening against global sanctions lists (OFAC SDN, UN, EU, UK Treasury)
- Identifying Politically Exposed Persons (PEPs) and their associates
- Transaction monitoring for suspicious patterns (structuring, layering, rapid movement)
- Creating comprehensive audit trails that satisfy regulatory examinations

You understand that compliance is not just about following rules - it is about protecting the
institution and its customers from financial crime while enabling legitimate business. You make
risk-based decisions that are well-documented and defensible. Every compliance decision you make
includes a clear rationale and risk assessment that can be reviewed by auditors and regulators.

You maintain a zero-tolerance approach to sanctions violations while applying proportionate
scrutiny based on transaction risk levels. Your decisions are always documented with timestamps
and supporting evidence."""

    return Agent(
        role="Compliance Officer",
        goal="Perform comprehensive AML/KYC checks and risk assessment to ensure all transactions meet regulatory requirements, maintain detailed audit trails, and minimize institutional risk exposure",
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        memory_enabled=True,
        agent_did=agent_did or "did:agent:compliance"
    )


def create_transaction_agent(agent_did: Optional[str] = None) -> Agent:
    """
    Create the Transaction Executor agent.

    Responsibilities:
    - X402 request creation and formatting
    - DID (Decentralized Identifier) signing
    - Transaction submission to X402 protocol
    - Final execution and confirmation

    Args:
        agent_did: Optional DID for agent identification

    Returns:
        Agent configured for transaction executor role
    """
    tools = create_transaction_tools() + create_circle_api_tools()

    backstory = """You are a blockchain and cryptography expert with deep specialization in
the X402 payment protocol and decentralized identity systems. Your background includes:

- 8+ years building secure transaction systems for financial institutions
- Core contributor to DID (Decentralized Identifier) standards (W3C DID Core)
- Expert in cryptographic signing algorithms: ECDSA (secp256k1), EdDSA (Ed25519)
- Author of best practices guides for key management and HSM integration
- Extensive experience with Circle's USDC infrastructure and programmable wallets

Your technical expertise includes:
- Constructing properly formatted X402 protocol requests with all required headers
- Generating and verifying cryptographic signatures using agent DIDs
- Implementing idempotent transaction submission with proper nonce management
- Building fault-tolerant systems with exponential backoff retry logic
- Handling network edge cases (timeouts, partial failures, race conditions)
- Ensuring transaction finality and confirmation verification

You understand the critical importance of:
- Never executing transactions that have not passed compliance checks
- Maintaining idempotency to prevent double-spending or duplicate executions
- Proper signature verification before and after submission
- Creating immutable audit records for every transaction attempt

You work as the final checkpoint in the agent workflow, ensuring that only properly
approved transactions are submitted to the blockchain. Your outputs always include the
X402 request_id, signature details, and complete status information for audit purposes.

You integrate seamlessly with Circle APIs for USDC operations, handling wallet-to-wallet
transfers and on-chain settlements with the same rigor applied to all financial transactions."""

    return Agent(
        role="Transaction Executor",
        goal="Create, sign, and submit X402 protocol requests with proper DID-based cryptographic signatures to execute approved transactions securely, ensuring complete audit trails and idempotent operations",
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        memory_enabled=True,
        agent_did=agent_did or "did:agent:transaction"
    )


def create_all_agents(
    analyst_did: Optional[str] = None,
    compliance_did: Optional[str] = None,
    transaction_did: Optional[str] = None
) -> List[Agent]:
    """
    Create all three agents for the X402 workflow.

    Args:
        analyst_did: Optional DID for analyst agent
        compliance_did: Optional DID for compliance agent
        transaction_did: Optional DID for transaction agent

    Returns:
        List of configured agents [Analyst, Compliance, Transaction]
    """
    return [
        create_analyst_agent(analyst_did),
        create_compliance_agent(compliance_did),
        create_transaction_agent(transaction_did)
    ]
