#!/usr/bin/env python3
"""
Process Existing Feedback Posts Through Workflow

This script processes all existing feedback posts that haven't been analyzed yet
through the complete workflow (bug detection, sentiment analysis, priority scoring, Jira creation).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bugbridge.agents.collection import process_post_through_workflow
from bugbridge.database.connection import get_session_context
from bugbridge.database.models import AnalysisResult, FeedbackPost as DBFeedbackPost
from bugbridge.models.feedback import FeedbackPost
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def convert_db_post_to_pydantic(db_post: DBFeedbackPost) -> FeedbackPost:
    """Convert database FeedbackPost model to Pydantic FeedbackPost model."""
    from pydantic import HttpUrl
    
    url = HttpUrl(db_post.url) if db_post.url else None
    
    return FeedbackPost(
        post_id=db_post.canny_post_id,
        board_id=db_post.board_id,
        title=db_post.title,
        content=db_post.content,
        author_id=db_post.author_id,
        author_name=db_post.author_name,
        created_at=db_post.created_at,
        updated_at=db_post.updated_at,
        votes=db_post.votes,
        comments_count=db_post.comments_count,
        status=db_post.status,
        url=url,
        tags=db_post.tags or [],
        collected_at=db_post.collected_at,
    )


async def find_unprocessed_posts() -> list[DBFeedbackPost]:
    """
    Find all feedback posts that don't have analysis results yet.
    
    Returns:
        List of unprocessed FeedbackPost database models.
    """
    async with get_session_context() as session:
        # Find all posts without analysis results
        # Use LEFT JOIN to find posts where analysis_results is NULL
        query = (
            select(DBFeedbackPost)
            .outerjoin(AnalysisResult, DBFeedbackPost.id == AnalysisResult.feedback_post_id)
            .where(AnalysisResult.id.is_(None))
            .options(selectinload(DBFeedbackPost.analysis_results))
        )
        
        result = await session.execute(query)
        posts = result.unique().scalars().all()
        
        return posts


async def process_all_existing_posts(
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Process all existing unprocessed feedback posts through the workflow.
    
    Args:
        limit: Maximum number of posts to process (None for all).
        dry_run: If True, only count posts without processing.
    
    Returns:
        Dictionary with processing statistics.
    """
    logger.info("Finding unprocessed feedback posts...")
    
    unprocessed_posts = await find_unprocessed_posts()
    total_unprocessed = len(unprocessed_posts)
    
    if limit:
        unprocessed_posts = unprocessed_posts[:limit]
    
    logger.info(
        f"Found {total_unprocessed} unprocessed posts"
        + (f" (processing first {len(unprocessed_posts)})" if limit else "")
    )
    
    if dry_run:
        return {
            "total_unprocessed": total_unprocessed,
            "would_process": len(unprocessed_posts),
            "dry_run": True,
        }
    
    if not unprocessed_posts:
        logger.info("No unprocessed posts found. All posts have been analyzed.")
        return {
            "total_unprocessed": 0,
            "processed_count": 0,
            "successful_processing": 0,
            "jira_tickets_created": 0,
            "errors": [],
        }
    
    logger.info(f"Processing {len(unprocessed_posts)} posts through workflow...")
    
    processing_results = []
    successful_count = 0
    jira_tickets_created = 0
    
    for i, db_post in enumerate(unprocessed_posts, 1):
        try:
            logger.info(
                f"[{i}/{len(unprocessed_posts)}] Processing post: {db_post.title[:50]}...",
                extra={
                    "post_id": db_post.canny_post_id,
                    "progress": f"{i}/{len(unprocessed_posts)}",
                },
            )
            
            # Convert DB model to Pydantic model
            pydantic_post = await convert_db_post_to_pydantic(db_post)
            
            # Process through workflow
            result = await process_post_through_workflow(pydantic_post)
            
            processing_results.append(result)
            
            if result.get("success"):
                successful_count += 1
                if result.get("jira_ticket_id"):
                    jira_tickets_created += 1
                    logger.info(
                        f"✅ Processed post {db_post.canny_post_id} - "
                        f"Priority: {result.get('priority_score')}, "
                        f"Jira: {result.get('jira_ticket_id')}"
                    )
                else:
                    logger.info(
                        f"✅ Processed post {db_post.canny_post_id} - "
                        f"Priority: {result.get('priority_score')} (below threshold)"
                    )
            else:
                logger.error(
                    f"❌ Failed to process post {db_post.canny_post_id}: {result.get('error')}"
                )
        
        except Exception as e:
            error_msg = f"Unexpected error processing post {db_post.canny_post_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            processing_results.append({
                "success": False,
                "post_id": db_post.canny_post_id,
                "error": error_msg,
            })
    
    logger.info(
        f"\n{'='*60}\n"
        f"Processing Complete!\n"
        f"{'='*60}\n"
        f"Total unprocessed: {total_unprocessed}\n"
        f"Processed: {len(processing_results)}\n"
        f"Successful: {successful_count}\n"
        f"Jira tickets created: {jira_tickets_created}\n"
        f"{'='*60}"
    )
    
    return {
        "total_unprocessed": total_unprocessed,
        "processed_count": len(processing_results),
        "successful_processing": successful_count,
        "jira_tickets_created": jira_tickets_created,
        "errors": [r.get("error") for r in processing_results if not r.get("success")],
    }


async def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process existing feedback posts through the workflow"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of posts to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count unprocessed posts without processing them",
    )
    
    args = parser.parse_args()
    
    try:
        results = await process_all_existing_posts(
            limit=args.limit,
            dry_run=args.dry_run,
        )
        
        if args.dry_run:
            print(f"\n📊 Dry Run Results:")
            print(f"   Total unprocessed posts: {results['total_unprocessed']}")
            print(f"   Would process: {results['would_process']}")
        else:
            print(f"\n📊 Processing Results:")
            print(f"   Total unprocessed: {results['total_unprocessed']}")
            print(f"   Processed: {results['processed_count']}")
            print(f"   Successful: {results['successful_processing']}")
            print(f"   Jira tickets created: {results['jira_tickets_created']}")
            if results.get("errors"):
                print(f"   Errors: {len(results['errors'])}")
        
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

