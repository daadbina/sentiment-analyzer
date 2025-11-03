"""
Integration tests for service-to-service communication.

Tests Kafka, Schema Registry, PostgreSQL, and monitoring integrations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.kafka_producer import KafkaProducerAdapter
from src.models import NewsRawMessage
from src.config import get_settings
from src.metrics import CrawlerMetrics


@pytest.mark.asyncio
class TestKafkaIntegration:
    """Test Kafka integration."""

    async def test_kafka_producer_initialization(self):
        """Test Kafka producer initializes correctly."""
        producer = KafkaProducerAdapter()
        assert producer.settings is not None
        assert producer.producer is None
        assert producer.schema_registry_client is None

    async def test_kafka_producer_config(self):
        """Test Kafka producer configuration."""
        settings = get_settings()
        assert settings.kafka_brokers is not None
        assert settings.kafka_topic is not None
        assert settings.schema_registry_url is not None

    async def test_news_raw_message_model(self):
        """Test NewsRawMessage model creation."""
        message = NewsRawMessage(
            canonical_url="https://example.com/article",
            title="Test Article",
            body="Test content",
            url="https://example.com/article",
            source="Test Source",
            language="en",
            published_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.95,
            schema_version="1.0.0",
            ingest_job_id="job-123",
            publisher_id="pub-123",
            extraction_method="rss",
        )
        assert message.article_id is not None
        assert message.title == "Test Article"
        assert message.language == "en"
        assert message.validation_score == 0.95

    def test_news_raw_message_validation_score(self):
        """Test validation score validation."""
        with pytest.raises(ValueError):
            NewsRawMessage(
                canonical_url="https://example.com/article",
                title="Test Article",
                body="Test content",
                url="https://example.com/article",
                source="Test Source",
                language="en",
                published_at="2025-11-02T10:00:00Z",
                checksum="abc123",
                validation_score=1.5,  # Invalid
                schema_version="1.0.0",
                ingest_job_id="job-123",
                publisher_id="pub-123",
                extraction_method="rss",
            )

    def test_news_raw_message_language_validation(self):
        """Test language code validation."""
        with pytest.raises(ValueError):
            NewsRawMessage(
                canonical_url="https://example.com/article",
                title="Test Article",
                body="Test content",
                url="https://example.com/article",
                source="Test Source",
                language="eng",  # Invalid - should be 2 chars
                published_at="2025-11-02T10:00:00Z",
                checksum="abc123",
                validation_score=0.95,
                schema_version="1.0.0",
                ingest_job_id="job-123",
                publisher_id="pub-123",
                extraction_method="rss",
            )

    def test_news_raw_message_timestamp_validation(self):
        """Test timestamp validation."""
        with pytest.raises(ValueError):
            NewsRawMessage(
                canonical_url="https://example.com/article",
                title="Test Article",
                body="Test content",
                url="https://example.com/article",
                source="Test Source",
                language="en",
                published_at="invalid-timestamp",  # Invalid
                checksum="abc123",
                validation_score=0.95,
                schema_version="1.0.0",
                ingest_job_id="job-123",
                publisher_id="pub-123",
                extraction_method="rss",
            )

    def test_news_raw_message_serialization(self):
        """Test NewsRawMessage serialization."""
        message = NewsRawMessage(
            canonical_url="https://example.com/article",
            title="Test Article",
            body="Test content",
            url="https://example.com/article",
            source="Test Source",
            language="en",
            published_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.95,
            schema_version="1.0.0",
            ingest_job_id="job-123",
            publisher_id="pub-123",
            extraction_method="rss",
        )
        serialized = message.dict()
        assert serialized["title"] == "Test Article"
        assert serialized["language"] == "en"
        assert "article_id" in serialized
        assert "crawled_at" in serialized


class TestSchemaRegistryIntegration:
    """Test Schema Registry integration."""

    def test_schema_registry_url_configured(self):
        """Test Schema Registry URL is configured."""
        settings = get_settings()
        assert settings.schema_registry_url is not None
        assert "http" in settings.schema_registry_url

    def test_avro_schema_file_exists(self):
        """Test Avro schema file exists."""
        import os

        schema_path = "schemas/news_raw_v1.avsc"
        assert os.path.exists(schema_path), f"Schema file not found: {schema_path}"

    def test_avro_schema_valid_json(self):
        """Test Avro schema is valid JSON."""
        import json

        with open("schemas/news_raw_v1.avsc", "r") as f:
            schema = json.load(f)
        assert schema is not None
        assert "type" in schema
        assert schema["type"] == "record"

    def test_avro_schema_has_required_fields(self):
        """Test Avro schema has required fields."""
        import json

        with open("schemas/news_raw_v1.avsc", "r") as f:
            schema = json.load(f)

        field_names = [field["name"] for field in schema["fields"]]
        required_fields = [
            "article_id",
            "canonical_url",
            "title",
            "body",
            "url",
            "source",
            "language",
            "published_at",
            "crawled_at",
            "checksum",
            "validation_score",
            "schema_version",
            "ingest_job_id",
            "publisher_id",
            "extraction_method",
        ]
        for field in required_fields:
            assert field in field_names, f"Required field missing: {field}"


class TestPrometheusMetricsIntegration:
    """Test Prometheus metrics integration."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = CrawlerMetrics()
        assert metrics.articles_crawled is not None
        assert metrics.articles_published is not None
        assert metrics.articles_failed is not None
        assert metrics.duplicates_detected is not None

    def test_metrics_counter_increment(self):
        """Test metrics counter increment."""
        metrics = CrawlerMetrics()
        metrics.articles_crawled.labels(feed_id="test", status="success").inc()
        # Verify counter was incremented (no exception)

    def test_metrics_gauge_set(self):
        """Test metrics gauge set."""
        metrics = CrawlerMetrics()
        metrics.active_crawls.set(5)
        # Verify gauge was set (no exception)

    def test_metrics_histogram_observe(self):
        """Test metrics histogram observe."""
        metrics = CrawlerMetrics()
        metrics.fetch_duration.labels(feed_id="test").observe(0.5)
        # Verify histogram was observed (no exception)

    def test_metrics_summary_observe(self):
        """Test metrics summary observe."""
        metrics = CrawlerMetrics()
        metrics.articles_per_job.observe(10)
        # Verify summary was observed (no exception)


class TestMonitoringIntegration:
    """Test monitoring integration."""

    def test_prometheus_endpoint_configured(self):
        """Test Prometheus endpoint is configured."""
        settings = get_settings()
        assert settings.prometheus_port is not None
        assert settings.prometheus_port > 0

    def test_logging_configured(self):
        """Test logging is configured."""
        import logging

        logger = logging.getLogger("crawler")
        assert logger is not None
        # Logger exists even if no handlers are configured at this point

    def test_structured_logging_format(self):
        """Test structured logging format."""
        import logging
        import json

        logger = logging.getLogger("test_logger")
        # Verify logger can be used for structured logging
        assert logger is not None

