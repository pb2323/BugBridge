"""
Scheduler Service for Feedback Collection

Manages scheduled collection of feedback posts from Canny.io using APScheduler.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bugbridge.agents.collection import collect_feedback_batch
from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class FeedbackCollectionScheduler:
    """
    Scheduler service for automatic feedback collection from Canny.io.

    Uses APScheduler to periodically collect feedback posts based on
    configured sync intervals.
    """

    def __init__(
        self,
        sync_interval_minutes: Optional[int] = None,
        board_id: Optional[str] = None,
    ):
        """
        Initialize feedback collection scheduler.

        Args:
            sync_interval_minutes: Collection interval in minutes (defaults to config).
            board_id: Board ID to collect from (defaults to config).
        """
        try:
            settings = get_settings()
            self.sync_interval_minutes = sync_interval_minutes or settings.canny.sync_interval_minutes
            self.board_id = board_id or settings.canny.board_id
        except Exception:
            if sync_interval_minutes is None:
                raise ValueError("sync_interval_minutes must be provided if config is not available")
            if board_id is None:
                raise ValueError("board_id must be provided if config is not available")
            self.sync_interval_minutes = sync_interval_minutes
            self.board_id = board_id

        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_id = "feedback_collection_job"

    async def _collect_feedback_job(self) -> None:
        """Scheduled job function to collect feedback."""
        logger.info(
            "Starting scheduled feedback collection",
            extra={
                "board_id": self.board_id,
                "interval_minutes": self.sync_interval_minutes,
            },
        )

        try:
            result = await collect_feedback_batch(
                board_id=self.board_id,
                limit=100,  # Collect up to 100 posts per run
                status=None,  # Collect all statuses
            )

            if result["success"]:
                logger.info(
                    f"Successfully collected {result['collected_count']} new posts",
                    extra={
                        "collected_count": result["collected_count"],
                        "board_id": self.board_id,
                    },
                )
            else:
                logger.error(
                    f"Failed to collect feedback: {result.get('error')}",
                    extra={
                        "error": result.get("error"),
                        "board_id": self.board_id,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error in scheduled feedback collection: {str(e)}",
                extra={"board_id": self.board_id},
                exc_info=True,
            )

    def start(self) -> None:
        """Start the scheduler and register the collection job."""
        if self.scheduler is not None:
            logger.warning("Scheduler is already running")
            return

        logger.info(
            f"Starting feedback collection scheduler (interval: {self.sync_interval_minutes} minutes)",
            extra={
                "sync_interval_minutes": self.sync_interval_minutes,
                "board_id": self.board_id,
            },
        )

        # Create async scheduler
        self.scheduler = AsyncIOScheduler()

        # Add job with interval trigger
        self.scheduler.add_job(
            func=self._collect_feedback_job,
            trigger=IntervalTrigger(minutes=self.sync_interval_minutes),
            id=self.job_id,
            name="Feedback Collection Job",
            replace_existing=True,
        )

        # Start scheduler
        self.scheduler.start()

        logger.info(
            "Feedback collection scheduler started",
            extra={
                "sync_interval_minutes": self.sync_interval_minutes,
                "board_id": self.board_id,
            },
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler is None:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping feedback collection scheduler")

        self.scheduler.shutdown(wait=True)
        self.scheduler = None

        logger.info("Feedback collection scheduler stopped")

    async def trigger_collection_now(self) -> dict[str, Any]:
        """
        Manually trigger a feedback collection job immediately.

        Returns:
            Collection result dictionary.
        """
        logger.info("Manually triggering feedback collection")

        return await collect_feedback_batch(
            board_id=self.board_id,
            limit=100,
            status=None,
        )

    def is_running(self) -> bool:
        """
        Check if the scheduler is currently running.

        Returns:
            True if scheduler is running, False otherwise.
        """
        return self.scheduler is not None and self.scheduler.running

    def get_next_run_time(self) -> Optional[str]:
        """
        Get the next scheduled run time.

        Returns:
            ISO format string of next run time, or None if not scheduled.
        """
        if self.scheduler is None:
            return None

        job = self.scheduler.get_job(self.job_id)
        if job is None:
            return None

        next_run = job.next_run_time
        if next_run is None:
            return None

        return next_run.isoformat()


# Global scheduler instance
_scheduler_instance: Optional[FeedbackCollectionScheduler] = None


def get_scheduler() -> FeedbackCollectionScheduler:
    """
    Get or create the global scheduler instance.

    Returns:
        FeedbackCollectionScheduler instance.
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = FeedbackCollectionScheduler()

    return _scheduler_instance


__all__ = [
    "FeedbackCollectionScheduler",
    "get_scheduler",
]

