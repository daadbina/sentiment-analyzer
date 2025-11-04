"""Custom exceptions for Embedding Service."""


class EmbeddingError(Exception):
    """Base exception for embedding service errors."""

    pass


class ModelLoadError(EmbeddingError):
    """Raised when model loading fails."""

    pass


class ModelNotFoundError(ModelLoadError):
    """Raised when requested model is not found."""

    pass


class PreprocessingError(EmbeddingError):
    """Raised when text preprocessing fails."""

    pass


class TokenizationError(PreprocessingError):
    """Raised when tokenization fails."""

    pass


class TruncationError(PreprocessingError):
    """Raised when text truncation fails."""

    pass


class EmbeddingComputationError(EmbeddingError):
    """Raised when embedding computation fails."""

    pass


class GPUError(EmbeddingComputationError):
    """Raised when GPU operations fail."""

    pass


class OutOfMemoryError(GPUError):
    """Raised when GPU/CPU runs out of memory."""

    pass


class ValidationError(EmbeddingError):
    """Raised when embedding validation fails."""

    pass


class QdrantWriteError(EmbeddingError):
    """Raised when Qdrant write operation fails."""

    pass


class QdrantConnectionError(QdrantWriteError):
    """Raised when Qdrant connection fails."""

    pass


class KafkaError(EmbeddingError):
    """Raised when Kafka operations fail."""

    pass


class KafkaConsumerError(KafkaError):
    """Raised when Kafka consumer fails."""

    pass


class KafkaProducerError(KafkaError):
    """Raised when Kafka producer fails."""

    pass


class DatabaseError(EmbeddingError):
    """Raised when database operations fail."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class CircuitBreakerOpenError(EmbeddingError):
    """Raised when circuit breaker is open."""

    pass


class ConfigurationError(EmbeddingError):
    """Raised when configuration is invalid."""

    pass


class DriftDetectionError(EmbeddingError):
    """Raised when drift detection fails."""

    pass


class TimeoutError(EmbeddingError):
    """Raised when operation times out."""

    pass

