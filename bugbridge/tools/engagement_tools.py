"""
Engagement Calculation Tools

LangChain tools for calculating engagement scores from feedback post data.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from langchain.tools import tool


class CalculateEngagementInput(BaseModel):
    """Input schema for engagement score calculation."""

    votes: int = Field(..., description="Number of votes on the feedback post", ge=0)
    comments_count: int = Field(..., description="Number of comments on the feedback post", ge=0)
    days_since_creation: Optional[float] = Field(
        None, description="Number of days since post creation (optional, for recency weighting)"
    )


def calculate_engagement_score(votes: int, comments_count: int, days_since_creation: Optional[float] = None) -> float:
    """
    Calculate engagement score from votes and comments.

    Engagement score formula:
    - Base score from votes (normalized, votes count more but with diminishing returns)
    - Bonus from comments (comments indicate active discussion)
    - Recency weighting (newer posts get slight boost)

    Args:
        votes: Number of votes.
        comments_count: Number of comments.
        days_since_creation: Optional days since creation for recency weighting.

    Returns:
        Engagement score (0.0 to ~100.0, but typically 0-50 range).
    """
    # Base engagement from votes (normalized with logarithmic scale)
    # Formula: 10 * log10(votes + 1) to prevent division by zero and give diminishing returns
    import math

    vote_score = 10 * math.log10(votes + 1) if votes > 0 else 0.0

    # Comment engagement (comments indicate active discussion)
    # Formula: 5 * log10(comments + 1)
    comment_score = 5 * math.log10(comments_count + 1) if comments_count > 0 else 0.0

    # Total base score
    base_score = vote_score + comment_score

    # Recency boost (if provided)
    # Newer posts (0-7 days) get up to 20% boost
    recency_multiplier = 1.0
    if days_since_creation is not None:
        if days_since_creation <= 7:
            # Linear decay from 1.2x to 1.0x over 7 days
            recency_multiplier = 1.2 - (days_since_creation / 7) * 0.2
        # After 7 days, no boost

    final_score = base_score * recency_multiplier

    # Cap at reasonable maximum (in practice, very high engagement)
    return min(final_score, 100.0)


@tool(args_schema=CalculateEngagementInput)
async def calculate_engagement_tool(votes: int, comments_count: int, days_since_creation: Optional[float] = None) -> float:
    """
    Calculate engagement score from feedback post votes and comments.

    This tool calculates an engagement score based on:
    - Number of votes (primary indicator of user interest)
    - Number of comments (indicates active discussion)
    - Recency of the post (newer posts get slight boost)

    Args:
        votes: Number of votes on the feedback post.
        comments_count: Number of comments on the feedback post.
        days_since_creation: Optional days since creation for recency weighting.

    Returns:
        Engagement score (float, typically 0-50 range).
    """
    return calculate_engagement_score(votes, comments_count, days_since_creation)


def create_engagement_tool() -> Any:
    """
    Create the engagement calculation LangChain tool.

    Returns:
        LangChain tool instance.
    """
    return calculate_engagement_tool


__all__ = [
    "calculate_engagement_score",
    "calculate_engagement_tool",
    "create_engagement_tool",
    "CalculateEngagementInput",
]

