"""
API Routes for Jira Tickets

FastAPI endpoints for querying Jira tickets linked to feedback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bugbridge.api.exceptions import NotFoundError
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.api.dependencies import get_authenticated_user, require_admin
from bugbridge.database.connection import get_session, get_session_context
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    JiraTicket as DBJiraTicket,
)
from bugbridge.config import get_settings
from bugbridge.integrations.mcp_jira import MCPJiraClient, MCPJiraError, MCPJiraNotFoundError
from bugbridge.utils.logging import get_logger
from bugbridge.utils.notifications import is_resolution_status, notify_customer_on_resolution

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
    session: AsyncSession = Depends(get_session),
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
    try:
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
    except Exception as e:
        logger.error(f"Error fetching Jira tickets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Jira tickets: {str(e)}"
        )


@router.get("/{ticket_id}", response_model=JiraTicketResponse, status_code=status.HTTP_200_OK)
async def get_jira_ticket(
    ticket_id: UUID,
    current_user = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> JiraTicketResponse:
    """
    Get detailed information about a specific Jira ticket.

    Includes linked feedback post information if available.
    """
    try:
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
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching Jira ticket {ticket_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Jira ticket: {str(e)}"
        )


class JiraTicketRefreshResponse(BaseModel):
    """Response model for Jira ticket refresh operation."""

    success: bool = Field(..., description="Whether the refresh succeeded")
    tickets_updated: int = Field(..., description="Number of tickets successfully updated")
    tickets_failed: int = Field(..., description="Number of tickets that failed to update")
    total_tickets: int = Field(..., description="Total number of tickets processed")
    errors: List[str] = Field(default_factory=list, description="List of error messages for failed tickets")
    timestamp: datetime = Field(..., description="Time the refresh completed")


@router.post("/refresh", response_model=JiraTicketRefreshResponse, status_code=status.HTTP_200_OK)
async def refresh_jira_tickets(
    current_user = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of tickets to refresh (default: all)"),
) -> JiraTicketRefreshResponse:
    """
    Refresh all Jira tickets from the Jira instance via MCP server.
    
    This endpoint fetches the latest status, priority, assignee, and other fields
    from Jira and updates the database records accordingly.
    
    Requires admin privileges.
    """
    try:
        logger.info("Starting Jira tickets refresh from MCP server")
        
        # Get all Jira tickets from database
        query = select(DBJiraTicket)
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        all_tickets = result.scalars().all()
        
        total_tickets = len(all_tickets)
        tickets_updated = 0
        tickets_failed = 0
        errors: List[str] = []
        
        if total_tickets == 0:
            logger.info("No Jira tickets found to refresh")
            return JiraTicketRefreshResponse(
                success=True,
                tickets_updated=0,
                tickets_failed=0,
                total_tickets=0,
                errors=[],
                timestamp=datetime.now(UTC),
            )
        
        # Initialize Jira client
        jira_client = MCPJiraClient(auto_connect=False)
        
        try:
            # Connect to MCP server
            await jira_client.connect()
            
            # Get resolution statuses from config
            settings = get_settings()
            resolution_statuses = settings.jira.resolution_done_statuses
            
            # Process each ticket
            for db_ticket in all_tickets:
                try:
                    # Store previous status before updating
                    previous_status = db_ticket.status
                    
                    # Fetch latest data from Jira
                    logger.debug(f"Refreshing ticket {db_ticket.jira_issue_key}")
                    latest_ticket = await jira_client.get_issue(db_ticket.jira_issue_key)
                    
                    # Update database record with latest data
                    db_ticket.status = latest_ticket.status
                    db_ticket.priority = latest_ticket.priority
                    db_ticket.assignee = latest_ticket.assignee
                    db_ticket.updated_at = datetime.now(UTC)
                    
                    # Check if ticket is resolved using config resolution statuses
                    current_status = latest_ticket.status
                    is_resolved = is_resolution_status(current_status, resolution_statuses)
                    
                    # Update resolved_at if ticket is resolved
                    if is_resolved:
                        if db_ticket.resolved_at is None:
                            db_ticket.resolved_at = datetime.now(UTC)
                            # Ticket was just resolved for the first time
                            # Trigger notification (will be committed with other changes)
                            try:
                                await notify_customer_on_resolution(
                                    session=session,
                                    db_ticket=db_ticket,
                                    previous_status=previous_status,
                                    current_status=current_status,
                                )
                            except Exception as notification_error:
                                # Log notification error but don't fail the refresh
                                logger.error(
                                    f"Failed to send notification for ticket {db_ticket.jira_issue_key}: {str(notification_error)}",
                                    exc_info=True,
                                )
                    else:
                        # If ticket is reopened, clear resolved_at
                        db_ticket.resolved_at = None
                    
                    tickets_updated += 1
                    logger.info(
                        f"Successfully refreshed ticket {db_ticket.jira_issue_key}: status={latest_ticket.status}, assignee={latest_ticket.assignee}",
                        extra={
                            "ticket_key": db_ticket.jira_issue_key,
                            "status": latest_ticket.status,
                            "assignee": latest_ticket.assignee,
                            "priority": latest_ticket.priority,
                        }
                    )
                    
                except MCPJiraNotFoundError:
                    error_msg = f"Ticket {db_ticket.jira_issue_key} not found in Jira"
                    errors.append(error_msg)
                    tickets_failed += 1
                    logger.warning(error_msg)
                    
                except MCPJiraError as e:
                    error_msg = f"Failed to refresh ticket {db_ticket.jira_issue_key}: {str(e)}"
                    errors.append(error_msg)
                    tickets_failed += 1
                    logger.error(error_msg, exc_info=True)
                    
                except Exception as e:
                    error_msg = f"Unexpected error refreshing ticket {db_ticket.jira_issue_key}: {str(e)}"
                    errors.append(error_msg)
                    tickets_failed += 1
                    logger.error(error_msg, exc_info=True)
            
            # Commit all updates
            await session.commit()
            
        finally:
            # Always disconnect
            try:
                await jira_client.disconnect()
            except Exception:
                pass  # Ignore disconnect errors
        
        logger.info(
            f"Jira tickets refresh completed: {tickets_updated} updated, {tickets_failed} failed out of {total_tickets} total"
        )
        
        return JiraTicketRefreshResponse(
            success=tickets_failed == 0,
            tickets_updated=tickets_updated,
            tickets_failed=tickets_failed,
            total_tickets=total_tickets,
            errors=errors[:10],  # Limit to first 10 errors
            timestamp=datetime.now(UTC),
        )
        
    except Exception as e:
        logger.error(f"Error refreshing Jira tickets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh Jira tickets: {str(e)}"
        )


__all__ = [
    "router",
    "JiraTicketResponse",
    "JiraTicketListResponse",
    "JiraTicketRefreshResponse",
]

