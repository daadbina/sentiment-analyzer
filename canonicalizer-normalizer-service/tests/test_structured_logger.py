"""Tests for structured logger."""

import pytest
from src.monitoring.structured_logger import (
    StructuredLogger,
    PerformanceLogger,
    correlation_id_var,
)


class TestStructuredLogger:
    """Test structured logger."""

    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_logger_get_correlation_id(self):
        """Test getting correlation ID."""
        logger = StructuredLogger("test_logger")
        correlation_id = logger._get_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) > 0

    def test_logger_correlation_id_consistency(self):
        """Test correlation ID is consistent."""
        logger = StructuredLogger("test_logger")
        id1 = logger._get_correlation_id()
        id2 = logger._get_correlation_id()
        assert id1 == id2

    def test_logger_set_correlation_id(self):
        """Test setting correlation ID."""
        test_id = "test-correlation-id-123"
        StructuredLogger.set_correlation_id(test_id)
        assert StructuredLogger.get_correlation_id() == test_id

    def test_logger_format_message(self):
        """Test message formatting."""
        logger = StructuredLogger("test_logger")
        message = logger._format_message("Test message", "INFO", key="value")
        assert isinstance(message, str)
        assert "Test message" in message
        assert "INFO" in message
        assert "correlation_id" in message

    def test_logger_debug(self):
        """Test debug logging."""
        logger = StructuredLogger("test_logger")
        # Should not raise error
        logger.debug("Debug message", extra_field="value")

    def test_logger_info(self):
        """Test info logging."""
        logger = StructuredLogger("test_logger")
        # Should not raise error
        logger.info("Info message", extra_field="value")

    def test_logger_warning(self):
        """Test warning logging."""
        logger = StructuredLogger("test_logger")
        # Should not raise error
        logger.warning("Warning message", extra_field="value")

    def test_logger_error(self):
        """Test error logging."""
        logger = StructuredLogger("test_logger")
        # Should not raise error
        logger.error("Error message", extra_field="value")

    def test_logger_critical(self):
        """Test critical logging."""
        logger = StructuredLogger("test_logger")
        # Should not raise error
        logger.critical("Critical message", extra_field="value")


class TestPerformanceLogger:
    """Test performance logger."""

    def test_performance_logger_initialization(self):
        """Test performance logger initialization."""
        logger = PerformanceLogger("perf_logger")
        assert logger is not None
        assert isinstance(logger.logger, StructuredLogger)

    def test_performance_logger_log_operation(self):
        """Test logging operation."""
        logger = PerformanceLogger("perf_logger")
        # Should not raise error
        logger.log_operation("test_operation", 100.5, True)

    def test_performance_logger_log_cache_hit(self):
        """Test logging cache hit."""
        logger = PerformanceLogger("perf_logger")
        # Should not raise error
        logger.log_cache_hit("redis", "key123")

    def test_performance_logger_log_cache_miss(self):
        """Test logging cache miss."""
        logger = PerformanceLogger("perf_logger")
        # Should not raise error
        logger.log_cache_miss("redis", "key123")

    def test_performance_logger_log_database_operation(self):
        """Test logging database operation."""
        logger = PerformanceLogger("perf_logger")
        # Should not raise error
        logger.log_database_operation("INSERT", "articles", 50.0, 10)

    def test_performance_logger_log_external_api_call(self):
        """Test logging external API call."""
        logger = PerformanceLogger("perf_logger")
        # Should not raise error
        logger.log_external_api_call("schema_registry", "/subjects", 25.0, 200)

    def test_performance_logger_log_error_with_context(self):
        """Test logging error with context."""
        logger = PerformanceLogger("perf_logger")
        try:
            raise ValueError("Test error")
        except ValueError as e:
            # Should not raise error
            logger.log_error_with_context(e, "test_context", user_id="123")


class TestCorrelationId:
    """Test correlation ID context variable."""

    def test_correlation_id_default(self):
        """Test default correlation ID."""
        # Clear any existing value
        correlation_id_var.set('')
        assert correlation_id_var.get() == ''

    def test_correlation_id_set_and_get(self):
        """Test setting and getting correlation ID."""
        test_id = "test-id-456"
        correlation_id_var.set(test_id)
        assert correlation_id_var.get() == test_id

    def test_correlation_id_via_logger(self):
        """Test correlation ID via logger."""
        test_id = "logger-test-id"
        StructuredLogger.set_correlation_id(test_id)
        assert StructuredLogger.get_correlation_id() == test_id

