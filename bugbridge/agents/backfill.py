"""
Backfilling Service for Historical Feedback Data

Provides functionality to backfill historical feedback posts from Canny.io
for initial setup or data migration purposes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from bugbridge.agents.collection import collect_feedback_from_canny, store_feedback_post
from bugbridge.config import get_settings
from bugbridge.database.connection import get_session_context
from bugbridge.integrations.canny import CannyClient, CannyAPIError
from bugbridge.models.feedback import FeedbackPost
from bugbridge.utils.logging import get_audit_logger, get_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()


async def backfill_historical_posts(
    board_id: Optional[str] = None,
    limit_per_batch: int = 100,
    max_posts: Optional[int] = None,
    status: Optional[str] = None,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Backfill historical feedback posts from Canny.io.

    This function collects all historical posts from Canny.io (or up to max_posts)
    with pagination support. Useful for initial setup or data migration.

    Args:
        board_id: Board ID to backfill from (defaults to config).
        limit_per_batch: Number of posts to retrieve per API call (default: 100).
        max_posts: Maximum number of posts to backfill (None = all available).
        status: Filter by post status (None = all statuses).
        skip_existing: Whether to skip posts that already exist in database.

    Returns:
        Dictionary with backfill results including:
        - success: Boolean indicating if backfill completed
        - total_collected: Total number of posts collected
        - total_skipped: Total number of duplicate posts skipped
        - total_failed: Total number of posts that failed to store
        - batches_processed: Number of API batches processed
        - errors: List of error messages
    """
    # Get default board_id from config if not provided
    if board_id is None:
        try:
            settings = get_settings()
            board_id = settings.canny.board_id
        except Exception:
            raise ValueError("board_id must be provided if config is not available")

    logger.info(
        f"Starting historical backfill for board {board_id}",
        extra={
            "board_id": board_id,
            "limit_per_batch": limit_per_batch,
            "max_posts": max_posts,
            "status": status,
            "skip_existing": skip_existing,
        },
    )

    total_collected = 0
    total_skipped = 0
    total_failed = 0
    batches_processed = 0
    errors: List[str] = []
    skip = 0

    try:
        async with CannyClient() as canny_client:
            while True:
                # Check if we've reached max_posts
                if max_posts is not None and total_collected >= max_posts:
                    logger.info(
                        f"Reached max_posts limit ({max_posts}), stopping backfill",
                        extra={"max_posts": max_posts, "total_collected": total_collected},
                    )
                    break

                # Calculate batch limit
                batch_limit = limit_per_batch
                if max_posts is not None:
                    remaining = max_posts - total_collected
                    if remaining < batch_limit:
                        batch_limit = remaining

                try:
                    # Collect batch of posts
                    posts = await canny_client.list_posts(
                        board_id=board_id,
                        limit=batch_limit,
                        skip=skip,
                        status=status,
                    )

                    # If no posts returned, we've reached the end
                    if not posts:
                        logger.info(
                            "No more posts available, backfill complete",
                            extra={"skip": skip, "batches_processed": batches_processed},
                        )
                        break

                    logger.info(
                        f"Retrieved batch of {len(posts)} posts (skip={skip})",
                        extra={
                            "batch_size": len(posts),
                            "skip": skip,
                            "batch_number": batches_processed + 1,
                        },
                    )

                    # Process batch
                    batch_collected = 0
                    batch_skipped = 0
                    batch_failed = 0

                    async with get_session_context() as session:
                        for post in posts:
                            try:
                                # Check if post exists
                                if skip_existing:
                                    from bugbridge.agents.collection import check_post_exists

                                    exists = await check_post_exists(session, post.post_id)
                                    if exists:
                                        batch_skipped += 1
                                        total_skipped += 1
                                        continue

                                # Store post
                                await store_feedback_post(session, post)
                                batch_collected += 1
                                total_collected += 1

                                audit_logger.log_agent_action(
                                    agent_name="BackfillService",
                                    action=f"backfilled_post_{post.post_id}",
                                    result="success",
                                    post_id=post.post_id,
                                    context={
                                        "title": post.title,
                                        "batch_number": batches_processed + 1,
                                    },
                                )

                            except Exception as e:
                                error_msg = f"Failed to store post {post.post_id}: {str(e)}"
                                logger.error(error_msg, extra={"post_id": post.post_id}, exc_info=True)
                                batch_failed += 1
                                total_failed += 1
                                errors.append(error_msg)

                    batches_processed += 1

                    logger.info(
                        f"Processed batch {batches_processed}: collected={batch_collected}, skipped={batch_skipped}, failed={batch_failed}",
                        extra={
                            "batch_number": batches_processed,
                            "collected": batch_collected,
                            "skipped": batch_skipped,
                            "failed": batch_failed,
                        },
                    )

                    # If we got fewer posts than requested, we've reached the end
                    if len(posts) < batch_limit:
                        logger.info(
                            "Received fewer posts than requested, backfill complete",
                            extra={
                                "posts_received": len(posts),
                                "batch_limit": batch_limit,
                            },
                        )
                        break

                    # Move to next batch
                    skip += len(posts)

                    # If we've collected max_posts, stop
                    if max_posts is not None and total_collected >= max_posts:
                        break

                except CannyAPIError as e:
                    error_msg = f"Canny API error during backfill (skip={skip}): {str(e)}"
                    logger.error(error_msg, extra={"skip": skip, "status_code": e.status_code}, exc_info=True)
                    errors.append(error_msg)
                    break  # Stop backfill on API error

                except Exception as e:
                    error_msg = f"Unexpected error during backfill (skip={skip}): {str(e)}"
                    logger.error(error_msg, extra={"skip": skip}, exc_info=True)
                    errors.append(error_msg)
                    break  # Stop backfill on unexpected error

    except Exception as e:
        error_msg = f"Critical error during backfill: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)

    result = {
        "success": len(errors) == 0 or total_collected > 0,
        "total_collected": total_collected,
        "total_skipped": total_skipped,
        "total_failed": total_failed,
        "batches_processed": batches_processed,
        "errors": errors,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    logger.info(
        f"Backfill completed: collected={total_collected}, skipped={total_skipped}, failed={total_failed}",
        extra=result,
    )

    audit_logger.log_agent_action(
        agent_name="BackfillService",
        action="backfill_completed",
        result="success" if result["success"] else "partial",
        context=result,
    )

    return result


async def backfill_with_date_range(
    board_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit_per_batch: int = 100,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    """
    Backfill historical posts within a specific date range.

    Note: Canny.io API doesn't directly support date filtering in list_posts,
    so this function collects all posts and filters by date client-side.

    Args:
        board_id: Board ID to backfill from (defaults to config).
        start_date: Only collect posts created after this date (None = no limit).
        end_date: Only collect posts created before this date (None = no limit).
        limit_per_batch: Number of posts to retrieve per API call.
        skip_existing: Whether to skip posts that already exist in database.

    Returns:
        Dictionary with backfill results.
    """
    logger.info(
        f"Starting date-filtered backfill: start_date={start_date}, end_date={end_date}",
        extra={
            "board_id": board_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    )

    # Collect all posts and filter by date
    total_collected = 0
    total_skipped = 0
    total_filtered_by_date = 0

    try:
        async with CannyClient() as canny_client:
            skip = 0
            while True:
                posts = await canny_client.list_posts(
                    board_id=board_id,
                    limit=limit_per_batch,
                    skip=skip,
                    status=None,
                )

                if not posts:
                    break

                # Filter by date range
                filtered_posts = []
                for post in posts:
                    if start_date and post.created_at < start_date:
                        total_filtered_by_date += 1
                        continue
                    if end_date and post.created_at > end_date:
                        total_filtered_by_date += 1
                        continue
                    filtered_posts.append(post)

                # Process filtered posts
                for post in filtered_posts:
                    try:
                        if skip_existing:
                            from bugbridge.agents.collection import check_post_exists

                            async with get_session_context() as session:
                                exists = await check_post_exists(session, post.post_id)
                                if exists:
                                    total_skipped += 1
                                    continue

                        async with get_session_context() as session:
                            await store_feedback_post(session, post)
                            total_collected += 1

                    except Exception as e:
                        logger.error(f"Failed to store post {post.post_id}: {str(e)}", exc_info=True)

                # If we got fewer posts than requested, we've reached the end
                if len(posts) < limit_per_batch:
                    break

                skip += len(posts)

    except Exception as e:
        logger.error(f"Error during date-filtered backfill: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "total_collected": total_collected,
            "total_skipped": total_skipped,
            "total_filtered_by_date": total_filtered_by_date,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return {
        "success": True,
        "total_collected": total_collected,
        "total_skipped": total_skipped,
        "total_filtered_by_date": total_filtered_by_date,
        "timestamp": datetime.now(UTC).isoformat(),
    }


__all__ = [
    "backfill_historical_posts",
    "backfill_with_date_range",
]

