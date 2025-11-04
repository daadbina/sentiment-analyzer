"""Custom exception hierarchy for Feature Engineering Service."""


class FeatureError(Exception):
    """Base exception for feature engineering errors."""

    pass


class ExtractionError(FeatureError):
    """Raised when feature extraction fails."""

    pass


class TransformationError(FeatureError):
    """Raised when feature transformation fails."""

    pass


class ValidationError(FeatureError):
    """Raised when feature validation fails."""

    pass


class FeastWriteError(FeatureError):
    """Raised when writing to Feast fails."""

    pass


class RedisWriteError(FeatureError):
    """Raised when writing to Redis fails."""

    pass


class KafkaError(FeatureError):
    """Raised when Kafka operations fail."""

    pass


class ConfigurationError(FeatureError):
    """Raised when configuration is invalid."""

    pass


class DriftDetectionError(FeatureError):
    """Raised when drift detection fails."""

    pass


class ReconciliationError(FeatureError):
    """Raised when offline-online reconciliation fails."""

    pass


class PostgresError(FeatureError):
    """Raised when PostgreSQL operations fail."""

    pass
