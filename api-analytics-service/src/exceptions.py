"""Custom exception hierarchy for API Analytics Service.

Provides structured error handling with trace IDs and proper HTTP status codes.
"""

from typing import Optional, Dict, Any
from http import HTTPStatus


class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            trace_id: Trace ID for debugging
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.trace_id = trace_id
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "trace_id": self.trace_id,
            "details": self.details,
        }


class AuthError(APIError):
    """Authentication error (invalid credentials, missing token)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize authentication error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code="AUTH_ERROR",
            trace_id=trace_id,
            details=details,
        )


class AuthorizationError(APIError):
    """Authorization error (insufficient permissions)."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize authorization error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            trace_id=trace_id,
            details=details,
        )


class ValidationError(APIError):
    """Validation error (invalid input)."""

    def __init__(
        self,
        message: str = "Validation failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            trace_id=trace_id,
            details=details,
        )


class QueryError(APIError):
    """Database query error."""

    def __init__(
        self,
        message: str = "Query execution failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize query error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="QUERY_ERROR",
            trace_id=trace_id,
            details=details,
        )


class CacheError(APIError):
    """Cache operation error."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize cache error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
            trace_id=trace_id,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize rate limit error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            trace_id=trace_id,
            details=details,
        )


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(
        self,
        message: str = "Resource not found",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize not found error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            trace_id=trace_id,
            details=details,
        )


class DatabaseConnectionError(APIError):
    """Database connection error."""

    def __init__(
        self,
        message: str = "Database connection failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize database connection error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_code="DB_CONNECTION_ERROR",
            trace_id=trace_id,
            details=details,
        )


class ExportError(APIError):
    """Export operation error."""

    def __init__(
        self,
        message: str = "Export operation failed",
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize export error."""
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="EXPORT_ERROR",
            trace_id=trace_id,
            details=details,
        )

