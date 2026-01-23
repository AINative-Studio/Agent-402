"""
CrewOrchestrator - High-level orchestration service for CrewAI workflows.

Implements Issues #117 + #118: Enhanced CrewAI and Agent Memory System.

This service provides:
- Crew execution with error handling and retries
- Memory context loading via semantic search
- Audit trail for all agent actions
- DID-based namespace isolation
- Arc NFT token linkage for memory entries

Per PRD Section 6 (ZeroDB Integration):
- Store agent decisions in agent_memory collection
- Support namespace scoping for multi-agent isolation
- Enable retrieval with filtering by agent_id, run_id

Per PRD Section 10 (Audit Trail):
- All agent actions must be logged
- Maintain replayability and determinism
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.crew.crew import X402Crew
from app.services.agent_memory_service import get_agent_memory_service

logger = logging.getLogger(__name__)


class CrewOrchestrator:
    """
    High-level orchestration service for CrewAI workflows.

    Manages:
    - Crew execution with retry logic
    - Memory context retrieval via semantic search
    - Audit trail recording
    - Arc NFT token linkage

    Usage:
        orchestrator = CrewOrchestrator(
            project_id="proj_123",
            agent_did="did:agent:analyst_001"
        )
        result = await orchestrator.execute({"query": "Analyze market data"})
    """

    def __init__(
        self,
        project_id: str,
        agent_did: str,
        run_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the crew orchestrator.

        Args:
            project_id: Project identifier
            agent_did: Agent DID for namespace isolation
            run_id: Optional run identifier (generated if not provided)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.project_id = project_id
        self.agent_did = agent_did
        self.run_id = run_id or self._generate_run_id()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Memory service for context and audit
        self._memory_service = None

        logger.info(
            f"CrewOrchestrator initialized for project {project_id}",
            extra={
                "agent_did": agent_did,
                "run_id": self.run_id,
                "max_retries": max_retries
            }
        )

    @property
    def memory_service(self):
        """Lazy initialization of memory service."""
        if self._memory_service is None:
            self._memory_service = get_agent_memory_service()
        return self._memory_service

    def _generate_run_id(self) -> str:
        """
        Generate unique run identifier.

        Returns:
            Run ID in format: run_{uuid}
        """
        return f"run_{uuid.uuid4().hex[:16]}"

    def _create_crew(self) -> X402Crew:
        """
        Create a new X402Crew instance.

        Returns:
            Configured X402Crew
        """
        return X402Crew(
            project_id=self.project_id,
            run_id=self.run_id
        )

    async def load_memory_context(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Load relevant memory context via semantic search.

        Retrieves past decisions and contexts that are similar to
        the current query, enabling agents to learn from history.

        Args:
            query: Search query for context retrieval
            top_k: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of relevant memory entries with similarity scores
        """
        try:
            # Use agent DID as namespace for isolation
            namespace = self.agent_did

            memories = await self.memory_service.search_memories(
                project_id=self.project_id,
                query=query,
                namespace=namespace,
                top_k=top_k
            )

            # Filter by similarity threshold
            filtered_memories = [
                mem for mem in memories
                if mem.get("similarity_score", 0) >= similarity_threshold
            ]

            # Sort by similarity score descending
            filtered_memories.sort(
                key=lambda x: x.get("similarity_score", 0),
                reverse=True
            )

            logger.info(
                f"Loaded {len(filtered_memories)} memory contexts for query",
                extra={
                    "project_id": self.project_id,
                    "agent_did": self.agent_did,
                    "query_preview": query[:100],
                    "results_count": len(filtered_memories)
                }
            )

            return filtered_memories

        except Exception as e:
            logger.warning(
                f"Failed to load memory context: {e}",
                extra={"project_id": self.project_id, "error": str(e)}
            )
            return []

    async def record_audit_event(
        self,
        action: str,
        details: Dict[str, Any],
        token_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record an audit event for traceability.

        All agent actions are logged to maintain a complete audit trail
        for compliance and debugging purposes.

        Args:
            action: Action type (e.g., "task_started", "decision_made")
            details: Action details
            token_id: Optional Arc NFT token ID for linkage

        Returns:
            Stored audit record with memory_id
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        metadata = {
            "action": action,
            "agent_did": self.agent_did,
            "timestamp": timestamp,
            **details
        }

        if token_id:
            metadata["token_id"] = token_id

        audit_content = f"Audit: {action} at {timestamp}"

        try:
            result = await self.memory_service.store_memory(
                project_id=self.project_id,
                agent_id=self.agent_did,
                run_id=self.run_id,
                memory_type="audit_event",
                content=audit_content,
                namespace=self.agent_did,
                metadata=metadata
            )

            logger.info(
                f"Recorded audit event: {action}",
                extra={
                    "memory_id": result.get("memory_id"),
                    "action": action,
                    "agent_did": self.agent_did,
                    "run_id": self.run_id
                }
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to record audit event: {e}",
                extra={"action": action, "error": str(e)}
            )
            # Return minimal result to avoid blocking workflow
            return {"memory_id": None, "error": str(e), "timestamp": timestamp}

    async def store_memory_with_token_link(
        self,
        content: str,
        memory_type: str,
        token_id: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store memory entry linked to an Arc NFT token.

        Links agent decisions to Arc blockchain token IDs for
        on-chain verification and ownership tracking.

        Args:
            content: Memory content
            memory_type: Type of memory (decision, context, etc.)
            token_id: Arc NFT token ID
            additional_metadata: Optional extra metadata

        Returns:
            Stored memory record with token linkage
        """
        metadata = {
            "token_id": token_id,
            "agent_did": self.agent_did,
            **(additional_metadata or {})
        }

        result = await self.memory_service.store_memory(
            project_id=self.project_id,
            agent_id=self.agent_did,
            run_id=self.run_id,
            memory_type=memory_type,
            content=content,
            namespace=self.agent_did,
            metadata=metadata
        )

        logger.info(
            f"Stored memory with token link",
            extra={
                "memory_id": result.get("memory_id"),
                "token_id": token_id,
                "memory_type": memory_type
            }
        )

        return result

    async def execute(
        self,
        input_data: Dict[str, Any],
        retry_on_failure: bool = True,
        load_context: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the crew workflow with orchestration features.

        Provides:
        - Memory context loading for informed decisions
        - Retry logic for transient failures
        - Audit trail for all actions

        Args:
            input_data: Input data for the workflow
            retry_on_failure: Whether to retry on failures
            load_context: Whether to load memory context first

        Returns:
            Workflow result with request_id and outputs
        """
        # Record workflow start
        await self.record_audit_event(
            action="workflow_started",
            details={
                "input_query": input_data.get("query", ""),
                "retry_enabled": retry_on_failure
            }
        )

        # Optionally load memory context
        context = []
        if load_context:
            query = input_data.get("query", "")
            if query:
                context = await self.load_memory_context(query)
                input_data["memory_context"] = context

        # Execute with retry logic
        last_error = None
        attempts = 0

        while attempts < self.max_retries:
            attempts += 1

            try:
                crew = self._create_crew()
                result = await crew.kickoff(input_data)

                # Record success
                await self.record_audit_event(
                    action="workflow_completed",
                    details={
                        "request_id": result.get("request_id"),
                        "attempts": attempts
                    }
                )

                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Workflow attempt {attempts} failed: {e}",
                    extra={
                        "attempt": attempts,
                        "max_retries": self.max_retries,
                        "error": str(e)
                    }
                )

                if not retry_on_failure or attempts >= self.max_retries:
                    break

                # Wait before retry
                import asyncio
                await asyncio.sleep(self.retry_delay)

        # Record failure
        await self.record_audit_event(
            action="workflow_failed",
            details={
                "error": str(last_error),
                "attempts": attempts
            }
        )

        # Re-raise or return error result
        if last_error:
            raise last_error

        return {
            "status": "failed",
            "error": "Max retries exceeded",
            "attempts": attempts
        }

    async def get_audit_trail(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the audit trail for this run.

        Args:
            limit: Maximum number of audit entries

        Returns:
            List of audit events in chronological order
        """
        try:
            memories, total, _ = await self.memory_service.list_memories(
                project_id=self.project_id,
                run_id=self.run_id,
                memory_type="audit_event",
                namespace=self.agent_did,
                limit=limit
            )

            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []


# Convenience function for creating orchestrators
def create_orchestrator(
    project_id: str,
    agent_did: str,
    **kwargs
) -> CrewOrchestrator:
    """
    Create a new CrewOrchestrator instance.

    Args:
        project_id: Project identifier
        agent_did: Agent DID for namespace isolation
        **kwargs: Additional orchestrator options

    Returns:
        Configured CrewOrchestrator
    """
    return CrewOrchestrator(
        project_id=project_id,
        agent_did=agent_did,
        **kwargs
    )
