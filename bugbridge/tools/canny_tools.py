"""LangChain tools for Canny.io operations"""

from typing import Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from bugbridge.integrations.canny import CannyAPIClient
from bugbridge.models.feedback import FeedbackPost
import asyncio


class ListPostsInput(BaseModel):
    """Input for ListPostsTool"""
    board_id: Optional[str] = Field(None, description="Board ID to fetch posts from")
    limit: int = Field(default=10, description="Maximum number of posts to return")
    skip: int = Field(default=0, description="Number of posts to skip for pagination")


class ListPostsTool(BaseTool):
    """Tool for listing posts from Canny.io"""
    
    name: str = "list_canny_posts"
    description: str = "List feedback posts from Canny.io board"
    args_schema: type[BaseModel] = ListPostsInput
    
    def _run(self, board_id: Optional[str] = None, limit: int = 10, skip: int = 0) -> str:
        """Synchronous version - not used in async context"""
        raise NotImplementedError("Use async version")
    
    async def _arun(
        self,
        board_id: Optional[str] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[dict]:
        """List posts from Canny.io
        
        Args:
            board_id: Board ID (optional)
            limit: Maximum posts to return
            skip: Pagination offset
        
        Returns:
            List of post dictionaries
        """
        client = CannyAPIClient()
        try:
            posts = await client.list_posts(board_id, limit, skip)
            return posts
        finally:
            await client.close()


class GetPostDetailsInput(BaseModel):
    """Input for GetPostDetailsTool"""
    post_id: str = Field(..., description="Post ID to retrieve details for")


class GetPostDetailsTool(BaseTool):
    """Tool for retrieving detailed post information"""
    
    name: str = "get_canny_post_details"
    description: str = "Retrieve detailed information for a specific Canny.io post"
    args_schema: type[BaseModel] = GetPostDetailsInput
    
    def _run(self, post_id: str) -> str:
        """Synchronous version - not used in async context"""
        raise NotImplementedError("Use async version")
    
    async def _arun(self, post_id: str) -> dict:
        """Retrieve post details
        
        Args:
            post_id: Post ID to retrieve
        
        Returns:
            Post data dictionary
        """
        client = CannyAPIClient()
        try:
            post = await client.retrieve_post(post_id)
            return post
        finally:
            await client.close()


class PostCommentInput(BaseModel):
    """Input for PostCommentTool"""
    post_id: str = Field(..., description="Post ID to comment on")
    comment_value: str = Field(..., description="Comment text content")
    author_id: Optional[str] = Field(None, description="Author ID (optional)")


class PostCommentTool(BaseTool):
    """Tool for posting comments to Canny.io posts"""
    
    name: str = "post_canny_comment"
    description: str = "Post a comment to a Canny.io feedback post"
    args_schema: type[BaseModel] = PostCommentInput
    
    def _run(self, post_id: str, comment_value: str, author_id: Optional[str] = None) -> str:
        """Synchronous version - not used in async context"""
        raise NotImplementedError("Use async version")
    
    async def _arun(
        self,
        post_id: str,
        comment_value: str,
        author_id: Optional[str] = None
    ) -> dict:
        """Post comment to Canny.io
        
        Args:
            post_id: Post ID to comment on
            comment_value: Comment text
            author_id: Optional author ID
        
        Returns:
            Response data
        """
        client = CannyAPIClient()
        try:
            result = await client.post_comment(post_id, comment_value, author_id)
            return result
        finally:
            await client.close()
