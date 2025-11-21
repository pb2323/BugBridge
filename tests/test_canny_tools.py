"""
Tests for Canny LangChain tools.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

import pytest

from bugbridge.models.feedback import FeedbackPost
from bugbridge.tools.canny_tools import (
    create_get_post_details_tool,
    create_list_posts_tool,
    create_post_comment_tool,
)


def feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Return sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="Sample",
        content="Content",
        author_id="author",
        author_name="Author",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        votes=5,
        comments_count=1,
        status="open",
        url="https://example.canny.io/posts/post_1",
        tags=["bug"],
    )


class FakeCannyClient:
    """Fake client for testing tools."""

    def __init__(self):
        self.comments: Dict[str, Any] = {}

    async def list_posts(self, **kwargs):
        return [feedback_post("post_1"), feedback_post("post_2")]

    async def get_post_details(self, post_id: str):
        return feedback_post(post_id)

    async def post_comment(self, post_id: str, value: str, author_id: str | None = None):
        self.comments[post_id] = value
        return {"id": "comment_1", "postID": post_id, "value": value}


@pytest.mark.asyncio
async def test_list_posts_tool_returns_posts():
    """List posts tool should return serialized posts."""
    client = FakeCannyClient()
    tool = create_list_posts_tool(client)

    result = await tool.coroutine(board_id="board_1", limit=2, skip=0, status=None)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["post_id"] == "post_1"


@pytest.mark.asyncio
async def test_get_post_details_tool_returns_post():
    """Get post details tool should return serialized post."""
    client = FakeCannyClient()
    tool = create_get_post_details_tool(client)

    result = await tool.coroutine(post_id="post_42")

    assert result["post_id"] == "post_42"
    assert result["title"] == "Sample"


@pytest.mark.asyncio
async def test_post_comment_tool_posts_comment():
    """Post comment tool should delegate to client."""
    client = FakeCannyClient()
    tool = create_post_comment_tool(client)

    response = await tool.coroutine(post_id="post_1", value="Thanks!", author_id="agent")

    assert response["id"] == "comment_1"
    assert client.comments["post_1"] == "Thanks!"

