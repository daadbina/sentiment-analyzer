"""
Custom exception hierarchy for Predictor Online Inference Service.

All exceptions inherit from PredictionError base class for consistent error handling.
Each exception includes context information for debugging and monitoring.
"""

from typing import Optional, Dict, Any


class PredictionError(Exception):
    """
    Base exception for all prediction service errors.
    
    Attributes:
        message: Human-readable error message
        context: Additional context information for debugging
        trace_id: Distributed tracing identifier
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize prediction error.
        
        Args:
            message: Human-readable error message
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.trace_id = trace_id
    
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
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if model_name:
            context["model_name"] = model_name
        if model_version:
            context["model_version"] = model_version
        super().__init__(message, context, trace_id)


class FeatureError(PredictionError):
    """
    Base exception for feature-related errors.
    
    This is the parent class for all feature store and feature validation errors.
    """
    pass


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
        group_id: Optional[str] = None,
        feature_names: Optional[list[str]] = None,
        store_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if feature_names:
            context["feature_names"] = feature_names
        if store_type:
            context["store_type"] = store_type
        super().__init__(message, context, trace_id)


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
        group_id: Optional[str] = None,
        missing_features: Optional[list[str]] = None,
        invalid_features: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize feature validation error.
        
        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            missing_features: List of missing required features
            invalid_features: Dictionary of invalid features and reasons
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if missing_features:
            context["missing_features"] = missing_features
        if invalid_features:
            context["invalid_features"] = invalid_features
        super().__init__(message, context, trace_id)


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
        group_id: Optional[str] = None,
        mismatched_features: Optional[Dict[str, tuple]] = None,
        reconciliation_rate: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize feature reconciliation error.
        
        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            mismatched_features: Dictionary of mismatched features with (offline, online) values
            reconciliation_rate: Calculated reconciliation rate
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if mismatched_features:
            context["mismatched_features"] = mismatched_features
        if reconciliation_rate is not None:
            context["reconciliation_rate"] = reconciliation_rate
        super().__init__(message, context, trace_id)


class InferenceError(PredictionError):
    """
    Base exception for inference-related errors.
    
    This includes failures during model prediction execution.
    """
    
    def __init__(
        self,
        message: str,
        group_id: Optional[str] = None,
        model_version: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        super().__init__(message, context, trace_id)


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
        group_id: Optional[str] = None,
        model_version: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        elapsed_ms: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize inference timeout error.
        
        Args:
            message: Human-readable error message
            group_id: ID of the semantic group
            model_version: Version of the model used for inference
            timeout_ms: Configured timeout in milliseconds
            elapsed_ms: Actual elapsed time in milliseconds
            context: Additional context information
            trace_id: Distributed tracing identifier
        """
        context = context or {}
        if timeout_ms is not None:
            context["timeout_ms"] = timeout_ms
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
        group_id: Optional[str] = None,
        label_source: Optional[str] = None,
        validation_failures: Optional[list[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        group_id: Optional[str] = None,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if group_id:
            context["group_id"] = group_id
        if source:
            context["source"] = source
        super().__init__(message, context, trace_id)


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
        operation: Optional[str] = None,
        key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if operation:
            context["operation"] = operation
        if key:
            context["key"] = key
        super().__init__(message, context, trace_id)


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
        topic: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if topic:
            context["topic"] = topic
        if operation:
            context["operation"] = operation
        super().__init__(message, context, trace_id)


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
        operation: Optional[str] = None,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        context = context or {}
        if operation:
            context["operation"] = operation
        if query:
            # Truncate query for logging (max 200 chars)
            context["query"] = query[:200] + "..." if len(query) > 200 else query
        super().__init__(message, context, trace_id)


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
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
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
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            details: Additional details about the validation failure
            trace_id: Distributed tracing identifier
        """
        super().__init__(message, details, trace_id)

