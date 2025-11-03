"""
Job scheduler for coordinating crawl jobs.

Manages scheduled crawling tasks using APScheduler.
"""

import logging
from typing import Optional, Callable
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

from .config import get_settings
from .models import CrawlJob

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """
    Scheduler for managing crawl jobs.

    Coordinates periodic crawling tasks using APScheduler.
    """

    def __init__(self) -> None:
        """Initialize scheduler."""
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.jobs: dict[str, Job] = {}
        self.current_job: Optional[CrawlJob] = None
        self.is_running = False

    async def start(self) -> None:
        """Start scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Crawl scheduler started")

    async def stop(self) -> None:
        """Stop scheduler gracefully."""
        if self.is_running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Crawl scheduler stopped")

    def schedule_crawl(
        self,
        feed_id: str,
        crawl_func: Callable,
        interval_minutes: int,
    ) -> Job:
        """
        Schedule periodic crawl job.

        Args:
            feed_id: Feed identifier.
            crawl_func: Async function to execute.
            interval_minutes: Interval in minutes.

        Returns:
            Job: Scheduled job.
        """
        job = self.scheduler.add_job(
            crawl_func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=feed_id,
            name=f"Crawl {feed_id}",
            replace_existing=True,
        )

        self.jobs[feed_id] = job
        logger.info(
            f"Scheduled crawl job for {feed_id} every {interval_minutes} minutes"
        )
        return job

    def unschedule_crawl(self, feed_id: str) -> None:
        """
        Unschedule crawl job.

        Args:
            feed_id: Feed identifier.
        """
        if feed_id in self.jobs:
            job = self.jobs[feed_id]
            job.remove()
            del self.jobs[feed_id]
            logger.info(f"Unscheduled crawl job for {feed_id}")

    def get_job(self, feed_id: str) -> Optional[Job]:
        """
        Get scheduled job.

        Args:
            feed_id: Feed identifier.

        Returns:
            Job or None if not found.
        """
        return self.jobs.get(feed_id)

    def get_all_jobs(self) -> list[Job]:
        """
        Get all scheduled jobs.

        Returns:
            list[Job]: All scheduled jobs.
        """
        return list(self.jobs.values())

    def pause_job(self, feed_id: str) -> None:
        """
        Pause scheduled job.

        Args:
            feed_id: Feed identifier.
        """
        job = self.get_job(feed_id)
        if job:
            job.pause()
            logger.info(f"Paused crawl job for {feed_id}")

    def resume_job(self, feed_id: str) -> None:
        """
        Resume paused job.

        Args:
            feed_id: Feed identifier.
        """
        job = self.get_job(feed_id)
        if job:
            job.resume()
            logger.info(f"Resumed crawl job for {feed_id}")

    def trigger_job(self, feed_id: str) -> None:
        """
        Manually trigger job execution.

        Args:
            feed_id: Feed identifier.
        """
        job = self.get_job(feed_id)
        if job:
            job.func()
            logger.info(f"Manually triggered crawl job for {feed_id}")

    def get_job_stats(self, feed_id: str) -> dict:
        """
        Get job statistics.

        Args:
            feed_id: Feed identifier.

        Returns:
            dict: Job statistics.
        """
        job = self.get_job(feed_id)

        if not job:
            return {}

        return {
            "feed_id": feed_id,
            "name": job.name,
            "next_run_time": (
                job.next_run_time.isoformat()
                if job.next_run_time else None
            ),
            "trigger": str(job.trigger),
            "paused": job.paused,
        }

    def get_all_stats(self) -> list[dict]:
        """
        Get statistics for all jobs.

        Returns:
            list[dict]: Statistics for all jobs.
        """
        return [self.get_job_stats(feed_id) for feed_id in self.jobs.keys()]

    async def create_crawl_job(self) -> CrawlJob:
        """
        Create new crawl job instance.

        Returns:
            CrawlJob: New crawl job.
        """
        job = CrawlJob()
        self.current_job = job
        return job

    async def complete_crawl_job(
        self,
        job: CrawlJob,
        status: str = "completed",
    ) -> None:
        """
        Mark crawl job as completed.

        Args:
            job: Crawl job to complete.
            status: Final status (completed, failed).
        """
        job.completed_at = datetime.utcnow().isoformat()
        job.status = status
        logger.info(
            f"Crawl job {job.job_id} completed with status {status}: "
            f"{job.articles_published} published, {job.articles_failed} failed"
        )
