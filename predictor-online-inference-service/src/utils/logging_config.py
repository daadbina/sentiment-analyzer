"""
Structured logging configuration for Predictor Online Inference Service.

Provides JSON-formatted logging with trace IDs and context information.
All logs include structured fields for easy parsing and analysis.
"""

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context fields.

    Adds service name, trace ID, and other context information to all log records.
    """

    def __init__(self, *args, service_name: str = "predictor-service", **kwargs):
        """
        Initialize custom JSON formatter.

        Args:
            service_name: Name of the service for log identification
        """
        super().__init__(*args, **kwargs)
        self.service_name = service_name

    def add_fields(
        self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]
    ) -> None:
        """
        Add custom fields to log record.

        Args:
            log_record: Dictionary to add fields to
            record: Original log record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)

        # Add service name
        log_record["service"] = self.service_name

        # Add timestamp in ISO format
        log_record["timestamp"] = self.formatTime(record, self.datefmt)

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add trace_id if present in extra
        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id

        # Add group_id if present in extra
        if hasattr(record, "group_id"):
            log_record["group_id"] = record.group_id

        # Add model_version if present in extra
        if hasattr(record, "model_version"):
            log_record["model_version"] = record.model_version

        # Add latency_ms if present in extra
        if hasattr(record, "latency_ms"):
            log_record["latency_ms"] = record.latency_ms

        # Add any other custom fields from extra
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                if key not in log_record:
                    log_record[key] = value


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "predictor-service",
    enable_json: bool = True,
) -> None:
    """
    Setup structured logging for the service.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
        enable_json: Whether to use JSON formatting (True) or plain text (False)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if enable_json:
        # Use JSON formatter
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            service_name=service_name,
        )
    else:
        # Use plain text formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("confluent_kafka").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)

    root_logger.info(
        f"Logging configured: level={log_level}, service={service_name}, json={enable_json}"
    )


class ContextLogger:
    """
    Logger wrapper that adds context information to all log messages.

    Provides convenient methods for logging with trace IDs and other context.
    """

    def __init__(
        self,
        logger: logging.Logger,
        trace_id: str | None = None,
        group_id: str | None = None,
        model_version: str | None = None,
        **extra_context,
    ):
        """
        Initialize context logger.

        Args:
            logger: Base logger instance
            trace_id: Trace ID for distributed tracing
            group_id: Semantic group ID
            model_version: Model version used
            **extra_context: Additional context fields
        """
        self.logger = logger
        self.context = {
            "trace_id": trace_id,
            "group_id": group_id,
            "model_version": model_version,
            **extra_context,
        }
        # Remove None values
        self.context = {k: v for k, v in self.context.items() if v is not None}

    def _log(self, level: int, message: str, **kwargs) -> None:
        """
        Log message with context.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional fields to add
        """
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        Log error message with context.

        Args:
            message: Error message
            exc_info: Whether to include exception info
            **kwargs: Additional fields
        """
        if exc_info:
            self.logger.error(message, exc_info=True, extra={**self.context, **kwargs})
        else:
            self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        Log critical message with context.

        Args:
            message: Critical message
            exc_info: Whether to include exception info
            **kwargs: Additional fields
        """
        if exc_info:
            self.logger.critical(message, exc_info=True, extra={**self.context, **kwargs})
        else:
            self._log(logging.CRITICAL, message, **kwargs)

    def with_context(self, **additional_context) -> "ContextLogger":
        """
        Create a new context logger with additional context.

        Args:
            **additional_context: Additional context fields to add

        Returns:
            New ContextLogger instance with merged context
        """
        merged_context = {**self.context, **additional_context}
        return ContextLogger(
            self.logger,
            trace_id=merged_context.get("trace_id"),
            group_id=merged_context.get("group_id"),
            model_version=merged_context.get("model_version"),
            **{
                k: v
                for k, v in merged_context.items()
                if k not in ["trace_id", "group_id", "model_version"]
            },
        )


def get_logger(
    name: str,
    trace_id: str | None = None,
    group_id: str | None = None,
    model_version: str | None = None,
    **extra_context,
) -> ContextLogger:
    """
    Get a context logger instance.

    Args:
        name: Logger name (usually __name__)
        trace_id: Trace ID for distributed tracing
        group_id: Semantic group ID
        model_version: Model version used
        **extra_context: Additional context fields

    Returns:
        ContextLogger instance with context

    Example:
        logger = get_logger(__name__, trace_id="123", group_id="456")
        logger.info("Processing prediction", latency_ms=150)
    """
    base_logger = logging.getLogger(name)
    return ContextLogger(
        base_logger,
        trace_id=trace_id,
        group_id=group_id,
        model_version=model_version,
        **extra_context,
    )
