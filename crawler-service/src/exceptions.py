"""
Custom exception hierarchy for Crawler Service.

Provides structured error handling with specific exception types for
different failure modes.
"""


class CrawlerException(Exception):
    """
    Base exception for all Crawler Service errors.

    All other exceptions inherit from this class for consistent error handling.
    """

    def __init__(self, message: str, error_code: str = "CRAWLER_ERROR") -> None:
        """
        Initialize CrawlerException.

        Args:
            message: Human-readable error message.
            error_code: Machine-readable error code for logging and monitoring.
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of exception."""
        return f"[{self.error_code}] {self.message}"


class FetchError(CrawlerException):
    """
    Raised when HTTP fetch operation fails.

    Covers network errors, timeouts, and HTTP error responses.
    """

    def __init__(
        self,
        message: str,
        url: str = "",
        status_code: int = 0,
        error_code: str = "FETCH_ERROR",
    ) -> None:
        """
        Initialize FetchError.

        Args:
            message: Error description.
            url: URL that failed to fetch.
            status_code: HTTP status code if applicable.
            error_code: Machine-readable error code.
        """
        self.url = url
        self.status_code = status_code
        super().__init__(message, error_code)


class ParseError(CrawlerException):
    """
    Raised when article parsing fails.

    Covers malformed HTML, missing required fields, and parsing exceptions.
    """

    def __init__(
        self,
        message: str,
        parser_type: str = "",
        error_code: str = "PARSE_ERROR",
    ) -> None:
        """
        Initialize ParseError.

        Args:
            message: Error description.
            parser_type: Type of parser that failed (rss, html, etc.).
            error_code: Machine-readable error code.
        """
        self.parser_type = parser_type
        super().__init__(message, error_code)


class ValidationError(CrawlerException):
    """
    Raised when article validation fails.

    Covers schema validation, data quality checks, and business rule violations.
    """

    def __init__(
        self,
        message: str,
        field: str = "",
        value: str = "",
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        """
        Initialize ValidationError.

        Args:
            message: Error description.
            field: Field that failed validation.
            value: Value that failed validation.
            error_code: Machine-readable error code.
        """
        self.field = field
        self.value = value
        super().__init__(message, error_code)


class PublishError(CrawlerException):
    """
    Raised when Kafka publish operation fails.

    Covers producer errors, serialization failures, and broker issues.
    """

    def __init__(
        self,
        message: str,
        topic: str = "",
        error_code: str = "PUBLISH_ERROR",
    ) -> None:
        """
        Initialize PublishError.

        Args:
            message: Error description.
            topic: Kafka topic that failed to publish to.
            error_code: Machine-readable error code.
        """
        self.topic = topic
        super().__init__(message, error_code)


class ConfigError(CrawlerException):
    """
    Raised when configuration is invalid or missing.

    Covers missing environment variables, invalid settings, and config file errors.
    """

    def __init__(
        self,
        message: str,
        config_key: str = "",
        error_code: str = "CONFIG_ERROR",
    ) -> None:
        """
        Initialize ConfigError.

        Args:
            message: Error description.
            config_key: Configuration key that is invalid or missing.
            error_code: Machine-readable error code.
        """
        self.config_key = config_key
        super().__init__(message, error_code)


class SchemaError(CrawlerException):
    """
    Raised when Avro schema validation fails.

    Covers schema registry errors and schema compatibility issues.
    """

    def __init__(
        self,
        message: str,
        schema_version: str = "",
        error_code: str = "SCHEMA_ERROR",
    ) -> None:
        """
        Initialize SchemaError.

        Args:
            message: Error description.
            schema_version: Schema version that failed validation.
            error_code: Machine-readable error code.
        """
        self.schema_version = schema_version
        super().__init__(message, error_code)


class CircuitBreakerOpenError(CrawlerException):
    """
    Raised when circuit breaker is open for a feed source.

    Indicates that a source has failed too many times and is temporarily disabled.
    """

    def __init__(
        self,
        message: str,
        feed_id: str = "",
        error_code: str = "CIRCUIT_BREAKER_OPEN",
    ) -> None:
        """
        Initialize CircuitBreakerOpenError.

        Args:
            message: Error description.
            feed_id: Feed source that triggered circuit breaker.
            error_code: Machine-readable error code.
        """
        self.feed_id = feed_id
        super().__init__(message, error_code)


class LanguageDetectionError(CrawlerException):
    """
    Raised when language detection fails or confidence is too low.

    Covers language detection service errors and low confidence results.
    """

    def __init__(
        self,
        message: str,
        detected_language: str = "",
        confidence: float = 0.0,
        error_code: str = "LANGUAGE_DETECTION_ERROR",
    ) -> None:
        """
        Initialize LanguageDetectionError.

        Args:
            message: Error description.
            detected_language: Detected language code.
            confidence: Detection confidence score.
            error_code: Machine-readable error code.
        """
        self.detected_language = detected_language
        self.confidence = confidence
        super().__init__(message, error_code)


class DuplicateArticleError(CrawlerException):
    """
    Raised when a duplicate article is detected.

    Indicates that the article has already been crawled and should be skipped.
    """

    def __init__(
        self,
        message: str,
        article_id: str = "",
        error_code: str = "DUPLICATE_ARTICLE",
    ) -> None:
        """
        Initialize DuplicateArticleError.

        Args:
            message: Error description.
            article_id: ID of the duplicate article.
            error_code: Machine-readable error code.
        """
        self.article_id = article_id
        super().__init__(message, error_code)


class NormalizationError(CrawlerException):
    """
    Raised when article normalization fails.

    Covers data transformation errors and normalization failures.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "NORMALIZATION_ERROR",
    ) -> None:
        """
        Initialize NormalizationError.

        Args:
            message: Error description.
            error_code: Machine-readable error code.
        """
        super().__init__(message, error_code)
