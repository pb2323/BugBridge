"""
API Routes for Feedback Posts

FastAPI endpoints for managing and querying feedback posts from Canny.io.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bugbridge.api.dependencies import get_authenticated_user, require_admin
from bugbridge.api.exceptions import NotFoundError
from bugbridge.agents.collection import collect_feedback_batch
from bugbridge.database.connection import get_session
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from bugbridge.database.models import (
    AnalysisResult,
    FeedbackPost as DBFeedbackPost,
    JiraTicket as DBJiraTicket,
)
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackPostResponse(BaseModel):
    """Response model for a feedback post."""

    id: UUID
    canny_post_id: str
    board_id: str
    title: str
    content: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    votes: int = 0
    comments_count: int = 0
    status: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    collected_at: datetime
    is_bug: Optional[bool] = None
    bug_severity: Optional[str] = None
    sentiment: Optional[str] = None
    priority_score: Optional[int] = None
    jira_ticket_key: Optional[str] = None
    jira_ticket_status: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Response model for paginated feedback list."""

    items: List[FeedbackPostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FeedbackRefreshResponse(BaseModel):
    """Response model for feedback refresh operation."""

    success: bool = Field(..., description="Whether the refresh succeeded")
    collected_count: int = Field(..., description="Number of new posts collected")
    processed_count: int = Field(0, description="Number of posts processed through the workflow")
    successful_processing: int = Field(0, description="Number of posts successfully analyzed")
    jira_tickets_created: int = Field(0, description="Number of Jira tickets created")
    timestamp: datetime = Field(..., description="Time the refresh completed")
    error: Optional[str] = Field(
        None, description="Error message if the refresh failed or was partial"
    )


@router.get("", response_model=FeedbackListResponse, status_code=status.HTTP_200_OK)
async def list_feedback_posts(
    current_user = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    board_ids: Optional[str] = Query(None, description="Comma-separated list of board IDs to filter by"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by"),
    statuses: Optional[str] = Query(None, description="Comma-separated list of statuses to filter by"),
    search: Optional[str] = Query(None, description="Search query for title and content"),
    is_bug: Optional[bool] = Query(None, description="Filter by bug status (true for bugs, false for features)"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment category"),
    min_priority: Optional[int] = Query(None, ge=0, le=100, description="Minimum priority score"),
    min_votes: Optional[int] = Query(None, ge=0, description="Minimum number of votes"),
    has_jira_ticket: Optional[bool] = Query(None, description="Filter by whether feedback has a linked Jira ticket"),
    sort_by: str = Query("collected_at", description="Field to sort by (collected_at, votes, priority_score)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
) -> FeedbackListResponse:
    """
    List feedback posts with filtering, pagination, and search.

    Supports filtering by:
    - Board IDs
    - Tags
    - Status
    - Bug/Feature classification
    - Sentiment
    - Priority score
    - Votes
    - Jira ticket linkage

    Supports searching in title and content fields.
    """
    try:
        # Build base query
        query = select(DBFeedbackPost)

        # Join with analysis results for filtering
        query = query.outerjoin(AnalysisResult, DBFeedbackPost.id == AnalysisResult.feedback_post_id)

        # Join with Jira tickets for filtering
        query = query.outerjoin(DBJiraTicket, DBFeedbackPost.id == DBJiraTicket.feedback_post_id)

        # Build filter conditions
        conditions = []

        # Board IDs filter
        if board_ids:
            board_id_list = [b.strip() for b in board_ids.split(",") if b.strip()]
            if board_id_list:
                conditions.append(DBFeedbackPost.board_id.in_(board_id_list))

        # Tags filter (PostgreSQL array overlap)
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            if tag_list:
                from sqlalchemy.dialects.postgresql import array
                conditions.append(DBFeedbackPost.tags.op("&&")(array(tag_list)))

        # Status filter
        if statuses:
            status_list = [s.strip() for s in statuses.split(",") if s.strip()]
            if status_list:
                conditions.append(DBFeedbackPost.status.in_(status_list))

        # Search filter (title and content)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    DBFeedbackPost.title.ilike(search_pattern),
                    DBFeedbackPost.content.ilike(search_pattern),
                )
            )

        # Bug/Feature filter
        if is_bug is not None:
            conditions.append(AnalysisResult.is_bug == is_bug)  # noqa: E712

        # Sentiment filter
        if sentiment:
            conditions.append(AnalysisResult.sentiment == sentiment)

        # Priority score filter
        if min_priority is not None:
            conditions.append(AnalysisResult.priority_score >= min_priority)

        # Votes filter
        if min_votes is not None:
            conditions.append(DBFeedbackPost.votes >= min_votes)

        # Jira ticket filter
        if has_jira_ticket is not None:
            if has_jira_ticket:
                conditions.append(DBJiraTicket.id.isnot(None))
            else:
                conditions.append(DBJiraTicket.id.is_(None))

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(DBFeedbackPost.id.distinct()))
        if conditions:
            count_query = count_query.select_from(DBFeedbackPost).outerjoin(
                AnalysisResult, DBFeedbackPost.id == AnalysisResult.feedback_post_id
            ).outerjoin(DBJiraTicket, DBFeedbackPost.id == DBJiraTicket.feedback_post_id).where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        # Sorting
        sort_field = getattr(DBFeedbackPost, sort_by, DBFeedbackPost.collected_at)
        if sort_by == "priority_score":
            sort_field = AnalysisResult.priority_score
        elif sort_by == "votes":
            sort_field = DBFeedbackPost.votes

        if sort_order.lower() == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await session.execute(query)
        posts = result.unique().scalars().all()

        # Build response with analysis and Jira data
        items = []
        for post in posts:
            # Get analysis result for this post
            analysis_query = select(AnalysisResult).where(AnalysisResult.feedback_post_id == post.id)
            analysis_result = (await session.execute(analysis_query)).scalar_one_or_none()

            # Get Jira ticket for this post
            jira_query = select(DBJiraTicket).where(DBJiraTicket.feedback_post_id == post.id)
            jira_ticket = (await session.execute(jira_query)).scalar_one_or_none()

            # Build response item
            item = FeedbackPostResponse(
                id=post.id,
                canny_post_id=post.canny_post_id,
                board_id=post.board_id,
                title=post.title,
                content=post.content,
                author_id=post.author_id,
                author_name=post.author_name,
                votes=post.votes,
                comments_count=post.comments_count,
                status=post.status,
                url=post.url,
                tags=post.tags or [],
                created_at=post.created_at,
                updated_at=post.updated_at,
                collected_at=post.collected_at,
                is_bug=analysis_result.is_bug if analysis_result else None,
                bug_severity=analysis_result.bug_severity if analysis_result else None,
                sentiment=analysis_result.sentiment if analysis_result else None,
                priority_score=analysis_result.priority_score if analysis_result else None,
                jira_ticket_key=jira_ticket.jira_issue_key if jira_ticket else None,
                jira_ticket_status=jira_ticket.status if jira_ticket else None,
            )
            items.append(item)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return FeedbackListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error fetching feedback posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feedback posts: {str(e)}"
        )


