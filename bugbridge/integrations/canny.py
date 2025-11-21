"""Canny.io API client for feedback collection"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bugbridge.config import config
from bugbridge.utils.retry import retry_with_backoff
from bugbridge.models.feedback import FeedbackPost

logger = logging.getLogger(__name__)


class CannyAPIClient:
    """Client for interacting with Canny.io API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize Canny API client
        
        Args:
            api_key: Canny.io API key (defaults to config)
            base_url: Base URL for Canny API (defaults to config)
        """
        self.api_key = api_key or config.canny.api_key
        self.base_url = base_url or config.canny.base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def _make_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a POST request to Canny API
        
        Args:
            endpoint: API endpoint path
            data: Request data dictionary
        
        Returns:
            Response data as dictionary
        
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key to request data
        request_data = {"apiKey": self.api_key, **data}
        
        logger.debug(f"Making request to {url}")
        
        response = await self.client.post(
            url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(httpx.HTTPError,))
    async def list_boards(self) -> List[Dict[str, Any]]:
        """List all boards
        
        Returns:
            List of board dictionaries
        """
        logger.info("Fetching boards list")
        result = await self._make_request("boards/list", {})
        return result.get("boards", [])
    
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(httpx.HTTPError,))
    async def list_posts(
        self, 
        board_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        sort: str = "created"
    ) -> List[Dict[str, Any]]:
        """List posts from a board
        
        Args:
            board_id: Board ID to fetch posts from (defaults to config)
            limit: Maximum number of posts to return
            skip: Number of posts to skip for pagination
            sort: Sort order (created, trending, top, etc.)
        
        Returns:
            List of post dictionaries
        """
        board_id = board_id or config.canny.board_id
        
        logger.info(f"Fetching posts from board {board_id} (limit={limit}, skip={skip})")
        
        result = await self._make_request(
            "posts/list",
            {
                "boardID": board_id,
                "limit": limit,
                "skip": skip,
                "sort": sort
            }
        )
        
        return result.get("posts", [])
    
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(httpx.HTTPError,))
    async def retrieve_post(self, post_id: str) -> Dict[str, Any]:
        """Retrieve detailed post information
        
        Args:
            post_id: Post ID to retrieve
        
        Returns:
            Post data dictionary
        """
        logger.info(f"Retrieving post {post_id}")
        
        result = await self._make_request(
            "posts/retrieve",
            {"id": post_id}
        )
        
        return result
    
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(httpx.HTTPError,))
    async def post_comment(
        self,
        post_id: str,
        comment_value: str,
        author_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a comment to a feedback post
        
        Args:
            post_id: Post ID to comment on
            comment_value: Comment text content
            author_id: Author ID (defaults to admin user)
        
        Returns:
            Response data
        """
        author_id = author_id or config.canny.admin_user_id
        
        logger.info(f"Posting comment to post {post_id}")
        
        result = await self._make_request(
            "comments/create",
            {
                "postID": post_id,
                "value": comment_value,
                "authorID": author_id
            }
        )
        
        return result
    
    @retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(httpx.HTTPError,))
    async def change_post_status(
        self,
        post_id: str,
        status: str,
        changer_id: Optional[str] = None,
        should_notify_voters: bool = True,
        comment_value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Change the status of a post
        
        Args:
            post_id: Post ID to update
            status: New status (open, in progress, complete)
            changer_id: User making the change (defaults to admin)
            should_notify_voters: Whether to notify voters
            comment_value: Optional comment explaining the change
        
        Returns:
            Updated post data
        """
        changer_id = changer_id or config.canny.admin_user_id
        
        logger.info(f"Changing post {post_id} status to {status}")
        
        request_data = {
            "postID": post_id,
            "status": status,
            "changerID": changer_id,
            "shouldNotifyVoters": should_notify_voters
        }
        
        if comment_value:
            request_data["commentValue"] = comment_value
        
        result = await self._make_request("posts/change_status", request_data)
        return result
    
    def _parse_post_to_model(self, post_data: Dict[str, Any]) -> FeedbackPost:
        """Parse Canny API post data to FeedbackPost model
        
        Args:
            post_data: Raw post data from Canny API
        
        Returns:
            FeedbackPost model instance
        """
        # Parse timestamps
        created_at = datetime.fromisoformat(post_data.get("created", "").replace("Z", "+00:00"))
        
        return FeedbackPost(
            post_id=post_data.get("id", ""),
            board_id=post_data.get("board", {}).get("id", ""),
            title=post_data.get("title", ""),
            content=post_data.get("details", ""),
            author_id=post_data.get("author", {}).get("id"),
            author_name=post_data.get("author", {}).get("name"),
            created_at=created_at,
            updated_at=created_at,  # Canny doesn't provide separate updated_at
            votes=post_data.get("score", 0),
            comments_count=post_data.get("commentCount", 0),
            status=post_data.get("status"),
            url=post_data.get("url"),
            tags=[tag.get("name", "") for tag in post_data.get("tags", [])],
            collected_at=datetime.now()
        )
    
    async def list_posts_as_models(
        self,
        board_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[FeedbackPost]:
        """List posts and return as FeedbackPost models
        
        Args:
            board_id: Board ID (defaults to config)
            limit: Maximum posts to return
            skip: Number to skip for pagination
        
        Returns:
            List of FeedbackPost models
        """
        posts_data = await self.list_posts(board_id, limit, skip)
        return [self._parse_post_to_model(post) for post in posts_data]
