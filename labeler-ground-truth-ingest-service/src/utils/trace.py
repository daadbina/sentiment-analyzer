"""Structured logging and tracing utilities."""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Structured logger with trace context."""

    def __init__(self, name: str, log_level: str = "INFO"):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level))

        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # JSON formatter - use custom format to avoid null fields
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.trace_id = str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())

    def _get_context(self) -> Dict[str, Any]:
        """Get logging context."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }

    def _log_json(self, level: int, context: Dict[str, Any]):
        """Log as JSON using the logger."""
        # Use msg_text as the message to avoid conflicts with reserved fields
        self.logger.log(level, json.dumps(context))

    def info(
        self,
        message: str,
        operation: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status: str = "success",
        **kwargs
    ):
        """Log info message."""
        context = self._get_context()
        context.update({
            "msg": message,
            "operation": operation,
            "duration_ms": duration_ms,
            "status": status,
            **kwargs
        })
        self._log_json(logging.INFO, context)

    def debug(
        self,
        message: str,
        operation: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log debug message."""
        context = self._get_context()
        context.update({
            "msg": message,
            "operation": operation,
            "duration_ms": duration_ms,
            **kwargs
        })
        self._log_json(logging.DEBUG, context)

    def warning(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Log warning message."""
        context = self._get_context()
        context.update({
            "msg": message,
            "operation": operation,
            **kwargs
        })
        self._log_json(logging.WARNING, context)

    def error(
        self,
        message: str,
        operation: Optional[str] = None,
        error_type: Optional[str] = None,
        **kwargs
    ):
        """Log error message."""
        context = self._get_context()
        context.update({
            "msg": message,
            "operation": operation,
            "error_type": error_type,
            **kwargs
        })
        self._log_json(logging.ERROR, context)

    def critical(
        self,
        message: str,
        operation: Optional[str] = None,
        error_type: Optional[str] = None,
        **kwargs
    ):
        """Log critical message."""
        context = self._get_context()
        context.update({
            "msg": message,
            "operation": operation,
            "error_type": error_type,
            **kwargs
        })
        self._log_json(logging.CRITICAL, context)


class TimedOperation:
    """Context manager for timed operations."""

    def __init__(self, logger: StructuredLogger, operation: str, **context):
        """Initialize timed operation."""
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        self.duration_ms = None

    def __enter__(self):
        """Enter context."""
        self.start_time = time.time()
        self.logger.debug(
            f"Starting operation: {self.operation}",
            operation=self.operation,
            **self.context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        self.duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.error(
                f"Operation failed: {self.operation}",
                operation=self.operation,
                duration_ms=self.duration_ms,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        else:
            self.logger.info(
                f"Operation completed: {self.operation}",
                operation=self.operation,
                duration_ms=self.duration_ms,
                status="success",
                **self.context
            )

        return False


def get_logger(name: str, log_level: str = "INFO") -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name, log_level)