@router.post("/refresh", response_model=FeedbackRefreshResponse, status_code=status.HTTP_200_OK)
async def refresh_feedback_posts(
    current_user = Depends(require_admin),
) -> FeedbackRefreshResponse:
    """
    Refresh feedback posts from Canny.io and process them through the workflow.

    This endpoint:
    - Calls the Feedback Collection Agent to fetch posts from Canny
    - Skips posts that already exist in the database
    - Stores only newly discovered posts
    - Automatically runs bug detection, sentiment analysis, and priority scoring
    - Creates Jira tickets for high-priority items (priority >= 50)

    Returns detailed statistics about collection and processing results.
    """
    try:
        logger.info("Starting manual feedback refresh and workflow processing")
        
        result = await collect_feedback_batch(
            board_id=None,  # Use default board from config
            limit=100,  # Reasonable batch size for manual refresh
            status=None,  # All statuses
            process_through_workflow=True,  # Automatically process through workflow
        )

        timestamp_str = result.get("timestamp")
        timestamp = (
            datetime.fromisoformat(timestamp_str)
            if isinstance(timestamp_str, str)
            else datetime.utcnow()
        )

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error during feedback refresh")
            logger.error(f"Feedback refresh failed: {error_msg}")
            return FeedbackRefreshResponse(
                success=False,
                collected_count=int(result.get("collected_count", 0) or 0),
                processed_count=int(result.get("processed_count", 0) or 0),
                successful_processing=int(result.get("successful_processing", 0) or 0),
                jira_tickets_created=int(result.get("jira_tickets_created", 0) or 0),
                timestamp=timestamp,
                error=error_msg,
            )

        logger.info(
            f"Feedback refresh completed: {result.get('collected_count')} collected, "
            f"{result.get('processed_count')} processed, "
            f"{result.get('jira_tickets_created')} Jira tickets created"
        )

        return FeedbackRefreshResponse(
            success=True,
            collected_count=int(result.get("collected_count", 0) or 0),
            processed_count=int(result.get("processed_count", 0) or 0),
            successful_processing=int(result.get("successful_processing", 0) or 0),
            jira_tickets_created=int(result.get("jira_tickets_created", 0) or 0),
            timestamp=timestamp,
            error=None,
        )
    except Exception as e:
        logger.error(f"Error refreshing feedback posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh feedback posts: {str(e)}",
        )


