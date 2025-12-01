"""
Report Filter Models

Pydantic models for filtering report data by date range, category, and other criteria.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ReportFilters(BaseModel):
    """
    Filters for customizing report generation.

    Attributes:
        start_date: Start date for date range filter (inclusive).
        end_date: End date for date range filter (inclusive).
        board_ids: Filter by specific board IDs (empty = all boards).
        tags: Filter by tags (empty = all tags).
        statuses: Filter by post statuses (empty = all statuses).
        sentiment_filter: Filter by sentiment categories (empty = all sentiments).
        bug_only: If True, only include items identified as bugs.
        feature_only: If True, only include feature requests (non-bugs).
        min_priority_score: Minimum priority score to include (0-100).
        min_votes: Minimum number of votes to include.
        jira_project_keys: Filter by Jira project keys (empty = all projects).
        jira_statuses: Filter by Jira ticket statuses (empty = all statuses).
    """

    start_date: Optional[datetime] = Field(
        None,
        description="Start date for date range filter (inclusive). If None, no start limit.",
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date for date range filter (inclusive). If None, no end limit.",
    )
    board_ids: List[str] = Field(
        default_factory=list,
        description="Filter by specific board IDs. Empty list = all boards.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Filter by tags. Empty list = all tags.",
    )
    statuses: List[str] = Field(
        default_factory=list,
        description="Filter by post statuses (e.g., 'open', 'complete', 'planned'). Empty list = all statuses.",
    )
    sentiment_filter: List[str] = Field(
        default_factory=list,
        description="Filter by sentiment categories (e.g., 'Positive', 'Negative', 'Neutral'). Empty list = all sentiments.",
    )
    bug_only: bool = Field(
        False,
        description="If True, only include items identified as bugs.",
    )
    feature_only: bool = Field(
        False,
        description="If True, only include feature requests (non-bugs).",
    )
    min_priority_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Minimum priority score to include (0-100). None = no minimum.",
    )
    min_votes: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum number of votes to include. None = no minimum.",
    )
    jira_project_keys: List[str] = Field(
        default_factory=list,
        description="Filter by Jira project keys. Empty list = all projects.",
    )
    jira_statuses: List[str] = Field(
        default_factory=list,
        description="Filter by Jira ticket statuses. Empty list = all statuses.",
    )

    @model_validator(mode="after")
    def _validate_bug_feature_exclusivity(self):  # noqa: D401
        """Ensure bug_only and feature_only are not both True."""
        if self.bug_only and self.feature_only:
            raise ValueError("bug_only and feature_only cannot both be True")
        return self

    @model_validator(mode="after")
    def _validate_date_range(self):  # noqa: D401
        """Ensure end_date is after start_date if both are provided."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after or equal to start_date")
        return self

    def to_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Get date range tuple for filtering.

        Returns:
            Tuple of (start_date, end_date) with proper time boundaries.
        """
        start = None
        end = None

        if self.start_date:
            # Start of day for start_date
            start = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        if self.end_date:
            # End of day for end_date (inclusive)
            end = self.end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        return (start, end)

    def is_empty(self) -> bool:
        """
        Check if all filters are empty (no filtering applied).

        Returns:
            True if no filters are set, False otherwise.
        """
        return (
            self.start_date is None
            and self.end_date is None
            and not self.board_ids
            and not self.tags
            and not self.statuses
            and not self.sentiment_filter
            and not self.bug_only
            and not self.feature_only
            and self.min_priority_score is None
            and self.min_votes is None
            and not self.jira_project_keys
            and not self.jira_statuses
        )


__all__ = [
    "ReportFilters",
]

