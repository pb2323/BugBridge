"""
Feedback Models

Pydantic models for feedback posts from Canny.io.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class FeedbackPost(BaseModel):
    """
    Represents a feedback post from Canny.io.
    
    Attributes:
        post_id: Unique identifier for the post from Canny.io
        board_id: ID of the Canny.io board this post belongs to
        title: Title of the feedback post
        content: Content/description of the feedback post
        author_id: ID of the user who created the post
        author_name: Name of the user who created the post
        created_at: Timestamp when the post was created
        updated_at: Timestamp when the post was last updated
        votes: Number of votes the post has received
        comments_count: Number of comments on the post
        status: Current status of the post (e.g., 'open', 'complete', 'planned')
        url: URL to the post on Canny.io
        tags: List of tags associated with the post
        collected_at: Timestamp when the post was collected by BugBridge
    """
    
    post_id: str = Field(..., description="Unique identifier for the post from Canny.io")
    board_id: str = Field(..., description="ID of the Canny.io board this post belongs to")
    title: str = Field(..., description="Title of the feedback post", min_length=1)
    content: str = Field(..., description="Content/description of the feedback post")
    author_id: Optional[str] = Field(None, description="ID of the user who created the post")
    author_name: Optional[str] = Field(None, description="Name of the user who created the post")
    created_at: datetime = Field(..., description="Timestamp when the post was created")
    updated_at: datetime = Field(..., description="Timestamp when the post was last updated")
    votes: int = Field(default=0, description="Number of votes the post has received", ge=0)
    comments_count: int = Field(default=0, description="Number of comments on the post", ge=0)
    status: Optional[str] = Field(None, description="Current status of the post")
    url: Optional[HttpUrl] = Field(None, description="URL to the post on Canny.io")
    tags: List[str] = Field(default_factory=list, description="List of tags associated with the post")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the post was collected by BugBridge")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "post_id": "651a1b2c3d4e5f6g7h8i9j0k",
                "board_id": "691d7a43749ccd4a28189d49",
                "title": "Feature request: Dark mode support",
                "content": "I would love to see a dark mode option in the application. It would help reduce eye strain during long work sessions.",
                "author_id": "user123",
                "author_name": "John Doe",
                "created_at": "2025-11-20T10:30:00Z",
                "updated_at": "2025-11-20T15:45:00Z",
                "votes": 42,
                "comments_count": 8,
                "status": "open",
                "url": "https://bugbridge.canny.io/admin/board/feedback-and-feature-requests/p/feature-request-dark-mode-support",
                "tags": ["feature-request", "ui/ux", "dark-mode"],
                "collected_at": "2025-11-20T16:00:00Z"
            }
        }

