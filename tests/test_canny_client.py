"""
Tests for Canny.io API client.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

import pytest

from bugbridge.integrations.canny import CannyAPIError, CannyClient
from bugbridge.utils.validators import ValidationError


def sample_post(post_id: str = "post_123") -> Dict[str, Any]:
    """Return sample post payload from Canny.io."""
    return {
        "id": post_id,
        "boardID": "board_1",
        "title": "Sample Post",
        "details": "Post content",
        "authorID": "author_1",
        "author": {"name": "Author Name"},
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-01-02T00:00:00Z",
        "voteCount": 5,
        "commentCount": 2,
        "status": "open",
        "url": "https://example.canny.io/posts/post_123",
        "tags": ["bug", "ui"],
    }


@pytest.mark.asyncio
async def test_list_posts_parses_response(monkeypatch):
    """CannyClient.list_posts should parse API response into FeedbackPost models."""
    client = CannyClient(api_key="test_key", subdomain="example")

    async def mock_request(self, endpoint, data=None, method="POST"):
        return {"posts": [sample_post("post_123")]}

    monkeypatch.setattr(CannyClient, "_make_request", mock_request)

    posts = await client.list_posts(board_id="board_1", limit=1)

    assert len(posts) == 1
    assert posts[0].post_id == "post_123"
    assert posts[0].title == "Sample Post"
    assert posts[0].votes == 5

    await client.close()


@pytest.mark.asyncio
async def test_get_post_details_returns_post(monkeypatch):
    """CannyClient.get_post_details should return single FeedbackPost."""
    client = CannyClient(api_key="test_key", subdomain="example")

    async def mock_request(self, endpoint, data=None, method="POST"):
        return sample_post("detail_post")

    monkeypatch.setattr(CannyClient, "_make_request", mock_request)

    post = await client.get_post_details("detail_post")

    assert post.post_id == "detail_post"
    assert post.author_name == "Author Name"

    await client.close()


@pytest.mark.asyncio
async def test_post_comment_requires_value():
    """post_comment should validate comment value."""
    client = CannyClient(api_key="test_key", subdomain="example")

    with pytest.raises(ValidationError):
        await client.post_comment(post_id="post_123", value="  ", author_id="author")

    await client.close()


@pytest.mark.asyncio
async def test_post_comment_calls_api(monkeypatch):
    """post_comment should call Canny API with expected payload."""
    client = CannyClient(api_key="test_key", subdomain="example")
    captured_payload = {}

    async def mock_request(self, endpoint, data=None, method="POST"):
        captured_payload["endpoint"] = endpoint
        captured_payload["data"] = data
        return {"id": "comment_1"}

    monkeypatch.setattr(CannyClient, "_make_request", mock_request)

    response = await client.post_comment(
        post_id="post_123",
        value="Thanks for the feedback!",
        author_id="author_123",
    )

    assert response["id"] == "comment_1"
    assert captured_payload["endpoint"] == "/comments/create"
    assert captured_payload["data"]["postID"] == "post_123"
    assert captured_payload["data"]["value"] == "Thanks for the feedback!"

    await client.close()

