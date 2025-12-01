"""
Main LangGraph Workflow

Defines the StateGraph workflow for BugBridge feedback processing pipeline.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Literal, Optional

from langgraph.graph import END, StateGraph

from bugbridge.agents.collection import collect_feedback_node
from bugbridge.agents.bug_detection import analyze_bug_node
from bugbridge.agents.sentiment import analyze_sentiment_node
from bugbridge.agents.priority import calculate_priority_node
from bugbridge.models.state import BugBridgeState


from bugbridge.agents.jira_creation import create_jira_ticket_node
from bugbridge.agents.monitoring import monitor_status_node
from bugbridge.agents.notification import notify_customer_node


def should_create_ticket(state: BugBridgeState) -> Literal["create_ticket", "skip"]:
    """
    Conditional edge function: determine if Jira ticket should be created.

    Args:
        state: Current workflow state.

    Returns:
        "create_ticket" if ticket should be created, "skip" otherwise.
    """
    from bugbridge.models.analysis import PriorityScoreResult

    priority_score_data = state.get("priority_score")
    if not priority_score_data:
        return "skip"

    # Handle both dict and PriorityScoreResult object
    if isinstance(priority_score_data, dict):
        priority_score_value = priority_score_data.get("priority_score")
    else:
        priority_score_value = priority_score_data.priority_score

    # Create ticket if priority score is >= 50 (medium priority or higher)
    if priority_score_value and priority_score_value >= 50:
        return "create_ticket"
    return "skip"


def should_monitor_ticket(state: BugBridgeState) -> Literal["monitor", "skip"]:
    """
    Conditional edge function: determine if ticket monitoring should start.

    Args:
        state: Current workflow state.

    Returns:
        "monitor" if monitoring should start, "skip" otherwise.
    """
    # Monitor if ticket was created
    if state.get("jira_ticket_id"):
        return "monitor"
    return "skip"


def should_notify_customer(state: BugBridgeState) -> Literal["notify", "skip", "timeout"]:
    """
    Conditional edge function: determine if customer should be notified or if monitoring timed out.

    Args:
        state: Current workflow state.

    Returns:
        "notify" if customer should be notified (ticket is resolved),
        "timeout" if monitoring has timed out,
        "skip" to continue monitoring (ticket not resolved yet, but not timed out).
    """
    from bugbridge.agents.monitoring import is_resolution_status
    from bugbridge.config import get_settings

    # Check for monitoring timeout
    if state.get("workflow_status") == "monitoring_timeout":
        return "timeout"

    # Check if workflow status indicates resolution
    if state.get("workflow_status") == "resolved":
        return "notify"

    # Also check ticket status against configured resolution statuses
    current_status = state.get("jira_ticket_status")
    if current_status:
        try:
            settings = get_settings()
            resolution_statuses = settings.jira.resolution_done_statuses
            if is_resolution_status(current_status, resolution_statuses):
                return "notify"
        except Exception:
            # Fallback to default statuses if config unavailable
            if current_status in ["Done", "Resolved", "Closed"]:
                return "notify"

    # Ticket not resolved yet - continue monitoring (skip notification for now)
    # The workflow will loop back to monitor_status, and the agent will handle polling delay
    return "skip"


def create_workflow() -> StateGraph:
    """
    Create and configure the BugBridge LangGraph workflow.

    Returns:
        Compiled StateGraph workflow ready for execution.
    """
    # Create StateGraph with BugBridgeState
    workflow = StateGraph(BugBridgeState)

    # Add nodes
    workflow.add_node("collect_feedback", collect_feedback_node)
    workflow.add_node("analyze_bug", analyze_bug_node)
    workflow.add_node("analyze_sentiment", analyze_sentiment_node)
    workflow.add_node("calculate_priority", calculate_priority_node)
    workflow.add_node("create_jira_ticket", create_jira_ticket_node)
    workflow.add_node("monitor_status", monitor_status_node)
    workflow.add_node("notify_customer", notify_customer_node)

    # Set entry point
    workflow.set_entry_point("collect_feedback")

    # Add sequential edges
    workflow.add_edge("collect_feedback", "analyze_bug")
    workflow.add_edge("analyze_bug", "analyze_sentiment")
    workflow.add_edge("analyze_sentiment", "calculate_priority")

    # Conditional edge: create ticket or skip
    workflow.add_conditional_edges(
        "calculate_priority",
        should_create_ticket,
        {
            "create_ticket": "create_jira_ticket",
            "skip": END,
        },
    )

    # Conditional edge: monitor ticket or skip
    workflow.add_conditional_edges(
        "create_jira_ticket",
        should_monitor_ticket,
        {
            "monitor": "monitor_status",
            "skip": END,
        },
    )

    # Conditional edge: notify customer, continue monitoring, or handle timeout
    # If ticket is resolved, notify customer; if timed out, end workflow; otherwise, continue monitoring (loop back)
    workflow.add_conditional_edges(
        "monitor_status",
        should_notify_customer,
        {
            "notify": "notify_customer",
            "skip": "monitor_status",  # Loop back to monitoring if not resolved yet (polling delay handled in agent)
            "timeout": END,  # End workflow if monitoring timeout reached
        },
    )

    # Complete workflow
    workflow.add_edge("notify_customer", END)

    return workflow


def compile_workflow() -> Any:
    """
    Compile the BugBridge workflow for execution.

    Returns:
        Compiled workflow application.
    """
    workflow = create_workflow()
    return workflow.compile()


# Create a global compiled workflow instance
_app: Any = None


def get_workflow_app() -> Any:
    """
    Get or create the compiled workflow application.

    Returns:
        Compiled workflow application instance.
    """
    global _app
    if _app is None:
        _app = compile_workflow()
    return _app


async def execute_workflow(
    initial_state: Optional[BugBridgeState] = None,
    config: Optional[Dict[str, Any]] = None,
    stream: bool = False,
) -> BugBridgeState:
    """
    Execute the BugBridge workflow with error handling.

    Args:
        initial_state: Initial workflow state (defaults to empty state).
        config: Optional runtime configuration for workflow execution.
        stream: Whether to stream workflow execution (default: False).

    Returns:
        Final workflow state after execution.

    Raises:
        RuntimeError: If workflow execution fails critically.
    """
    from bugbridge.utils.logging import get_logger

    workflow_logger = get_logger(__name__)

    if initial_state is None:
        initial_state = {
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

    try:
        workflow_logger.info(
            "Starting workflow execution",
            extra={
                "has_feedback_post": initial_state.get("feedback_post") is not None,
                "workflow_status": initial_state.get("workflow_status"),
            },
        )

        app = get_workflow_app()

        if stream:
            # Stream execution
            final_state = None
            async for state in app.astream(initial_state, config=config):
                final_state = state
                workflow_logger.debug(f"Workflow state update: {list(state.keys())}")
            return final_state if final_state else initial_state
        else:
            # Execute synchronously (async but waits for completion)
            result = await app.ainvoke(initial_state, config=config)
            return result

    except Exception as e:
        workflow_logger.error(
            f"Workflow execution failed: {str(e)}",
            exc_info=True,
        )
        # Return state with error
        return {
            **initial_state,
            "workflow_status": "failed",
            "errors": initial_state.get("errors", []) + [f"Workflow execution failed: {str(e)}"],
        }


async def stream_workflow(
    initial_state: Optional[BugBridgeState] = None,
    config: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[BugBridgeState]:
    """
    Stream workflow execution, yielding state updates at each step.

    Args:
        initial_state: Initial workflow state (defaults to empty state).
        config: Optional runtime configuration for workflow execution.

    Yields:
        Workflow state after each node execution.
    """
    from bugbridge.utils.logging import get_logger

    workflow_logger = get_logger(__name__)

    if initial_state is None:
        initial_state = {
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

    try:
        app = get_workflow_app()

        async for state_update in app.astream(initial_state, config=config):
            workflow_logger.debug(f"Workflow state update: {list(state_update.keys())}")
            yield state_update

    except Exception as e:
        workflow_logger.error(
            f"Workflow streaming failed: {str(e)}",
            exc_info=True,
        )
        # Yield error state
        yield {
            **initial_state,
            "workflow_status": "failed",
            "errors": initial_state.get("errors", []) + [f"Workflow execution failed: {str(e)}"],
        }


__all__ = [
    "create_workflow",
    "compile_workflow",
    "get_workflow_app",
    "execute_workflow",
    "stream_workflow",
    "should_create_ticket",
    "should_monitor_ticket",
    "should_notify_customer",
    # Node functions (exported for reference)
    "analyze_bug_node",
    "analyze_sentiment_node",
    "calculate_priority_node",
    "create_jira_ticket_node",
    "monitor_status_node",
    "notify_customer_node",
]

