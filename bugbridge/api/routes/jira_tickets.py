"""
API Routes for Jira Tickets

FastAPI endpoints for querying Jira tickets linked to feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bugbridge.api.exceptions import NotFoundError
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.api.dependencies import get_authenticated_user
from bugbridge.database.connection import get_session
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    JiraTicket as DBJiraTicket,
)
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/jira-tickets", tags=["jira-tickets"])


class JiraTicketResponse(BaseModel):
    """Response model for a Jira ticket."""

    id: UUID
    jira_issue_key: str
    jira_issue_id: Optional[str] = None
    jira_project_key: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    updated_at: datetime
    feedback_post_id: Optional[UUID] = None
    feedback_post_title: Optional[str] = None
    feedback_post_canny_id: Optional[str] = None

    class Config:
        from_attributes = True


class JiraTicketListResponse(BaseModel):
    """Response model for paginated Jira ticket list."""

    items: List[JiraTicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=JiraTicketListResponse, status_code=status.HTTP_200_OK)
async def list_jira_tickets(
    current_user = Depends(get_authenticated_user),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    project_keys: Optional[str] = Query(None, description="Comma-separated list of project keys to filter by"),
    statuses: Optional[str] = Query(None, description="Comma-separated list of statuses to filter by"),
    priorities: Optional[str] = Query(None, description="Comma-separated list of priorities to filter by"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    resolved_only: Optional[bool] = Query(None, description="Filter to only resolved tickets"),
    unresolved_only: Optional[bool] = Query(None, description="Filter to only unresolved tickets"),
    has_feedback: Optional[bool] = Query(None, description="Filter by whether ticket has linked feedback"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, updated_at, resolved_at)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
) -> JiraTicketListResponse:
    """
    List Jira tickets with filtering, pagination, and sorting.

    Supports filtering by:
    - Project keys
    - Statuses
    - Priorities
    - Assignee
    - Resolution status
    - Feedback linkage
    """
    async with get_session() as session:
        # Build base query
        query = select(DBJiraTicket)

        # Join with feedback posts
        query = query.outerjoin(DBFeedbackPost, DBJiraTicket.feedback_post_id == DBFeedbackPost.id)

        # Build filter conditions
        conditions = []

        # Project keys filter
        if project_keys:
            project_key_list = [p.strip() for p in project_keys.split(",") if p.strip()]
            if project_key_list:
                conditions.append(DBJiraTicket.jira_project_key.in_(project_key_list))

        # Status filter
        if statuses:
            status_list = [s.strip() for s in statuses.split(",") if s.strip()]
            if status_list:
                conditions.append(DBJiraTicket.status.in_(status_list))

        # Priority filter
        if priorities:
            priority_list = [p.strip() for p in priorities.split(",") if p.strip()]
            if priority_list:
                conditions.append(DBJiraTicket.priority.in_(priority_list))

        # Assignee filter
        if assignee:
            conditions.append(DBJiraTicket.assignee == assignee)

        # Resolution status filter
        if resolved_only:
            conditions.append(DBJiraTicket.resolved_at.isnot(None))
        elif unresolved_only:
            conditions.append(DBJiraTicket.resolved_at.is_(None))

        # Feedback linkage filter
        if has_feedback is not None:
            if has_feedback:
                conditions.append(DBJiraTicket.feedback_post_id.isnot(None))
            else:
                conditions.append(DBJiraTicket.feedback_post_id.is_(None))

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(DBJiraTicket.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        # Sorting
        sort_field = getattr(DBJiraTicket, sort_by, DBJiraTicket.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await session.execute(query)
        tickets = result.unique().scalars().all()

        # Build response with feedback post information
        items = []
        for ticket in tickets:
            # Get feedback post if linked
            feedback_post = None
            if ticket.feedback_post_id:
                feedback_query = select(DBFeedbackPost).where(DBFeedbackPost.id == ticket.feedback_post_id)
                feedback_result = await session.execute(feedback_query)
                feedback_post = feedback_result.scalar_one_or_none()

            item = JiraTicketResponse(
                id=ticket.id,
                jira_issue_key=ticket.jira_issue_key,
                jira_issue_id=ticket.jira_issue_id,
                jira_project_key=ticket.jira_project_key,
                status=ticket.status,
                priority=ticket.priority,
                assignee=ticket.assignee,
                created_at=ticket.created_at,
                resolved_at=ticket.resolved_at,
                updated_at=ticket.updated_at,
                feedback_post_id=ticket.feedback_post_id,
                feedback_post_title=feedback_post.title if feedback_post else None,
                feedback_post_canny_id=feedback_post.canny_post_id if feedback_post else None,
            )
            items.append(item)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return JiraTicketListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/{ticket_id}", response_model=JiraTicketResponse, status_code=status.HTTP_200_OK)
async def get_jira_ticket(
    ticket_id: UUID,
    current_user = Depends(get_authenticated_user),
) -> JiraTicketResponse:
    """
    Get detailed information about a specific Jira ticket.

    Includes linked feedback post information if available.
    """
    async with get_session() as session:
        # Get Jira ticket
        query = select(DBJiraTicket).where(DBJiraTicket.id == ticket_id)
        result = await session.execute(query)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise NotFoundError(
                message=f"Jira ticket with ID {ticket_id} not found",
                resource_type="jira_ticket",
                resource_id=str(ticket_id),
            )

        # Get feedback post if linked
        feedback_post = None
        if ticket.feedback_post_id:
            feedback_query = select(DBFeedbackPost).where(DBFeedbackPost.id == ticket.feedback_post_id)
            feedback_result = await session.execute(feedback_query)
            feedback_post = feedback_result.scalar_one_or_none()

        return JiraTicketResponse(
            id=ticket.id,
            jira_issue_key=ticket.jira_issue_key,
            jira_issue_id=ticket.jira_issue_id,
            jira_project_key=ticket.jira_project_key,
            status=ticket.status,
            priority=ticket.priority,
            assignee=ticket.assignee,
            created_at=ticket.created_at,
            resolved_at=ticket.resolved_at,
            updated_at=ticket.updated_at,
            feedback_post_id=ticket.feedback_post_id,
            feedback_post_title=feedback_post.title if feedback_post else None,
            feedback_post_canny_id=feedback_post.canny_post_id if feedback_post else None,
        )


__all__ = [
    "router",
    "JiraTicketResponse",
    "JiraTicketListResponse",
]

