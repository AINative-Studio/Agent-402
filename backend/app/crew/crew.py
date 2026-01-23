"""
Main CrewAI orchestration for Agent-402.

Implements Epic 12 Story 1: Sequential 3-agent workflow with memory persistence.
Implements Issues #117 + #118: Enhanced orchestration with error handling and retries.
Implements Gemini Integration: LLM-powered agent decision-making.

Process: Analyst -> Compliance -> Transaction

Features:
- Each agent stores outputs in agent_memory with proper metadata
- Error handling with structured error responses
- Retry logic for transient failures
- Crew-level memory sharing via consistent run_id
- Final output includes X402 request_id
- Optional Gemini LLM integration for real decision-making (use_llm flag)
"""
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from app.crew.agents import (
    create_analyst_agent,
    create_compliance_agent,
    create_transaction_agent,
    Agent
)
from app.crew.tasks import (
    create_analyst_task,
    create_compliance_task,
    create_transaction_task,
    Task
)
from app.services.agent_memory_service import get_agent_memory_service
from app.services.x402_service import x402_service
from app.services.compliance_service import compliance_service
from app.schemas.compliance_events import (
    ComplianceEventCreate,
    ComplianceEventType,
    ComplianceOutcome
)
from app.schemas.x402_requests import X402RequestStatus

logger = logging.getLogger(__name__)

# Response schemas for structured LLM output
ANALYST_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "data_sources": {"type": "array", "items": {"type": "string"}},
        "market_data": {"type": "object"},
        "quality_score": {"type": "number"},
        "recommendation": {"type": "string"}
    },
    "required": ["data_sources", "market_data", "quality_score", "recommendation"]
}

COMPLIANCE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "aml_check": {"type": "string", "enum": ["PASS", "FAIL"]},
        "kyc_check": {"type": "string", "enum": ["PASS", "FAIL"]},
        "sanctions_screening": {"type": "string", "enum": ["CLEAR", "FLAGGED"]},
        "risk_score": {"type": "number"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "compliance_status": {"type": "string", "enum": ["PASS", "FAIL"]},
        "justification": {"type": "string"}
    },
    "required": ["aml_check", "kyc_check", "risk_score", "compliance_status"]
}

TRANSACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["execute", "abort", "retry"]},
        "transaction_details": {"type": "object"},
        "signature_verified": {"type": "boolean"},
        "notes": {"type": "string"}
    },
    "required": ["action"]
}


class Process(Enum):
    """Process execution types."""
    sequential = "sequential"
    hierarchical = "hierarchical"


class Crew:
    """Simplified CrewAI Crew implementation."""

    def __init__(
        self,
        agents: List[Agent],
        tasks: List[Task],
        process: Process = Process.sequential,
        verbose: bool = True
    ):
        """
        Initialize crew with agents and tasks.

        Args:
            agents: List of agents in the crew
            tasks: List of tasks to execute
            process: Execution process (sequential or hierarchical)
            verbose: Enable verbose output
        """
        self.agents = agents
        self.tasks = tasks
        self.process = process
        self.verbose = verbose

    def kickoff(self) -> str:
        """
        Execute the crew workflow.

        Returns:
            Final output from the last task
        """
        if self.process == Process.sequential:
            return self._execute_sequential()
        else:
            raise NotImplementedError("Only sequential process is supported")

    def _execute_sequential(self) -> str:
        """
        Execute tasks sequentially.

        Returns:
            Final task output
        """
        outputs = []
        for task in self.tasks:
            if self.verbose:
                logger.info(f"Executing task for {task.agent.role}")

            # Simulate task execution
            output = f"Output from {task.agent.role}: Completed successfully"
            outputs.append(output)

        return outputs[-1] if outputs else "No output"


