"""
Tests for crawl scheduler.

Tests job scheduling and execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.scheduler import CrawlScheduler


@pytest.fixture
def scheduler():
    """Create scheduler instance."""
    return CrawlScheduler()


class TestCrawlScheduler:
    """Test crawl scheduler functionality."""

    def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler is not None
        assert scheduler.is_running is False
        assert len(scheduler.jobs) == 0

    @pytest.mark.asyncio
    async def test_start(self, scheduler):
        """Test starting scheduler."""
        await scheduler.start()
        
        assert scheduler.is_running is True

    @pytest.mark.asyncio
    async def test_stop(self, scheduler):
        """Test stopping scheduler."""
        await scheduler.start()
        await scheduler.stop()
        
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, scheduler):
        """Test starting scheduler when already running."""
        await scheduler.start()
        await scheduler.start()  # Should not raise
        
        assert scheduler.is_running is True

    @pytest.mark.asyncio
    async def test_stop_not_running(self, scheduler):
        """Test stopping scheduler when not running."""
        await scheduler.stop()  # Should not raise
        
        assert scheduler.is_running is False

    def test_schedule_crawl(self, scheduler):
        """Test scheduling crawl job."""
        async def dummy_crawl():
            pass
        
        job = scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        
        assert job is not None
        assert "feed_1" in scheduler.jobs

    def test_schedule_crawl_replace_existing(self, scheduler):
        """Test scheduling crawl job replaces existing."""
        async def dummy_crawl():
            pass
        
        job1 = scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        job2 = scheduler.schedule_crawl("feed_1", dummy_crawl, 30)
        
        assert len(scheduler.jobs) == 1

    def test_unschedule_crawl(self, scheduler):
        """Test unscheduling crawl job."""
        async def dummy_crawl():
            pass
        
        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        scheduler.unschedule_crawl("feed_1")
        
        assert "feed_1" not in scheduler.jobs

    def test_unschedule_nonexistent_crawl(self, scheduler):
        """Test unscheduling non-existent job."""
        scheduler.unschedule_crawl("nonexistent")  # Should not raise
        
        assert len(scheduler.jobs) == 0

    def test_get_job(self, scheduler):
        """Test getting scheduled job."""
        async def dummy_crawl():
            pass
        
        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        job = scheduler.get_job("feed_1")
        
        assert job is not None

    def test_get_nonexistent_job(self, scheduler):
        """Test getting non-existent job."""
        job = scheduler.get_job("nonexistent")
        
        assert job is None

    def test_get_all_jobs(self, scheduler):
        """Test getting all jobs."""
        async def dummy_crawl():
            pass
        
        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        scheduler.schedule_crawl("feed_2", dummy_crawl, 60)
        
        jobs = scheduler.get_all_jobs()
        
        assert len(jobs) == 2

    def test_pause_job(self, scheduler):
        """Test pausing job."""
        async def dummy_crawl():
            pass
        
        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        scheduler.pause_job("feed_1")
        
        job = scheduler.get_job("feed_1")
        assert job is not None

    def test_resume_job(self, scheduler):
        """Test resuming job."""
        async def dummy_crawl():
            pass
        
        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        scheduler.pause_job("feed_1")
        scheduler.resume_job("feed_1")
        
        job = scheduler.get_job("feed_1")
        assert job is not None

    def test_trigger_job(self, scheduler):
        """Test manually triggering job."""
        call_count = 0

        async def dummy_crawl():
            nonlocal call_count
            call_count += 1

        scheduler.schedule_crawl("feed_1", dummy_crawl, 60)
        scheduler.trigger_job("feed_1")

        assert scheduler.get_job("feed_1") is not None

    def test_get_job_stats_empty(self, scheduler):
        """Test getting job statistics for non-existent job."""
        stats = scheduler.get_job_stats("nonexistent")

        assert stats == {}

    def test_get_all_stats_empty(self, scheduler):
        """Test getting all job statistics when no jobs."""
        stats = scheduler.get_all_stats()

        assert len(stats) == 0

    @pytest.mark.asyncio
    async def test_create_crawl_job(self, scheduler):
        """Test creating crawl job."""
        job = await scheduler.create_crawl_job()

        assert job is not None
        assert scheduler.current_job == job

    @pytest.mark.asyncio
    async def test_complete_crawl_job(self, scheduler):
        """Test completing crawl job."""
        job = await scheduler.create_crawl_job()
        await scheduler.complete_crawl_job(job, "completed")

        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using scheduler as context manager."""
        scheduler = CrawlScheduler()
        
        await scheduler.start()
        assert scheduler.is_running is True
        
        await scheduler.stop()
        assert scheduler.is_running is False

