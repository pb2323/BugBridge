"""Feedback Collection Agent for collecting posts from Canny.io"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from bugbridge.integrations.canny import CannyAPIClient
from bugbridge.models.feedback import FeedbackPost
from bugbridge.database.models import FeedbackPostDB
from bugbridge.database.connection import AsyncSessionLocal
from bugbridge.config import config

logger = logging.getLogger(__name__)


class FeedbackCollectionAgent:
    """Agent responsible for collecting feedback from Canny.io"""
    
    def __init__(self):
        """Initialize the Feedback Collection Agent"""
        self.canny_client = CannyAPIClient()
        self.board_id = config.canny.board_id
    
    async def close(self):
        """Close resources"""
        await self.canny_client.close()
    
    async def collect_new_posts(
        self,
        limit: int = 100,
        skip: int = 0
    ) -> List[FeedbackPost]:
        """Collect new posts from Canny.io
        
        Args:
            limit: Maximum number of posts to fetch
            skip: Number of posts to skip (for pagination)
        
        Returns:
            List of new FeedbackPost models
        """
        logger.info(f"Collecting posts from Canny.io (limit={limit}, skip={skip})")
        
        # Fetch posts from Canny.io
        posts = await self.canny_client.list_posts_as_models(
            board_id=self.board_id,
            limit=limit,
            skip=skip
        )
        
        logger.info(f"Fetched {len(posts)} posts from Canny.io")
        
        # Filter out posts that already exist in database
        new_posts = await self._filter_new_posts(posts)
        
        logger.info(f"Found {len(new_posts)} new posts to process")
        
        return new_posts
    
    async def _filter_new_posts(self, posts: List[FeedbackPost]) -> List[FeedbackPost]:
        """Filter out posts that already exist in database
        
        Args:
            posts: List of FeedbackPost models
        
        Returns:
            List of new posts not in database
        """
        if not posts:
            return []
        
        async with AsyncSessionLocal() as session:
            # Get all post IDs from the fetched posts
            post_ids = [post.post_id for post in posts]
            
            # Query database for existing posts
            result = await session.execute(
                select(FeedbackPostDB.canny_post_id).where(
                    FeedbackPostDB.canny_post_id.in_(post_ids)
                )
            )
            existing_post_ids = set(row[0] for row in result.fetchall())
            
            # Filter out existing posts
            new_posts = [
                post for post in posts 
                if post.post_id not in existing_post_ids
            ]
            
            return new_posts
    
    async def save_posts_to_database(self, posts: List[FeedbackPost]) -> int:
        """Save feedback posts to database
        
        Args:
            posts: List of FeedbackPost models to save
        
        Returns:
            Number of posts saved
        """
        if not posts:
            return 0
        
        logger.info(f"Saving {len(posts)} posts to database")
        
        async with AsyncSessionLocal() as session:
            for post in posts:
                # Convert Pydantic model to SQLAlchemy model
                db_post = FeedbackPostDB(
                    canny_post_id=post.post_id,
                    board_id=post.board_id,
                    title=post.title,
                    content=post.content,
                    author_id=post.author_id,
                    author_name=post.author_name,
                    votes=post.votes,
                    comments_count=post.comments_count,
                    status=post.status,
                    url=post.url,
                    tags=post.tags,
                    collected_at=post.collected_at,
                    created_at=post.created_at,
                    updated_at=post.updated_at
                )
                
                session.add(db_post)
            
            await session.commit()
        
        logger.info(f"Successfully saved {len(posts)} posts to database")
        
        return len(posts)
    
    async def collect_and_save(
        self,
        limit: int = 100,
        skip: int = 0
    ) -> List[FeedbackPost]:
        """Collect new posts and save them to database
        
        Args:
            limit: Maximum posts to fetch
            skip: Pagination offset
        
        Returns:
            List of newly collected and saved posts
        """
        # Collect new posts
        new_posts = await self.collect_new_posts(limit, skip)
        
        # Save to database
        if new_posts:
            await self.save_posts_to_database(new_posts)
        
        return new_posts
    
    async def backfill_historical_data(self, max_posts: int = 1000) -> int:
        """Backfill historical posts from Canny.io
        
        Args:
            max_posts: Maximum number of historical posts to fetch
        
        Returns:
            Total number of posts collected
        """
        logger.info(f"Starting historical backfill (max_posts={max_posts})")
        
        total_collected = 0
        batch_size = 100
        skip = 0
        
        while skip < max_posts:
            # Collect batch
            new_posts = await self.collect_and_save(limit=batch_size, skip=skip)
            
            # If no new posts, we've reached the end
            if not new_posts:
                break
            
            total_collected += len(new_posts)
            skip += batch_size
            
            logger.info(f"Backfill progress: {total_collected} posts collected")
        
        logger.info(f"Backfill complete: {total_collected} total posts collected")
        
        return total_collected
