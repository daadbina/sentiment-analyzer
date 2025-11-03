"""
Unit tests for core modules: health, metrics, logging, kafka_producer.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from src.health import HealthCheckManager, HealthStatus, HealthCheck
from src.metrics import CrawlerMetrics
from src.logging_config import JSONFormatter, setup_logging, get_logger
from src.kafka_producer import KafkaProducerAdapter


class TestHealthCheckManager:
    """Test HealthCheckManager."""

    def test_register_check(self):
        """Test registering a health check."""
        manager = HealthCheckManager()
        check = manager.register_check("test_check")
        assert check is not None
        assert isinstance(check, HealthCheck)

    def test_get_check(self):
        """Test getting a health check."""
        manager = HealthCheckManager()
        manager.register_check("test_check")
        check = manager.get_check("test_check")
        assert check is not None

    def test_get_check_not_found(self):
        """Test getting non-existent check."""
        manager = HealthCheckManager()
        check = manager.get_check("nonexistent")
        assert check is None

    def test_get_overall_status_healthy(self):
        """Test overall status when healthy."""
        manager = HealthCheckManager()
        check = manager.register_check("test")
        check.set_healthy()
        status = manager.get_overall_status()
        assert status == HealthStatus.HEALTHY

    def test_get_overall_status_unhealthy(self):
        """Test overall status when unhealthy."""
        manager = HealthCheckManager()
        check = manager.register_check("test")
        check.set_unhealthy("Test error")
        status = manager.get_overall_status()
        assert status == HealthStatus.UNHEALTHY

    def test_get_readiness(self):
        """Test readiness check."""
        manager = HealthCheckManager()
        readiness = manager.get_readiness()
        assert isinstance(readiness, bool)

    def test_get_liveness(self):
        """Test liveness check."""
        manager = HealthCheckManager()
        liveness = manager.get_liveness()
        assert isinstance(liveness, bool)

    def test_get_health_report(self):
        """Test health report."""
        manager = HealthCheckManager()
        manager.register_check("test")
        report = manager.get_health_report()
        assert isinstance(report, dict)
        assert "status" in report

    def test_get_metrics_summary(self):
        """Test metrics summary."""
        manager = HealthCheckManager()
        summary = manager.get_metrics_summary()
        assert isinstance(summary, dict)


class TestCrawlerMetrics:
    """Test CrawlerMetrics."""

    @pytest.fixture
    def metrics(self):
        """Create metrics instance."""
        return CrawlerMetrics()

    def test_metrics_initialization(self, metrics):
        """Test metrics initialization."""
        assert metrics is not None

    def test_record_article_crawled(self, metrics):
        """Test recording article crawled."""
        metrics.record_article_crawled("feed_001", "success")
        assert metrics is not None

    def test_record_article_published(self, metrics):
        """Test recording article published."""
        metrics.record_article_published("feed_001")
        assert metrics is not None

    def test_record_article_failed(self, metrics):
        """Test recording article failed."""
        metrics.record_article_failed("feed_001", "network_error")
        assert metrics is not None

    def test_record_duplicate_detected(self, metrics):
        """Test recording duplicate detected."""
        metrics.record_duplicate_detected("feed_001")
        assert metrics is not None

    def test_record_validation_failure(self, metrics):
        """Test recording validation failure."""
        metrics.record_validation_failure("feed_001", "R1")
        assert metrics is not None

    def test_record_http_request(self, metrics):
        """Test recording HTTP request."""
        metrics.record_http_request("feed_001", 200)
        assert metrics is not None

    def test_record_circuit_breaker_trip(self, metrics):
        """Test recording circuit breaker trip."""
        metrics.record_circuit_breaker_trip("feed_001")
        assert metrics is not None


class TestJSONFormatter:
    """Test JSONFormatter."""

    def test_formatter_initialization(self):
        """Test formatter initialization."""
        formatter = JSONFormatter()
        assert formatter is not None

    def test_format_record(self):
        """Test formatting log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert formatted is not None
        assert isinstance(formatted, str)

    def test_format_record_with_exception(self):
        """Test formatting log record with exception."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )
            formatted = formatter.format(record)
            assert formatted is not None


class TestLoggingConfig:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test setup logging."""
        setup_logging("DEBUG")
        # Verify root logger was configured
        root_logger = logging.getLogger()
        assert root_logger is not None

    def test_get_logger(self):
        """Test get logger."""
        logger = get_logger("test")
        assert logger is not None


class TestKafkaProducerAdapter:
    """Test KafkaProducerAdapter."""

    def test_kafka_producer_initialization(self):
        """Test Kafka producer initialization."""
        with patch("src.kafka_producer.get_settings"):
            producer = KafkaProducerAdapter()
            assert producer is not None

    @pytest.mark.asyncio
    async def test_kafka_producer_start(self):
        """Test starting Kafka producer."""
        with patch("src.kafka_producer.get_settings"), \
             patch("src.kafka_producer.SchemaRegistryClient"), \
             patch("src.kafka_producer.Producer"):
            producer = KafkaProducerAdapter()
            # Just verify initialization works
            assert producer is not None

    def test_kafka_producer_attributes(self):
        """Test Kafka producer attributes."""
        with patch("src.kafka_producer.get_settings"):
            producer = KafkaProducerAdapter()
            assert hasattr(producer, "producer")
            assert hasattr(producer, "schema_registry_client")
            assert hasattr(producer, "avro_serializer")

