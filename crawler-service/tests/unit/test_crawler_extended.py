"""
Extended unit tests for crawler module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.crawler import CrawlerApplication
from src.models import FeedSource, CrawlJob
from src.parser.base import ParsedArticle


class TestCrawlerApplicationExtended:
    """Extended tests for CrawlerApplication."""

    @pytest.fixture
    def crawler(self):
        """Create crawler instance."""
        return CrawlerApplication()

    @pytest.fixture
    def sample_feed(self):
        """Create sample feed source."""
        return FeedSource(
            feed_id="test-feed-1",
            name="Test Feed",
            url="https://example.com/feed.xml",
            feed_type="rss",
            timeout_seconds=30,
            enabled=True,
        )

    @pytest.fixture
    def sample_article(self):
        """Create sample article."""
        return ParsedArticle(
            title="Test Article",
            body="Test content",
            url="https://example.com/article",
            canonical_url="https://example.com/article",
            published_at=datetime.utcnow(),
            author="Test Author",
            source="Test Source",
            language="en",
            extraction_method="html",
        )

    @pytest.mark.asyncio
    async def test_init(self, crawler):
        """Test crawler initialization."""
        assert crawler.settings is not None
        assert crawler.feed_registry is not None
        assert crawler.scheduler is not None
        assert crawler.kafka_producer is not None
        assert crawler.http_fetcher is not None
        assert crawler.parser_factory is not None
        assert crawler.validator is not None
        assert crawler.dedup_engine is not None
        assert crawler.normalizer is not None
        assert crawler.metrics is not None
        assert crawler.health_manager is not None
        assert crawler.is_running is False

    @pytest.mark.asyncio
    async def test_start_success(self, crawler):
        """Test successful crawler start."""
        with patch.object(crawler.kafka_producer, 'start', new_callable=AsyncMock), \
             patch.object(crawler.scheduler, 'start', new_callable=AsyncMock):
            
            await crawler.start()
            
            assert crawler.is_running is True

    @pytest.mark.asyncio
    async def test_start_failure(self, crawler):
        """Test crawler start failure."""
        with patch.object(crawler.kafka_producer, 'start', new_callable=AsyncMock) as mock_start:
            mock_start.side_effect = Exception("Start failed")
            
            with pytest.raises(Exception):
                await crawler.start()

    @pytest.mark.asyncio
    async def test_stop_success(self, crawler):
        """Test successful crawler stop."""
        crawler.is_running = True
        
        with patch.object(crawler.scheduler, 'stop', new_callable=AsyncMock), \
             patch.object(crawler.kafka_producer, 'stop', new_callable=AsyncMock):
            
            await crawler.stop()
            
            assert crawler.is_running is False

    @pytest.mark.asyncio
    async def test_stop_error_handling(self, crawler):
        """Test crawler stop with error handling."""
        crawler.is_running = True
        
        with patch.object(crawler.scheduler, 'stop', new_callable=AsyncMock) as mock_stop:
            mock_stop.side_effect = Exception("Stop failed")
            
            # Should not raise
            await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_feed_success(self, crawler, sample_feed, sample_article):
        """Test successful feed crawl."""
        crawler.kafka_producer = MagicMock()
        crawler.kafka_producer.publish = AsyncMock()
        
        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.parser_factory, 'create_parser') as mock_parser, \
             patch.object(crawler.dedup_engine, 'is_duplicate', return_value=False), \
             patch.object(crawler.validator, 'validate', return_value=(True, 0.95, [])), \
             patch.object(crawler.normalizer, 'normalize') as mock_normalize, \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:
            
            mock_fetch.return_value = ("<html>content</html>", "text/html")
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = [sample_article]
            mock_parser.return_value = mock_parser_instance
            mock_normalize.return_value = MagicMock()
            mock_job.return_value = CrawlJob(job_id="job-1")
            
            job = await crawler.crawl_feed(sample_feed)
            
            assert job is not None
            assert crawler.current_job is not None

    @pytest.mark.asyncio
    async def test_crawl_feed_with_duplicates(self, crawler, sample_feed, sample_article):
        """Test feed crawl with duplicate detection."""
        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.parser_factory, 'create_parser') as mock_parser, \
             patch.object(crawler.dedup_engine, 'is_duplicate', return_value=True), \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:
            
            mock_fetch.return_value = ("<html>content</html>", "text/html")
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = [sample_article]
            mock_parser.return_value = mock_parser_instance
            mock_job.return_value = CrawlJob(job_id="job-1")
            
            job = await crawler.crawl_feed(sample_feed)
            
            assert job is not None

    @pytest.mark.asyncio
    async def test_crawl_feed_with_validation_failure(self, crawler, sample_feed, sample_article):
        """Test feed crawl with validation failure."""
        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.parser_factory, 'create_parser') as mock_parser, \
             patch.object(crawler.dedup_engine, 'is_duplicate', return_value=False), \
             patch.object(crawler.validator, 'validate', return_value=(False, 0.5, ["Invalid title"])), \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:
            
            mock_fetch.return_value = ("<html>content</html>", "text/html")
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = [sample_article]
            mock_parser.return_value = mock_parser_instance
            mock_job.return_value = CrawlJob(job_id="job-1")
            
            job = await crawler.crawl_feed(sample_feed)
            
            assert job is not None

    @pytest.mark.asyncio
    async def test_crawl_feed_fetch_error(self, crawler, sample_feed):
        """Test feed crawl with fetch error."""
        from src.exceptions import FetchError

        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:

            mock_fetch.side_effect = FetchError("Fetch failed", url=sample_feed.url)
            mock_job.return_value = CrawlJob(job_id="job-1")

            # Should raise FetchError
            with pytest.raises(FetchError):
                await crawler.crawl_feed(sample_feed)

    @pytest.mark.asyncio
    async def test_crawl_feed_parse_error(self, crawler, sample_feed):
        """Test feed crawl with parse error."""
        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.parser_factory, 'create_parser') as mock_parser, \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:

            mock_fetch.return_value = ("<html>content</html>", "text/html")
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.side_effect = Exception("Parse error")
            mock_parser.return_value = mock_parser_instance
            mock_job.return_value = CrawlJob(job_id="job-1")

            # Should raise Exception
            with pytest.raises(Exception):
                await crawler.crawl_feed(sample_feed)

    @pytest.mark.asyncio
    async def test_crawl_feed_publish_error(self, crawler, sample_feed, sample_article):
        """Test feed crawl with publish error."""
        from src.exceptions import PublishError
        
        crawler.kafka_producer = MagicMock()
        crawler.kafka_producer.publish = AsyncMock(side_effect=PublishError("Publish failed"))
        
        with patch.object(crawler.http_fetcher, 'fetch', new_callable=AsyncMock) as mock_fetch, \
             patch.object(crawler.parser_factory, 'create_parser') as mock_parser, \
             patch.object(crawler.dedup_engine, 'is_duplicate', return_value=False), \
             patch.object(crawler.validator, 'validate', return_value=(True, 0.95, [])), \
             patch.object(crawler.normalizer, 'normalize') as mock_normalize, \
             patch.object(crawler.scheduler, 'create_crawl_job', new_callable=AsyncMock) as mock_job:
            
            mock_fetch.return_value = ("<html>content</html>", "text/html")
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = [sample_article]
            mock_parser.return_value = mock_parser_instance
            mock_normalize.return_value = MagicMock()
            mock_job.return_value = CrawlJob(job_id="job-1")
            
            job = await crawler.crawl_feed(sample_feed)
            
            assert job is not None

