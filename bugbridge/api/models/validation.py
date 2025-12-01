"""
Request/Response Validation Models

Pydantic models for validating API requests and responses with comprehensive
field validation, custom validators, and error messages.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Ensure page_size is within reasonable bounds."""
        if v > 100:
            raise ValueError("page_size cannot exceed 100")
        return v


class DateRangeParams(BaseModel):
    """Date range parameters for filtering."""

    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeParams":
        """Ensure end_date is after start_date if both are provided."""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
        return self


class FeedbackFilterParams(BaseModel):
    """Filter parameters for feedback posts."""

    board_ids: Optional[str] = Field(None, description="Comma-separated list of board IDs")
    tags: Optional[str] = Field(None, description="Comma-separated list of tags")
    statuses: Optional[str] = Field(None, description="Comma-separated list of statuses")
    search: Optional[str] = Field(None, min_length=1, max_length=500, description="Search query")
    is_bug: Optional[bool] = Field(None, description="Filter by bug status")
    sentiment: Optional[str] = Field(None, description="Filter by sentiment category")
    min_priority: Optional[int] = Field(None, ge=0, le=100, description="Minimum priority score")
    min_votes: Optional[int] = Field(None, ge=0, description="Minimum number of votes")
    has_jira_ticket: Optional[bool] = Field(None, description="Filter by Jira ticket linkage")

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: Optional[str]) -> Optional[str]:
        """Validate sentiment value."""
        if v is not None:
            valid_sentiments = ["positive", "neutral", "negative", "urgent"]
            if v.lower() not in valid_sentiments:
                raise ValueError(f"sentiment must be one of: {', '.join(valid_sentiments)}")
        return v.lower() if v else v


class SortParams(BaseModel):
    """Sorting parameters for list endpoints."""

    sort_by: str = Field("collected_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc or desc)")

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order."""
        v_lower = v.lower()
        if v_lower not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v_lower


class JiraTicketFilterParams(BaseModel):
    """Filter parameters for Jira tickets."""

    project_keys: Optional[str] = Field(None, description="Comma-separated list of project keys")
    statuses: Optional[str] = Field(None, description="Comma-separated list of statuses")
    priorities: Optional[str] = Field(None, description="Comma-separated list of priorities")
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    resolved_only: Optional[bool] = Field(None, description="Filter to only resolved tickets")
    unresolved_only: Optional[bool] = Field(None, description="Filter to only unresolved tickets")
    has_feedback: Optional[bool] = Field(None, description="Filter by feedback linkage")

    @model_validator(mode="after")
    def validate_resolution_filters(self) -> "JiraTicketFilterParams":
        """Ensure resolved_only and unresolved_only are not both True."""
        if self.resolved_only and self.unresolved_only:
            raise ValueError("resolved_only and unresolved_only cannot both be True")
        return self


class ReportFilterParams(BaseModel):
    """Filter parameters for report generation."""

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

    @model_validator(mode="after")
    def validate_filters(self) -> "ReportFilterParams":
        """Validate filter combinations."""
        if self.bug_only and self.feature_only:
            raise ValueError("bug_only and feature_only cannot both be True")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
        return self

    @field_validator("sentiment_filter")
    @classmethod
    def validate_sentiment_filter(cls, v: List[str]) -> List[str]:
        """Validate sentiment filter values."""
        valid_sentiments = ["positive", "neutral", "negative", "urgent"]
        for sentiment in v:
            if sentiment.lower() not in valid_sentiments:
                raise ValueError(f"Invalid sentiment: {sentiment}. Must be one of: {', '.join(valid_sentiments)}")
        return [s.lower() for s in v]


class UUIDPathParam(BaseModel):
    """UUID path parameter validation."""

    id: UUID = Field(..., description="Resource UUID")

    @field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v: str | UUID) -> UUID:
        """Validate and convert UUID."""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        return v


class StringPathParam(BaseModel):
    """String path parameter validation."""

    value: str = Field(..., min_length=1, max_length=255, description="String parameter value")

    @field_validator("value")
    @classmethod
    def validate_string(cls, v: str) -> str:
        """Validate string parameter."""
        if not v.strip():
            raise ValueError("String parameter cannot be empty or whitespace only")
        return v.strip()


__all__ = [
    "PaginationParams",
    "DateRangeParams",
    "FeedbackFilterParams",
    "SortParams",
    "JiraTicketFilterParams",
    "ReportFilterParams",
    "UUIDPathParam",
    "StringPathParam",
]

