"""Structured logging with correlation IDs."""

import logging
import json
import uuid
from typing import Any, Optional
from datetime import datetime, timezone
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


class StructuredLogger:
    """Logger with structured JSON output and correlation IDs."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.name = name

    def _get_correlation_id(self) -> str:
        """Get or create correlation ID.

        Returns:
            Correlation ID
        """
        correlation_id = correlation_id_var.get()
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            correlation_id_var.set(correlation_id)
        return correlation_id

    def _format_message(
        self,
        message: str,
        level: str,
        **kwargs
    ) -> str:
        """Format message as JSON.

        Args:
            message: Log message
            level: Log level
            **kwargs: Additional fields

        Returns:
            JSON formatted message
        """
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'logger': self.name,
            'message': message,
            'correlation_id': self._get_correlation_id(),
            **kwargs,
        }
        return json.dumps(log_entry)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message.

        Args:
            message: Log message
            **kwargs: Additional fields
        """
        self.logger.debug(self._format_message(message, 'DEBUG', **kwargs))

    def info(self, message: str, **kwargs) -> None:
        """Log info message.

        Args:
            message: Log message
            **kwargs: Additional fields
        """
        self.logger.info(self._format_message(message, 'INFO', **kwargs))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message.

        Args:
            message: Log message
            **kwargs: Additional fields
        """
        self.logger.warning(self._format_message(message, 'WARNING', **kwargs))

    def error(self, message: str, **kwargs) -> None:
        """Log error message.

        Args:
            message: Log message
            **kwargs: Additional fields
        """
        self.logger.error(self._format_message(message, 'ERROR', **kwargs))

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message.

        Args:
            message: Log message
            **kwargs: Additional fields
        """
        self.logger.critical(self._format_message(message, 'CRITICAL', **kwargs))

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Set correlation ID for current context.

        Args:
            correlation_id: Correlation ID
        """
        correlation_id_var.set(correlation_id)

    @staticmethod
    def get_correlation_id() -> str:
        """Get correlation ID for current context.

        Returns:
            Correlation ID
        """
        return correlation_id_var.get()


class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, name: str):
        """Initialize performance logger.

        Args:
            name: Logger name
        """
        self.logger = StructuredLogger(name)

    def log_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        **kwargs
    ) -> None:
        """Log operation performance.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **kwargs: Additional fields
        """
        self.logger.info(
            f"Operation completed: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            **kwargs,
        )

    def log_cache_hit(self, cache_type: str, key: str) -> None:
        """Log cache hit.

        Args:
            cache_type: Type of cache
            key: Cache key
        """
        self.logger.debug(
            f"Cache hit: {cache_type}",
            cache_type=cache_type,
            cache_key=key,
            event='cache_hit',
        )

    def log_cache_miss(self, cache_type: str, key: str) -> None:
        """Log cache miss.

        Args:
            cache_type: Type of cache
            key: Cache key
        """
        self.logger.debug(
            f"Cache miss: {cache_type}",
            cache_type=cache_type,
            cache_key=key,
            event='cache_miss',
        )

    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int,
    ) -> None:
        """Log database operation.

        Args:
            operation: Operation type (INSERT, UPDATE, DELETE, SELECT)
            table: Table name
            duration_ms: Duration in milliseconds
            rows_affected: Number of rows affected
        """
        self.logger.info(
            f"Database operation: {operation}",
            operation=operation,
            table=table,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            event='database_operation',
        )

    def log_external_api_call(
        self,
        api_name: str,
        endpoint: str,
        duration_ms: float,
        status_code: int,
    ) -> None:
        """Log external API call.

        Args:
            api_name: API name
            endpoint: API endpoint
            duration_ms: Duration in milliseconds
            status_code: HTTP status code
        """
        self.logger.info(
            f"External API call: {api_name}",
            api_name=api_name,
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=status_code,
            event='external_api_call',
        )

    def log_error_with_context(
        self,
        error: Exception,
        context: str,
        **kwargs
    ) -> None:
        """Log error with context.

        Args:
            error: Exception
            context: Error context
            **kwargs: Additional fields
        """
        self.logger.error(
            f"Error in {context}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            **kwargs,
        )

