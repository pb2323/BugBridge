"""
Scheduler Service for Feedback Collection and Report Generation

Manages scheduled collection of feedback posts from Canny.io and
daily report generation using APScheduler.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bugbridge.agents.collection import collect_feedback_batch
from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger
from bugbridge.workflows.reporting import execute_reporting_workflow

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


class ReportGenerationScheduler:
    """
    Scheduler service for automatic daily report generation.

    Uses APScheduler with cron trigger to generate reports at configured times.
    """

    def __init__(
        self,
        schedule_cron: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        """
        Initialize report generation scheduler.

        Args:
            schedule_cron: Cron expression for report schedule (defaults to config).
            enabled: Whether reporting is enabled (defaults to config).
        """
        try:
            settings = get_settings()
            reporting_settings = settings.reporting
            self.schedule_cron = schedule_cron or reporting_settings.schedule_cron
            self.enabled = enabled if enabled is not None else reporting_settings.enabled
        except Exception:
            if schedule_cron is None:
                raise ValueError("schedule_cron must be provided if config is not available")
            if enabled is None:
                enabled = True
            self.schedule_cron = schedule_cron
            self.enabled = enabled

        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_id = "report_generation_job"

    async def _generate_report_job(self) -> None:
        """Scheduled job function to generate daily report."""
        if not self.enabled:
            logger.debug("Report generation is disabled, skipping scheduled job")
            return

        logger.info(
            "Starting scheduled report generation",
            extra={
                "schedule_cron": self.schedule_cron,
            },
        )

        try:
            # Execute reporting workflow (defaults to yesterday's date)
            result = await execute_reporting_workflow()

            if result.get("report_id"):
                logger.info(
                    f"Successfully generated daily report (ID: {result['report_id']})",
                    extra={
                        "report_id": result["report_id"],
                        "report_date": result.get("report_date"),
                    },
                )
            else:
                errors = result.get("errors", [])
                logger.error(
                    f"Failed to generate report: {errors}",
                    extra={
                        "errors": errors,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error in scheduled report generation: {str(e)}",
                exc_info=True,
            )

    def start(self) -> None:
        """Start the scheduler and register the report generation job."""
        if not self.enabled:
            logger.info("Report generation is disabled, scheduler will not start")
            return

        if self.scheduler is not None:
            logger.warning("Report scheduler is already running")
            return

        logger.info(
            f"Starting report generation scheduler (cron: {self.schedule_cron})",
            extra={
                "schedule_cron": self.schedule_cron,
            },
        )

        # Create async scheduler
        self.scheduler = AsyncIOScheduler()

        # Parse cron expression and add job with cron trigger
        # Cron format: "minute hour day month day_of_week"
        # Example: "0 9 * * *" = Daily at 9:00 AM
        try:
            cron_parts = self.schedule_cron.split()
            if len(cron_parts) != 5:
                raise ValueError(f"Invalid cron expression: {self.schedule_cron}. Expected format: 'minute hour day month day_of_week'")

            minute, hour, day, month, day_of_week = cron_parts

            # Create cron trigger from crontab string
            # CronTrigger.from_crontab() parses standard cron format
            trigger = CronTrigger.from_crontab(self.schedule_cron)

            # Add job with cron trigger
            self.scheduler.add_job(
                func=self._generate_report_job,
                trigger=trigger,
                id=self.job_id,
                name="Daily Report Generation Job",
                replace_existing=True,
            )

            # Start scheduler
            self.scheduler.start()

            logger.info(
                "Report generation scheduler started",
                extra={
                    "schedule_cron": self.schedule_cron,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to start report scheduler: {str(e)}",
                extra={"schedule_cron": self.schedule_cron},
                exc_info=True,
            )
            raise

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler is None:
            logger.warning("Report scheduler is not running")
            return

        logger.info("Stopping report generation scheduler")

        self.scheduler.shutdown(wait=True)
        self.scheduler = None

        logger.info("Report generation scheduler stopped")

    async def trigger_report_now(self) -> dict[str, Any]:
        """
        Manually trigger a report generation job immediately.

        Returns:
            Report generation result dictionary.
        """
        logger.info("Manually triggering report generation")

        result = await execute_reporting_workflow()
        return {
            "success": result.get("report_id") is not None,
            "report_id": result.get("report_id"),
            "report_date": result.get("report_date"),
            "errors": result.get("errors", []),
        }

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


# Global report scheduler instance
_report_scheduler_instance: Optional[ReportGenerationScheduler] = None


def get_report_scheduler() -> ReportGenerationScheduler:
    """
    Get or create the global report scheduler instance.

    Returns:
        ReportGenerationScheduler instance.
    """
    global _report_scheduler_instance

    if _report_scheduler_instance is None:
        _report_scheduler_instance = ReportGenerationScheduler()

    return _report_scheduler_instance


__all__ = [
    "FeedbackCollectionScheduler",
    "get_scheduler",
    "ReportGenerationScheduler",
    "get_report_scheduler",
]

