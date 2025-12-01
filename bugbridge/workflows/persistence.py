"""
Workflow State Persistence

Functions for saving and loading workflow state to/from the database
for workflow resumption and state management.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.database.connection import get_session_context
from bugbridge.database.models import FeedbackPost as DBFeedbackPost, WorkflowState
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def save_workflow_state(
    state: BugBridgeState,
    feedback_post_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> str:
    """
    Save workflow state to database.

    Args:
        state: Current workflow state to save.
        feedback_post_id: Canny.io post ID (extracted from state if not provided).
        workflow_id: Unique workflow identifier (generated if not provided).

    Returns:
        Workflow ID (UUID string).
    """
    # Extract feedback_post_id from state if not provided
    if feedback_post_id is None and state.get("feedback_post"):
        feedback_post = state["feedback_post"]
        if hasattr(feedback_post, "post_id"):
            feedback_post_id = feedback_post.post_id
        elif isinstance(feedback_post, dict):
            feedback_post_id = feedback_post.get("post_id")

    if not feedback_post_id:
        raise ValueError("feedback_post_id must be provided or available in state")

    # Generate workflow_id if not provided
    if workflow_id is None:
        workflow_id = str(uuid4())

    # Find the feedback post in database to get its internal ID
    async with get_session_context() as session:
        result = await session.execute(
            select(DBFeedbackPost).where(DBFeedbackPost.canny_post_id == feedback_post_id)
        )
        db_feedback_post = result.scalar_one_or_none()

        if not db_feedback_post:
            raise ValueError(f"Feedback post {feedback_post_id} not found in database")

        # Serialize state to JSON (convert Pydantic models to dicts)
        state_dict = _serialize_state_for_storage(state)

        # Create or update workflow state record
        # Use workflow_id as the id if provided, otherwise create new
        workflow_uuid = UUID(workflow_id) if workflow_id else uuid4()
        result = await session.execute(
            select(WorkflowState).where(WorkflowState.id == workflow_uuid)
        )
        existing_state = result.scalar_one_or_none()

        if existing_state:
            # Update existing workflow state
            existing_state.state_data = state_dict
            existing_state.workflow_status = state.get("workflow_status") or "unknown"
            workflow_state = existing_state
        else:
            # Create new workflow state with specified ID or auto-generate
            workflow_state = WorkflowState(
                id=workflow_uuid,
                feedback_post_id=db_feedback_post.id,
                state_data=state_dict,
                workflow_status=state.get("workflow_status") or "unknown",
            )
            session.add(workflow_state)

        await session.flush()

        logger.info(
            f"Saved workflow state: {workflow_id}",
            extra={
                "workflow_id": workflow_id,
                "feedback_post_id": feedback_post_id,
                "workflow_status": state.get("workflow_status"),
            },
        )

        return workflow_id


async def load_workflow_state(workflow_id: str) -> Optional[BugBridgeState]:
    """
    Load workflow state from database.

    Args:
        workflow_id: Workflow identifier (UUID string).

    Returns:
        Workflow state dictionary, or None if not found.
    """
    async with get_session_context() as session:
        result = await session.execute(
            select(WorkflowState).where(WorkflowState.id == UUID(workflow_id))
        )
        workflow_state = result.scalar_one_or_none()

        if not workflow_state:
            logger.warning(f"Workflow state not found: {workflow_id}", extra={"workflow_id": workflow_id})
            return None

        # Deserialize state from JSON
        state = _deserialize_state_from_storage(workflow_state.state_data or {})

        logger.info(
            f"Loaded workflow state: {workflow_id}",
            extra={
                "workflow_id": workflow_id,
                "workflow_status": workflow_state.workflow_status,
            },
        )

        return state


async def get_workflow_state_by_post_id(feedback_post_id: str) -> Optional[BugBridgeState]:
    """
    Load workflow state by feedback post ID.

    Args:
        feedback_post_id: Canny.io post ID.

    Returns:
        Workflow state dictionary, or None if not found.
    """
    async with get_session_context() as session:
        # Find feedback post
        result = await session.execute(
            select(DBFeedbackPost).where(DBFeedbackPost.canny_post_id == feedback_post_id)
        )
        db_feedback_post = result.scalar_one_or_none()

        if not db_feedback_post:
            return None

        # Find most recent workflow state for this post
        result = await session.execute(
            select(WorkflowState)
            .where(WorkflowState.feedback_post_id == db_feedback_post.id)
            .order_by(WorkflowState.last_updated_at.desc())
            .limit(1)
        )
        workflow_state = result.scalar_one_or_none()

        if not workflow_state:
            return None

        # Deserialize state from JSON
        state = _deserialize_state_from_storage(workflow_state.state_data or {})

        return state


def _serialize_state_for_storage(state: BugBridgeState) -> Dict[str, Any]:
    """
    Serialize workflow state to JSON-serializable dictionary.

    Args:
        state: Workflow state to serialize.

    Returns:
        JSON-serializable dictionary.
    """
    from bugbridge.models.feedback import FeedbackPost

    state_dict: Dict[str, Any] = {}

    # Serialize feedback_post if present
    if state.get("feedback_post"):
        feedback_post = state["feedback_post"]
        if hasattr(feedback_post, "model_dump"):
            state_dict["feedback_post"] = feedback_post.model_dump(mode="json")
        elif isinstance(feedback_post, dict):
            state_dict["feedback_post"] = feedback_post
        else:
            state_dict["feedback_post"] = json.loads(feedback_post.json() if hasattr(feedback_post, "json") else str(feedback_post))

    # Serialize analysis results if present
    if state.get("bug_detection"):
        bug_detection = state["bug_detection"]
        if hasattr(bug_detection, "model_dump"):
            state_dict["bug_detection"] = bug_detection.model_dump(mode="json")
        else:
            state_dict["bug_detection"] = bug_detection

    if state.get("sentiment_analysis"):
        sentiment = state["sentiment_analysis"]
        if hasattr(sentiment, "model_dump"):
            state_dict["sentiment_analysis"] = sentiment.model_dump(mode="json")
        else:
            state_dict["sentiment_analysis"] = sentiment

    if state.get("priority_score"):
        priority = state["priority_score"]
        if hasattr(priority, "model_dump"):
            state_dict["priority_score"] = priority.model_dump(mode="json")
        else:
            state_dict["priority_score"] = priority

    # Serialize simple fields
    state_dict["jira_ticket_id"] = state.get("jira_ticket_id")
    state_dict["jira_ticket_url"] = state.get("jira_ticket_url")
    state_dict["jira_ticket_status"] = state.get("jira_ticket_status")
    state_dict["workflow_status"] = state.get("workflow_status")
    state_dict["errors"] = state.get("errors", [])

    # Serialize timestamps (convert datetime to ISO strings)
    timestamps = state.get("timestamps", {})
    state_dict["timestamps"] = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in timestamps.items()
    }

    # Serialize metadata
    state_dict["metadata"] = state.get("metadata", {})

    return state_dict


def _deserialize_state_from_storage(state_dict: Dict[str, Any]) -> BugBridgeState:
    """
    Deserialize workflow state from JSON dictionary.

    Args:
        state_dict: JSON dictionary from database.

    Returns:
        Workflow state dictionary.
    """
    from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
    from bugbridge.models.feedback import FeedbackPost

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Deserialize feedback_post if present
    if state_dict.get("feedback_post"):
        try:
            state["feedback_post"] = FeedbackPost.model_validate(state_dict["feedback_post"])
        except Exception as e:
            logger.warning(f"Failed to deserialize feedback_post: {str(e)}")

    # Deserialize analysis results if present
    if state_dict.get("bug_detection"):
        try:
            state["bug_detection"] = BugDetectionResult.model_validate(state_dict["bug_detection"])
        except Exception as e:
            logger.warning(f"Failed to deserialize bug_detection: {str(e)}")

    if state_dict.get("sentiment_analysis"):
        try:
            state["sentiment_analysis"] = SentimentAnalysisResult.model_validate(state_dict["sentiment_analysis"])
        except Exception as e:
            logger.warning(f"Failed to deserialize sentiment_analysis: {str(e)}")

    if state_dict.get("priority_score"):
        try:
            state["priority_score"] = PriorityScoreResult.model_validate(state_dict["priority_score"])
        except Exception as e:
            logger.warning(f"Failed to deserialize priority_score: {str(e)}")

    # Deserialize simple fields
    state["jira_ticket_id"] = state_dict.get("jira_ticket_id")
    state["jira_ticket_url"] = state_dict.get("jira_ticket_url")
    state["jira_ticket_status"] = state_dict.get("jira_ticket_status")
    state["workflow_status"] = state_dict.get("workflow_status")
    state["errors"] = state_dict.get("errors", [])

    # Deserialize timestamps (convert ISO strings to datetime)
    timestamps_dict = state_dict.get("timestamps", {})
    state["timestamps"] = {
        key: datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        for key, value in timestamps_dict.items()
    }

    # Deserialize metadata
    state["metadata"] = state_dict.get("metadata", {})

    return state


__all__ = [
    "save_workflow_state",
    "load_workflow_state",
    "get_workflow_state_by_post_id",
]

