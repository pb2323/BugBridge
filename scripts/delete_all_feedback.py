#!/usr/bin/env python3
"""
Delete all feedback posts and related data from the database.

This script will delete:
- All feedback posts
- All analysis results
- All Jira tickets
- All workflow states
- All notifications
- All reports

Use with caution! This is irreversible.

Usage:
    python scripts/delete_all_feedback.py          # Interactive mode (requires confirmation)
    python scripts/delete_all_feedback.py --force  # Skip confirmation
    python scripts/delete_all_feedback.py --dry-run # Preview what would be deleted
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.database.connection import get_session_context
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    JiraTicket as DBJiraTicket,
    AnalysisResult,
    WorkflowState,
    Notification,
    Report,
)
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def delete_all_feedback_data(dry_run: bool = False, force: bool = False) -> dict:
    """
    Delete all feedback posts and related data from the database.
    
    Args:
        dry_run: If True, only count records without deleting.
    
    Returns:
        Dictionary with deletion statistics.
    """
    stats = {
        "feedback_posts": 0,
        "analysis_results": 0,
        "jira_tickets": 0,
        "workflow_states": 0,
        "notifications": 0,
        "reports": 0,
    }
    
    async with get_session_context() as session:
        # Count existing records
        logger.info("Counting existing records...")
        
        # Get actual counts
        feedback_result = await session.execute(select(DBFeedbackPost))
        feedback_posts = feedback_result.scalars().all()
        stats["feedback_posts"] = len(feedback_posts)
        
        analysis_result = await session.execute(select(AnalysisResult))
        analysis_results = analysis_result.scalars().all()
        stats["analysis_results"] = len(analysis_results)
        
        jira_result = await session.execute(select(DBJiraTicket))
        jira_tickets = jira_result.scalars().all()
        stats["jira_tickets"] = len(jira_tickets)
        
        workflow_result = await session.execute(select(WorkflowState))
        workflow_states = workflow_result.scalars().all()
        stats["workflow_states"] = len(workflow_states)
        
        notification_result = await session.execute(select(Notification))
        notifications = notification_result.scalars().all()
        stats["notifications"] = len(notifications)
        
        report_result = await session.execute(select(Report))
        reports = report_result.scalars().all()
        stats["reports"] = len(reports)
        
        logger.info(f"Found {stats['feedback_posts']} feedback posts")
        logger.info(f"Found {stats['analysis_results']} analysis results")
        logger.info(f"Found {stats['jira_tickets']} Jira tickets")
        logger.info(f"Found {stats['workflow_states']} workflow states")
        logger.info(f"Found {stats['notifications']} notifications")
        logger.info(f"Found {stats['reports']} reports")
        
        if dry_run:
            logger.info("DRY RUN - No data will be deleted")
            return stats
        
        # Confirm deletion
        print("\n" + "="*60)
        print("⚠️  WARNING: You are about to DELETE ALL feedback data!")
        print("="*60)
        print(f"  - {stats['feedback_posts']} feedback posts")
        print(f"  - {stats['analysis_results']} analysis results")
        print(f"  - {stats['jira_tickets']} Jira tickets")
        print(f"  - {stats['workflow_states']} workflow states")
        print(f"  - {stats['notifications']} notifications")
        print(f"  - {stats['reports']} reports")
        print("="*60)
        print("\nThis action is IRREVERSIBLE!\n")
        
        if not force:
            response = input("Type 'DELETE' to confirm: ")
            if response != "DELETE":
                logger.info("Deletion cancelled by user")
                return {"cancelled": True, **stats}
        
        logger.info("Starting deletion...")
        
        # Delete in correct order (respecting foreign keys)
        # 1. Delete notifications (references feedback_post_id and jira_ticket_id)
        if stats["notifications"] > 0:
            logger.info("Deleting notifications...")
            await session.execute(delete(Notification))
            logger.info(f"✅ Deleted {stats['notifications']} notifications")
        
        # 2. Delete Jira tickets (references feedback_post_id)
        if stats["jira_tickets"] > 0:
            logger.info("Deleting Jira tickets...")
            await session.execute(delete(DBJiraTicket))
            logger.info(f"✅ Deleted {stats['jira_tickets']} Jira tickets")
        
        # 3. Delete analysis results (references feedback_post_id)
        if stats["analysis_results"] > 0:
            logger.info("Deleting analysis results...")
            await session.execute(delete(AnalysisResult))
            logger.info(f"✅ Deleted {stats['analysis_results']} analysis results")
        
        # 4. Delete workflow states (references feedback_post_id via JSON)
        if stats["workflow_states"] > 0:
            logger.info("Deleting workflow states...")
            await session.execute(delete(WorkflowState))
            logger.info(f"✅ Deleted {stats['workflow_states']} workflow states")
        
        # 5. Delete reports (standalone table)
        if stats["reports"] > 0:
            logger.info("Deleting reports...")
            await session.execute(delete(Report))
            logger.info(f"✅ Deleted {stats['reports']} reports")
        
        # 6. Delete feedback posts (parent table)
        if stats["feedback_posts"] > 0:
            logger.info("Deleting feedback posts...")
            await session.execute(delete(DBFeedbackPost))
            logger.info(f"✅ Deleted {stats['feedback_posts']} feedback posts")
        
        # Commit all deletions
        await session.commit()
        
        logger.info("✅ All feedback data deleted successfully")
        
    return {"deleted": True, **stats}


async def main():
    """Main entry point."""
    # Check for flags
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv
    
    try:
        if dry_run:
            logger.info("Running in DRY RUN mode")
        if force:
            logger.info("Running in FORCE mode (skipping confirmation)")
        
        result = await delete_all_feedback_data(dry_run=dry_run, force=force)
        
        if result.get("cancelled"):
            print("\n❌ Deletion cancelled")
            sys.exit(1)
        
        if result.get("deleted"):
            print("\n" + "="*60)
            print("✅ SUCCESS: All feedback data has been deleted")
            print("="*60)
            print(f"  - Deleted {result['feedback_posts']} feedback posts")
            print(f"  - Deleted {result['analysis_results']} analysis results")
            print(f"  - Deleted {result['jira_tickets']} Jira tickets")
            print(f"  - Deleted {result['workflow_states']} workflow states")
            print(f"  - Deleted {result['notifications']} notifications")
            print(f"  - Deleted {result['reports']} reports")
            print("="*60)
            print("\nYou can now use the 'Refresh from Canny' button in the UI")
            print("to fetch and process all posts fresh from Canny.io\n")
        else:
            print("\n📊 DRY RUN Results:")
            print(f"  - {result['feedback_posts']} feedback posts would be deleted")
            print(f"  - {result['analysis_results']} analysis results would be deleted")
            print(f"  - {result['jira_tickets']} Jira tickets would be deleted")
            print(f"  - {result['workflow_states']} workflow states would be deleted")
            print(f"  - {result['notifications']} notifications would be deleted")
            print(f"  - {result['reports']} reports would be deleted")
            print("\nRun without --dry-run to actually delete the data\n")
        
    except Exception as e:
        logger.error(f"Error during deletion: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

