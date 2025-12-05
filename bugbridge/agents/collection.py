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
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    AnalysisResult as DBAnalysisResult,
    JiraTicket as DBJiraTicket,
)
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


async def _save_workflow_results_to_db(post_id: str, state: Dict[str, Any]) -> None:
    """
    Save workflow analysis results and Jira ticket to the database.
    
    Args:
        post_id: Canny post ID.
        state: Workflow state containing analysis results.
    """
    from bugbridge.database.models import (
        FeedbackPost as DBFeedbackPost,
        AnalysisResult as DBAnalysisResult,
        JiraTicket as DBJiraTicket,
    )
    from bugbridge.models.analysis import BugDetectionResult, SentimentAnalysisResult, PriorityScoreResult
    
    async with get_session_context() as session:
        # Find the feedback post
        result = await session.execute(
            select(DBFeedbackPost).where(DBFeedbackPost.canny_post_id == post_id)
        )
        db_post = result.scalar_one_or_none()
        
        if not db_post:
            logger.warning(f"Feedback post {post_id} not found in database, skipping result save")
            return
        
        # Extract results from state
        bug_detection = state.get("bug_detection")
        sentiment_analysis = state.get("sentiment_analysis")
        priority_score = state.get("priority_score")
        
        # Prepare analysis result data
        is_bug = None
        confidence = None
        bug_severity = None
        analysis_data = {}
        
        if bug_detection:
            if isinstance(bug_detection, BugDetectionResult):
                is_bug = bug_detection.is_bug
                confidence = bug_detection.confidence
                bug_severity = bug_detection.bug_severity
                analysis_data["bug_reasoning"] = bug_detection.reasoning
                analysis_data["keywords_identified"] = bug_detection.keywords_identified
            elif isinstance(bug_detection, dict):
                is_bug = bug_detection.get("is_bug")
                confidence = bug_detection.get("confidence")
                bug_severity = bug_detection.get("bug_severity")
                analysis_data["bug_reasoning"] = bug_detection.get("reasoning")
                analysis_data["keywords_identified"] = bug_detection.get("keywords_identified", [])
        
        sentiment = None
        sentiment_score = None
        urgency = None
        
        if sentiment_analysis:
            if isinstance(sentiment_analysis, SentimentAnalysisResult):
                sentiment = sentiment_analysis.sentiment
                sentiment_score = sentiment_analysis.sentiment_score
                urgency = sentiment_analysis.urgency
                analysis_data["emotions_detected"] = sentiment_analysis.emotions_detected
                analysis_data["sentiment_reasoning"] = sentiment_analysis.reasoning
            elif isinstance(sentiment_analysis, dict):
                sentiment = sentiment_analysis.get("sentiment")
                sentiment_score = sentiment_analysis.get("sentiment_score")
                urgency = sentiment_analysis.get("urgency")
                analysis_data["emotions_detected"] = sentiment_analysis.get("emotions_detected", [])
                analysis_data["sentiment_reasoning"] = sentiment_analysis.get("reasoning")
        
        priority_score_value = None
        is_burning_issue = None
        recommended_jira_priority = None
        
        if priority_score:
            if isinstance(priority_score, PriorityScoreResult):
                priority_score_value = priority_score.priority_score
                is_burning_issue = priority_score.is_burning_issue
                recommended_jira_priority = priority_score.recommended_jira_priority
                analysis_data["priority_reasoning"] = priority_score.priority_reasoning
            elif isinstance(priority_score, dict):
                priority_score_value = priority_score.get("priority_score")
                is_burning_issue = priority_score.get("is_burning_issue")
                recommended_jira_priority = priority_score.get("recommended_jira_priority")
                analysis_data["priority_reasoning"] = priority_score.get("priority_reasoning")
        
        # Check if analysis result already exists
        existing_result = await session.execute(
            select(DBAnalysisResult).where(DBAnalysisResult.feedback_post_id == db_post.id)
        )
        db_analysis = existing_result.scalar_one_or_none()
        
        if db_analysis:
            # Update existing analysis result
            if is_bug is not None:
                db_analysis.is_bug = is_bug
                db_analysis.confidence = confidence
                db_analysis.bug_severity = bug_severity
            
            if sentiment is not None:
                db_analysis.sentiment = sentiment
                db_analysis.sentiment_score = sentiment_score
                db_analysis.urgency = urgency
            
            if priority_score_value is not None:
                db_analysis.priority_score = priority_score_value
                db_analysis.is_burning_issue = is_burning_issue
                if recommended_jira_priority:
                    analysis_data["recommended_jira_priority"] = recommended_jira_priority
            
            # Update analysis_data JSON with reasoning and other details
            if analysis_data:
                existing_data = db_analysis.analysis_data or {}
                existing_data.update(analysis_data)
                db_analysis.analysis_data = existing_data
            
            db_analysis.analyzed_at = datetime.now(UTC)
        else:
            # Store recommended_jira_priority in analysis_data if present
            if recommended_jira_priority:
                analysis_data["recommended_jira_priority"] = recommended_jira_priority
            
            # Create new analysis result
            db_analysis = DBAnalysisResult(
                feedback_post_id=db_post.id,
                is_bug=is_bug,
                confidence=confidence,
                bug_severity=bug_severity,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                urgency=urgency,
                priority_score=priority_score_value,
                is_burning_issue=is_burning_issue if is_burning_issue is not None else False,
                analysis_data=analysis_data if analysis_data else None,
                analyzed_at=datetime.now(UTC),
            )
            session.add(db_analysis)
        
        # Save Jira ticket if created
        jira_ticket_key = state.get("jira_ticket_id")
        if jira_ticket_key:
            # Check if Jira ticket already exists
            existing_ticket = await session.execute(
                select(DBJiraTicket).where(DBJiraTicket.jira_issue_key == jira_ticket_key)
            )
            db_ticket = existing_ticket.scalar_one_or_none()
            
            if not db_ticket:
                # Create new Jira ticket record
                # Note: Assignee will be populated when user clicks "Refresh from Jira"
                jira_ticket_url = state.get("jira_ticket_url")
                jira_ticket_status = state.get("jira_ticket_status", "To Do")
                
                # Extract issue ID from URL if available (format: .../issue/{issue_id})
                jira_issue_id = None
                if jira_ticket_url:
                    url_str = str(jira_ticket_url)
                    # Try to extract issue ID from URL like: .../rest/api/2/issue/10064
                    if "/issue/" in url_str:
                        try:
                            jira_issue_id = url_str.split("/issue/")[-1].split("/")[0]
                        except Exception:
                            pass
                
                # Extract project key from ticket key (e.g., "ECS-37" -> "ECS")
                project_key = jira_ticket_key.split("-")[0] if "-" in jira_ticket_key else "UNKNOWN"
                
                db_ticket = DBJiraTicket(
                    feedback_post_id=db_post.id,
                    jira_issue_key=jira_ticket_key,
                    jira_issue_id=jira_issue_id,
                    jira_project_key=project_key,
                    status=jira_ticket_status,
                    priority=recommended_jira_priority or "Medium",
                    assignee=None,  # Will be populated when refreshing from Jira
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(db_ticket)
                logger.info(f"Saved Jira ticket {jira_ticket_key} to database", extra={"ticket_key": jira_ticket_key})
        
        await session.commit()
        logger.info(f"Saved workflow results to database for post {post_id}")


async def process_post_through_workflow(post: FeedbackPost) -> Dict[str, Any]:
    """
    Process a single feedback post through the analysis and Jira workflow.

    This runs bug detection, sentiment analysis, priority scoring, and
    potentially creates a Jira ticket if the priority is high enough.

    Args:
        post: FeedbackPost to process.

    Returns:
        Dictionary with processing results.
    """
    from bugbridge.agents.bug_detection import analyze_bug_node
    from bugbridge.agents.sentiment import analyze_sentiment_node
    from bugbridge.agents.priority import calculate_priority_node
    from bugbridge.agents.jira_creation import create_jira_ticket_node
    from bugbridge.models.state import BugBridgeState
    from bugbridge.workflows.persistence import save_workflow_state

    logger.info(
        f"Processing post through workflow: {post.title[:50]}...",
        extra={"post_id": post.post_id},
    )

    # Initialize workflow state with the collected post
    state: BugBridgeState = {
        "feedback_post": post,
        "workflow_status": "collected",
        "errors": [],
        "timestamps": {
            "workflow_start": datetime.now(UTC),
        },
        "metadata": {
            "source": "canny",
            "auto_processed": True,
        },
    }

    try:
        # Step 1: Bug Detection
        logger.debug(f"Running bug detection for post {post.post_id}")
        state = await analyze_bug_node(state)
        if state.get("workflow_status") == "failed":
            raise Exception(f"Bug detection failed: {state.get('errors', [])}")

        # Step 2: Sentiment Analysis
        logger.debug(f"Running sentiment analysis for post {post.post_id}")
        state = await analyze_sentiment_node(state)
        if state.get("workflow_status") == "failed":
            raise Exception(f"Sentiment analysis failed: {state.get('errors', [])}")

        # Step 3: Priority Scoring
        logger.debug(f"Running priority scoring for post {post.post_id}")
        state = await calculate_priority_node(state)
        if state.get("workflow_status") == "failed":
            raise Exception(f"Priority scoring failed: {state.get('errors', [])}")

        # Step 4: Jira Ticket Creation (if priority >= 50)
        priority_score = state.get("priority_score")
        if priority_score:
            from bugbridge.models.analysis import PriorityScoreResult
            
            score_value = (
                priority_score.priority_score
                if isinstance(priority_score, PriorityScoreResult)
                else priority_score.get("priority_score", 0)
            )

            if score_value >= 50:
                logger.debug(
                    f"Priority score {score_value} >= 50, creating Jira ticket for post {post.post_id}"
                )
                state = await create_jira_ticket_node(state)
                if state.get("jira_ticket_id"):
                    logger.info(
                        f"Created Jira ticket {state['jira_ticket_id']} for post {post.post_id}",
                        extra={
                            "post_id": post.post_id,
                            "jira_ticket_id": state["jira_ticket_id"],
                            "priority_score": score_value,
                        },
                    )
            else:
                logger.info(
                    f"Priority score {score_value} < 50, skipping Jira ticket creation for post {post.post_id}",
                    extra={"post_id": post.post_id, "priority_score": score_value},
                )

        # Save analysis results and Jira ticket to database
        await _save_workflow_results_to_db(post.post_id, state)
        
        # Save workflow state to database
        state["workflow_status"] = "completed"
        state["timestamps"]["workflow_end"] = datetime.now(UTC)
        await save_workflow_state(state, feedback_post_id=post.post_id)

        return {
            "success": True,
            "post_id": post.post_id,
            "is_bug": state.get("bug_detection", {}).get("is_bug") if isinstance(state.get("bug_detection"), dict) else getattr(state.get("bug_detection"), "is_bug", None),
            "sentiment": state.get("sentiment_analysis", {}).get("sentiment") if isinstance(state.get("sentiment_analysis"), dict) else getattr(state.get("sentiment_analysis"), "sentiment", None),
            "priority_score": score_value if priority_score else None,
            "jira_ticket_id": state.get("jira_ticket_id"),
            "errors": state.get("errors", []),
        }

    except Exception as e:
        error_msg = f"Workflow processing failed for post {post.post_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Save failed state
        state["workflow_status"] = "failed"
        state["errors"] = state.get("errors", []) + [error_msg]
        state["timestamps"]["workflow_end"] = datetime.now(UTC)
        
        try:
            await save_workflow_state(state, feedback_post_id=post.post_id)
        except Exception as save_error:
            logger.error(f"Failed to save error state: {str(save_error)}")

        return {
            "success": False,
            "post_id": post.post_id,
            "error": error_msg,
            "errors": state.get("errors", []),
        }


async def collect_feedback_batch(
    board_id: Optional[str] = None,
    limit: int = 100,
    status: Optional[str] = None,
    process_through_workflow: bool = True,
) -> Dict[str, Any]:
    """
    Collect a batch of feedback posts and optionally process them through the workflow.

    This function is used by the sync interval mechanism to collect
    multiple posts at once and automatically process them through
    bug detection, sentiment analysis, priority scoring, and Jira creation.

    Args:
        board_id: Board ID to filter posts (defaults to config).
        limit: Maximum number of posts to retrieve.
        status: Filter by post status.
        process_through_workflow: If True, automatically processes collected posts
            through the analysis and Jira workflow. Default: True.

    Returns:
        Dictionary with collection and processing results.
    """
    try:
        posts = await collect_feedback_from_canny(
            board_id=board_id,
            limit=limit,
            status=status,
            skip_duplicates=True,
        )

        processing_results = []
        
        if process_through_workflow and posts:
            logger.info(
                f"Processing {len(posts)} collected posts through workflow",
                extra={"post_count": len(posts)},
            )
            
            # Process each post through the workflow
            for post in posts:
                try:
                    result = await process_post_through_workflow(post)
                    processing_results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to process post {post.post_id}: {str(e)}",
                        extra={"post_id": post.post_id},
                        exc_info=True,
                    )
                    processing_results.append({
                        "success": False,
                        "post_id": post.post_id,
                        "error": str(e),
                    })

            successful_processing = sum(1 for r in processing_results if r.get("success"))
            jira_tickets_created = sum(1 for r in processing_results if r.get("jira_ticket_id"))
            
            logger.info(
                f"Workflow processing complete: {successful_processing}/{len(posts)} successful, "
                f"{jira_tickets_created} Jira tickets created",
                extra={
                    "total_posts": len(posts),
                    "successful": successful_processing,
                    "jira_tickets": jira_tickets_created,
                },
            )

        return {
            "success": True,
            "collected_count": len(posts),
            "posts": [post.model_dump(mode="json") for post in posts],
            "processing_results": processing_results,
            "processed_count": len(processing_results),
            "successful_processing": sum(1 for r in processing_results if r.get("success")),
            "jira_tickets_created": sum(1 for r in processing_results if r.get("jira_ticket_id")),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Batch collection failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "collected_count": 0,
            "posts": [],
            "processing_results": [],
            "processed_count": 0,
            "successful_processing": 0,
            "jira_tickets_created": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }


__all__ = [
    "collect_feedback_node",
    "collect_feedback_from_canny",
    "collect_feedback_batch",
    "process_post_through_workflow",
    "check_post_exists",
    "store_feedback_post",
]

