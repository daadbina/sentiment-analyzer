"""
Main crawler application orchestrator.

Coordinates all crawler components and manages crawl execution.
"""

import logging
from typing import Optional, List

from .config import get_settings
from .feed_registry import FeedRegistry
from .scheduler import CrawlScheduler
from .kafka_producer import KafkaProducerAdapter
from .fetcher import HTTPFetcher
from .parser import ParserFactory
from .validation import ArticleValidator
from .deduplication import DeduplicationEngine
from .normalizer import ArticleNormalizer
from .metrics import CrawlerMetrics
from .health import HealthCheckManager
from .logging_config import get_logger
from .models import CrawlJob, FeedSource
from .database import DatabaseManager
from .kafka_admin import KafkaTopicManager

logger = logging.getLogger(__name__)


class CrawlerApplication:
    """
    Main crawler application.

    Orchestrates all components for crawling news feeds.
    """

    def __init__(self) -> None:
        """Initialize crawler application."""
        self.settings = get_settings()
        self.logger = get_logger(__name__)

        # Initialize infrastructure components
        self.database = DatabaseManager()
        self.kafka_topic_manager = KafkaTopicManager()

        # Initialize components
        self.feed_registry = FeedRegistry()
        self.scheduler = CrawlScheduler()
        self.kafka_producer = KafkaProducerAdapter()
        self.http_fetcher = HTTPFetcher()
        self.parser_factory = ParserFactory()
        self.validator = ArticleValidator()
        self.dedup_engine = DeduplicationEngine()
        self.normalizer = ArticleNormalizer()
        self.metrics = CrawlerMetrics()
        self.health_manager = HealthCheckManager()

        # Register health checks
        self.health_manager.register_check("database")
        self.health_manager.register_check("kafka_topics")
        self.health_manager.register_check("kafka_producer")
        self.health_manager.register_check("feed_registry")
        self.health_manager.register_check("scheduler")
        self.health_manager.register_check("http_fetcher")

        self.is_running = False
        self.current_job: Optional[CrawlJob] = None

    async def start(self) -> None:
        """Start crawler application."""
        try:
            self.logger.info("Starting crawler application")

            # Initialize database
            self.logger.info("Initializing database...")
            await self.database.initialize()
            self.health_manager.get_check("database").set_healthy()
            self.logger.info("Database initialized successfully")

            # Initialize Kafka topics
            self.logger.info("Initializing Kafka topics...")
            await self.kafka_topic_manager.initialize()
            self.health_manager.get_check("kafka_topics").set_healthy()
            self.logger.info("Kafka topics initialized successfully")

            # Start Kafka producer
            await self.kafka_producer.start()
            self.health_manager.get_check("kafka_producer").set_healthy()

            # Start scheduler
            await self.scheduler.start()
            self.health_manager.get_check("scheduler").set_healthy()

            # Mark feed registry as healthy
            self.health_manager.get_check("feed_registry").set_healthy()
            self.health_manager.get_check("http_fetcher").set_healthy()

            self.is_running = True
            self.logger.info("Crawler application started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start crawler: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop crawler application gracefully."""
        try:
            self.logger.info("Stopping crawler application")

            self.is_running = False

            # Stop scheduler
            await self.scheduler.stop()

            # Stop Kafka producer
            await self.kafka_producer.stop()

            # Stop HTTP fetcher (cleanup aiohttp session)
            await self.http_fetcher.stop()

            # Close database connection
            await self.database.close()

            # Close Kafka admin client
            self.kafka_topic_manager.close()

            self.logger.info("Crawler application stopped")

        except Exception as e:
            self.logger.error(f"Error stopping crawler: {str(e)}")

    async def crawl_feed(self, feed: FeedSource) -> CrawlJob:
        """
        Crawl a single feed.

        Args:
            feed: Feed to crawl.

        Returns:
            CrawlJob: Job execution result.
        """
        job = await self.scheduler.create_crawl_job()
        self.current_job = job

        try:
            self.logger.info(f"Starting crawl job {job.job_id} for feed {feed.feed_id}")

            # Fetch feed content
            content, content_type = await self.http_fetcher.fetch(
                feed.url, timeout=feed.timeout_seconds
            )
            self.metrics.record_http_request(feed.feed_id, 200)

            # Parse articles
            parser = self.parser_factory.create_parser(feed.feed_id, feed.feed_type)
            articles = await parser.parse(content, feed.url)

            self.logger.info(f"Parsed {len(articles)} articles from {feed.feed_id}")

            # Process each article
            for article in articles:
                try:
                    # Check for duplicates
                    if self.dedup_engine.is_duplicate(article):
                        self.metrics.record_duplicate_detected(feed.feed_id)
                        job.articles_crawled += 1
                        continue

                    # Validate article
                    validation_result = self.validator.validate(article)
                    self.metrics.record_validation_score(feed.feed_id, validation_result.validation_score)

                    if not validation_result.is_valid:
                        for error in validation_result.errors:
                            self.logger.warning(f"Validation failed: {error}")
                            self.metrics.record_validation_failure(feed.feed_id, error)
                        job.articles_failed += 1
                        continue

                    # Normalize article
                    message = self.normalizer.normalize(
                        article,
                        feed_id=feed.feed_id,
                        job_id=job.job_id,
                        validation_score=validation_result.validation_score,
                    )

                    # Publish to Kafka
                    await self.kafka_producer.publish(message)
                    self.metrics.record_article_published(feed.feed_id)
                    job.articles_published += 1

                    # Add to dedup cache
                    self.dedup_engine.add_article(article)

                except Exception as e:
                    self.logger.error(f"Error processing article: {str(e)}")
                    self.metrics.record_article_failed(feed.feed_id, type(e).__name__)
                    job.articles_failed += 1

                job.articles_crawled += 1

            # Complete job
            await self.scheduler.complete_crawl_job(job, status="completed")
            self.metrics.record_articles_per_job(job.articles_published)

            return job

        except Exception as e:
            self.logger.error(f"Crawl job {job.job_id} failed: {str(e)}")
            await self.scheduler.complete_crawl_job(job, status="failed")
            job.errors.append(str(e))
            raise

    async def crawl_all_feeds(self) -> List[CrawlJob]:
        """
        Crawl all enabled feeds.

        Returns:
            list[CrawlJob]: List of job results.
        """
        jobs = []
        feeds = self.feed_registry.get_enabled_feeds()

        self.logger.info(f"Starting crawl of {len(feeds)} feeds")

        for feed in feeds:
            try:
                job = await self.crawl_feed(feed)
                jobs.append(job)
            except Exception as e:
                self.logger.error(f"Failed to crawl feed {feed.feed_id}: {str(e)}")

        return jobs

    def get_health_status(self) -> dict:
        """
        Get health status.

        Returns:
            dict: Health report.
        """
        return self.health_manager.get_health_report()

    def get_metrics(self) -> dict:
        """
        Get metrics summary.

        Returns:
            dict: Metrics summary.
        """
        return {
            "health": self.health_manager.get_metrics_summary(),
            "dedup_cache": self.dedup_engine.get_cache_stats(),
            "feed_registry": self.feed_registry.get_stats(),
            "scheduler": {
                "jobs": len(self.scheduler.get_all_jobs()),
                "job_stats": self.scheduler.get_all_stats(),
            },
        }
