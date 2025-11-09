"""
Custom exception hierarchy for Predictor Online Inference Service.

All exceptions inherit from PredictionError base class for consistent error handling.
Each exception includes context information for debugging and monitoring.
"""

from typing import Any


class PredictionError(Exception):
    """
    Base exception for all prediction service errors.

    Attributes:
        message: Human-readable error message
        group_id: ID of the semantic group (optional)
        context: Additional context information for debugging
        trace_id: Distributed tracing identifier
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize prediction error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        super().__init__(message)
        self.message = message
        self.group_id = group_id
        self.context = context or {}
        self.trace_id = trace_id

        # Add group_id to context for backward compatibility
        if group_id:
            self.context["group_id"] = group_id

    def __str__(self) -> str:
        """Return string representation of error."""
        parts = [self.message]
        if self.trace_id:
            parts.append(f"trace_id={self.trace_id}")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"context=({context_str})")
        return " | ".join(parts)


class ModelLoadError(PredictionError):
    """
    Exception raised when model loading from MLflow fails.

    This includes failures in:
    - Model artifact download
    - Model deserialization
    - Model validation
    - Model version resolution
    """

    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        model_version: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize model load error.

        Args:
            message: Human-readable error message
            model_name: Name of the model that failed to load
            model_version: Version of the model that failed to load
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.model_name = model_name
        self.model_version = model_version
        context = context or {}
        if model_name:
            context["model_name"] = model_name
        if model_version:
            context["model_version"] = model_version
        super().__init__(message, context=context, trace_id=trace_id)


class FeatureError(PredictionError):
    """
    Base exception for feature-related errors.

    This is the parent class for all feature store and feature validation errors.
    """

    def __init__(
        self,
        message: str,
        feature_name: str | None = None,
        group_id: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize feature error.

        Args:
            message: Human-readable error message
            feature_name: Name of the feature that caused the error
            group_id: ID of the semantic group
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.feature_name = feature_name
        context = context or {}
        if feature_name:
            context["feature_name"] = feature_name
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class FeatureFetchError(FeatureError):
    """
    Exception raised when feature retrieval from Feast fails.

    This includes failures in:
    - Feast online store connection
    - Feature retrieval queries
    - Feature deserialization
    - Network timeouts
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        feature_names: list[str] | None = None,
        store_type: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize feature fetch error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            feature_names: Names of features that failed to fetch
            store_type: Type of feature store (online/offline)
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.feature_names = feature_names
        self.store_type = store_type
        context = context or {}
        if feature_names:
            context["feature_names"] = feature_names
        if store_type:
            context["store_type"] = store_type
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class FeatureValidationError(FeatureError):
    """
    Exception raised when feature validation fails.

    This includes failures in:
    - Feature schema validation
    - Feature completeness checks
    - Feature type verification
    - Feature range validation
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        missing_features: list[str] | None = None,
        invalid_features: dict[str, str] | None = None,
        validation_type: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize feature validation error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            missing_features: List of missing required features
            invalid_features: Dictionary of invalid features and reasons
            validation_type: Type of validation that failed
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.missing_features = missing_features
        self.invalid_features = invalid_features
        self.validation_type = validation_type
        context = context or {}
        if missing_features:
            context["missing_features"] = missing_features
        if invalid_features:
            context["invalid_features"] = invalid_features
        if validation_type:
            context["validation_type"] = validation_type
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class FeatureReconciliationError(FeatureError):
    """
    Exception raised when feature reconciliation between offline and online stores fails.

    This includes:
    - Mismatch between offline and online feature values
    - Reconciliation rate below threshold
    - Feature version inconsistencies
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        mismatched_features: dict[str, tuple] | None = None,
        reconciliation_rate: float | None = None,
        mismatch_rate: float | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize feature reconciliation error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            mismatched_features: Dictionary of mismatched features with (offline, online) values
            reconciliation_rate: Calculated reconciliation rate
            mismatch_rate: Calculated mismatch rate (for backward compatibility)
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.mismatched_features = mismatched_features
        self.reconciliation_rate = reconciliation_rate
        self.mismatch_rate = mismatch_rate or (1.0 - reconciliation_rate if reconciliation_rate is not None else None)
        context = context or {}
        if mismatched_features:
            context["mismatched_features"] = mismatched_features
        if reconciliation_rate is not None:
            context["reconciliation_rate"] = reconciliation_rate
        if self.mismatch_rate is not None:
            context["mismatch_rate"] = self.mismatch_rate
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class InferenceError(PredictionError):
    """
    Base exception for inference-related errors.

    This includes failures during model prediction execution.
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        model_version: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize inference error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            model_version: Version of the model used for inference
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if model_version:
            context["model_version"] = model_version
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class InferenceTimeoutError(InferenceError):
    """
    Exception raised when inference exceeds timeout threshold.

    This indicates performance issues that may require:
    - Model optimization
    - Resource scaling
    - Timeout adjustment
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        model_version: str | None = None,
        timeout_ms: int | None = None,
        timeout_seconds: int | None = None,
        elapsed_ms: int | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize inference timeout error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            model_version: Version of the model used for inference
            timeout_ms: Configured timeout in milliseconds
            timeout_seconds: Configured timeout in seconds (for backward compatibility)
            elapsed_ms: Actual elapsed time in milliseconds
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.timeout_ms = timeout_ms
        self.timeout_seconds = timeout_seconds or (timeout_ms // 1000 if timeout_ms is not None else None)
        self.elapsed_ms = elapsed_ms
        context = context or {}
        if timeout_ms is not None:
            context["timeout_ms"] = timeout_ms
        if self.timeout_seconds is not None:
            context["timeout_seconds"] = self.timeout_seconds
        if elapsed_ms is not None:
            context["elapsed_ms"] = elapsed_ms
        super().__init__(message, group_id, model_version, context, trace_id)


class LabelValidationError(PredictionError):
    """
    Exception raised when ground-truth label validation fails.

    This includes failures in:
    - Label schema validation
    - Label freshness checks
    - Label source license verification
    - Label confidence validation
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        label_source: str | None = None,
        validation_failures: list[str] | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize label validation error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            label_source: Source of the label (ACLED/GDELT/CoinGecko)
            validation_failures: List of validation failure reasons
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if label_source:
            context["label_source"] = label_source
        if validation_failures:
            context["validation_failures"] = validation_failures
        super().__init__(message, context, trace_id)


class LabelFetchError(PredictionError):
    """
    Exception raised when ground-truth label retrieval fails.

    This includes failures in:
    - PostgreSQL query execution
    - Kafka message consumption
    - Label deserialization
    - Network timeouts
    """

    def __init__(
        self,
        message: str,
        group_id: str | None = None,
        source: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize label fetch error.

        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            source: Source of the fetch attempt (postgres/kafka)
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.source = source
        context = context or {}
        if source:
            context["source"] = source
        super().__init__(message, group_id=group_id, context=context, trace_id=trace_id)


class CacheError(PredictionError):
    """
    Exception raised when Redis cache operations fail.

    This includes failures in:
    - Redis connection
    - Cache read/write operations
    - Cache invalidation
    - Serialization/deserialization
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        key: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize cache error.

        Args:
            message: Human-readable error message
            operation: Cache operation that failed (get/set/delete)
            key: Cache key involved in the operation
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.operation = operation
        self.key = key
        context = context or {}
        if operation:
            context["operation"] = operation
        if key:
            context["key"] = key
        super().__init__(message, context=context, trace_id=trace_id)


class KafkaError(PredictionError):
    """
    Exception raised when Kafka operations fail.

    This includes failures in:
    - Kafka connection
    - Message consumption
    - Message production
    - Offset management
    - Schema registry operations
    """

    def __init__(
        self,
        message: str,
        topic: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize Kafka error.

        Args:
            message: Human-readable error message
            topic: Kafka topic involved in the operation
            operation: Kafka operation that failed (consume/produce)
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.topic = topic
        self.operation = operation
        context = context or {}
        if topic:
            context["topic"] = topic
        if operation:
            context["operation"] = operation
        super().__init__(message, context=context, trace_id=trace_id)


class PostgresError(PredictionError):
    """
    Exception raised when PostgreSQL operations fail.

    This includes failures in:
    - Database connection
    - Query execution
    - Transaction management
    - Connection pool exhaustion
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        query: str | None = None,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize PostgreSQL error.

        Args:
            message: Human-readable error message
            operation: Database operation that failed (query/insert/update)
            query: SQL query that failed (truncated for logging)
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        self.operation = operation
        self.query = query
        context = context or {}
        if operation:
            context["operation"] = operation
        if query:
            # Truncate query for logging (max 200 chars)
            truncated_query = query[:200] + "..." if len(query) > 200 else query
            context["query"] = truncated_query
        super().__init__(message, context=context, trace_id=trace_id)


class ServiceError(PredictionError):
    """
    Exception raised when service-level operations fail.

    This includes failures in:
    - Service initialization
    - Service startup
    - Service shutdown
    - Component coordination
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize service error.

        Args:
            message: Human-readable error message
            details: Additional details about the error
            trace_id: Distributed tracing identifier
        """
        super().__init__(message, details, trace_id)


class ValidationError(PredictionError):
    """
    Exception raised when validation operations fail.

    This includes failures in:
    - Data validation
    - Schema validation
    - Business rule validation
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            details: Additional details about the validation failure
            trace_id: Distributed tracing identifier
        """
        super().__init__(message, details, trace_id)
