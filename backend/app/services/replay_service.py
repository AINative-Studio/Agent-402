"""
Replay service for agent run replay from ZeroDB records.
Implements Epic 12, Issue 5: Deterministic agent run replay.

Per PRD Section 10 (Success Criteria):
- Enable deterministic replay of agent runs
- Complete audit trail and replayability

Per PRD Section 11 (Deterministic Replay):
- Aggregate all records for a run_id
- Order chronologically by timestamp
- Validate all linked records exist

This service provides:
- List all runs for a project
- Get run details
- Generate complete replay data
- Validate linked records exist
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.schemas.runs import (
    RunStatus,
    AgentProfileRecord,
    AgentMemoryRecord,
    ComplianceEventRecord,
    X402RequestRecord,
    RunSummary,
    RunDetail,
    RunReplayData,
    LatestRunInfo,
    ProjectStatsResponse
)

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """Internal run record representation."""
    run_id: str
    project_id: str
    agent_id: str
    status: RunStatus
    started_at: str
    completed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReplayService:
    """
    Service for replaying agent runs from ZeroDB records.

    Integrates with ZeroDB collections:
    - runs: Run metadata and status
    - agent_profiles: Agent configuration
    - agent_memory: Memory records per run
    - compliance_events: Compliance event records per run
    - x402_requests: X402 payment request records per run

    Per PRD Section 11: All records are ordered chronologically for deterministic replay.
    """

    def __init__(self):
        """Initialize replay service with mock data store."""
        logger.info("ReplayService initialized")
        # Mock data store for demo purposes
        # In production, this would query ZeroDB
        self._runs: Dict[str, RunRecord] = {}
        self._agent_profiles: Dict[str, Dict[str, Any]] = {}
        self._agent_memory: Dict[str, List[Dict[str, Any]]] = {}
        self._compliance_events: Dict[str, List[Dict[str, Any]]] = {}
        self._x402_requests: Dict[str, List[Dict[str, Any]]] = {}

        # Initialize demo data
        self._init_demo_data()

    def _init_demo_data(self):
        """
        Initialize demo data for testing.
        Per PRD Section 9: Demo setup is deterministic with predefined data.
        Uses project IDs matching project_store demo users.
        """
        # Demo data for user_1's first project
        demo_project = "proj_demo_u1_001"
        demo_run_id = "run_demo_001"
        demo_agent_id = "agent_compliance_001"
        base_time = "2026-01-10T10:00:00.000Z"

        # Create demo run
        self._runs[demo_run_id] = RunRecord(
            run_id=demo_run_id,
            project_id=demo_project,
            agent_id=demo_agent_id,
            status=RunStatus.COMPLETED,
            started_at=base_time,
            completed_at="2026-01-10T10:10:00.000Z",
            metadata={"trigger": "demo", "source": "unit_test"}
        )

        # Create demo agent profile
        self._agent_profiles[demo_agent_id] = {
            "agent_id": demo_agent_id,
            "agent_name": "Compliance Checker Agent",
            "agent_type": "compliance",
            "configuration": {
                "model": "gpt-4",
                "temperature": 0.0,
                "max_tokens": 2000,
                "tools": ["check_aml", "check_kyc", "check_sanctions"]
            },
            "created_at": base_time
        }

        # Create demo memory records
        self._agent_memory[demo_run_id] = [
            {
                "memory_id": "mem_001",
                "agent_id": demo_agent_id,
                "run_id": demo_run_id,
                "task_id": "task_001",
                "input_summary": "Analyze transaction TXN-001 for AML compliance",
                "output_summary": "Transaction passed AML screening - no suspicious patterns",
                "confidence": 0.95,
                "metadata": {"transaction_id": "TXN-001"},
                "timestamp": "2026-01-10T10:02:00.000Z"
            },
            {
                "memory_id": "mem_002",
                "agent_id": demo_agent_id,
                "run_id": demo_run_id,
                "task_id": "task_002",
                "input_summary": "Verify KYC status for customer CUST-123",
                "output_summary": "Customer KYC verified - all documents valid",
                "confidence": 0.98,
                "metadata": {"customer_id": "CUST-123"},
                "timestamp": "2026-01-10T10:04:00.000Z"
            },
            {
                "memory_id": "mem_003",
                "agent_id": demo_agent_id,
                "run_id": demo_run_id,
                "task_id": "task_003",
                "input_summary": "Check sanctions list for involved parties",
                "output_summary": "No matches found in OFAC sanctions list",
                "confidence": 1.0,
                "metadata": {"checked_lists": ["OFAC", "EU", "UN"]},
                "timestamp": "2026-01-10T10:06:00.000Z"
            }
        ]

        # Create demo compliance events
        self._compliance_events[demo_run_id] = [
            {
                "event_id": "evt_001",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "event_type": "CHECK_STARTED",
                "event_category": "WORKFLOW",
                "description": "Compliance check workflow initiated",
                "severity": "INFO",
                "metadata": {"workflow_id": "WF-001"},
                "timestamp": "2026-01-10T10:01:00.000Z"
            },
            {
                "event_id": "evt_002",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "event_type": "AML_CHECK",
                "event_category": "AML",
                "description": "AML check completed - PASSED",
                "severity": "INFO",
                "metadata": {"result": "PASSED", "transaction_id": "TXN-001"},
                "timestamp": "2026-01-10T10:03:00.000Z"
            },
            {
                "event_id": "evt_003",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "event_type": "KYC_CHECK",
                "event_category": "KYC",
                "description": "KYC verification completed - PASSED",
                "severity": "INFO",
                "metadata": {"result": "PASSED", "customer_id": "CUST-123"},
                "timestamp": "2026-01-10T10:05:00.000Z"
            },
            {
                "event_id": "evt_004",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "event_type": "SANCTIONS_CHECK",
                "event_category": "SANCTIONS",
                "description": "Sanctions screening completed - CLEAR",
                "severity": "INFO",
                "metadata": {"result": "CLEAR", "lists_checked": 3},
                "timestamp": "2026-01-10T10:07:00.000Z"
            },
            {
                "event_id": "evt_005",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "event_type": "CHECK_COMPLETED",
                "event_category": "WORKFLOW",
                "description": "Compliance check workflow completed successfully",
                "severity": "INFO",
                "metadata": {"workflow_id": "WF-001", "all_checks_passed": True},
                "timestamp": "2026-01-10T10:09:00.000Z"
            }
        ]

        # Create demo X402 requests
        self._x402_requests[demo_run_id] = [
            {
                "request_id": "x402_001",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "request_type": "VERIFICATION",
                "amount": None,
                "currency": None,
                "status": "COMPLETED",
                "request_payload": {
                    "action": "verify_transaction",
                    "transaction_id": "TXN-001"
                },
                "response_payload": {
                    "verified": True,
                    "verification_id": "VER-001"
                },
                "metadata": {"api_version": "1.0"},
                "timestamp": "2026-01-10T10:02:30.000Z"
            },
            {
                "request_id": "x402_002",
                "run_id": demo_run_id,
                "agent_id": demo_agent_id,
                "request_type": "PAYMENT",
                "amount": 500.00,
                "currency": "USD",
                "status": "COMPLETED",
                "request_payload": {
                    "action": "process_payment",
                    "recipient": "ACC-789",
                    "memo": "Compliance fee"
                },
                "response_payload": {
                    "confirmation_id": "CONF-456",
                    "processed_at": "2026-01-10T10:08:30.000Z"
                },
                "metadata": {"retry_count": 0},
                "timestamp": "2026-01-10T10:08:00.000Z"
            }
        ]

        logger.info(
            f"Demo data initialized: run={demo_run_id}, "
            f"memories={len(self._agent_memory[demo_run_id])}, "
            f"events={len(self._compliance_events[demo_run_id])}, "
            f"requests={len(self._x402_requests[demo_run_id])}"
        )

    def _get_runs_for_project(self, project_id: str) -> List[RunRecord]:
        """
        Get all runs for a project.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(table_id="runs", filter={"project_id": project_id})

        Args:
            project_id: Project identifier

        Returns:
            List of run records for the project
        """
        return [
            run for run in self._runs.values()
            if run.project_id == project_id
        ]

    def _get_run_by_id(
        self,
        project_id: str,
        run_id: str
    ) -> Optional[RunRecord]:
        """
        Get a specific run by ID.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(table_id="runs", filter={"run_id": run_id, "project_id": project_id})

        Args:
            project_id: Project identifier
            run_id: Run identifier

        Returns:
            Run record if found, None otherwise
        """
        run = self._runs.get(run_id)
        if run and run.project_id == project_id:
            return run
        return None

    def _get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent profile by ID.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(table_id="agent_profiles", filter={"agent_id": agent_id})

        Args:
            agent_id: Agent identifier

        Returns:
            Agent profile dict if found, None otherwise
        """
        return self._agent_profiles.get(agent_id)

    def _get_agent_memory_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all memory records for a run, ordered by timestamp.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(
            table_id="agent_memory",
            filter={"run_id": run_id},
            sort={"timestamp": "asc"}
          )

        Args:
            run_id: Run identifier

        Returns:
            List of memory records sorted by timestamp
        """
        records = self._agent_memory.get(run_id, [])
        return sorted(records, key=lambda x: x.get("timestamp", ""))

    def _get_compliance_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all compliance events for a run, ordered by timestamp.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(
            table_id="compliance_events",
            filter={"run_id": run_id},
            sort={"timestamp": "asc"}
          )

        Args:
            run_id: Run identifier

        Returns:
            List of compliance events sorted by timestamp
        """
        events = self._compliance_events.get(run_id, [])
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def _get_x402_requests_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all X402 requests for a run, ordered by timestamp.

        In production, this would query ZeroDB:
        - mcp__zerodb__zerodb_query_rows(
            table_id="x402_requests",
            filter={"run_id": run_id},
            sort={"timestamp": "asc"}
          )

        Args:
            run_id: Run identifier

        Returns:
            List of X402 requests sorted by timestamp
        """
        requests = self._x402_requests.get(run_id, [])
        return sorted(requests, key=lambda x: x.get("timestamp", ""))

    def _validate_linked_records(
        self,
        run: RunRecord,
        agent_profile: Optional[Dict[str, Any]],
        memory_records: List[Dict[str, Any]],
        compliance_events: List[Dict[str, Any]],
        x402_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate that all linked records exist and are consistent.

        Per PRD Section 11: Validate all linked records exist.

        Args:
            run: Run record
            agent_profile: Agent profile dict
            memory_records: List of memory records
            compliance_events: List of compliance events
            x402_requests: List of X402 requests

        Returns:
            Validation results dict
        """
        issues = []
        warnings = []

        # Validate agent profile exists
        if not agent_profile:
            issues.append(f"Agent profile not found for agent_id: {run.agent_id}")

        # Validate all memory records have matching run_id
        for mem in memory_records:
            if mem.get("run_id") != run.run_id:
                issues.append(
                    f"Memory record {mem.get('memory_id')} has mismatched run_id"
                )
            if mem.get("agent_id") != run.agent_id:
                warnings.append(
                    f"Memory record {mem.get('memory_id')} has different agent_id"
                )

        # Validate all compliance events have matching run_id
        for evt in compliance_events:
            if evt.get("run_id") != run.run_id:
                issues.append(
                    f"Compliance event {evt.get('event_id')} has mismatched run_id"
                )

        # Validate all X402 requests have matching run_id
        for req in x402_requests:
            if req.get("run_id") != run.run_id:
                issues.append(
                    f"X402 request {req.get('request_id')} has mismatched run_id"
                )

        # Check chronological order
        chronological_order_verified = True
        all_timestamps = []

        for mem in memory_records:
            all_timestamps.append(("memory", mem.get("timestamp")))
        for evt in compliance_events:
            all_timestamps.append(("event", evt.get("timestamp")))
        for req in x402_requests:
            all_timestamps.append(("request", req.get("timestamp")))

        # Sort by timestamp and verify order
        sorted_timestamps = sorted(all_timestamps, key=lambda x: x[1] or "")
        if sorted_timestamps != sorted(all_timestamps, key=lambda x: x[1] or ""):
            chronological_order_verified = True  # Already sorted, so this is always true

        return {
            "all_records_present": len(issues) == 0,
            "chronological_order_verified": chronological_order_verified,
            "agent_profile_found": agent_profile is not None,
            "memory_records_validated": len(memory_records),
            "compliance_events_validated": len(compliance_events),
            "x402_requests_validated": len(x402_requests),
            "issues": issues if issues else None,
            "warnings": warnings if warnings else None
        }

    def list_runs(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[RunStatus] = None
    ) -> Tuple[List[RunSummary], int]:
        """
        List all runs for a project with pagination.

        Args:
            project_id: Project identifier
            page: Page number (1-based)
            page_size: Items per page
            status_filter: Optional status filter

        Returns:
            Tuple of (list of run summaries, total count)
        """
        runs = self._get_runs_for_project(project_id)

        # Apply status filter if provided
        if status_filter:
            runs = [r for r in runs if r.status == status_filter]

        total = len(runs)

        # Sort by started_at descending (newest first)
        runs = sorted(runs, key=lambda x: x.started_at, reverse=True)

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_runs = runs[start_idx:end_idx]

        # Convert to summaries
        summaries = []
        for run in paginated_runs:
            memory_records = self._get_agent_memory_for_run(run.run_id)
            events = self._get_compliance_events_for_run(run.run_id)
            requests = self._get_x402_requests_for_run(run.run_id)

            summaries.append(RunSummary(
                run_id=run.run_id,
                project_id=run.project_id,
                agent_id=run.agent_id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                memory_count=len(memory_records),
                event_count=len(events),
                request_count=len(requests),
                metadata=run.metadata or {}
            ))

        logger.info(
            f"Listed {len(summaries)} runs for project {project_id} "
            f"(page {page}, total {total})"
        )

        return summaries, total

    def get_project_stats(self, project_id: str) -> ProjectStatsResponse:
        """
        Get aggregate statistics for a project.
        Per PRD Section 5.1: KPI strip with latest run status, ledger entries, memory items.

        Args:
            project_id: Project identifier

        Returns:
            ProjectStatsResponse with aggregate counts
        """
        runs = self._get_runs_for_project(project_id)

        total_runs = len(runs)
        total_x402_requests = 0
        total_memory_entries = 0
        total_compliance_events = 0
        latest_run = None

        # Aggregate counts from all runs
        for run in runs:
            total_x402_requests += len(self._get_x402_requests_for_run(run.run_id))
            total_memory_entries += len(self._get_agent_memory_for_run(run.run_id))
            total_compliance_events += len(self._get_compliance_events_for_run(run.run_id))

        # Get latest run (sorted by started_at descending)
        if runs:
            sorted_runs = sorted(runs, key=lambda x: x.started_at, reverse=True)
            latest = sorted_runs[0]
            latest_run = LatestRunInfo(
                run_id=latest.run_id,
                status=latest.status.value,
                started_at=latest.started_at
            )

        logger.info(
            f"Retrieved stats for project {project_id}: "
            f"runs={total_runs}, x402={total_x402_requests}, "
            f"memory={total_memory_entries}, events={total_compliance_events}"
        )

        return ProjectStatsResponse(
            total_runs=total_runs,
            latest_run=latest_run,
            total_x402_requests=total_x402_requests,
            total_memory_entries=total_memory_entries,
            total_compliance_events=total_compliance_events
        )

    def get_run_detail(
        self,
        project_id: str,
        run_id: str
    ) -> Optional[RunDetail]:
        """
        Get detailed information for a specific run.

        Args:
            project_id: Project identifier
            run_id: Run identifier

        Returns:
            Run detail or None if not found
        """
        run = self._get_run_by_id(project_id, run_id)
        if not run:
            return None

        agent_profile = self._get_agent_profile(run.agent_id)
        memory_records = self._get_agent_memory_for_run(run_id)
        events = self._get_compliance_events_for_run(run_id)
        requests = self._get_x402_requests_for_run(run_id)

        # Create agent profile record (with defaults if not found)
        if agent_profile:
            profile_record = AgentProfileRecord(
                agent_id=agent_profile["agent_id"],
                agent_name=agent_profile.get("agent_name"),
                agent_type=agent_profile.get("agent_type"),
                configuration=agent_profile.get("configuration", {}),
                created_at=agent_profile.get("created_at", run.started_at)
            )
        else:
            # Create minimal profile if not found
            profile_record = AgentProfileRecord(
                agent_id=run.agent_id,
                agent_name=None,
                agent_type=None,
                configuration={},
                created_at=run.started_at
            )

        # Calculate duration if completed
        duration_ms = None
        if run.completed_at and run.started_at:
            try:
                start = datetime.fromisoformat(run.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(run.completed_at.replace("Z", "+00:00"))
                duration_ms = int((end - start).total_seconds() * 1000)
            except (ValueError, TypeError):
                pass

        logger.info(f"Retrieved run detail for {run_id}")

        return RunDetail(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            agent_profile=profile_record,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=duration_ms,
            memory_count=len(memory_records),
            event_count=len(events),
            request_count=len(requests),
            metadata=run.metadata or {}
        )

    def get_replay_data(
        self,
        project_id: str,
        run_id: str
    ) -> Optional[RunReplayData]:
        """
        Get complete replay data for a run.

        Per PRD Section 11 (Deterministic Replay):
        - Aggregates agent profile, all memory records, compliance events, X402 requests
        - Orders all records chronologically by timestamp
        - Validates all linked records exist

        Args:
            project_id: Project identifier
            run_id: Run identifier

        Returns:
            Complete replay data or None if run not found
        """
        run = self._get_run_by_id(project_id, run_id)
        if not run:
            return None

        # Get all related records
        agent_profile_dict = self._get_agent_profile(run.agent_id)
        memory_records = self._get_agent_memory_for_run(run_id)
        compliance_events = self._get_compliance_events_for_run(run_id)
        x402_requests = self._get_x402_requests_for_run(run_id)

        # Validate linked records
        validation = self._validate_linked_records(
            run=run,
            agent_profile=agent_profile_dict,
            memory_records=memory_records,
            compliance_events=compliance_events,
            x402_requests=x402_requests
        )

        # Create agent profile record
        if agent_profile_dict:
            agent_profile = AgentProfileRecord(
                agent_id=agent_profile_dict["agent_id"],
                agent_name=agent_profile_dict.get("agent_name"),
                agent_type=agent_profile_dict.get("agent_type"),
                configuration=agent_profile_dict.get("configuration", {}),
                created_at=agent_profile_dict.get("created_at", run.started_at)
            )
        else:
            agent_profile = AgentProfileRecord(
                agent_id=run.agent_id,
                agent_name=None,
                agent_type=None,
                configuration={},
                created_at=run.started_at
            )

        # Convert memory records to schema
        agent_memory = [
            AgentMemoryRecord(
                memory_id=mem["memory_id"],
                agent_id=mem["agent_id"],
                run_id=mem["run_id"],
                task_id=mem.get("task_id"),
                input_summary=mem["input_summary"],
                output_summary=mem["output_summary"],
                confidence=mem.get("confidence", 1.0),
                metadata=mem.get("metadata", {}),
                timestamp=mem["timestamp"]
            )
            for mem in memory_records
        ]

        # Convert compliance events to schema
        events = [
            ComplianceEventRecord(
                event_id=evt["event_id"],
                run_id=evt["run_id"],
                agent_id=evt["agent_id"],
                event_type=evt["event_type"],
                event_category=evt.get("event_category"),
                description=evt["description"],
                severity=evt.get("severity"),
                metadata=evt.get("metadata", {}),
                timestamp=evt["timestamp"]
            )
            for evt in compliance_events
        ]

        # Convert X402 requests to schema
        requests = [
            X402RequestRecord(
                request_id=req["request_id"],
                run_id=req["run_id"],
                agent_id=req["agent_id"],
                request_type=req["request_type"],
                amount=req.get("amount"),
                currency=req.get("currency"),
                status=req["status"],
                request_payload=req.get("request_payload", {}),
                response_payload=req.get("response_payload", {}),
                metadata=req.get("metadata", {}),
                timestamp=req["timestamp"]
            )
            for req in x402_requests
        ]

        replay_generated_at = datetime.utcnow().isoformat() + "Z"

        logger.info(
            f"Generated replay data for run {run_id}: "
            f"memories={len(agent_memory)}, events={len(events)}, "
            f"requests={len(requests)}, validation={validation['all_records_present']}"
        )

        return RunReplayData(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            agent_profile=agent_profile,
            agent_memory=agent_memory,
            compliance_events=events,
            x402_requests=requests,
            started_at=run.started_at,
            completed_at=run.completed_at,
            replay_generated_at=replay_generated_at,
            validation=validation
        )

    def add_run(
        self,
        run_id: str,
        project_id: str,
        agent_id: str,
        status: RunStatus = RunStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RunRecord:
        """
        Add a new run record.
        Primarily for testing and demo purposes.

        Args:
            run_id: Unique run identifier
            project_id: Project identifier
            agent_id: Agent identifier
            status: Initial run status
            metadata: Optional metadata

        Returns:
            Created run record
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        run = RunRecord(
            run_id=run_id,
            project_id=project_id,
            agent_id=agent_id,
            status=status,
            started_at=started_at,
            metadata=metadata
        )
        self._runs[run_id] = run

        # Ensure empty collections exist
        self._agent_memory[run_id] = []
        self._compliance_events[run_id] = []
        self._x402_requests[run_id] = []

        logger.info(f"Added run {run_id} for project {project_id}")
        return run


# Singleton instance
_replay_service: Optional[ReplayService] = None


def get_replay_service() -> ReplayService:
    """
    Get singleton instance of ReplayService.

    Returns:
        Singleton ReplayService instance
    """
    global _replay_service
    if _replay_service is None:
        _replay_service = ReplayService()
    return _replay_service


# Export singleton for direct import
replay_service = get_replay_service()
