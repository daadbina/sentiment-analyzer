"""Custom exceptions for canonicalizer-normalizer service."""


class NormalizationError(Exception):
    """Base exception for normalization errors."""

    def __init__(self, message: str, error_code: str = "NORMALIZATION_ERROR"):
        """Initialize exception."""
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class URLCanonicalizationError(NormalizationError):
    """Exception for URL canonicalization errors."""

    def __init__(self, message: str, url: str = "", error_code: str = "URL_CANONICALIZATION_ERROR"):
        """Initialize exception."""
        self.url = url
        super().__init__(message, error_code)


class PublisherResolutionError(NormalizationError):
    """Exception for publisher resolution errors."""

    def __init__(self, message: str, domain: str = "", error_code: str = "PUBLISHER_RESOLUTION_ERROR"):
        """Initialize exception."""
        self.domain = domain
        super().__init__(message, error_code)


class ContentNormalizationError(NormalizationError):
    """Exception for content normalization errors."""

    def __init__(self, message: str, error_code: str = "CONTENT_NORMALIZATION_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class MetadataEnrichmentError(NormalizationError):
    """Exception for metadata enrichment errors."""

    def __init__(self, message: str, error_code: str = "METADATA_ENRICHMENT_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class DomainClassificationError(NormalizationError):
    """Exception for domain classification errors."""

    def __init__(self, message: str, error_code: str = "DOMAIN_CLASSIFICATION_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class FuzzyDeduplicationError(NormalizationError):
    """Exception for fuzzy deduplication errors."""

    def __init__(self, message: str, error_code: str = "FUZZY_DEDUPLICATION_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class KafkaError(NormalizationError):
    """Exception for Kafka-related errors."""

    def __init__(self, message: str, topic: str = "", error_code: str = "KAFKA_ERROR"):
        """Initialize exception."""
        self.topic = topic
        super().__init__(message, error_code)


class DatabaseError(NormalizationError):
    """Exception for database-related errors."""

    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class CacheError(NormalizationError):
    """Exception for cache-related errors."""

    def __init__(self, message: str, error_code: str = "CACHE_ERROR"):
        """Initialize exception."""
        super().__init__(message, error_code)


class CircuitBreakerError(NormalizationError):
    """Exception for circuit breaker errors."""

    def __init__(self, message: str, service: str = "", error_code: str = "CIRCUIT_BREAKER_ERROR"):
        """Initialize exception."""
        self.service = service
        super().__init__(message, error_code)

