"""
Feedback Collection Agent

Agent responsible for collecting feedback posts from Canny.io,
filtering duplicates, and storing them in the database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.database.connection import get_session_context
from bugbridge.database.models import FeedbackPost as DBFeedbackPost
from bugbridge.integrations.canny import CannyClient, CannyAPIError
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_audit_logger, get_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()


async def check_post_exists(session: AsyncSession, post_id: str) -> bool:
    """
    Check if a feedback post already exists in the database.

    Args:
        session: Database session.
        post_id: Canny.io post ID.

    Returns:
        True if post exists, False otherwise.
    """
    result = await session.execute(
        select(DBFeedbackPost).where(DBFeedbackPost.canny_post_id == post_id)
    )
    return result.scalar_one_or_none() is not None


async def store_feedback_post(session: AsyncSession, post: FeedbackPost) -> DBFeedbackPost:
    """
    Store a feedback post in the database.

    Args:
        session: Database session.
        post: FeedbackPost Pydantic model to store.

    Returns:
        Stored database model instance.
    """
    db_post = DBFeedbackPost(
        canny_post_id=post.post_id,
        board_id=post.board_id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_name=post.author_name,
        created_at=post.created_at,
        updated_at=post.updated_at,
        votes=post.votes,
        comments_count=post.comments_count,
        status=post.status,
        url=str(post.url) if post.url else None,
        tags=post.tags,
        collected_at=post.collected_at,
    )

    session.add(db_post)
    await session.flush()  # Flush to get ID if needed

    return db_post


async def collect_feedback_from_canny(
    board_id: Optional[str] = None,
    limit: int = 100,
    status: Optional[str] = None,
    skip_duplicates: bool = True,
) -> List[FeedbackPost]:
    """
    Collect feedback posts from Canny.io.

    Args:
        board_id: Board ID to filter posts (defaults to config).
        limit: Maximum number of posts to retrieve.
        status: Filter by post status (e.g., "open", "complete").
        skip_duplicates: Whether to skip posts that already exist in database.

    Returns:
        List of newly collected FeedbackPost instances.
    """
    collected_posts: List[FeedbackPost] = []

    async with CannyClient() as canny_client:
        try:
            # List posts from Canny.io
            all_posts = await canny_client.list_posts(
                board_id=board_id,
                limit=limit,
                skip=0,
                status=status,
            )

            logger.info(
                f"Retrieved {len(all_posts)} posts from Canny.io",
                extra={"count": len(all_posts), "board_id": board_id},
            )

            if skip_duplicates:
                # Check each post against database
                async with get_session_context() as session:
                    new_posts = []
                    for post in all_posts:
                        exists = await check_post_exists(session, post.post_id)
                        if not exists:
                            new_posts.append(post)
                        else:
                            logger.debug(
                                f"Skipping duplicate post {post.post_id}",
                                extra={"post_id": post.post_id},
                            )

                    collected_posts = new_posts
                    logger.info(
                        f"Found {len(new_posts)} new posts (skipped {len(all_posts) - len(new_posts)} duplicates)",
                        extra={"new_count": len(new_posts), "total_count": len(all_posts)},
                    )
            else:
                collected_posts = all_posts

            # Store new posts in database
            if collected_posts:
                async with get_session_context() as session:
                    for post in collected_posts:
                        try:
                            await store_feedback_post(session, post)
                            audit_logger.log_agent_action(
                                agent_name="FeedbackCollectionAgent",
                                action=f"collected_post_{post.post_id}",
                                result="success",
                                post_id=post.post_id,
                                context={
                                    "title": post.title,
                                    "board_id": post.board_id,
                                    "votes": post.votes,
                                },
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to store post {post.post_id}: {str(e)}",
                                extra={"post_id": post.post_id},
                                exc_info=True,
                            )

        except CannyAPIError as e:
            logger.error(
                f"Canny API error during collection: {str(e)}",
                extra={"status_code": e.status_code},
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during feedback collection: {str(e)}",
                exc_info=True,
            )
            raise

    return collected_posts


async def collect_feedback_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for collecting feedback from Canny.io.

    This function:
    1. Collects new feedback posts from Canny.io
    2. Filters duplicates against database
    3. Stores new posts in database
    4. Updates workflow state with collected post

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with collected feedback post.
    """
    logger.info(
        "Starting feedback collection",
        extra={
            "workflow_status": state.get("workflow_status"),
        },
    )

    try:
        # Collect feedback from Canny.io
        # For now, collect a single post (will be extended to batch processing)
        posts = await collect_feedback_from_canny(
            board_id=None,  # Use config default
            limit=1,  # Collect one post at a time for workflow processing
            status="open",  # Only collect open posts
            skip_duplicates=True,
        )

        if not posts:
            # No new posts to process
            logger.info("No new feedback posts to collect")
            return {
                **state,
                "workflow_status": None,  # No workflow to start
                "errors": state.get("errors", []) + ["No new posts available"],
                "timestamps": {
                    **state.get("timestamps", {}),
                    "collection_attempt": datetime.now(UTC),
                },
            }

        # Use the first collected post for workflow processing
        post = posts[0]

        logger.info(
            f"Collected feedback post: {post.title[:50]}...",
            extra={
                "post_id": post.post_id,
                "board_id": post.board_id,
                "votes": post.votes,
            },
        )

        # Update state with collected post
        updated_state: BugBridgeState = {
            **state,
            "feedback_post": post,
            "workflow_status": "collected",
            "errors": state.get("errors", []),
            "timestamps": {
                **state.get("timestamps", {}),
                "collected_at": datetime.now(UTC),
            },
            "metadata": {
                **state.get("metadata", {}),
                "source": "canny",
                "collection_method": "polling",
            },
        }

        audit_logger.log_workflow_state_change(
            workflow_id=post.post_id,  # Use post_id as workflow identifier
            from_state=state.get("workflow_status") or "initial",
            to_state="collected",
            post_id=post.post_id,
            context={
                "title": post.title,
                "board_id": post.board_id,
            },
        )

        return updated_state

    except CannyAPIError as e:
        error_msg = f"Canny API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **state,
            "workflow_status": "failed",
            "errors": state.get("errors", []) + [error_msg],
            "timestamps": {
                **state.get("timestamps", {}),
                "collection_failed_at": datetime.now(UTC),
            },
        }

    except Exception as e:
        error_msg = f"Unexpected error during feedback collection: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            **state,
            "workflow_status": "failed",
            "errors": state.get("errors", []) + [error_msg],
            "timestamps": {
                **state.get("timestamps", {}),
                "collection_failed_at": datetime.now(UTC),
            },
        }


async def collect_feedback_batch(
    board_id: Optional[str] = None,
    limit: int = 100,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Collect a batch of feedback posts (for scheduled sync).

    This function is used by the sync interval mechanism to collect
    multiple posts at once without triggering individual workflows.

    Args:
        board_id: Board ID to filter posts (defaults to config).
        limit: Maximum number of posts to retrieve.
        status: Filter by post status.

    Returns:
        Dictionary with collection results.
    """
    try:
        posts = await collect_feedback_from_canny(
            board_id=board_id,
            limit=limit,
            status=status,
            skip_duplicates=True,
        )

        return {
            "success": True,
            "collected_count": len(posts),
            "posts": [post.model_dump(mode="json") for post in posts],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Batch collection failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "collected_count": 0,
            "posts": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }


__all__ = [
    "collect_feedback_node",
    "collect_feedback_from_canny",
    "collect_feedback_batch",
    "check_post_exists",
    "store_feedback_post",
]