class X402Crew:
    """
    Main crew orchestration for Agent-402 workflow.

    Manages the 3-agent sequential workflow:
    1. Analyst Agent - Market data aggregation
    2. Compliance Agent - AML/KYC checks
    3. Transaction Agent - X402 submission

    Each agent stores outputs in agent_memory.
    Returns final X402 request_id.

    Features:
    - use_llm=True: Uses Gemini for real LLM-powered decisions
    - use_llm=False: Uses simulated/hardcoded responses (for testing)
    """

    def __init__(
        self,
        project_id: str,
        run_id: Optional[str] = None,
        use_llm: bool = False
    ):
        """
        Initialize X402 crew with project and run identifiers.

        Args:
            project_id: Project identifier
            run_id: Optional run identifier (generated if not provided)
            use_llm: Whether to use Gemini LLM for real decision-making
                     (default: False for backward compatibility)
        """
        self.project_id = project_id
        self.run_id = run_id or self._generate_run_id()
        self.use_llm = use_llm
        self._gemini_service = None

        # Create the 3 agent personas
        self.agents = [
            create_analyst_agent(),
            create_compliance_agent(),
            create_transaction_agent()
        ]

        # Agent IDs for memory storage
        self.agent_ids = {
            "analyst": "agent_analyst",
            "compliance": "agent_compliance",
            "transaction": "agent_transaction"
        }

    def _get_gemini_service(self):
        """
        Get or create Gemini service instance (lazy loading).

        Returns:
            GeminiService instance or None if unavailable
        """
        if self._gemini_service is None and self.use_llm:
            try:
                from app.services.gemini_service import get_gemini_service
                self._gemini_service = get_gemini_service()
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Gemini service: {e}. "
                    "Falling back to simulation mode."
                )
                self.use_llm = False
        return self._gemini_service

    def _convert_agent_tools_to_gemini_format(self, agent: Agent) -> List[Dict[str, Any]]:
        """
        Convert agent tools to Gemini-compatible format.

        Args:
            agent: Agent with tools to convert

        Returns:
            List of tools in Gemini format
        """
        gemini_tools = []
        for tool in agent.tools:
            gemini_tool = tool.to_dict()
            gemini_tools.append(gemini_tool)
        return gemini_tools

    def _generate_run_id(self) -> str:
        """
        Generate unique run identifier.

        Returns:
            Run ID in format: run_{uuid}
        """
        return f"run_{uuid.uuid4().hex[:16]}"

    def create_tasks(self, input_data: Dict[str, Any]) -> List[Task]:
        """
        Create sequential tasks for the workflow.

        Args:
            input_data: Input data including query and other context

        Returns:
            List of tasks in execution order
        """
        # Task 1: Analyst - Market data aggregation
        analyst_task = create_analyst_task(
            self.agents[0],
            {
                "query": input_data.get("query", ""),
                "project_id": self.project_id,
                "run_id": self.run_id
            }
        )

        # Task 2: Compliance - AML/KYC checks
        compliance_task = create_compliance_task(
            self.agents[1],
            {
                "analyst_output": "{analyst_output}",  # Placeholder for sequential context
                "project_id": self.project_id,
                "run_id": self.run_id
            }
        )

        # Task 3: Transaction - X402 submission
        transaction_task = create_transaction_task(
            self.agents[2],
            {
                "compliance_output": "{compliance_output}",  # Placeholder for sequential context
                "project_id": self.project_id,
                "run_id": self.run_id
            }
        )

        return [analyst_task, compliance_task, transaction_task]

    def create_crew(self) -> Crew:
        """
        Create the crew instance with agents and tasks.

        Returns:
            Configured Crew instance
        """
        tasks = self.create_tasks({"query": "Default query"})
        return Crew(
            agents=self.agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )

    async def store_agent_output(
        self,
        agent_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store agent output in agent_memory.

        Args:
            agent_id: Agent identifier
            memory_type: Type of memory (e.g., "analyst_output")
            content: Memory content
            metadata: Optional additional metadata

        Returns:
            Memory record with memory_id
        """
        memory_service = get_agent_memory_service()

        memory = await memory_service.store_memory(
            project_id=self.project_id,
            agent_id=agent_id,
            run_id=self.run_id,
            memory_type=memory_type,
            content=content,
            namespace="x402_workflow",
            metadata=metadata or {}
        )

        logger.info(
            f"Stored {memory_type} for {agent_id}",
            extra={
                "memory_id": memory.get("memory_id"),
                "run_id": self.run_id,
                "project_id": self.project_id
            }
        )

        return memory

    def _execute_crew(self, input_data: Dict[str, Any]) -> str:
        """
        Execute the crew workflow (synchronous simulation).

        In production, this would delegate to actual CrewAI execution.
        For now, simulates the workflow.

        Args:
            input_data: Input data for workflow

        Returns:
            Final workflow output
        """
        crew = self.create_crew()
        return crew.kickoff()

    async def _execute_analyst_task(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Execute analyst task: Market data aggregation.

        Uses Gemini LLM when use_llm=True, otherwise falls back to simulation.

        Args:
            query: User query for market data

        Returns:
            Analyst output with market data
        """
        logger.info(f"Executing analyst task for query: {query}")

        if self.use_llm:
            analyst_output = await self._execute_analyst_task_with_llm(query)
        else:
            analyst_output = self._execute_analyst_task_simulated(query)

        # Store in agent_memory
        memory = await self.store_agent_output(
            agent_id=self.agent_ids["analyst"],
            memory_type="analyst_output",
            content=str(analyst_output),
            metadata={"query": query, "use_llm": self.use_llm}
        )

        analyst_output["memory_id"] = memory.get("memory_id")
        return analyst_output

    def _execute_analyst_task_simulated(self, query: str) -> Dict[str, Any]:
        """
        Execute analyst task with simulated/hardcoded response.

        Args:
            query: User query for market data

        Returns:
            Simulated analyst output
        """
        return {
            "query": query,
            "data_sources": ["CoinGecko", "Binance", "Kraken"],
            "market_data": {
                "BTC_USD": 45000.00,
                "ETH_USD": 3200.00,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "quality_score": 0.95,
            "recommendation": "Data quality is high, proceed with transaction"
        }

    async def _execute_analyst_task_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Execute analyst task using Gemini LLM.

        Args:
            query: User query for market data

        Returns:
            LLM-generated analyst output
        """
        gemini = self._get_gemini_service()
        if gemini is None:
            logger.warning("Gemini unavailable, falling back to simulation")
            return self._execute_analyst_task_simulated(query)

        analyst_agent = self.agents[0]  # Analyst agent

        # Build prompt with agent context
        prompt = f"""
You are a {analyst_agent.role}.

Goal: {analyst_agent.goal}

Background: {analyst_agent.backstory[:500]}...

Task: Analyze and aggregate market data based on the following query:
{query}

Provide a structured response with:
1. Data sources you would query
2. Market data findings
3. Data quality score (0.0-1.0)
4. Your recommendation

Respond with valid JSON.
"""

        try:
            # Get tools for function calling
            tools = self._convert_agent_tools_to_gemini_format(analyst_agent)

            # Try structured generation
            result = await gemini.generate_structured(
                prompt=prompt,
                response_schema=ANALYST_RESPONSE_SCHEMA,
                timeout_seconds=30
            )

            parsed = result.get("parsed", {})
            return {
                "query": query,
                "data_sources": parsed.get("data_sources", ["CoinGecko", "Binance"]),
                "market_data": parsed.get("market_data", {
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }),
                "quality_score": parsed.get("quality_score", 0.9),
                "recommendation": parsed.get("recommendation", "Proceed with caution"),
                "llm_model": result.get("model"),
                "llm_latency_ms": result.get("latency_ms")
            }
        except Exception as e:
            logger.error(f"Gemini analyst task failed: {e}")
            logger.info("Falling back to simulated analyst output")
            return self._execute_analyst_task_simulated(query)

    async def _execute_compliance_task(
        self,
        analyst_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute compliance task: AML/KYC checks and risk scoring.

        Uses Gemini LLM when use_llm=True, otherwise falls back to simulation.

        Args:
            analyst_output: Output from analyst task

        Returns:
            Compliance output with risk assessment
        """
        logger.info("Executing compliance task")

        if self.use_llm:
            compliance_output = await self._execute_compliance_task_with_llm(analyst_output)
        else:
            compliance_output = self._execute_compliance_task_simulated(analyst_output)

        # Determine if compliance passed
        risk_score = compliance_output.get("risk_score", 0.5)
        compliance_passed = compliance_output.get("compliance_status") == "PASS"

        # Store in agent_memory
        memory = await self.store_agent_output(
            agent_id=self.agent_ids["compliance"],
            memory_type="compliance_output",
            content=str(compliance_output),
            metadata={"risk_score": risk_score, "use_llm": self.use_llm}
        )

        compliance_output["memory_id"] = memory.get("memory_id")

        # Create compliance event
        event_data = ComplianceEventCreate(
            agent_id=self.agent_ids["compliance"],
            event_type=ComplianceEventType.KYC_CHECK,
            outcome=ComplianceOutcome.PASS if compliance_passed else ComplianceOutcome.FAIL,
            risk_score=risk_score,
            details=compliance_output,
            run_id=self.run_id
        )

        compliance_event = await compliance_service.create_event(
            project_id=self.project_id,
            event_data=event_data
        )

        compliance_output["event_id"] = compliance_event.event_id if hasattr(compliance_event, 'event_id') else compliance_event.get("event_id")

        return compliance_output

    def _execute_compliance_task_simulated(
        self,
        analyst_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute compliance task with simulated/hardcoded response.

        Args:
            analyst_output: Output from analyst task

        Returns:
            Simulated compliance output
        """
        risk_score = 0.15  # Low risk (0.0 = lowest, 1.0 = highest)
        compliance_passed = risk_score < 0.5

        return {
            "aml_check": "PASS",
            "kyc_check": "PASS",
            "sanctions_screening": "CLEAR",
            "risk_score": risk_score,
            "risk_level": "low",
            "compliance_status": "PASS" if compliance_passed else "FAIL",
            "analyst_memory_id": analyst_output.get("memory_id"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    async def _execute_compliance_task_with_llm(
        self,
        analyst_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute compliance task using Gemini LLM.

        Args:
            analyst_output: Output from analyst task

        Returns:
            LLM-generated compliance output
        """
        gemini = self._get_gemini_service()
        if gemini is None:
            logger.warning("Gemini unavailable, falling back to simulation")
            return self._execute_compliance_task_simulated(analyst_output)

        compliance_agent = self.agents[1]  # Compliance agent

        # Build prompt with agent context and analyst output
        prompt = f"""
You are a {compliance_agent.role}.

Goal: {compliance_agent.goal}

Background: {compliance_agent.backstory[:500]}...

Previous Analysis from Market Data Analyst:
{json.dumps(analyst_output, indent=2, default=str)}

Task: Perform comprehensive compliance and risk assessment based on the analyst's findings.

You must:
1. Review the transaction details against AML/KYC requirements
2. Perform sanctions list screening (assume CLEAR unless data suggests otherwise)
3. Calculate a risk score (0.0 = lowest risk, 1.0 = highest risk)
4. Make a PASS/FAIL determination with justification

For this analysis, assume:
- This is a legitimate crypto transaction
- The counterparty is a known entity
- No sanctions flags detected

Respond with valid JSON.
"""

        try:
            result = await gemini.generate_structured(
                prompt=prompt,
                response_schema=COMPLIANCE_RESPONSE_SCHEMA,
                timeout_seconds=30
            )

            parsed = result.get("parsed", {})
            risk_score = parsed.get("risk_score", 0.5)
            compliance_status = parsed.get("compliance_status", "PASS" if risk_score < 0.5 else "FAIL")

            return {
                "aml_check": parsed.get("aml_check", "PASS"),
                "kyc_check": parsed.get("kyc_check", "PASS"),
                "sanctions_screening": parsed.get("sanctions_screening", "CLEAR"),
                "risk_score": risk_score,
                "risk_level": parsed.get("risk_level", "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"),
                "compliance_status": compliance_status,
                "justification": parsed.get("justification", ""),
                "analyst_memory_id": analyst_output.get("memory_id"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "llm_model": result.get("model"),
                "llm_latency_ms": result.get("latency_ms")
            }
        except Exception as e:
            logger.error(f"Gemini compliance task failed: {e}")
            logger.info("Falling back to simulated compliance output")
            return self._execute_compliance_task_simulated(analyst_output)

    async def _execute_transaction_task(
        self,
        compliance_output: Dict[str, Any],
        analyst_output: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute transaction task: X402 request submission.

        Uses Gemini LLM when use_llm=True for execution planning,
        otherwise falls back to direct execution.

        Args:
            compliance_output: Output from compliance task
            analyst_output: Output from analyst task
            input_data: Original input data

        Returns:
            Transaction output with request_id
        """
        logger.info("Executing transaction task")

        # Check compliance status
        if compliance_output.get("compliance_status") != "PASS":
            logger.warning("Compliance check failed, aborting transaction")
            raise Exception("Compliance check failed - transaction aborted")

        # Get LLM guidance if enabled
        llm_guidance = None
        if self.use_llm:
            llm_guidance = await self._get_transaction_llm_guidance(
                compliance_output, analyst_output, input_data
            )

        # Build X402 request payload
        request_payload = self._build_transaction_payload(
            compliance_output, analyst_output, input_data, llm_guidance
        )

        # Create X402 request
        x402_request = await x402_service.create_request(
            project_id=self.project_id,
            agent_id=self.agent_ids["transaction"],
            task_id="transaction_task",
            run_id=self.run_id,
            request_payload=request_payload,
            signature="simulated_signature_" + uuid.uuid4().hex[:16],
            status=X402RequestStatus.PENDING,
            linked_memory_ids=[
                analyst_output.get("memory_id", ""),
                compliance_output.get("memory_id", "")
            ],
            linked_compliance_ids=[
                compliance_output.get("event_id", "")
            ],
            metadata={
                "workflow": "x402_crew",
                "run_id": self.run_id,
                "use_llm": self.use_llm
            }
        )

        transaction_output = {
            "status": "SUCCESS",
            "request_id": x402_request.get("request_id"),
            "signature": "simulated_signature",
            "analyst_memory_id": analyst_output.get("memory_id"),
            "compliance_memory_id": compliance_output.get("memory_id"),
            "compliance_event_id": compliance_output.get("event_id"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Add LLM metadata if available
        if llm_guidance:
            transaction_output["llm_action"] = llm_guidance.get("action")
            transaction_output["llm_model"] = llm_guidance.get("llm_model")
            transaction_output["llm_latency_ms"] = llm_guidance.get("llm_latency_ms")

        # Store in agent_memory
        memory = await self.store_agent_output(
            agent_id=self.agent_ids["transaction"],
            memory_type="transaction_output",
            content=str(transaction_output),
            metadata={
                "request_id": x402_request.get("request_id"),
                "use_llm": self.use_llm
            }
        )

        transaction_output["memory_id"] = memory.get("memory_id")

        return transaction_output

    def _build_transaction_payload(
        self,
        compliance_output: Dict[str, Any],
        analyst_output: Dict[str, Any],
        input_data: Dict[str, Any],
        llm_guidance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build the X402 request payload.

        Args:
            compliance_output: Output from compliance task
            analyst_output: Output from analyst task
            input_data: Original input data
            llm_guidance: Optional LLM guidance for transaction

        Returns:
            X402 request payload
        """
        payload = {
            "method": "POST",
            "url": "https://x402.protocol.example/transactions",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "query": input_data.get("query"),
                "market_data": analyst_output.get("market_data"),
                "compliance_status": compliance_output.get("compliance_status"),
                "risk_score": compliance_output.get("risk_score")
            }
        }

        # Add LLM guidance to payload if available
        if llm_guidance:
            payload["body"]["llm_action"] = llm_guidance.get("action")
            payload["body"]["llm_notes"] = llm_guidance.get("notes")

        return payload

    async def _get_transaction_llm_guidance(
        self,
        compliance_output: Dict[str, Any],
        analyst_output: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get LLM guidance for transaction execution.

        Args:
            compliance_output: Output from compliance task
            analyst_output: Output from analyst task
            input_data: Original input data

        Returns:
            LLM guidance dict or None if unavailable
        """
        gemini = self._get_gemini_service()
        if gemini is None:
            return None

        transaction_agent = self.agents[2]  # Transaction agent

        prompt = f"""
You are a {transaction_agent.role}.

Goal: {transaction_agent.goal}

Background: {transaction_agent.backstory[:500]}...

Compliance Decision:
{json.dumps(compliance_output, indent=2, default=str)}

Market Analysis:
{json.dumps(analyst_output, indent=2, default=str)}

Original Request:
{json.dumps(input_data, indent=2, default=str)}

Task: Based on the approved compliance status and market analysis,
determine the action for transaction execution.

Options:
- "execute": Proceed with the transaction
- "retry": Wait and retry later (market conditions suboptimal)
- "abort": Abort despite compliance pass (safety concern)

Respond with valid JSON.
"""

        try:
            result = await gemini.generate_structured(
                prompt=prompt,
                response_schema=TRANSACTION_RESPONSE_SCHEMA,
                timeout_seconds=15  # Fast model for transaction agent
            )

            parsed = result.get("parsed", {})
            return {
                "action": parsed.get("action", "execute"),
                "transaction_details": parsed.get("transaction_details", {}),
                "signature_verified": parsed.get("signature_verified", True),
                "notes": parsed.get("notes", ""),
                "llm_model": result.get("model"),
                "llm_latency_ms": result.get("latency_ms")
            }
        except Exception as e:
            logger.error(f"Gemini transaction guidance failed: {e}")
            return None

    async def kickoff(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete 3-agent workflow.

        Args:
            input_data: Input data including query

        Returns:
            Final result with request_id and all outputs
        """
        logger.info(
            f"Starting X402 crew workflow for project {self.project_id}",
            extra={"run_id": self.run_id, "input_data": input_data}
        )

        try:
            # Step 1: Analyst - Market data aggregation
            analyst_output = await self._execute_analyst_task(
                query=input_data.get("query", "")
            )

            # Step 2: Compliance - AML/KYC checks
            compliance_output = await self._execute_compliance_task(
                analyst_output=analyst_output
            )

            # Step 3: Transaction - X402 submission
            transaction_output = await self._execute_transaction_task(
                compliance_output=compliance_output,
                analyst_output=analyst_output,
                input_data=input_data
            )

            # Build final result
            result = {
                "status": "completed",
                "run_id": self.run_id,
                "request_id": transaction_output.get("request_id"),
                "analyst_output": analyst_output,
                "compliance_output": compliance_output,
                "transaction_output": transaction_output,
                "memory_ids": [
                    analyst_output.get("memory_id"),
                    compliance_output.get("memory_id"),
                    transaction_output.get("memory_id")
                ],
                "compliance_event_id": compliance_output.get("event_id")
            }

            logger.info(
                f"X402 crew workflow completed successfully",
                extra={
                    "run_id": self.run_id,
                    "request_id": transaction_output.get("request_id")
                }
            )

            return result

        except Exception as e:
            logger.error(
                f"X402 crew workflow failed: {e}",
                extra={"run_id": self.run_id, "error": str(e)}
            )
            raise
