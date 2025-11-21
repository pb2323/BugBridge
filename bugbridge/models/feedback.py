"""Pydantic models for feedback posts"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FeedbackPost(BaseModel):
    """Model for Canny.io feedback post"""
    
    post_id: str = Field(..., description="Canny.io post ID")
    board_id: str = Field(..., description="Canny.io board ID")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post content/details")
    author_id: Optional[str] = Field(None, description="Author Canny.io ID")
    author_name: Optional[str] = Field(None, description="Author name")
    created_at: datetime = Field(..., description="Post creation timestamp")
    updated_at: datetime = Field(..., description="Post last update timestamp")
    votes: int = Field(default=0, description="Number of votes")
    comments_count: int = Field(default=0, description="Number of comments")
    status: Optional[str] = Field(None, description="Post status")
    url: Optional[str] = Field(None, description="URL to post")
    tags: List[str] = Field(default_factory=list, description="Post tags")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "post_id": "691d7c0a58a681e83ef06510",
                "board_id": "691d7a43749ccd4a28189d49",
                "title": "Bug: Login page not loading",
                "content": "The login page shows a blank screen when accessing from mobile devices.",
                "author_id": "6072c28346f94e0f03499a52",
                "author_name": "John Doe",
                "created_at": "2024-11-19T10:30:00Z",
                "updated_at": "2024-11-19T10:30:00Z",
                "votes": 15,
                "comments_count": 3,
                "status": "open",
                "url": "https://bugbridge.canny.io/feedback/login-bug",
                "tags": ["bug", "mobile", "urgent"],
                "collected_at": "2024-11-19T11:00:00Z"
            }
        }
