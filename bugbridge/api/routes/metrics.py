"""
API Routes for Metrics and Statistics

FastAPI endpoints for aggregated metrics and statistics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


class MetricsResponse(BaseModel):
    """Response model for aggregated metrics."""

    # Overview
    total_feedback_posts: int = Field(..., description="Total number of feedback posts")
    total_bugs: int = Field(..., description="Total number of bugs identified")
    total_feature_requests: int = Field(..., description="Total number of feature requests")
    bugs_percentage: float = Field(..., description="Percentage of bugs vs total posts")

    # Sentiment distribution
    sentiment_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of sentiment categories"
    )

    # Priority distribution
    priority_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of priority scores (ranges)"
    )

    # Jira integration
    total_jira_tickets: int = Field(..., description="Total number of Jira tickets created")
    resolved_tickets: int = Field(..., description="Number of resolved Jira tickets")
    resolution_rate: float = Field(..., description="Percentage of tickets resolved")

    # Time-based metrics
    average_response_time_hours: Optional[float] = Field(
        None, description="Average time from feedback to ticket creation (hours)"
    )
    average_resolution_time_hours: Optional[float] = Field(
        None, description="Average time to resolution (hours)"
    )

    # Recent activity (last 7 days)
    recent_posts: int = Field(..., description="Number of posts in the last 7 days")
    recent_tickets: int = Field(..., description="Number of tickets created in the last 7 days")
    recent_resolutions: int = Field(..., description="Number of tickets resolved in the last 7 days")

    # Top priorities
    top_priority_items: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top priority items requiring attention"
    )


@router.get("", response_model=MetricsResponse, status_code=status.HTTP_200_OK)
async def get_metrics(
    current_user = Depends(get_authenticated_user),
    start_date: Optional[datetime] = Query(None, description="Start date for metrics calculation"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics calculation"),
) -> MetricsResponse:
    """
    Get aggregated metrics and statistics.

    If no date range is provided, calculates metrics for all time.
    If only start_date is provided, calculates from that date to now.
    If only end_date is provided, calculates from the beginning to that date.
    """
    async with get_session() as session:
        # Determine date range
        if start_date is None and end_date is None:
            # All time
            date_conditions = []
        else:
            date_conditions = []
            if start_date:
                date_conditions.append(DBFeedbackPost.collected_at >= start_date)
            if end_date:
                date_conditions.append(DBFeedbackPost.collected_at <= end_date)

        # Total feedback posts
        total_posts_query = select(func.count(DBFeedbackPost.id))
        if date_conditions:
            total_posts_query = total_posts_query.where(*date_conditions)
        total_posts = (await session.execute(total_posts_query)).scalar() or 0

        # Total bugs
        bugs_query = select(func.count(AnalysisResult.id)).join(
            DBFeedbackPost, AnalysisResult.feedback_post_id == DBFeedbackPost.id
        ).where(AnalysisResult.is_bug == True)  # noqa: E712
        if date_conditions:
            bugs_query = bugs_query.where(*date_conditions)
        total_bugs = (await session.execute(bugs_query)).scalar() or 0

        # Total feature requests
        features_query = select(func.count(AnalysisResult.id)).join(
            DBFeedbackPost, AnalysisResult.feedback_post_id == DBFeedbackPost.id
        ).where(AnalysisResult.is_bug == False)  # noqa: E712
        if date_conditions:
            features_query = features_query.where(*date_conditions)
        total_features = (await session.execute(features_query)).scalar() or 0

        bugs_percentage = (total_bugs / total_posts * 100) if total_posts > 0 else 0.0

        # Sentiment distribution
        sentiment_query = select(
            AnalysisResult.sentiment,
            func.count(AnalysisResult.id).label("count"),
        ).join(
            DBFeedbackPost, AnalysisResult.feedback_post_id == DBFeedbackPost.id
        ).where(AnalysisResult.sentiment.isnot(None))
        if date_conditions:
            sentiment_query = sentiment_query.where(*date_conditions)
        sentiment_query = sentiment_query.group_by(AnalysisResult.sentiment)

        sentiment_results = await session.execute(sentiment_query)
        sentiment_distribution: Dict[str, int] = {}
        for row in sentiment_results:
            sentiment_distribution[row.sentiment] = row.count

        # Priority distribution (by ranges)
        priority_ranges = {
            "0-25": (0, 25),
            "26-50": (26, 50),
            "51-75": (51, 75),
            "76-100": (76, 100),
        }
        priority_distribution: Dict[str, int] = {}
        for range_name, (min_score, max_score) in priority_ranges.items():
            priority_query = select(func.count(AnalysisResult.id)).join(
                DBFeedbackPost, AnalysisResult.feedback_post_id == DBFeedbackPost.id
            ).where(
                AnalysisResult.priority_score >= min_score,
                AnalysisResult.priority_score <= max_score,
            )
            if date_conditions:
                priority_query = priority_query.where(*date_conditions)
            count = (await session.execute(priority_query)).scalar() or 0
            priority_distribution[range_name] = count

        # Jira tickets
        tickets_query = select(func.count(DBJiraTicket.id))
        if date_conditions:
            tickets_query = tickets_query.where(DBJiraTicket.created_at >= start_date if start_date else True)
        total_tickets = (await session.execute(tickets_query)).scalar() or 0

        # Resolved tickets
        resolved_query = select(func.count(DBJiraTicket.id)).where(DBJiraTicket.resolved_at.isnot(None))
        if date_conditions:
            resolved_query = resolved_query.where(DBJiraTicket.resolved_at >= start_date if start_date else True)
        resolved_tickets = (await session.execute(resolved_query)).scalar() or 0

        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0.0

        # Average response time
        response_time_query = select(
            func.avg(
                func.extract("epoch", DBJiraTicket.created_at - DBFeedbackPost.collected_at) / 3600.0
            )
        ).join(DBFeedbackPost, DBJiraTicket.feedback_post_id == DBFeedbackPost.id)
        if date_conditions:
            response_time_query = response_time_query.where(*date_conditions)
        avg_response_time = (await session.execute(response_time_query)).scalar()
        average_response_time_hours = float(avg_response_time) if avg_response_time else None

        # Average resolution time
        resolution_time_query = select(
            func.avg(
                func.extract("epoch", DBJiraTicket.resolved_at - DBJiraTicket.created_at) / 3600.0
            )
        ).where(DBJiraTicket.resolved_at.isnot(None))
        if date_conditions:
            resolution_time_query = resolution_time_query.where(
                DBJiraTicket.resolved_at >= start_date if start_date else True
            )
        avg_resolution_time = (await session.execute(resolution_time_query)).scalar()
        average_resolution_time_hours = float(avg_resolution_time) if avg_resolution_time else None

        # Recent activity (last 7 days)
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        recent_posts_query = select(func.count(DBFeedbackPost.id)).where(
            DBFeedbackPost.collected_at >= seven_days_ago
        )
        recent_posts = (await session.execute(recent_posts_query)).scalar() or 0

        recent_tickets_query = select(func.count(DBJiraTicket.id)).where(
            DBJiraTicket.created_at >= seven_days_ago
        )
        recent_tickets = (await session.execute(recent_tickets_query)).scalar() or 0

        recent_resolutions_query = select(func.count(DBJiraTicket.id)).where(
            DBJiraTicket.resolved_at >= seven_days_ago, DBJiraTicket.resolved_at.isnot(None)
        )
        recent_resolutions = (await session.execute(recent_resolutions_query)).scalar() or 0

        # Top priority items
        priority_items_query = select(
            DBFeedbackPost.title,
            AnalysisResult.priority_score,
            AnalysisResult.analysis_data,
            DBFeedbackPost.canny_post_id,
        ).join(
            AnalysisResult, DBFeedbackPost.id == AnalysisResult.feedback_post_id
        ).where(
            AnalysisResult.priority_score.isnot(None)
        ).order_by(
            AnalysisResult.priority_score.desc()
        ).limit(10)

        if date_conditions:
            priority_items_query = priority_items_query.where(*date_conditions)

        priority_results = await session.execute(priority_items_query)
        top_priority_items: List[Dict[str, Any]] = []
        for row in priority_results:
            recommended_priority = "N/A"
            if row.analysis_data and isinstance(row.analysis_data, dict):
                recommended_priority = row.analysis_data.get("recommended_jira_priority", "N/A")

            top_priority_items.append({
                "title": row.title,
                "priority_score": row.priority_score,
                "priority": recommended_priority,
                "post_id": row.canny_post_id,
            })

        return MetricsResponse(
            total_feedback_posts=total_posts,
            total_bugs=total_bugs,
            total_feature_requests=total_features,
            bugs_percentage=bugs_percentage,
            sentiment_distribution=sentiment_distribution,
            priority_distribution=priority_distribution,
            total_jira_tickets=total_tickets,
            resolved_tickets=resolved_tickets,
            resolution_rate=resolution_rate,
            average_response_time_hours=average_response_time_hours,
            average_resolution_time_hours=average_resolution_time_hours,
            recent_posts=recent_posts,
            recent_tickets=recent_tickets,
            recent_resolutions=recent_resolutions,
            top_priority_items=top_priority_items,
        )


__all__ = [
    "router",
    "MetricsResponse",
]

