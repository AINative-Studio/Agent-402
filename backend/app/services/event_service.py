"""
Event service layer.
Implements business logic for event operations.

PRD Alignment:
- §6: ZeroDB Integration with compliance_events and event logging
- §10: Success Criteria - audit trail and replayability
"""
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from app.core.config import settings
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)


class EventService:
    """
    Event service for creating and managing events.
    Uses ZeroDB MCP tools for event storage.
    """

    def __init__(self):
        """Initialize event service with ZeroDB configuration."""
        self.api_key = os.getenv("ZERODB_API_KEY")
        self.project_id = os.getenv("ZERODB_PROJECT_ID")
        self.base_url = os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio")

    async def create_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an event in ZeroDB with stable response format.

        Per GitHub Issue #40 (Stable Response Format):
        - Returns consistent format: id, event_type, data, timestamp, created_at
        - All fields always present in same order
        - Normalized ISO8601 timestamps

        Args:
            event_type: Type of event (e.g., 'agent_decision', 'compliance_check')
            data: Event payload data
            timestamp: Optional ISO 8601 timestamp (auto-generated if not provided)
            source: Optional event source identifier
            correlation_id: Optional correlation ID for tracking related events

        Returns:
            Stable event creation response per Issue #40:
            {
                "id": "evt_...",
                "event_type": "...",
                "data": {...},
                "timestamp": "2024-01-15T10:30:00.000Z",
                "created_at": "2024-01-15T10:30:01.234Z"
            }

        Raises:
            HTTPException: If event creation fails
        """
        # Generate event ID (UUID format)
        event_id = f"evt_{uuid.uuid4().hex[:16]}"

        # Normalize timestamp to ISO8601 with milliseconds
        if timestamp is None:
            now = datetime.now(timezone.utc)
            timestamp = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        else:
            # Parse and re-format to ensure consistent format
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            except (ValueError, AttributeError):
                # If parsing fails, use current time
                now = datetime.now(timezone.utc)
                timestamp = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Server-side created_at timestamp
        created_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Prepare event data for storage (internal format with all metadata)
        event_data = {
            "id": event_id,
            "event_type": event_type,
            "data": data,
            "timestamp": timestamp,
            "created_at": created_at
        }

        if source:
            event_data["source"] = source
        if correlation_id:
            event_data["correlation_id"] = correlation_id

        # Persist event to ZeroDB
        try:
            client = get_zerodb_client()
            # Map to events table schema:
            # id (uuid), event_id (text), project_id (text), event_type (text),
            # source (text), correlation_id (text), data (jsonb),
            # timestamp (timestamp), created_at (timestamp)
            row_data = {
                "id": str(uuid.uuid4()),
                "event_id": event_id,
                "project_id": self.project_id,
                "event_type": event_type,
                "source": source or "",
                "correlation_id": correlation_id or "",
                "data": json.dumps(data),  # jsonb column expects JSON string
                "timestamp": timestamp,
                "created_at": created_at
            }
            await client.insert_row("events", row_data)
            logger.info(f"Event persisted to ZeroDB: {event_id}")
        except Exception as e:
            # Log error but don't fail - still return the event
            logger.error(f"Failed to persist event to ZeroDB: {e}")

        # Return stable response format per Issue #40
        # Fields MUST be in this exact order: id, event_type, data, timestamp, created_at
        return {
            "id": event_id,
            "event_type": event_type,
            "data": data,
            "timestamp": timestamp,
            "created_at": created_at
        }

    async def store_agent_decision(
        self,
        agent_id: str,
        decision: str,
        reasoning: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an agent_decision event.

        Args:
            agent_id: Agent identifier (DID or agent ID)
            decision: Decision made by the agent
            reasoning: Reasoning behind the decision
            context: Additional context for the decision
            correlation_id: Optional correlation ID

        Returns:
            Event creation response
        """
        return await self.create_event(
            event_type="agent_decision",
            data={
                "agent_id": agent_id,
                "decision": decision,
                "reasoning": reasoning,
                "context": context
            },
            correlation_id=correlation_id
        )

    async def store_agent_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an agent_tool_call event.

        Args:
            agent_id: Agent identifier
            tool_name: Name of the tool called
            parameters: Parameters passed to the tool
            result: Optional result returned by the tool
            correlation_id: Optional correlation ID

        Returns:
            Event creation response
        """
        data = {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "parameters": parameters
        }
        if result is not None:
            data["result"] = result

        return await self.create_event(
            event_type="agent_tool_call",
            data=data,
            correlation_id=correlation_id
        )

    async def store_agent_error(
        self,
        agent_id: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an agent_error event.

        Args:
            agent_id: Agent identifier
            error_type: Type/category of error
            error_message: Error message
            context: Additional error context
            correlation_id: Optional correlation ID

        Returns:
            Event creation response
        """
        return await self.create_event(
            event_type="agent_error",
            data={
                "agent_id": agent_id,
                "error_type": error_type,
                "error_message": error_message,
                "context": context
            },
            correlation_id=correlation_id
        )

    async def store_agent_start(
        self,
        agent_id: str,
        task: str,
        config: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an agent_start event.

        Args:
            agent_id: Agent identifier
            task: Task being started
            config: Agent configuration for this task
            correlation_id: Optional correlation ID

        Returns:
            Event creation response
        """
        return await self.create_event(
            event_type="agent_start",
            data={
                "agent_id": agent_id,
                "task": task,
                "config": config
            },
            correlation_id=correlation_id
        )

    async def store_agent_complete(
        self,
        agent_id: str,
        result: Dict[str, Any],
        duration_ms: int,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an agent_complete event.

        Args:
            agent_id: Agent identifier
            result: Result of the completed task
            duration_ms: Task duration in milliseconds
            correlation_id: Optional correlation ID

        Returns:
            Event creation response
        """
        return await self.create_event(
            event_type="agent_complete",
            data={
                "agent_id": agent_id,
                "result": result,
                "duration_ms": duration_ms
            },
            correlation_id=correlation_id
        )


# Singleton instance
event_service = EventService()
