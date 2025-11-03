"""
Prometheus metrics for monitoring crawler service.

Tracks performance, reliability, and data quality metrics.
"""

import logging
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class CrawlerMetrics:
    """
    Prometheus metrics for crawler service.

    Tracks all key performance indicators and operational metrics.
    """

    def __init__(self) -> None:
        """Initialize metrics."""
        # Counter metrics
        self.articles_crawled = Counter(
            "crawler_articles_crawled_total",
            "Total articles crawled",
            ["feed_id", "status"],
        )

        self.articles_published = Counter(
            "crawler_articles_published_total",
            "Total articles published to Kafka",
            ["feed_id"],
        )

        self.articles_failed = Counter(
            "crawler_articles_failed_total",
            "Total articles that failed processing",
            ["feed_id", "error_type"],
        )

        self.duplicates_detected = Counter(
            "crawler_duplicates_detected_total",
            "Total duplicate articles detected",
            ["feed_id"],
        )

        self.validation_failures = Counter(
            "crawler_validation_failures_total",
            "Total validation failures",
            ["feed_id", "rule"],
        )

        self.http_requests = Counter(
            "crawler_http_requests_total",
            "Total HTTP requests",
            ["feed_id", "status_code"],
        )

        self.circuit_breaker_trips = Counter(
            "crawler_circuit_breaker_trips_total",
            "Total circuit breaker trips",
            ["feed_id"],
        )

        # Gauge metrics
        self.active_crawls = Gauge(
            "crawler_active_crawls",
            "Number of active crawl jobs",
        )

        self.dedup_cache_size = Gauge(
            "crawler_dedup_cache_size",
            "Current deduplication cache size",
        )

        self.feed_registry_size = Gauge(
            "crawler_feed_registry_size",
            "Number of feeds in registry",
        )

        self.enabled_feeds = Gauge(
            "crawler_enabled_feeds",
            "Number of enabled feeds",
        )

        # Histogram metrics
        self.fetch_duration = Histogram(
            "crawler_fetch_duration_seconds",
            "HTTP fetch duration",
            ["feed_id"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
        )

        self.parse_duration = Histogram(
            "crawler_parse_duration_seconds",
            "Article parsing duration",
            ["parser_type"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
        )

        self.validation_duration = Histogram(
            "crawler_validation_duration_seconds",
            "Article validation duration",
            buckets=(0.01, 0.05, 0.1, 0.5),
        )

        self.publish_duration = Histogram(
            "crawler_publish_duration_seconds",
            "Kafka publish duration",
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
        )

        # Summary metrics
        self.validation_score = Summary(
            "crawler_validation_score",
            "Article validation score distribution",
            ["feed_id"],
        )

        self.articles_per_job = Summary(
            "crawler_articles_per_job",
            "Articles processed per crawl job",
        )

    def record_article_crawled(self, feed_id: str, status: str = "success") -> None:
        """
        Record article crawled.

        Args:
            feed_id: Feed identifier.
            status: Crawl status (success, failed).
        """
        self.articles_crawled.labels(feed_id=feed_id, status=status).inc()

    def record_article_published(self, feed_id: str) -> None:
        """
        Record article published to Kafka.

        Args:
            feed_id: Feed identifier.
        """
        self.articles_published.labels(feed_id=feed_id).inc()

    def record_article_failed(self, feed_id: str, error_type: str) -> None:
        """
        Record article processing failure.

        Args:
            feed_id: Feed identifier.
            error_type: Type of error.
        """
        self.articles_failed.labels(feed_id=feed_id, error_type=error_type).inc()

    def record_duplicate_detected(self, feed_id: str) -> None:
        """
        Record duplicate article detected.

        Args:
            feed_id: Feed identifier.
        """
        self.duplicates_detected.labels(feed_id=feed_id).inc()

    def record_validation_failure(self, feed_id: str, rule: str) -> None:
        """
        Record validation failure.

        Args:
            feed_id: Feed identifier.
            rule: Validation rule that failed.
        """
        self.validation_failures.labels(feed_id=feed_id, rule=rule).inc()

    def record_http_request(self, feed_id: str, status_code: int) -> None:
        """
        Record HTTP request.

        Args:
            feed_id: Feed identifier.
            status_code: HTTP status code.
        """
        self.http_requests.labels(feed_id=feed_id, status_code=status_code).inc()

    def record_circuit_breaker_trip(self, feed_id: str) -> None:
        """
        Record circuit breaker trip.

        Args:
            feed_id: Feed identifier.
        """
        self.circuit_breaker_trips.labels(feed_id=feed_id).inc()

    def set_active_crawls(self, count: int) -> None:
        """
        Set number of active crawls.

        Args:
            count: Number of active crawls.
        """
        self.active_crawls.set(count)

    def set_dedup_cache_size(self, size: int) -> None:
        """
        Set deduplication cache size.

        Args:
            size: Cache size.
        """
        self.dedup_cache_size.set(size)

    def set_feed_registry_size(self, total: int, enabled: int) -> None:
        """
        Set feed registry sizes.

        Args:
            total: Total feeds.
            enabled: Enabled feeds.
        """
        self.feed_registry_size.set(total)
        self.enabled_feeds.set(enabled)

    def record_fetch_duration(self, feed_id: str, duration: float) -> None:
        """
        Record HTTP fetch duration.

        Args:
            feed_id: Feed identifier.
            duration: Duration in seconds.
        """
        self.fetch_duration.labels(feed_id=feed_id).observe(duration)

    def record_parse_duration(self, parser_type: str, duration: float) -> None:
        """
        Record parsing duration.

        Args:
            parser_type: Parser type used.
            duration: Duration in seconds.
        """
        self.parse_duration.labels(parser_type=parser_type).observe(duration)

    def record_validation_duration(self, duration: float) -> None:
        """
        Record validation duration.

        Args:
            duration: Duration in seconds.
        """
        self.validation_duration.observe(duration)

    def record_publish_duration(self, duration: float) -> None:
        """
        Record publish duration.

        Args:
            duration: Duration in seconds.
        """
        self.publish_duration.observe(duration)

    def record_validation_score(self, feed_id: str, score: float) -> None:
        """
        Record validation score.

        Args:
            feed_id: Feed identifier.
            score: Validation score (0.0-1.0).
        """
        self.validation_score.labels(feed_id=feed_id).observe(score)

    def record_articles_per_job(self, count: int) -> None:
        """
        Record articles processed per job.

        Args:
            count: Number of articles.
        """
        self.articles_per_job.observe(count)
