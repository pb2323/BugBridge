"""
API Routes for Report Generation

FastAPI endpoints for manually triggering report generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.api.exceptions import NotFoundError, ValidationError
from pydantic import BaseModel, Field

from bugbridge.agents.reporting import get_reporting_agent
from bugbridge.api.dependencies import get_authenticated_user, require_admin
from bugbridge.database.connection import get_session
from bugbridge.models.report_filters import ReportFilters
from bugbridge.utils.logging import get_logger
from bugbridge.workflows.reporting import execute_reporting_workflow

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportFiltersRequest(BaseModel):
    """Request model for report filters."""

    start_date: Optional[datetime] = Field(None, description="Start date for date range filter")
    end_date: Optional[datetime] = Field(None, description="End date for date range filter")
    board_ids: List[str] = Field(default_factory=list, description="Filter by board IDs")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    statuses: List[str] = Field(default_factory=list, description="Filter by post statuses")
    sentiment_filter: List[str] = Field(default_factory=list, description="Filter by sentiment categories")
    bug_only: bool = Field(False, description="Only include items identified as bugs")
    feature_only: bool = Field(False, description="Only include feature requests")
    min_priority_score: Optional[int] = Field(None, ge=0, le=100, description="Minimum priority score")
    min_votes: Optional[int] = Field(None, ge=0, description="Minimum number of votes")
    jira_project_keys: List[str] = Field(default_factory=list, description="Filter by Jira project keys")
    jira_statuses: List[str] = Field(default_factory=list, description="Filter by Jira ticket statuses")


class ReportGenerationRequest(BaseModel):
    """Request model for report generation."""

    report_date: Optional[datetime] = Field(None, description="Date for which to generate report (defaults to yesterday)")
    filters: Optional[ReportFiltersRequest] = Field(None, description="Optional filters to apply")


class ReportGenerationResponse(BaseModel):
    """Response model for report generation."""

    success: bool = Field(..., description="Whether report generation was successful")
    report_id: Optional[str] = Field(None, description="Generated report ID")
    report_date: Optional[datetime] = Field(None, description="Report date")
    metrics: Optional[dict] = Field(None, description="Report metrics")
    summary: Optional[dict] = Field(None, description="Report summary")
    content: Optional[str] = Field(None, description="Formatted report content (Markdown)")
    delivery: Optional[dict] = Field(None, description="Delivery results for each channel")
    errors: List[str] = Field(default_factory=list, description="List of errors if any")


@router.post("/generate", response_model=ReportGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_report(
    request: ReportGenerationRequest,
    current_user = Depends(require_admin()),
) -> ReportGenerationResponse:
    """
    Generate a custom report with optional filters.

    This endpoint allows manual triggering of report generation with customizable filters.
    The report will be generated, stored in the database, and delivered via configured channels.

    **Example Request:**
    ```json
    {
        "report_date": "2025-01-15T00:00:00Z",
        "filters": {
            "board_ids": ["board1", "board2"],
            "tags": ["bug", "urgent"],
            "bug_only": true,
            "min_priority_score": 70
        }
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "report_id": "abc123...",
        "report_date": "2025-01-15T00:00:00Z",
        "metrics": {...},
        "summary": {...},
        "content": "# Daily Report...",
        "delivery": {
            "email": {"success": true},
            "file_storage": {"success": true, "file_path": "./reports/..."}
        }
    }
    ```
    """
    try:
        # Convert request filters to ReportFilters model
        filters = None
        if request.filters:
            filters = ReportFilters(
                start_date=request.filters.start_date,
                end_date=request.filters.end_date,
                board_ids=request.filters.board_ids,
                tags=request.filters.tags,
                statuses=request.filters.statuses,
                sentiment_filter=request.filters.sentiment_filter,
                bug_only=request.filters.bug_only,
                feature_only=request.filters.feature_only,
                min_priority_score=request.filters.min_priority_score,
                min_votes=request.filters.min_votes,
                jira_project_keys=request.filters.jira_project_keys,
                jira_statuses=request.filters.jira_statuses,
            )

        logger.info(
            "API request to generate report",
            extra={
                "report_date": request.report_date.isoformat() if request.report_date else None,
                "has_filters": filters is not None and not filters.is_empty() if filters else False,
            },
        )

        # Generate report
        agent = get_reporting_agent()
        
        # Debug logging for current_user
        logger.info(
            f"Current user object type: {type(current_user)}, has email: {hasattr(current_user, 'email')}",
            extra={
                "user_type": str(type(current_user)),
                "user_id": str(getattr(current_user, 'id', None)),
                "username": getattr(current_user, 'username', None),
                "email_attr_exists": hasattr(current_user, 'email'),
                "email_value": getattr(current_user, 'email', None),
            }
        )
        
        # Get current user's email for notification
        user_email = current_user.email if hasattr(current_user, 'email') and current_user.email else None
        
        if hasattr(current_user, 'username'):
            logger.info(
                f"Generating report for user: {current_user.username}, email: {user_email}",
                extra={"username": current_user.username, "user_email": user_email},
            )
        else:
            logger.info(
                f"Generating report, email: {user_email}",
                extra={"user_email": user_email},
            )
        
        result = await agent.generate_daily_report(
            report_date=request.report_date,
            filters=filters,
            user_email=user_email,
        )

        return ReportGenerationResponse(
            success=True,
            report_id=result.get("report_id"),
            report_date=result.get("report_date"),
            metrics=result.get("metrics"),
            summary=result.get("summary"),
            content=result.get("content"),
            delivery=result.get("delivery"),
            errors=[],
        )

    except Exception as e:
        logger.error(f"Failed to generate report via API: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        ) from e


@router.get("", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def list_reports(
    current_user = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
) -> Dict[str, Any]:
    """
    List historical reports with filtering and pagination.
    """
    from bugbridge.database.models import Report as DBReport
    from sqlalchemy import and_, func, select

    try:
        # Build query
        query = select(DBReport)

        # Build filter conditions
        conditions = []
        if report_type:
            conditions.append(DBReport.report_type == report_type)
        if start_date:
            conditions.append(DBReport.report_date >= start_date)
        if end_date:
            conditions.append(DBReport.report_date <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(DBReport.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        # Sorting (most recent first)
        query = query.order_by(DBReport.generated_at.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await session.execute(query)
        reports = result.scalars().all()

        # Build response
        items = []
        for report in reports:
            items.append({
                "id": str(report.id),
                "report_type": report.report_type,
                "report_date": report.report_date.isoformat() if report.report_date else None,
                "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                "has_content": report.report_content is not None,
                "has_metrics": report.metrics is not None,
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error fetching reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reports: {str(e)}"
        )


@router.get("/{report_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_report(
    report_id: str,
    current_user = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get specific report details including content and metrics.
    """
    from bugbridge.database.models import Report as DBReport
    from sqlalchemy import select
    from uuid import UUID as UUIDType

    try:
        report_uuid = UUIDType(report_id)
    except ValueError:
        raise ValidationError(
            message=f"Invalid report ID format: {report_id}",
            details={"field": "report_id", "format": "UUID"},
        )

    try:
        query = select(DBReport).where(DBReport.id == report_uuid)
        result = await session.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError(
                message=f"Report with ID {report_id} not found",
                resource_type="report",
                resource_id=report_id,
            )

        return {
            "id": str(report.id),
            "report_type": report.report_type,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "content": report.report_content,
            "metrics": report.metrics,
        }
    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch report: {str(e)}"
        )


@router.post("/generate/workflow", response_model=ReportGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_report_workflow(
    request: ReportGenerationRequest,
    current_user = Depends(require_admin()),
) -> ReportGenerationResponse:
    """
    Generate a report using the LangGraph workflow.

    This endpoint uses the full reporting workflow instead of just the agent.
    Useful for testing the complete workflow pipeline.
    """
    try:
        logger.info(
            "API request to generate report via workflow",
            extra={
                "report_date": request.report_date.isoformat() if request.report_date else None,
            },
        )

        # Execute workflow
        result = await execute_reporting_workflow(report_date=request.report_date)

        return ReportGenerationResponse(
            success=result.get("report_id") is not None,
            report_id=result.get("report_id"),
            report_date=result.get("report_date"),
            metrics=result.get("metrics"),
            summary=result.get("summary"),
            content=result.get("content"),
            delivery=result.get("delivery"),
            errors=result.get("errors", []),
        )

    except Exception as e:
        logger.error(f"Failed to generate report via workflow API: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report via workflow: {str(e)}",
        ) from e


__all__ = [
    "router",
    "ReportGenerationRequest",
    "ReportGenerationResponse",
    "ReportFiltersRequest",
]

