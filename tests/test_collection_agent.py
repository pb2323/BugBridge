"""
Tests for Feedback Collection Agent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List

import pytest

from bugbridge.agents import collection
from bugbridge.models.feedback import FeedbackPost


def make_feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Create a sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="Sample Post",
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


@pytest.mark.asyncio
async def test_collect_feedback_node_updates_state(monkeypatch):
    """collect_feedback_node should update workflow state when post collected."""
    async def mock_collect(**kwargs):
        return [make_feedback_post("new_post")]

    monkeypatch.setattr(collection, "collect_feedback_from_canny", mock_collect)

    new_state = await collection.collect_feedback_node({})

    assert new_state["workflow_status"] == "collected"
    assert new_state["feedback_post"].post_id == "new_post"
    assert new_state["metadata"]["source"] == "canny"


@pytest.mark.asyncio
async def test_collect_feedback_node_handles_no_posts(monkeypatch):
    """collect_feedback_node should handle scenario with no new posts."""
    async def mock_collect(**kwargs):
        return []

    monkeypatch.setattr(collection, "collect_feedback_from_canny", mock_collect)

    state = await collection.collect_feedback_node({})

    assert state["workflow_status"] is None
    assert "No new posts available" in state["errors"]


@pytest.mark.asyncio
async def test_collect_feedback_from_canny_skips_duplicates(monkeypatch):
    """collect_feedback_from_canny should skip posts already stored."""
    # Fake Canny client
    class FakeCannyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def list_posts(self, **kwargs):
            return [make_feedback_post("existing"), make_feedback_post("new")]

    stored_posts: List[str] = []

    async def mock_check(session, post_id):
        return post_id == "existing"

    async def mock_store(session, post):
        stored_posts.append(post.post_id)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def dummy_session_context():
        class DummySession:
            pass

        yield DummySession()

    monkeypatch.setattr(collection, "CannyClient", FakeCannyClient)
    monkeypatch.setattr(collection, "check_post_exists", mock_check)
    monkeypatch.setattr(collection, "store_feedback_post", mock_store)
    monkeypatch.setattr(collection, "get_session_context", dummy_session_context)

    posts = await collection.collect_feedback_from_canny(
        board_id="board",
        limit=10,
        status=None,
        skip_duplicates=True,
    )

    assert len(posts) == 1
    assert posts[0].post_id == "new"
    assert stored_posts == ["new"]


@pytest.mark.asyncio
async def test_collect_feedback_batch_returns_summary(monkeypatch):
    """collect_feedback_batch should return summary information."""
    async def mock_collect(**kwargs):
        return [make_feedback_post("batch_post")]

    monkeypatch.setattr(collection, "collect_feedback_from_canny", mock_collect)

    result = await collection.collect_feedback_batch(board_id="board", limit=50, status=None)

    assert result["success"] is True
    assert result["collected_count"] == 1
    assert result["posts"][0]["post_id"] == "batch_post"

