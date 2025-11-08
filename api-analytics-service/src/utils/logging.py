"""Structured logging for API Analytics Service.

Provides trace ID propagation, user tracking, and audit logging.
"""

import logging
import json
import time
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime

# Context variables for trace propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
endpoint_var: ContextVar[Optional[str]] = ContextVar("endpoint", default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "user_id": user_id_var.get(),
            "endpoint": endpoint_var.get(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with structured formatter
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get logger with context support.

    Args:
        name: Logger name

    Returns:
        Logger adapter with context support
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {})


class LogContext:
    """Context manager for setting logging context."""

    def __init__(
        self,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """Initialize log context.

        Args:
            trace_id: Trace ID
            user_id: User ID
            endpoint: API endpoint
        """
        self.trace_id = trace_id
        self.user_id = user_id
        self.endpoint = endpoint
        self.prev_trace_id = None
        self.prev_user_id = None
        self.prev_endpoint = None

    def __enter__(self):
        """Enter context."""
        self.prev_trace_id = trace_id_var.get()
        self.prev_user_id = user_id_var.get()
        self.prev_endpoint = endpoint_var.get()

        if self.trace_id:
            trace_id_var.set(self.trace_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        if self.endpoint:
            endpoint_var.set(self.endpoint)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        trace_id_var.set(self.prev_trace_id)
        user_id_var.set(self.prev_user_id)
        endpoint_var.set(self.prev_endpoint)


class LatencyTracker:
    """Track operation latency."""

    def __init__(self, logger: logging.Logger, operation: str):
        """Initialize latency tracker.

        Args:
            logger: Logger instance
            operation: Operation name
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Enter context."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log latency."""
        if self.start_time:
            latency_ms = (time.time() - self.start_time) * 1000
            self.logger.info(
                f"{self.operation} completed",
                extra={
                    "extra_fields": {
                        "operation": self.operation,
                        "latency_ms": latency_ms,
                    }
                },
            )


def log_audit(
    logger: logging.Logger,
    action: str,
    resource: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log audit event.

    Args:
        logger: Logger instance
        action: Action performed
        resource: Resource affected
        user_id: User ID
        details: Additional details
    """
    audit_data = {
        "action": action,
        "resource": resource,
        "user_id": user_id or user_id_var.get(),
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        audit_data.update(details)

    logger.info(
        f"AUDIT: {action} on {resource}",
        extra={"extra_fields": audit_data},
    )


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context.

    Args:
        trace_id: Trace ID
    """
    trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Get trace ID from current context.

    Returns:
        Trace ID or None
    """
    return trace_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set user ID for current context.

    Args:
        user_id: User ID
    """
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """Get user ID from current context.

    Returns:
        User ID or None
    """
    return user_id_var.get()


def set_endpoint(endpoint: str) -> None:
    """Set endpoint for current context.

    Args:
        endpoint: API endpoint
    """
    endpoint_var.set(endpoint)


def get_endpoint() -> Optional[str]:
    """Get endpoint from current context.

    Returns:
        Endpoint or None
    """
    return endpoint_var.get()

