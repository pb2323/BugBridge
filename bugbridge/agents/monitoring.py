"""
Monitoring Agent

Monitors Jira ticket status changes and detects when tickets are resolved.
Triggers notification workflow when resolution is detected.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from bugbridge.agents.base import BaseAgent
from bugbridge.config import JiraSettings, get_settings
from bugbridge.integrations.mcp_jira import (
    MCPJiraClient,
    MCPJiraError,
    MCPJiraConnectionError,
    MCPJiraNotFoundError,
)
from bugbridge.models.jira import JiraTicket
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


def is_resolution_status(status: str, resolution_statuses: List[str]) -> bool:
    """
    Check if a status indicates resolution.

    Args:
        status: Current Jira ticket status.
        resolution_statuses: List of statuses that indicate resolution.

    Returns:
        True if status is a resolution status, False otherwise.
    """
    if not status or not resolution_statuses:
        return False

    # Normalize status for comparison (case-insensitive, strip whitespace)
    normalized_status = status.strip().lower()
    normalized_resolution_statuses = [s.strip().lower() for s in resolution_statuses]

    return normalized_status in normalized_resolution_statuses


def track_status_change(
    state: BugBridgeState,
    previous_status: Optional[str],
    current_status: str,
    ticket_key: str,
) -> BugBridgeState:
    """
    Track status change in workflow state.

    Args:
        state: Current workflow state.
        previous_status: Previous ticket status (if any).
        current_status: Current ticket status.
        ticket_key: Jira ticket key.

    Returns:
        Updated workflow state with status change tracking.
    """
    # Initialize status history if not present
    if "status_history" not in state.get("metadata", {}):
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"]["status_history"] = []

    status_history: List[Dict[str, Any]] = state["metadata"]["status_history"]

    # Only track if status actually changed
    if previous_status != current_status:
        status_entry = {
            "status": current_status,
            "previous_status": previous_status,
            "ticket_key": ticket_key,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        status_history.append(status_entry)

        logger.info(
            f"Status change detected for {ticket_key}: {previous_status} → {current_status}",
            extra={
                "agent_name": "monitoring_agent",
                "ticket_key": ticket_key,
                "previous_status": previous_status,
                "current_status": current_status,
            },
        )

    # Update current status in state
    state["jira_ticket_status"] = current_status
    state["metadata"]["status_history"] = status_history

    return state


class MonitoringAgent(BaseAgent):
    """
    Monitoring Agent for tracking Jira ticket status changes.

    This agent:
    - Polls Jira for ticket status updates
    - Tracks status change history
    - Detects resolution statuses
    - Triggers notification workflow when tickets are resolved
    """

    def __init__(
        self,
        llm=None,  # Monitoring agent doesn't use LLM, but kept for consistency
        deterministic: bool = True,
        jira_client: Optional[MCPJiraClient] = None,
    ):
        """
        Initialize Monitoring Agent.

        Args:
            llm: Optional XAI LLM instance (not used, but kept for consistency).
            deterministic: Whether to enforce deterministic behavior.
            jira_client: Optional MCPJiraClient instance (creates one if not provided).
        """
        super().__init__(
            name="monitoring_agent",
            llm=llm,
            deterministic=deterministic,
        )
        self._jira_client = jira_client
        self._settings: Optional[JiraSettings] = None

    def _get_jira_client(self) -> MCPJiraClient:
        """
        Get or create MCPJiraClient instance.

        Returns:
            MCPJiraClient instance.
        """
        if self._jira_client:
            return self._jira_client

        try:
            settings = get_settings()
            self._settings = settings.jira

            return MCPJiraClient(
                server_url=str(self._settings.server_url),
                project_key=self._settings.project_key,
                auto_connect=True,
            )
        except Exception as e:
            logger.error(
                f"Failed to create MCP Jira client: {str(e)}",
                extra={"agent_name": self.name},
                exc_info=True,
            )
            raise

    async def check_ticket_status(self, ticket_key: str) -> Optional[JiraTicket]:
        """
        Check current status of a Jira ticket.

        Args:
            ticket_key: Jira issue key (e.g., "PROJ-123").

        Returns:
            JiraTicket object with current status, or None if ticket not found.

        Raises:
            MCPJiraError: If status check fails.
        """
        jira_client = self._get_jira_client()

        try:
            logger.info(
                f"Checking status for Jira ticket {ticket_key}",
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                },
            )

            async with jira_client.connection():
                ticket = await jira_client.get_issue(ticket_key)

            logger.info(
                f"Retrieved status for {ticket_key}: {ticket.status}",
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                    "status": ticket.status,
                },
            )

            return ticket

        except MCPJiraNotFoundError:
            logger.warning(
                f"Jira ticket {ticket_key} not found",
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                },
            )
            return None
        except MCPJiraConnectionError as e:
            error_msg = f"Connection error checking ticket status: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                    "error_type": "connection",
                },
                exc_info=True,
            )
            raise
        except MCPJiraError as e:
            error_msg = f"Failed to check ticket status: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                    "error_type": "generic",
                },
                exc_info=True,
            )
            raise

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute monitoring check for Jira ticket status.

        Args:
            state: Current workflow state containing jira_ticket_id.

        Returns:
            Updated workflow state with current ticket status and resolution detection.
        """
        # Validate required state
        ticket_key = state.get("jira_ticket_id")
        if not ticket_key:
            error_msg = "Monitoring Agent requires jira_ticket_id in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Get settings for resolution statuses
        try:
            settings = get_settings()
            jira_settings = settings.jira
            resolution_statuses = jira_settings.resolution_done_statuses
        except Exception as e:
            error_msg = f"Failed to load Jira settings: {str(e)}"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Get previous status from state
        previous_status = state.get("jira_ticket_status")

        # Check current ticket status
        try:
            ticket = await self.check_ticket_status(ticket_key)
            if not ticket:
                error_msg = f"Jira ticket {ticket_key} not found"
                logger.error(error_msg, extra={"agent_name": self.name, "ticket_key": ticket_key})
                return self.add_state_error(state, error_msg)

            current_status = ticket.status

            # Track status change
            state = track_status_change(state, previous_status, current_status, ticket_key)

            # Check if ticket is resolved
            is_resolved = is_resolution_status(current_status, resolution_statuses)

            if is_resolved:
                logger.info(
                    f"Ticket {ticket_key} is resolved with status: {current_status}",
                    extra={
                        "agent_name": self.name,
                        "ticket_key": ticket_key,
                        "status": current_status,
                        "resolution_statuses": resolution_statuses,
                    },
                )

                # Update workflow state
                state["workflow_status"] = "resolved"
                state = self.update_state_timestamp(state, "resolved_at")

                # Log agent decision
                self.log_agent_decision(
                    "ticket_resolved",
                    f"Ticket {ticket_key} resolved with status: {current_status}",
                    state,
                    {
                        "ticket_key": ticket_key,
                        "status": current_status,
                        "previous_status": previous_status,
                    },
                )

                # Log agent action
                self.log_agent_action(
                    "ticket_resolution_detected",
                    {
                        "ticket_key": ticket_key,
                        "status": current_status,
                        "previous_status": previous_status,
                    },
                    state,
                )
            else:
                # Ticket is still in progress
                state["workflow_status"] = "monitoring"
                state = self.update_state_timestamp(state, "status_checked_at")

                # Get polling attempt info
                monitoring_meta = state.get("metadata", {}).get("monitoring", {})
                attempt_count = monitoring_meta.get("attempt_count", 0)

                logger.info(
                    f"Ticket {ticket_key} status: {current_status} (not resolved yet, attempt {attempt_count})",
                    extra={
                        "agent_name": self.name,
                        "ticket_key": ticket_key,
                        "status": current_status,
                        "attempt_count": attempt_count,
                        "next_check_in_seconds": poll_interval,
                    },
                )

                # Log agent action
                self.log_agent_action(
                    "status_check",
                    {
                        "ticket_key": ticket_key,
                        "status": current_status,
                        "is_resolved": False,
                        "attempt_count": attempt_count,
                    },
                    state,
                )

                # Store polling interval in metadata for workflow delay handling
                if "metadata" not in state:
                    state["metadata"] = {}
                state["metadata"]["monitoring"]["poll_interval_seconds"] = poll_interval
                state["metadata"]["monitoring"]["next_check_at"] = (
                    datetime.now(UTC) + timedelta(seconds=poll_interval)
                ).isoformat()

            return state

        except MCPJiraConnectionError as e:
            error_msg = f"Connection error monitoring ticket {ticket_key}: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                    "error_type": "connection",
                },
                exc_info=True,
            )
            # Don't fail the workflow on connection errors - just log and continue monitoring
            # The next polling cycle will retry
            state["workflow_status"] = "monitoring"
            return self.add_state_error(state, error_msg)

        except MCPJiraError as e:
            error_msg = f"Failed to monitor ticket {ticket_key}: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "ticket_key": ticket_key,
                    "error_type": "generic",
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

    async def run(self, state: BugBridgeState) -> BugBridgeState:
        """
        Run the monitoring agent (wrapper for execute).

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        logger.info(
            "Starting monitoring agent execution",
            extra={"agent_name": self.name},
        )

        try:
            result_state = await self.execute(state)
            logger.info(
                "Monitoring agent execution completed",
                extra={"agent_name": self.name},
            )
            return result_state
        except Exception as e:
            error_msg = f"Monitoring agent execution failed: {str(e)}"
            logger.error(
                error_msg,
                extra={"agent_name": self.name},
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)


async def monitor_status_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for Monitoring Agent.

    This node:
    - Checks Jira ticket status
    - Detects resolution
    - Implements polling delay before next check (if not resolved)
    - Handles monitoring timeout

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with current ticket status.
    """
    agent = MonitoringAgent()
    result_state = await agent.run(state)

    # If ticket is not resolved and not timed out, add polling delay
    # The delay is handled here at the workflow level to prevent immediate re-execution
    workflow_status = result_state.get("workflow_status")
    if workflow_status == "monitoring":
        # Get polling interval from metadata (set by agent)
        metadata = result_state.get("metadata", {})
        monitoring_meta = metadata.get("monitoring", {})
        poll_interval = monitoring_meta.get("poll_interval_seconds")

        if poll_interval:
            logger.info(
                f"Waiting {poll_interval} seconds before next status check",
                extra={
                    "agent_name": "monitoring_agent",
                    "poll_interval_seconds": poll_interval,
                },
            )
            # Sleep for polling interval before next check
            # This prevents the workflow from immediately looping back
            await asyncio.sleep(poll_interval)

    return result_state


def get_monitoring_agent() -> MonitoringAgent:
    """
    Get or create Monitoring Agent instance.

    Returns:
        MonitoringAgent instance.
    """
    return MonitoringAgent()

