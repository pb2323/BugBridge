"""
Notification Utilities

Helper functions for handling customer notifications when Jira tickets are resolved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.agents.notification import NotificationAgent
from bugbridge.config import get_settings
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    JiraTicket as DBJiraTicket,
    Notification as DBNotification,
)
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger
from pydantic import HttpUrl

logger = get_logger(__name__)


def convert_db_post_to_pydantic(db_post: DBFeedbackPost) -> FeedbackPost:
    """
    Convert database FeedbackPost model to Pydantic FeedbackPost model.
    
    Args:
        db_post: Database FeedbackPost model.
        
    Returns:
        Pydantic FeedbackPost model.
    """
    url = HttpUrl(db_post.url) if db_post.url else None
    
    return FeedbackPost(
        post_id=db_post.canny_post_id,
        board_id=db_post.board_id,
        title=db_post.title,
        content=db_post.content,
        author_id=db_post.author_id,
        author_name=db_post.author_name,
        created_at=db_post.created_at,
        updated_at=db_post.updated_at,
        votes=db_post.votes,
        comments_count=db_post.comments_count,
        status=db_post.status,
        url=url,
        tags=db_post.tags or [],
        collected_at=db_post.collected_at,
    )


async def check_notification_sent(
    session: AsyncSession,
    jira_ticket_id: UUID,
    feedback_post_id: UUID,
) -> bool:
    """
    Check if a notification has already been sent for this ticket/feedback post.
    
    Args:
        session: Database session.
        jira_ticket_id: Jira ticket database ID.
        feedback_post_id: Feedback post database ID.
        
    Returns:
        True if notification was already sent, False otherwise.
    """
    query = select(DBNotification).where(
        DBNotification.jira_ticket_id == jira_ticket_id,
        DBNotification.feedback_post_id == feedback_post_id,
        DBNotification.notification_status == "sent",
    )
    result = await session.execute(query)
    existing_notification = result.scalar_one_or_none()
    
    return existing_notification is not None


def is_resolution_status(status: str, resolution_statuses: list[str]) -> bool:
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


async def notify_customer_on_resolution(
    session: AsyncSession,
    db_ticket: DBJiraTicket,
    previous_status: Optional[str],
    current_status: str,
) -> bool:
    """
    Trigger customer notification when a Jira ticket becomes resolved.
    
    This function:
    - Checks if ticket status changed to resolved/done
    - Verifies notification hasn't been sent already
    - Triggers the notification agent to post reply to Canny.io
    - Saves notification record to database
    
    Args:
        session: Database session.
        db_ticket: Database Jira ticket model.
        previous_status: Previous ticket status (before refresh).
        current_status: Current ticket status (after refresh).
        
    Returns:
        True if notification was sent successfully, False otherwise.
    """
    try:
        # Get settings to check resolution statuses
        settings = get_settings()
        resolution_statuses = settings.jira.resolution_done_statuses
        
        # Check if ticket is now resolved
        if not is_resolution_status(current_status, resolution_statuses):
            logger.debug(
                f"Ticket {db_ticket.jira_issue_key} is not resolved (status: {current_status}), skipping notification"
            )
            return False
        
        # Check if ticket was already resolved (status didn't change to resolved)
        if previous_status and is_resolution_status(previous_status, resolution_statuses):
            logger.debug(
                f"Ticket {db_ticket.jira_issue_key} was already resolved (previous: {previous_status}), skipping notification"
            )
            return False
        
        # Check if notification was already sent
        if not db_ticket.feedback_post_id:
            logger.warning(
                f"Ticket {db_ticket.jira_issue_key} has no linked feedback post, cannot send notification"
            )
            return False
        
        notification_sent = await check_notification_sent(
            session=session,
            jira_ticket_id=db_ticket.id,
            feedback_post_id=db_ticket.feedback_post_id,
        )
        
        if notification_sent:
            logger.info(
                f"Notification already sent for ticket {db_ticket.jira_issue_key}, skipping"
            )
            return False
        
        # Get feedback post
        query = select(DBFeedbackPost).where(DBFeedbackPost.id == db_ticket.feedback_post_id)
        result = await session.execute(query)
        db_feedback_post = result.scalar_one_or_none()
        
        if not db_feedback_post:
            logger.error(
                f"Feedback post {db_ticket.feedback_post_id} not found for ticket {db_ticket.jira_issue_key}"
            )
            return False
        
        # Convert to Pydantic model
        feedback_post = convert_db_post_to_pydantic(db_feedback_post)
        
        # Get Jira ticket URL
        jira_settings = settings.jira
        if jira_settings.instance_url:
            jira_instance_url = str(jira_settings.instance_url)
            jira_ticket_url = f"{jira_instance_url}/browse/{db_ticket.jira_issue_key}"
        else:
            # Fallback: construct URL from ticket key only (notification will still work without full URL)
            logger.warning(
                f"JIRA__INSTANCE_URL not set for ticket {db_ticket.jira_issue_key}, "
                "notification will be sent without full ticket URL"
            )
            jira_ticket_url = None
        
        # Create workflow state for notification agent
        state: BugBridgeState = {
            "feedback_post": feedback_post,
            "jira_ticket_id": db_ticket.jira_issue_key,
            "jira_ticket_url": str(jira_ticket_url) if jira_ticket_url else None,
            "jira_ticket_status": current_status,
            "metadata": {},
        }
        
        # Initialize notification agent
        notification_agent = NotificationAgent()
        
        # Execute notification agent
        logger.info(
            f"Triggering notification for ticket {db_ticket.jira_issue_key} (status: {current_status})",
            extra={
                "ticket_key": db_ticket.jira_issue_key,
                "feedback_post_id": feedback_post.post_id,
                "feedback_post_title": feedback_post.title,
                "current_status": current_status,
                "previous_status": previous_status,
            }
        )
        
        result_state = await notification_agent.execute(state)
        
        # Check if notification was successful
        errors = result_state.get("errors", [])
        workflow_status = result_state.get("workflow_status")
        
        logger.info(
            f"Notification agent execution completed for ticket {db_ticket.jira_issue_key}",
            extra={
                "ticket_key": db_ticket.jira_issue_key,
                "workflow_status": workflow_status,
                "has_errors": bool(errors),
                "error_count": len(errors) if errors else 0,
            }
        )
        
        if errors:
            error_msg = errors[-1] if errors else "Unknown error"
            logger.error(
                f"Notification agent failed for ticket {db_ticket.jira_issue_key}: {error_msg}",
                extra={
                    "ticket_key": db_ticket.jira_issue_key,
                    "error": error_msg,
                }
            )
            return False
        
        # Check if workflow status indicates failure
        if workflow_status != "notified":
            logger.error(
                f"Notification workflow did not complete successfully for ticket {db_ticket.jira_issue_key}. Status: {workflow_status}",
                extra={
                    "ticket_key": db_ticket.jira_issue_key,
                    "workflow_status": workflow_status,
                }
            )
            return False
        
        # Save notification record to database
        notification_meta = result_state.get("metadata", {}).get("notification", {})
        
        notification = DBNotification(
            feedback_post_id=db_feedback_post.id,
            jira_ticket_id=db_ticket.id,
            notification_type="resolution_confirmation",
            notification_status="sent",
            reply_content=notification_meta.get("reply_message"),
            sent_at=datetime.now(UTC),
        )
        
        session.add(notification)
        await session.flush()  # Flush to get the ID, but don't commit yet (let caller commit)
        
        logger.info(
            f"Successfully sent notification for ticket {db_ticket.jira_issue_key} to feedback post {feedback_post.post_id}"
        )
        
        return True
        
    except Exception as e:
        logger.error(
            f"Error sending notification for ticket {db_ticket.jira_issue_key}: {str(e)}",
            exc_info=True,
        )
        return False

