"""
LangChain Tools for Canny.io Integration

Tools that enable AI agents to interact with Canny.io API for collecting
feedback posts, retrieving post details, and posting comments.
"""

from __future__ import annotations

from typing import Optional, Type

from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field

from bugbridge.integrations.canny import CannyClient, CannyAPIError
from bugbridge.models.feedback import FeedbackPost
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class ListPostsInput(BaseModel):
    """Input schema for ListPostsTool."""

    board_id: Optional[str] = Field(None, description="Board ID to filter posts (defaults to config)")
    limit: int = Field(100, ge=1, le=100, description="Maximum number of posts to retrieve (1-100)")
    skip: int = Field(0, ge=0, description="Number of posts to skip for pagination")
    status: Optional[str] = Field(None, description="Filter by post status (e.g., 'open', 'complete')")


class GetPostDetailsInput(BaseModel):
    """Input schema for GetPostDetailsTool."""

    post_id: str = Field(..., description="Canny.io post ID")


class PostCommentInput(BaseModel):
    """Input schema for PostCommentTool."""

    post_id: str = Field(..., description="Canny.io post ID to comment on")
    value: str = Field(..., min_length=1, description="Comment text/content")
    author_id: Optional[str] = Field(None, description="Author ID for the comment (defaults to admin user)")


def create_list_posts_tool(canny_client: CannyClient) -> BaseTool:
    """
    Create a LangChain tool for listing posts from Canny.io.

    Args:
        canny_client: Initialized CannyClient instance.

    Returns:
        LangChain StructuredTool for listing posts.
    """
    async def list_posts(
        board_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        status: Optional[str] = None,
    ) -> list[dict]:
        """
        List posts from Canny.io with pagination support.

        Args:
            board_id: Board ID to filter posts (defaults to config).
            limit: Maximum number of posts to retrieve (1-100).
            skip: Number of posts to skip for pagination.
            status: Filter by post status (e.g., 'open', 'complete').

        Returns:
            List of post dictionaries (serialized FeedbackPost models).
        """
        try:
            posts = await canny_client.list_posts(
                board_id=board_id,
                limit=limit,
                skip=skip,
                status=status,
            )

            # Serialize posts to dictionaries for tool output
            return [post.model_dump(mode="json") for post in posts]

        except CannyAPIError as e:
            logger.error(
                f"Failed to list posts: {str(e)}",
                extra={"status_code": e.status_code},
            )
            return {"error": str(e)}

        except Exception as e:
            logger.error(f"Unexpected error listing posts: {str(e)}", exc_info=True)
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "list_canny_posts",
        args_schema=ListPostsInput,
        return_direct=True,
    )(list_posts)

    decorated_tool.description = (
        "List feedback posts from Canny.io with pagination support. "
        "Use this to collect new feedback posts or retrieve multiple posts at once."
    )

    return decorated_tool


def create_get_post_details_tool(canny_client: CannyClient) -> BaseTool:
    """
    Create a LangChain tool for getting post details from Canny.io.

    Args:
        canny_client: Initialized CannyClient instance.

    Returns:
        LangChain StructuredTool for getting post details.
    """
    async def get_post_details(post_id: str) -> dict:
        """
        Retrieve detailed information for a specific post.

        Args:
            post_id: Canny.io post ID.

        Returns:
            Post dictionary (serialized FeedbackPost model) with detailed information.
        """
        try:
            post = await canny_client.get_post_details(post_id)
            return post.model_dump(mode="json")

        except CannyAPIError as e:
            logger.error(
                f"Failed to get post details for {post_id}: {str(e)}",
                extra={"post_id": post_id, "status_code": e.status_code},
            )
            return {"error": str(e)}

        except Exception as e:
            logger.error(
                f"Unexpected error getting post details for {post_id}: {str(e)}",
                extra={"post_id": post_id},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "get_canny_post_details",
        args_schema=GetPostDetailsInput,
        return_direct=True,
    )(get_post_details)

    decorated_tool.description = (
        "Retrieve detailed information for a specific Canny.io feedback post. "
        "Use this to get full post content, metadata, and engagement metrics."
    )

    return decorated_tool


def create_post_comment_tool(canny_client: CannyClient) -> BaseTool:
    """
    Create a LangChain tool for posting comments to Canny.io posts.

    Args:
        canny_client: Initialized CannyClient instance.

    Returns:
        LangChain StructuredTool for posting comments.
    """
    async def post_comment(
        post_id: str,
        value: str,
        author_id: Optional[str] = None,
    ) -> dict:
        """
        Post a comment to a Canny.io feedback post.

        Args:
            post_id: Canny.io post ID to comment on.
            value: Comment text/content.
            author_id: Author ID for the comment (defaults to admin user).

        Returns:
            Comment response from API (typically contains comment ID).
        """
        try:
            response = await canny_client.post_comment(
                post_id=post_id,
                value=value,
                author_id=author_id,
            )
            return response

        except CannyAPIError as e:
            logger.error(
                f"Failed to post comment to {post_id}: {str(e)}",
                extra={"post_id": post_id, "status_code": e.status_code},
            )
            return {"error": str(e)}

        except Exception as e:
            logger.error(
                f"Unexpected error posting comment to {post_id}: {str(e)}",
                extra={"post_id": post_id},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "post_canny_comment",
        args_schema=PostCommentInput,
        return_direct=True,
    )(post_comment)

    decorated_tool.description = (
        "Post a comment to a Canny.io feedback post. "
        "Use this to notify customers when their issues are resolved or to provide updates on feedback."
    )

    return decorated_tool


def get_canny_tools(canny_client: CannyClient) -> list[BaseTool]:
    """
    Get all LangChain tools for Canny.io integration.

    Args:
        canny_client: Initialized CannyClient instance.

    Returns:
        List of LangChain BaseTool instances for Canny.io operations.
    """
    return [
        create_list_posts_tool(canny_client),
        create_get_post_details_tool(canny_client),
        create_post_comment_tool(canny_client),
    ]


__all__ = [
    "ListPostsInput",
    "GetPostDetailsInput",
    "PostCommentInput",
    "create_list_posts_tool",
    "create_get_post_details_tool",
    "create_post_comment_tool",
    "get_canny_tools",
]

