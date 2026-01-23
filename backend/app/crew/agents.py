"""
Agent persona definitions for the 3-agent workflow.

Implements Epic 12 Story 1: CrewAI Runtime with 3 Agent Personas
Issue #115: Gemini AI Integration

- Analyst Agent: Market data aggregation, API calls, data transformation
  Model: gemini-pro (deep analysis)
- Compliance Agent: AML/KYC checks, risk scoring, regulatory validation
  Model: gemini-pro (thorough checks)
- Transaction Agent: X402 request submission, DID signing, final execution
  Model: gemini-1.5-flash (fast execution)
"""
from typing import Dict, Any, List, Optional


class Agent:
    """
    Lightweight agent class representing CrewAI Agent interface.

    Integrated with Gemini LLM for AI-powered decision making.
    """

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        model: str = "gemini-pro",
        verbose: bool = True,
        allow_delegation: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize an agent with role, goal, and backstory.

        Args:
            role: Agent's role identifier
            goal: Agent's objective
            backstory: Agent's background and expertise
            model: Gemini model to use (gemini-pro, gemini-1.5-flash)
            verbose: Enable verbose output
            allow_delegation: Allow delegating tasks to other agents
            tools: List of tool definitions for function calling
        """
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model = model
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.tools = tools or []

    def get_system_prompt(self) -> str:
        """
        Generate system prompt for Gemini from agent configuration.

        Returns:
            System prompt string combining role, goal, and backstory
        """
        return f"""You are a {self.role}.

Goal: {self.goal}

Background: {self.backstory}

Always respond in a structured format and provide clear reasoning for your decisions.
When using tools, explain why you're calling each tool and what you expect to learn from it."""


# Circle Tool Definitions for Function Calling
CIRCLE_TOOLS = [
    {
        "name": "create_wallet",
        "description": "Create a new Circle wallet for USDC operations",
        "parameters": {
            "type": "object",
            "properties": {
                "blockchain": {
                    "type": "string",
                    "description": "Target blockchain (e.g., ETH-SEPOLIA, MATIC-MUMBAI)",
                    "enum": ["ETH-SEPOLIA", "MATIC-MUMBAI", "ETH", "MATIC"]
                },
                "wallet_set_id": {
                    "type": "string",
                    "description": "Optional wallet set ID for grouping"
                }
            },
            "required": ["blockchain"]
        }
    },
    {
        "name": "get_wallet_balance",
        "description": "Get USDC balance for a Circle wallet",
        "parameters": {
            "type": "object",
            "properties": {
                "wallet_id": {
                    "type": "string",
                    "description": "Circle wallet identifier"
                }
            },
            "required": ["wallet_id"]
        }
    },
    {
        "name": "transfer_usdc",
        "description": "Transfer USDC between Circle wallets",
        "parameters": {
            "type": "object",
            "properties": {
                "source_wallet_id": {
                    "type": "string",
                    "description": "Source Circle wallet ID"
                },
                "destination_wallet_id": {
                    "type": "string",
                    "description": "Destination Circle wallet ID"
                },
                "amount": {
                    "type": "string",
                    "description": "Transfer amount in USDC (e.g., '100.00')"
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Unique key for idempotent operation"
                }
            },
            "required": ["source_wallet_id", "destination_wallet_id", "amount"]
        }
    },
    {
        "name": "get_transfer_status",
        "description": "Get status of a USDC transfer",
        "parameters": {
            "type": "object",
            "properties": {
                "transfer_id": {
                    "type": "string",
                    "description": "Circle transfer identifier"
                }
            },
            "required": ["transfer_id"]
        }
    }
]

