"""
Structured logging configuration for crawler service.

Implements JSON logging with trace IDs for distributed tracing.
"""

import logging
import json
import sys
from typing import Any, Dict
from datetime import datetime
import uuid

from .config import get_settings


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON with trace ID and context.
    """

    def __init__(self, trace_id: str = "") -> None:
        """
        Initialize JSON formatter.

        Args:
            trace_id: Trace ID for correlation.
        """
        super().__init__()
        self.trace_id = trace_id or str(uuid.uuid4())

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record.

        Returns:
            str: JSON formatted log.
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": self.trace_id,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger with trace ID support.

    Provides convenient methods for logging with context.
    """

    def __init__(self, name: str, trace_id: str = "") -> None:
        """
        Initialize structured logger.

        Args:
            name: Logger name.
            trace_id: Trace ID for correlation.
        """
        self.logger = logging.getLogger(name)
        self.trace_id = trace_id or str(uuid.uuid4())

    def _log(
        self,
        level: int,
        message: str,
        **kwargs,
    ) -> None:
        """
        Internal logging method with extra fields.

        Args:
            level: Log level.
            message: Log message.
            **kwargs: Extra fields to include.
        """
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(unknown file)",
            0,
            message,
            (),
            None,
        )
        record.extra_fields = kwargs
        self.logger.handle(record)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)


def setup_logging(
    log_level: str = "INFO",
    trace_id: str = "",
) -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        trace_id: Trace ID for correlation.
    """
    settings = get_settings()

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Set formatter based on environment
    if settings.log_format == "json":
        formatter = JSONFormatter(trace_id=trace_id)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("confluent_kafka").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, trace_id: str = "") -> StructuredLogger:
    """
    Get structured logger instance.

    Args:
        name: Logger name.
        trace_id: Trace ID for correlation.

    Returns:
        StructuredLogger: Logger instance.
    """
    return StructuredLogger(name, trace_id=trace_id)


class LogContext:
    """
    Context manager for logging with trace ID.

    Automatically includes trace ID in all logs within context.
    """

    def __init__(self, trace_id: str = "") -> None:
        """
        Initialize log context.

        Args:
            trace_id: Trace ID (generated if not provided).
        """
        self.trace_id = trace_id or str(uuid.uuid4())
        self.logger = get_logger(__name__, trace_id=self.trace_id)

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            self.logger.error(
                f"Exception in context: {exc_type.__name__}: {exc_val}",
                trace_id=self.trace_id,
            )