@router.get("/{post_id}", response_model=FeedbackPostResponse, status_code=status.HTTP_200_OK)
async def get_feedback_post(
    post_id: UUID,
    current_user = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> FeedbackPostResponse:
    """
    Get detailed information about a specific feedback post.

    Includes analysis results and linked Jira ticket information.
    """
    try:
        # Get feedback post
        query = select(DBFeedbackPost).where(DBFeedbackPost.id == post_id)
        result = await session.execute(query)
        post = result.scalar_one_or_none()

        if not post:
            raise NotFoundError(
                message=f"Feedback post with ID {post_id} not found",
                resource_type="feedback_post",
                resource_id=str(post_id),
            )

        # Get analysis result
        analysis_query = select(AnalysisResult).where(AnalysisResult.feedback_post_id == post.id)
        analysis_result = (await session.execute(analysis_query)).scalar_one_or_none()

        # Get Jira ticket
        jira_query = select(DBJiraTicket).where(DBJiraTicket.feedback_post_id == post.id)
        jira_ticket = (await session.execute(jira_query)).scalar_one_or_none()

        return FeedbackPostResponse(
            id=post.id,
            canny_post_id=post.canny_post_id,
            board_id=post.board_id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_name=post.author_name,
            votes=post.votes,
            comments_count=post.comments_count,
            status=post.status,
            url=post.url,
            tags=post.tags or [],
            created_at=post.created_at,
            updated_at=post.updated_at,
            collected_at=post.collected_at,
            is_bug=analysis_result.is_bug if analysis_result else None,
            bug_severity=analysis_result.bug_severity if analysis_result else None,
            sentiment=analysis_result.sentiment if analysis_result else None,
            priority_score=analysis_result.priority_score if analysis_result else None,
            jira_ticket_key=jira_ticket.jira_issue_key if jira_ticket else None,
            jira_ticket_status=jira_ticket.status if jira_ticket else None,
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching feedback post {post_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feedback post: {str(e)}"
        )


class FeedbackProcessResponse(BaseModel):
    """Response model for processing existing posts."""

    success: bool = Field(..., description="Whether the processing succeeded")
    total_unprocessed: int = Field(..., description="Total number of unprocessed posts found")
    processed_count: int = Field(..., description="Number of posts processed")
    successful_processing: int = Field(..., description="Number of posts successfully analyzed")
    jira_tickets_created: int = Field(..., description="Number of Jira tickets created")
    timestamp: datetime = Field(..., description="Time the processing completed")
    error: Optional[str] = Field(
        None, description="Error message if the processing failed or was partial"
    )


@router.post("/process-existing", response_model=FeedbackProcessResponse, status_code=status.HTTP_200_OK)
async def process_existing_feedback_posts(
    current_user = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of posts to process (default: all)"),
) -> FeedbackProcessResponse:
    """
    Process all existing unprocessed feedback posts through the workflow.

    This endpoint:
    - Finds all feedback posts that don't have analysis results yet
    - Processes each through bug detection, sentiment analysis, and priority scoring
    - Creates Jira tickets for high-priority items (priority >= 50)
    
    Use this to backfill analysis for posts that were collected before the workflow was enabled.
    """
    from bugbridge.agents.collection import process_post_through_workflow
    from bugbridge.database.models import AnalysisResult
    from sqlalchemy.orm import selectinload
    
    try:
        logger.info("Starting processing of existing unprocessed feedback posts")
        
        # Find all posts without analysis results
        query = (
            select(DBFeedbackPost)
            .outerjoin(AnalysisResult, DBFeedbackPost.id == AnalysisResult.feedback_post_id)
            .where(AnalysisResult.id.is_(None))
            .options(selectinload(DBFeedbackPost.analysis_results))
        )
        
        result = await session.execute(query)
        unprocessed_posts = result.unique().scalars().all()
        total_unprocessed = len(unprocessed_posts)
        
        if limit:
            unprocessed_posts = unprocessed_posts[:limit]
        
        logger.info(
            f"Found {total_unprocessed} unprocessed posts"
            + (f" (processing first {len(unprocessed_posts)})" if limit else "")
        )
        
        if not unprocessed_posts:
            logger.info("No unprocessed posts found")
            return FeedbackProcessResponse(
                success=True,
                total_unprocessed=0,
                processed_count=0,
                successful_processing=0,
                jira_tickets_created=0,
                timestamp=datetime.now(UTC),
                error=None,
            )
        
        # Process each post
        processing_results = []
        
        for db_post in unprocessed_posts:
            try:
                # Convert DB model to Pydantic model
                from bugbridge.models.feedback import FeedbackPost as PydanticFeedbackPost
                from pydantic import HttpUrl
                
                url = HttpUrl(db_post.url) if db_post.url else None
                pydantic_post = PydanticFeedbackPost(
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
                
                # Process through workflow
                result = await process_post_through_workflow(pydantic_post)
                processing_results.append(result)
                
            except Exception as e:
                logger.error(
                    f"Failed to process post {db_post.canny_post_id}: {str(e)}",
                    exc_info=True,
                )
                processing_results.append({
                    "success": False,
                    "post_id": db_post.canny_post_id,
                    "error": str(e),
                })
        
        successful_count = sum(1 for r in processing_results if r.get("success"))
        jira_tickets_created = sum(1 for r in processing_results if r.get("jira_ticket_id"))
        
        logger.info(
            f"Processing complete: {successful_count}/{len(processing_results)} successful, "
            f"{jira_tickets_created} Jira tickets created"
        )
        
        return FeedbackProcessResponse(
            success=True,
            total_unprocessed=total_unprocessed,
            processed_count=len(processing_results),
            successful_processing=successful_count,
            jira_tickets_created=jira_tickets_created,
            timestamp=datetime.now(UTC),
            error=None,
        )
        
    except Exception as e:
        logger.error(f"Error processing existing feedback posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process existing feedback posts: {str(e)}",
        )


@router.post("/{post_id}/process", response_model=FeedbackProcessResponse, status_code=status.HTTP_200_OK)
async def process_single_feedback_post(
    post_id: str,
    current_user = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> FeedbackProcessResponse:
    """
    Process a single feedback post through the workflow.

    This endpoint:
    - Finds the specified feedback post by ID
    - Processes it through bug detection, sentiment analysis, and priority scoring
    - Creates a Jira ticket if priority >= 50
    - Can reprocess posts that were already analyzed
    
    Useful for reprocessing individual posts or triggering analysis for specific posts.
    """
    from bugbridge.agents.collection import process_post_through_workflow
    from bugbridge.models.feedback import FeedbackPost as PydanticFeedbackPost
    
    try:
        logger.info(f"Processing single feedback post: {post_id}")
        
        # Find the post
        result = await session.execute(
            select(DBFeedbackPost).where(DBFeedbackPost.id == post_id)
        )
        db_post = result.scalar_one_or_none()
        
        if not db_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback post not found: {post_id}"
            )
        
        # Convert to Pydantic model
        pydantic_post = PydanticFeedbackPost(
            post_id=db_post.canny_post_id,
            board_id=db_post.board_id,
            title=db_post.title,
            content=db_post.content,
            author_id=db_post.author_id,
            author_name=db_post.author_name,
            votes=db_post.votes,
            comments_count=db_post.comments_count,
            status=db_post.status,
            url=db_post.url,
            tags=db_post.tags or [],
            created_at=db_post.created_at,
            updated_at=db_post.updated_at,
        )
        
        # Process through workflow
        result = await process_post_through_workflow(pydantic_post)
        
        success = result.get("success", False)
        jira_ticket_created = 1 if result.get("jira_ticket_id") else 0
        
        return FeedbackProcessResponse(
            success=success,
            total_unprocessed=1,
            processed_count=1,
            successful_processing=1 if success else 0,
            jira_tickets_created=jira_ticket_created,
            timestamp=datetime.now(UTC),
            error=result.get("error") if not success else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing feedback post {post_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process feedback post: {str(e)}",
        )


__all__ = [
    "router",
    "FeedbackPostResponse",
    "FeedbackListResponse",
    "FeedbackRefreshResponse",
    "FeedbackProcessResponse",
]