# Market Data Tool Definitions
MARKET_DATA_TOOLS = [
    {
        "name": "get_usdc_price",
        "description": "Get current USDC price and market data",
        "parameters": {
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "description": "Quote currency (USD, EUR, etc.)",
                    "default": "USD"
                }
            }
        }
    },
    {
        "name": "get_market_volatility",
        "description": "Get current market volatility indicators",
        "parameters": {
            "type": "object",
            "properties": {
                "asset": {
                    "type": "string",
                    "description": "Asset symbol (USDC, ETH, BTC, etc.)"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Timeframe for volatility (1h, 24h, 7d)",
                    "enum": ["1h", "24h", "7d"]
                }
            },
            "required": ["asset"]
        }
    }
]

# Compliance Tool Definitions
COMPLIANCE_TOOLS = [
    {
        "name": "check_aml_status",
        "description": "Check AML (Anti-Money Laundering) status for an address or entity",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address or entity identifier"
                },
                "check_type": {
                    "type": "string",
                    "description": "Type of AML check",
                    "enum": ["basic", "enhanced", "full"]
                }
            },
            "required": ["address"]
        }
    },
    {
        "name": "check_sanctions_list",
        "description": "Check if an address or entity is on sanctions lists",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address or entity identifier"
                },
                "lists": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sanctions lists to check (OFAC, UN, EU)"
                }
            },
            "required": ["address"]
        }
    },
    {
        "name": "calculate_risk_score",
        "description": "Calculate risk score for a transaction or entity",
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_amount": {
                    "type": "string",
                    "description": "Transaction amount in USDC"
                },
                "source_address": {
                    "type": "string",
                    "description": "Source wallet address"
                },
                "destination_address": {
                    "type": "string",
                    "description": "Destination wallet address"
                },
                "transaction_type": {
                    "type": "string",
                    "description": "Type of transaction",
                    "enum": ["transfer", "payment", "withdrawal", "deposit"]
                }
            },
            "required": ["transaction_amount", "source_address", "destination_address"]
        }
    }
]


def create_analyst_agent() -> Agent:
    """
    Create the Market Data Analyst agent.

    Uses gemini-pro for deep analysis of market conditions.

    Responsibilities:
    - Market data aggregation from various sources
    - API calls to external data providers
    - Data transformation and normalization
    - Preliminary data quality checks

    Returns:
        Agent configured for analyst role with gemini-pro model
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
        model="gemini-pro",
        verbose=True,
        allow_delegation=False,
        tools=MARKET_DATA_TOOLS
    )


def create_compliance_agent() -> Agent:
    """
    Create the Compliance Officer agent.

    Uses gemini-pro for thorough compliance checks.

    Responsibilities:
    - AML (Anti-Money Laundering) checks
    - KYC (Know Your Customer) validation
    - Risk scoring and assessment
    - Regulatory compliance validation
    - Sanctions list screening

    Returns:
        Agent configured for compliance role with gemini-pro model
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
        model="gemini-pro",
        verbose=True,
        allow_delegation=False,
        tools=COMPLIANCE_TOOLS
    )


def create_transaction_agent() -> Agent:
    """
    Create the Transaction Executor agent.

    Uses gemini-1.5-flash for fast execution.

    Responsibilities:
    - X402 request creation and formatting
    - DID (Decentralized Identifier) signing
    - Transaction submission to X402 protocol
    - Final execution and confirmation

    Returns:
        Agent configured for transaction executor role with gemini-flash model
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
        model="gemini-1.5-flash",
        verbose=True,
        allow_delegation=False,
        tools=CIRCLE_TOOLS
    )


def get_all_agents() -> Dict[str, Agent]:
    """
    Get all configured agents.

    Returns:
        Dictionary mapping agent type to Agent instance
    """
    return {
        "analyst": create_analyst_agent(),
        "compliance": create_compliance_agent(),
        "transaction": create_transaction_agent()
    }


def get_agent_by_type(agent_type: str) -> Optional[Agent]:
    """
    Get a specific agent by type.

    Args:
        agent_type: Type of agent (analyst, compliance, transaction)

    Returns:
        Agent instance or None if type not found
    """
    agents = get_all_agents()
    return agents.get(agent_type)
