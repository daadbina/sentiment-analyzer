"""Exception hierarchy for Ingest Validator Service."""

from typing import Optional, Dict, Any


class ValidationError(Exception):
    """Base exception for validation errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        severity: str = "ERROR",
        retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            error_code: Unique error code (e.g., "R1_TIMESTAMP_INVALID")
            severity: ERROR, WARNING, or CRITICAL
            retry_count: Number of retry attempts
            context: Additional context information
        """
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.retry_count = retry_count
        self.context = context or {}
        super().__init__(self.message)


class TimestampValidationError(ValidationError):
    """Raised when timestamp validation fails."""

    def __init__(
        self,
        message: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R1_TIMESTAMP_INVALID",
            severity=severity,
            context=context,
        )


class LanguageDetectionError(ValidationError):
    """Raised when language detection fails."""

    def __init__(
        self,
        message: str,
        severity: str = "WARNING",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R2_LANGUAGE_DETECTION_FAILED",
            severity=severity,
            context=context,
        )


class DuplicateDetectionError(ValidationError):
    """Raised when duplicate detection fails."""

    def __init__(
        self,
        message: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R3_DUPLICATE_DETECTED",
            severity=severity,
            context=context,
        )


class EncodingValidationError(ValidationError):
    """Raised when encoding validation fails."""

    def __init__(
        self,
        message: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R9_ENCODING_INVALID",
            severity=severity,
            context=context,
        )


class SourceVerificationError(ValidationError):
    """Raised when source verification fails."""

    def __init__(
        self,
        message: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R6_SOURCE_UNVERIFIED",
            severity=severity,
            context=context,
        )


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""

    def __init__(
        self,
        message: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="R12_SCHEMA_INVALID",
            severity=severity,
            context=context,
        )


class ContentQualityError(ValidationError):
    """Raised when content quality checks fail."""

    def __init__(
        self,
        message: str,
        severity: str = "WARNING",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONTENT_QUALITY_LOW",
            severity=severity,
            context=context,
        )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker open for service: {service_name}")


class KafkaError(Exception):
    """Raised when Kafka operations fail."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class CacheError(Exception):
    """Raised when cache operations fail."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class DatabaseError(Exception):
    """Raised when database operations fail."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)
