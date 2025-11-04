"""Distributed tracing utilities for feature-engineering-service."""

import uuid
import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime

# Context variables for trace propagation
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
group_id_var: ContextVar[str] = ContextVar("group_id", default="")

logger = logging.getLogger(__name__)


class TraceContext:
    """Context manager for distributed tracing."""

    def __init__(
        self,
        trace_id: Optional[str] = None,
        group_id: Optional[str] = None,
        operation: str = "unknown",
    ):
        """Initialize trace context.

        Args:
            trace_id: Trace ID (generated if not provided)
            group_id: Group ID for correlation
            operation: Operation name for logging
        """
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.group_id = group_id or ""
        self.operation = operation
        self.start_time = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}

    def __enter__(self):
        """Enter context."""
        trace_id_var.set(self.trace_id)
        span_id_var.set(self.span_id)
        group_id_var.set(self.group_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        log_data = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "group_id": self.group_id,
            "operation": self.operation,
            "duration_ms": duration_ms,
            "status": "error" if exc_type else "success",
        }
        if exc_type:
            log_data["error"] = str(exc_val)
        log_data.update(self.metadata)
        logger.info(f"Trace completed: {log_data}")

    def add_metadata(self, key: str, value: Any):
        """Add metadata to trace."""
        self.metadata[key] = value


def get_trace_id() -> str:
    """Get current trace ID."""
    return trace_id_var.get()


def get_span_id() -> str:
    """Get current span ID."""
    return span_id_var.get()


def get_group_id() -> str:
    """Get current group ID."""
    return group_id_var.get()


def set_trace_id(trace_id: str):
    """Set trace ID."""
    trace_id_var.set(trace_id)


def set_group_id(group_id: str):
    """Set group ID."""
    group_id_var.set(group_id)


class StructuredLogger:
    """Structured logging with trace context."""

    def __init__(self, name: str):
        """Initialize logger."""
        self.logger = logging.getLogger(name)

    def _add_context(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Add trace context to log data."""
        context = {
            "trace_id": get_trace_id(),
            "span_id": get_span_id(),
            "group_id": get_group_id(),
        }
        context.update(extra)
        return context

    def debug(self, message: str, exc_info: bool = False, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=self._add_context(kwargs), exc_info=exc_info)

    def info(self, message: str, exc_info: bool = False, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=self._add_context(kwargs), exc_info=exc_info)

    def warning(self, message: str, exc_info: bool = False, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=self._add_context(kwargs), exc_info=exc_info)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=self._add_context(kwargs), exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=self._add_context(kwargs), exc_info=exc_info)

