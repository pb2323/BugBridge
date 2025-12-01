"""
API Routes for Feedback Posts

FastAPI endpoints for managing and querying feedback posts from Canny.io.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from bugbridge.api.exceptions import NotFoundError
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from bugbridge.api.dependencies import get_authenticated_user
from bugbridge.database.connection import get_session
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


@router.get("", response_model=FeedbackListResponse, status_code=status.HTTP_200_OK)
async def list_feedback_posts(
    current_user = Depends(get_authenticated_user),
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
    async with get_session() as session:
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


@router.get("/{post_id}", response_model=FeedbackPostResponse, status_code=status.HTTP_200_OK)
async def get_feedback_post(
    post_id: UUID,
    current_user = Depends(get_authenticated_user),
) -> FeedbackPostResponse:
    """
    Get detailed information about a specific feedback post.

    Includes analysis results and linked Jira ticket information.
    """
    async with get_session() as session:
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


__all__ = [
    "router",
    "FeedbackPostResponse",
    "FeedbackListResponse",
]

