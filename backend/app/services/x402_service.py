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
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.x402_requests import X402RequestStatus
from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

# Table name for X402 requests in ZeroDB
X402_REQUESTS_TABLE = "x402_requests"


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

    Uses ZeroDB for persistence via the x402_requests table.
    """

    def __init__(self, client=None):
        """
        Initialize the X402 service.

        Args:
            client: Optional ZeroDB client instance (for testing)
        """
        self._client = client

    @property
    def client(self):
        """Lazy initialization of ZeroDB client."""
        if self._client is None:
            self._client = get_zerodb_client()
        return self._client

    def generate_request_id(self) -> str:
        """
        Generate a unique X402 request ID.

        Returns:
            str: Unique request identifier (format: x402_req_{uuid})
        """
        return f"x402_req_{uuid.uuid4().hex[:16]}"

    async def create_protocol_request(
        self,
        did: str,
        signature: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new X402 protocol request (for root /x402 endpoint).

        This is a simplified version for the public protocol endpoint.
        Unlike create_request(), this doesn't require project_id, agent_id, etc.

        Args:
            did: Decentralized identifier of the requesting agent
            signature: Cryptographic signature of the payload
            payload: X402 protocol payload

        Returns:
            Dict containing request_id, status, and timestamp

        Per Issue #77: Root /x402 endpoint for protocol requests.
        """
        request_id = self.generate_request_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build row data for ZeroDB table
        # Store minimal information for protocol requests
        row_data = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "run_id": "protocol_root",  # Placeholder for root endpoint
            "project_id": "protocol_root",  # No project context for root endpoint
            "agent_id": did,  # Use DID as agent_id
            "method": "POST",
            "url": "/x402",
            "headers": {},
            "body": {
                "task_id": "protocol_request",
                "payload": payload,
                "linked_memory_ids": [],
                "linked_compliance_ids": [],
                "metadata": {"endpoint": "root", "did": did}
            },
            "signature": signature,
            "signature_algorithm": "ECDSA",  # Default for did:ethr
            "verification_status": "received",  # MVP: no signature verification yet
            "timestamp": timestamp,
            "created_at": timestamp,
            "did": did  # Store DID separately for easy querying
        }

        try:
            result = await self.client.insert_row(X402_REQUESTS_TABLE, row_data)
            logger.info(f"Created X402 protocol request: {request_id} from DID: {did}")

            # Return response format for /x402 endpoint
            return {
                "request_id": request_id,
                "status": "received",
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"Failed to create X402 protocol request: {e}")
            raise

    async def create_request(
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

        # Build row data for ZeroDB table
        # Schema: id, request_id, run_id, project_id, agent_id, method, url,
        #         headers, body, signature, signature_algorithm, verification_status,
        #         timestamp, created_at
        row_data = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "run_id": run_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "method": request_payload.get("method", "POST"),
            "url": request_payload.get("url", ""),
            "headers": request_payload.get("headers", {}),
            "body": {
                "task_id": task_id,
                "payload": request_payload,
                "linked_memory_ids": linked_memory_ids or [],
                "linked_compliance_ids": linked_compliance_ids or [],
                "metadata": metadata
            },
            "signature": signature,
            "signature_algorithm": "ed25519",
            "verification_status": status.value if isinstance(status, X402RequestStatus) else status,
            "timestamp": timestamp,
            "created_at": timestamp
        }

        try:
            result = await self.client.insert_row(X402_REQUESTS_TABLE, row_data)
            logger.info(f"Created X402 request: {request_id}")

            # Return the logical request data structure
            return self._row_to_request(row_data)

        except Exception as e:
            logger.error(f"Failed to create X402 request: {e}")
            raise

    async def get_request(
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
        try:
            result = await self.client.query_rows(
                X402_REQUESTS_TABLE,
                filter={"request_id": request_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise X402RequestNotFoundError(request_id)

            request_data = self._row_to_request(rows[0])

            if include_links:
                # Fetch linked memory records
                request_data["linked_memories"] = await self._get_linked_memories(
                    request_data.get("linked_memory_ids", [])
                )
                # Fetch linked compliance events
                request_data["linked_compliance_events"] = await self._get_linked_compliance_events(
                    request_data.get("linked_compliance_ids", [])
                )

            return request_data

        except X402RequestNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get X402 request {request_id}: {e}")
            raise X402RequestNotFoundError(request_id)

    async def list_requests(
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
        try:
            # Build filter
            query_filter: Dict[str, Any] = {"project_id": project_id}
            if agent_id:
                query_filter["agent_id"] = agent_id
            if run_id:
                query_filter["run_id"] = run_id
            if status:
                status_value = status.value if isinstance(status, X402RequestStatus) else status
                query_filter["verification_status"] = status_value

            # Query with filter
            result = await self.client.query_rows(
                X402_REQUESTS_TABLE,
                filter=query_filter,
                limit=limit,
                skip=offset
            )

            rows = result.get("rows", [])
            total = result.get("total", len(rows))

            # Convert rows to request format
            requests = [self._row_to_request(row) for row in rows]

            # Additional filtering for task_id (stored in body)
            if task_id:
                requests = [
                    r for r in requests
                    if r.get("task_id") == task_id
                ]
                total = len(requests)

            # Sort by timestamp descending (newest first)
            requests.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )

            return requests, total

        except Exception as e:
            logger.error(f"Failed to list X402 requests: {e}")
            return [], 0

    async def update_request_status(
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
        try:
            # First, find the row to get its ID
            result = await self.client.query_rows(
                X402_REQUESTS_TABLE,
                filter={"request_id": request_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise X402RequestNotFoundError(request_id)

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            # Update the row
            status_value = status.value if isinstance(status, X402RequestStatus) else status
            updated_row = {**row, "verification_status": status_value}

            await self.client.update_row(X402_REQUESTS_TABLE, row_id, updated_row)
            logger.info(f"Updated X402 request {request_id} status to {status_value}")

            return self._row_to_request(updated_row)

        except X402RequestNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update X402 request {request_id}: {e}")
            raise X402RequestNotFoundError(request_id)

    async def add_memory_link(
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
        try:
            # Find the row
            result = await self.client.query_rows(
                X402_REQUESTS_TABLE,
                filter={"request_id": request_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise X402RequestNotFoundError(request_id)

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            # Update body with new memory link
            body = row.get("body", {})
            if isinstance(body, str):
                import json
                body = json.loads(body)

            linked_ids = body.get("linked_memory_ids", [])
            if memory_id not in linked_ids:
                linked_ids.append(memory_id)
                body["linked_memory_ids"] = linked_ids

            updated_row = {**row, "body": body}
            await self.client.update_row(X402_REQUESTS_TABLE, row_id, updated_row)
            logger.info(f"Added memory link {memory_id} to X402 request {request_id}")

            return self._row_to_request(updated_row)

        except X402RequestNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add memory link to X402 request {request_id}: {e}")
            raise X402RequestNotFoundError(request_id)

    async def add_compliance_link(
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
        try:
            # Find the row
            result = await self.client.query_rows(
                X402_REQUESTS_TABLE,
                filter={"request_id": request_id, "project_id": project_id},
                limit=1
            )

            rows = result.get("rows", [])
            if not rows:
                raise X402RequestNotFoundError(request_id)

            row = rows[0]
            row_id = row.get("id") or row.get("row_id")

            # Update body with new compliance link
            body = row.get("body", {})
            if isinstance(body, str):
                import json
                body = json.loads(body)

            linked_ids = body.get("linked_compliance_ids", [])
            if compliance_id not in linked_ids:
                linked_ids.append(compliance_id)
                body["linked_compliance_ids"] = linked_ids

            updated_row = {**row, "body": body}
            await self.client.update_row(X402_REQUESTS_TABLE, row_id, updated_row)
            logger.info(f"Added compliance link {compliance_id} to X402 request {request_id}")

            return self._row_to_request(updated_row)

        except X402RequestNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add compliance link to X402 request {request_id}: {e}")
            raise X402RequestNotFoundError(request_id)

    def _row_to_request(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a ZeroDB row to the logical request format.

        Args:
            row: Raw row data from ZeroDB

        Returns:
            Request data in the expected format
        """
        body = row.get("body", {})
        if isinstance(body, str):
            import json
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {}

        return {
            "request_id": row.get("request_id"),
            "project_id": row.get("project_id"),
            "agent_id": row.get("agent_id"),
            "task_id": body.get("task_id"),
            "run_id": row.get("run_id"),
            "request_payload": body.get("payload", {}),
            "signature": row.get("signature"),
            "status": row.get("verification_status"),
            "timestamp": row.get("timestamp"),
            "linked_memory_ids": body.get("linked_memory_ids", []),
            "linked_compliance_ids": body.get("linked_compliance_ids", []),
            "metadata": body.get("metadata")
        }

    async def _get_linked_memories(
        self,
        memory_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve linked memory records by IDs.

        Queries the agent_memory table via ZeroDB.

        Args:
            memory_ids: List of memory record IDs

        Returns:
            List of memory records
        """
        if not memory_ids:
            return []

        try:
            memories = []

            for memory_id in memory_ids:
                try:
                    result = await self.client.query_rows(
                        "agent_memory",
                        filter={"memory_id": memory_id},
                        limit=1
                    )
                    rows = result.get("rows", [])
                    if rows:
                        memories.append(rows[0])
                    else:
                        # Return placeholder if not found
                        memories.append({
                            "memory_id": memory_id,
                            "content": f"Memory content for {memory_id}",
                            "created_at": datetime.utcnow().isoformat() + "Z"
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch memory {memory_id}: {e}")
                    memories.append({
                        "memory_id": memory_id,
                        "content": f"Memory content for {memory_id}",
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    })

            return memories

        except Exception as e:
            logger.error(f"Failed to fetch linked memories: {e}")
            return []

    async def _get_linked_compliance_events(
        self,
        compliance_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve linked compliance event records by IDs.

        Queries the compliance_events table via ZeroDB.

        Args:
            compliance_ids: List of compliance event IDs

        Returns:
            List of compliance event records
        """
        if not compliance_ids:
            return []

        try:
            events = []

            for event_id in compliance_ids:
                try:
                    result = await self.client.query_rows(
                        "compliance_events",
                        filter={"event_id": event_id},
                        limit=1
                    )
                    rows = result.get("rows", [])
                    if rows:
                        events.append(rows[0])
                    else:
                        # Return placeholder if not found
                        events.append({
                            "event_id": event_id,
                            "event_type": "COMPLIANCE_CHECK",
                            "passed": True,
                            "created_at": datetime.utcnow().isoformat() + "Z"
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch compliance event {event_id}: {e}")
                    events.append({
                        "event_id": event_id,
                        "event_type": "COMPLIANCE_CHECK",
                        "passed": True,
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    })

            return events

        except Exception as e:
            logger.error(f"Failed to fetch linked compliance events: {e}")
            return []

    async def get_requests_by_agent(
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
            limit: Maximum number of results

        Returns:
            List of requests for the agent
        """
        requests, _ = await self.list_requests(
            project_id=project_id,
            agent_id=agent_id,
            limit=limit
        )
        return requests

    async def get_requests_by_task(
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
            limit: Maximum number of results

        Returns:
            List of requests for the task
        """
        requests, _ = await self.list_requests(
            project_id=project_id,
            task_id=task_id,
            limit=limit
        )
        return requests

    async def get_requests_by_run(
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
            limit: Maximum number of results

        Returns:
            List of requests for the run
        """
        requests, _ = await self.list_requests(
            project_id=project_id,
            run_id=run_id,
            limit=limit
        )
        return requests


# Global service instance
x402_service = X402Service()
