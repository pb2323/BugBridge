"""
Canny.io API Client

Async client for interacting with Canny.io API to collect feedback posts,
retrieve post details, and post comments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import os

import httpx
from pydantic_settings import SettingsError

from bugbridge.config import get_settings
from bugbridge.models.feedback import FeedbackPost
from bugbridge.utils.logging import get_logger
from bugbridge.utils.retry import async_retry_with_backoff
from bugbridge.utils.validators import ValidationError, validate_post_id

logger = get_logger(__name__)


class CannyAPIError(Exception):
    """Raised when Canny.io API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """Initialize Canny API error with message, status code, and response."""
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class CannyClient:
    """
    Async client for Canny.io API.

    This client handles authentication, request formatting, error handling,
    and rate limiting with exponential backoff retry logic.
    """

    BASE_URL = "https://canny.io/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        subdomain: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Canny.io API client.

        Args:
            api_key: Canny.io API key (defaults to config).
            subdomain: Canny.io subdomain (defaults to config).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for failed requests.
        Prefers configuration from Settings.canny, but gracefully falls back to
        environment variables when global settings loading fails (for example,
        due to unrelated sections like `jira` being misconfigured).
        """
        # Preferred path: load from Settings
        try:
            settings = get_settings()
            self.api_key = api_key or settings.canny.api_key.get_secret_value()
            self.subdomain = subdomain or settings.canny.subdomain
        except SettingsError as e:
            # Settings failed (often due to another section like `jira`), so we
            # fall back to raw environment variables for Canny-specific config.
            logger.warning(
                "SettingsError while loading Canny configuration; "
                "falling back to CANNY_API_KEY and CANNY_SUBDOMAIN env vars. "
                "Original error: %s",
                str(e),
            )

            env_api_key = api_key or os.getenv("CANNY_API_KEY")
            env_subdomain = subdomain or os.getenv("CANNY_SUBDOMAIN")

            if not env_api_key:
                raise ValueError(
                    "Canny API key not available. Set CANNY_API_KEY in your environment or .env file."
                ) from e
            if not env_subdomain:
                raise ValueError(
                    "Canny subdomain not available. Set CANNY_SUBDOMAIN in your environment or .env file."
                ) from e

            self.api_key = env_api_key
            self.subdomain = env_subdomain
        except Exception:
            # Generic fallback: explicit params or env vars
            env_api_key = api_key or os.getenv("CANNY_API_KEY")
            env_subdomain = subdomain or os.getenv("CANNY_SUBDOMAIN")

            if not env_api_key:
                raise ValueError("API key must be provided if config is not available")
            if not env_subdomain:
                raise ValueError("Subdomain must be provided if config is not available")

            self.api_key = env_api_key
            self.subdomain = env_subdomain

        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = f"https://{self.subdomain}.canny.io"
        self.api_url = f"{CannyClient.BASE_URL}"

        # Create async HTTP client with default timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            base_url=self.api_url,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> CannyClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def _build_request_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Build request payload with API key.

        Args:
            **kwargs: Additional parameters for the request.

        Returns:
            Request payload dictionary.
        """
        return {
            "apiKey": self.api_key,
            **kwargs,
        }

    @async_retry_with_backoff(
        exceptions=(httpx.HTTPError, httpx.RequestError, CannyAPIError),
        max_retries=3,
        base_delay=2.0,
    )
    async def _make_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Dict[str, Any]:
        """
        Make an async HTTP request to Canny.io API.

        Args:
            endpoint: API endpoint path (e.g., "/posts/list").
            data: Request payload (API key will be added automatically).
            method: HTTP method (default: POST).

        Returns:
            JSON response from API.

        Raises:
            CannyAPIError: If API returns an error.
        """
        if data is None:
            data = {}

        request_data = self._build_request_data(**data)

        try:
            logger.debug(
                f"Making {method} request to {endpoint}",
                extra={
                    "endpoint": endpoint,
                    "method": method,
                },
            )

            response = await self.client.request(
                method=method,
                url=endpoint,
                json=request_data,
            )

            response.raise_for_status()

            # Canny API returns JSON
            result = response.json()

            # Check for API-level errors in response
            if "error" in result:
                error_msg = result.get("error", "Unknown API error")
                raise CannyAPIError(
                    f"Canny API error: {error_msg}",
                    status_code=response.status_code,
                    response=result,
                )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} for {endpoint}: {e.response.text}",
                extra={
                    "endpoint": endpoint,
                    "status_code": e.response.status_code,
                },
            )
            raise CannyAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(
                f"Request error for {endpoint}: {str(e)}",
                extra={"endpoint": endpoint},
            )
            raise CannyAPIError(f"Request failed: {str(e)}") from e

    def _parse_post(self, post_data: Dict[str, Any]) -> FeedbackPost:
        """
        Parse Canny.io post data into FeedbackPost model.

        Args:
            post_data: Raw post data from Canny API.

        Returns:
            FeedbackPost model instance.
        """
        # Parse tags (can be array or comma-separated string)
        tags = post_data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif not isinstance(tags, list):
            tags = []

        # Parse timestamps
        created_at = (
            datetime.fromisoformat(post_data["created"].replace("Z", "+00:00"))
            if post_data.get("created")
            else datetime.now(UTC)
        )
        updated_at = (
            datetime.fromisoformat(post_data["updated"].replace("Z", "+00:00"))
            if post_data.get("updated")
            else datetime.now(UTC)
        )

        return FeedbackPost(
            post_id=post_data["id"],
            board_id=post_data.get("boardID", ""),
            title=post_data.get("title", ""),
            content=post_data.get("details", "") or post_data.get("markdown", ""),
            author_id=post_data.get("authorID"),
            author_name=post_data.get("author", {}).get("name") if isinstance(post_data.get("author"), dict) else None,
            created_at=created_at,
            updated_at=updated_at,
            votes=post_data.get("voteCount", 0) or post_data.get("votes", 0) or 0,
            comments_count=post_data.get("commentCount", 0) or post_data.get("comments", 0) or 0,
            status=post_data.get("status", "open"),
            url=post_data.get("url"),
            tags=tags,
            collected_at=datetime.now(UTC),
        )

    async def list_posts(
        self,
        board_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
        status: Optional[str] = None,
    ) -> List[FeedbackPost]:
        """
        List posts from Canny.io with pagination support.

        Args:
            board_id: Board ID to filter posts (defaults to config board_id).
            limit: Maximum number of posts to retrieve (default: 100, max: 100).
            skip: Number of posts to skip for pagination (default: 0).
            status: Filter by post status (e.g., "open", "complete", "in progress").

        Returns:
            List of FeedbackPost instances.

        Raises:
            CannyAPIError: If API request fails.
        """
        # Get default board_id from config if not provided
        if board_id is None:
            try:
                settings = get_settings()
                board_id = settings.canny.board_id
            except SettingsError as e:
                logger.warning(
                    "SettingsError while loading Canny board_id; "
                    "falling back to CANNY_BOARD_ID env var. "
                    "Original error: %s",
                    str(e),
                )
                env_board_id = os.getenv("CANNY_BOARD_ID")
                if not env_board_id:
                    raise ValueError(
                        "board_id must be provided if config is not available. "
                        "Set CANNY_BOARD_ID in your environment or .env file."
                    ) from e
                board_id = env_board_id
            except Exception:
                raise ValueError("board_id must be provided if config is not available")

        # Validate limit
        limit = min(max(1, limit), 100)  # Clamp between 1 and 100

        request_data: Dict[str, Any] = {
            "limit": limit,
            "skip": skip,
        }

        # Add optional filters
        if board_id:
            request_data["boardID"] = board_id
        if status:
            request_data["status"] = status

        logger.info(
            f"Listing posts from board {board_id} (limit={limit}, skip={skip})",
            extra={
                "board_id": board_id,
                "limit": limit,
                "skip": skip,
                "status": status,
            },
        )

        response = await self._make_request("/posts/list", data=request_data)

        # Canny API returns posts in a "posts" array
        posts_data = response.get("posts", [])
        posts = [self._parse_post(post_data) for post_data in posts_data]

        logger.info(
            f"Retrieved {len(posts)} posts from Canny.io",
            extra={
                "board_id": board_id,
                "count": len(posts),
            },
        )

        return posts

    async def get_post_details(self, post_id: str) -> FeedbackPost:
        """
        Retrieve detailed information for a specific post.

        Args:
            post_id: Canny.io post ID.

        Returns:
            FeedbackPost instance with detailed information.

        Raises:
            CannyAPIError: If API request fails or post not found.
            ValidationError: If post_id is invalid.
        """
        # Validate post_id
        post_id = validate_post_id(post_id)

        logger.info(
            f"Retrieving post details for {post_id}",
            extra={"post_id": post_id},
        )

        response = await self._make_request("/posts/retrieve", data={"id": post_id})

        # Canny API returns post directly in response
        post_data = response
        if not post_data or "id" not in post_data:
            raise CannyAPIError(f"Post {post_id} not found", response=response)

        post = self._parse_post(post_data)

        logger.info(
            f"Retrieved post details: {post.title[:50]}...",
            extra={"post_id": post_id},
        )

        return post

    async def post_comment(
        self,
        post_id: str,
        value: str,
        author_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post a comment to a Canny.io feedback post.

        Args:
            post_id: Canny.io post ID to comment on.
            value: Comment text/content.
            author_id: Author ID for the comment (defaults to admin user from config).

        Returns:
            Comment response from API (typically contains comment ID).

        Raises:
            CannyAPIError: If API request fails.
            ValidationError: If post_id is invalid.
        """
        # Validate post_id
        post_id = validate_post_id(post_id)

        # Validate comment value
        if not value or not value.strip():
            raise ValidationError("Comment value cannot be empty")

        # Get default author_id from config if not provided
        if author_id is None:
            try:
                # Note: CANNY_ADMIN_USER_ID is not in settings, but could be added
                # For now, raise if not provided
                raise ValueError("author_id must be provided")
            except Exception:
                raise ValueError("author_id must be provided if config is not available")

        request_data = {
            "postID": post_id,
            "value": value.strip(),
            "authorID": author_id,
        }

        logger.info(
            f"Posting comment to post {post_id}",
            extra={
                "post_id": post_id,
                "author_id": author_id,
            },
        )

        response = await self._make_request("/comments/create", data=request_data)

        logger.info(
            f"Successfully posted comment to post {post_id}",
            extra={"post_id": post_id},
        )

        return response


__all__ = [
    "CannyClient",
    "CannyAPIError",
]

