"""
X402 Request Service Layer.
Implements business logic for X402 signed request operations.

Per PRD Section 6 (ZeroDB Integration):
- X402 signed requests are logged with agent and task linkage
- Supports linking to agent_memory and compliance_events records
- Enables audit trail for X402 protocol transactions

Per PRD Section 8 (X402 Protocol):
- X402 requests contain signed payment authorizations
- Requests must be traceable to originating agent and task
- Supports compliance and audit requirements

Epic 12 Issue 4: X402 requests linked to agent + task.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.x402_requests import X402RequestStatus
from app.core.errors import APIError


class X402RequestNotFoundError(APIError):
    """
    Raised when an X402 request is not found.

    Returns:
        - HTTP 404 (Not Found)
        - error_code: X402_REQUEST_NOT_FOUND
        - detail: Message including request ID
    """

    def __init__(self, request_id: str):
        detail = f"X402 request not found: {request_id}" if request_id else "X402 request not found"
        super().__init__(
            status_code=404,
            error_code="X402_REQUEST_NOT_FOUND",
            detail=detail
        )


class X402Service:
    """
    Service for managing X402 signed requests.

    Handles creation, retrieval, and linking of X402 requests
    to agent_memory and compliance_events records.

    For MVP: Uses in-memory storage simulation
    For Production: Will use ZeroDB for persistence
    """

    def __init__(self):
        """Initialize the X402 service with in-memory storage."""
        # In-memory store for MVP: project_id -> request_id -> request_data
        self._request_store: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # Simulated linked records stores (for MVP demonstration)
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._compliance_store: Dict[str, Dict[str, Any]] = {}

    def generate_request_id(self) -> str:
        """
        Generate a unique X402 request ID.

        Returns:
            str: Unique request identifier (format: x402_req_{uuid})
        """
        return f"x402_req_{uuid.uuid4().hex[:16]}"

    def create_request(
        self,
        project_id: str,
        agent_id: str,
        task_id: str,
        run_id: str,
        request_payload: Dict[str, Any],
        signature: str,
        status: X402RequestStatus = X402RequestStatus.PENDING,
        linked_memory_ids: Optional[List[str]] = None,
        linked_compliance_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new X402 request record.

        Args:
            project_id: Project identifier
            agent_id: Agent identifier that produced the request
            task_id: Task identifier that produced the request
            run_id: Run identifier for execution context
            request_payload: X402 protocol payload
            signature: Cryptographic signature
            status: Initial request status
            linked_memory_ids: Optional list of linked memory record IDs
            linked_compliance_ids: Optional list of linked compliance event IDs
            metadata: Optional additional metadata

        Returns:
            Dict containing the created request record
        """
        request_id = self.generate_request_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        request_data = {
            "request_id": request_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "run_id": run_id,
            "request_payload": request_payload,
            "signature": signature,
            "status": status.value if isinstance(status, X402RequestStatus) else status,
            "timestamp": timestamp,
            "linked_memory_ids": linked_memory_ids or [],
            "linked_compliance_ids": linked_compliance_ids or [],
            "metadata": metadata
        }

        # Initialize project store if needed
        if project_id not in self._request_store:
            self._request_store[project_id] = {}

        # Store the request
        self._request_store[project_id][request_id] = request_data

        return request_data

    def get_request(
        self,
        project_id: str,
        request_id: str,
        include_links: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve an X402 request by ID.

        Args:
            project_id: Project identifier
            request_id: X402 request identifier
            include_links: If True, include full linked records

        Returns:
            Dict containing the request record

        Raises:
            X402RequestNotFoundError: If request not found
        """
        if project_id not in self._request_store:
            raise X402RequestNotFoundError(request_id)

        if request_id not in self._request_store[project_id]:
            raise X402RequestNotFoundError(request_id)

        request_data = self._request_store[project_id][request_id].copy()

        if include_links:
            # Fetch linked memory records
            request_data["linked_memories"] = self._get_linked_memories(
                request_data.get("linked_memory_ids", [])
            )
            # Fetch linked compliance events
            request_data["linked_compliance_events"] = self._get_linked_compliance_events(
                request_data.get("linked_compliance_ids", [])
            )

        return request_data

    def list_requests(
        self,
        project_id: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        status: Optional[X402RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List X402 requests with optional filters.

        Args:
            project_id: Project identifier
            agent_id: Optional filter by agent ID
            task_id: Optional filter by task ID
            run_id: Optional filter by run ID
            status: Optional filter by status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (list of requests, total count)
        """
        if project_id not in self._request_store:
            return [], 0

        all_requests = list(self._request_store[project_id].values())

        # Apply filters
        filtered_requests = []
        for request in all_requests:
            if agent_id and request.get("agent_id") != agent_id:
                continue
            if task_id and request.get("task_id") != task_id:
                continue
            if run_id and request.get("run_id") != run_id:
                continue
            if status:
                status_value = status.value if isinstance(status, X402RequestStatus) else status
                if request.get("status") != status_value:
                    continue
            filtered_requests.append(request)

        # Sort by timestamp descending (newest first)
        filtered_requests.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        total = len(filtered_requests)

        # Apply pagination
        paginated_requests = filtered_requests[offset:offset + limit]

        return paginated_requests, total

    def update_request_status(
        self,
        project_id: str,
        request_id: str,
        status: X402RequestStatus
    ) -> Dict[str, Any]:
        """
        Update the status of an X402 request.

        Args:
            project_id: Project identifier
            request_id: X402 request identifier
            status: New status

        Returns:
            Updated request record

        Raises:
            X402RequestNotFoundError: If request not found
        """
        if project_id not in self._request_store:
            raise X402RequestNotFoundError(request_id)

        if request_id not in self._request_store[project_id]:
            raise X402RequestNotFoundError(request_id)

        self._request_store[project_id][request_id]["status"] = (
            status.value if isinstance(status, X402RequestStatus) else status
        )

        return self._request_store[project_id][request_id]

    def add_memory_link(
        self,
        project_id: str,
        request_id: str,
        memory_id: str
    ) -> Dict[str, Any]:
        """
        Add a memory record link to an X402 request.

        Args:
            project_id: Project identifier
            request_id: X402 request identifier
            memory_id: Memory record ID to link

        Returns:
            Updated request record

        Raises:
            X402RequestNotFoundError: If request not found
        """
        if project_id not in self._request_store:
            raise X402RequestNotFoundError(request_id)

        if request_id not in self._request_store[project_id]:
            raise X402RequestNotFoundError(request_id)

        linked_ids = self._request_store[project_id][request_id].get("linked_memory_ids", [])
        if memory_id not in linked_ids:
            linked_ids.append(memory_id)
            self._request_store[project_id][request_id]["linked_memory_ids"] = linked_ids

        return self._request_store[project_id][request_id]

    def add_compliance_link(
        self,
        project_id: str,
        request_id: str,
        compliance_id: str
    ) -> Dict[str, Any]:
        """
        Add a compliance event link to an X402 request.

        Args:
            project_id: Project identifier
            request_id: X402 request identifier
            compliance_id: Compliance event ID to link

        Returns:
            Updated request record

        Raises:
            X402RequestNotFoundError: If request not found
        """
        if project_id not in self._request_store:
            raise X402RequestNotFoundError(request_id)

        if request_id not in self._request_store[project_id]:
            raise X402RequestNotFoundError(request_id)

        linked_ids = self._request_store[project_id][request_id].get("linked_compliance_ids", [])
        if compliance_id not in linked_ids:
            linked_ids.append(compliance_id)
            self._request_store[project_id][request_id]["linked_compliance_ids"] = linked_ids

        return self._request_store[project_id][request_id]

    def _get_linked_memories(
        self,
        memory_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve linked memory records by IDs.

        For MVP: Returns simulated memory records.
        For Production: Will query agent_memory table via ZeroDB.

        Args:
            memory_ids: List of memory record IDs

        Returns:
            List of memory records
        """
        memories = []
        for memory_id in memory_ids:
            if memory_id in self._memory_store:
                memories.append(self._memory_store[memory_id])
            else:
                # Return placeholder for demo
                memories.append({
                    "memory_id": memory_id,
                    "content": f"Memory content for {memory_id}",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                })
        return memories

    def _get_linked_compliance_events(
        self,
        compliance_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve linked compliance event records by IDs.

        For MVP: Returns simulated compliance records.
        For Production: Will query compliance_events table via ZeroDB.

        Args:
            compliance_ids: List of compliance event IDs

        Returns:
            List of compliance event records
        """
        events = []
        for event_id in compliance_ids:
            if event_id in self._compliance_store:
                events.append(self._compliance_store[event_id])
            else:
                # Return placeholder for demo
                events.append({
                    "event_id": event_id,
                    "event_type": "COMPLIANCE_CHECK",
                    "passed": True,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                })
        return events

    def get_requests_by_agent(
        self,
        project_id: str,
        agent_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all X402 requests for a specific agent.

        Args:
            project_id: Project identifier
            agent_id: Agent identifier

        Returns:
            List of requests for the agent
        """
        requests, _ = self.list_requests(
            project_id=project_id,
            agent_id=agent_id,
            limit=limit
        )
        return requests

    def get_requests_by_task(
        self,
        project_id: str,
        task_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all X402 requests for a specific task.

        Args:
            project_id: Project identifier
            task_id: Task identifier

        Returns:
            List of requests for the task
        """
        requests, _ = self.list_requests(
            project_id=project_id,
            task_id=task_id,
            limit=limit
        )
        return requests

    def get_requests_by_run(
        self,
        project_id: str,
        run_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all X402 requests for a specific run.

        Args:
            project_id: Project identifier
            run_id: Run identifier

        Returns:
            List of requests for the run
        """
        requests, _ = self.list_requests(
            project_id=project_id,
            run_id=run_id,
            limit=limit
        )
        return requests


# Global service instance
x402_service = X402Service()
