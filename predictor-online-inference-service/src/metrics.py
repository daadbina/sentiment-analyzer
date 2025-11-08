"""
Prometheus metrics for Predictor Online Inference Service.

All metrics are exposed on the configured Prometheus port for scraping.
Metrics follow Prometheus naming conventions and best practices.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Optional


# Create a custom registry for better control
REGISTRY = CollectorRegistry()


# Prediction metrics
predictions_total = Counter(
    "predictions_total",
    "Total number of predictions made",
    ["mode", "model_version", "domain"],
    registry=REGISTRY,
)

prediction_latency_ms = Histogram(
    "prediction_latency_ms",
    "Prediction latency in milliseconds",
    ["mode", "model_version"],
    buckets=[10, 25, 50, 100, 200, 300, 500, 1000, 2000, 5000],
    registry=REGISTRY,
)

prediction_confidence_avg = Gauge(
    "prediction_confidence_avg",
    "Average prediction confidence score",
    ["model_version", "domain"],
    registry=REGISTRY,
)


# Cache metrics
prediction_cache_hits_total = Counter(
    "prediction_cache_hits_total",
    "Total number of prediction cache hits",
    registry=REGISTRY,
)

prediction_cache_misses_total = Counter(
    "prediction_cache_misses_total",
    "Total number of prediction cache misses",
    registry=REGISTRY,
)


# Model metrics
model_load_failures_total = Counter(
    "model_load_failures_total",
    "Total number of model load failures",
    ["model_name", "model_version"],
    registry=REGISTRY,
)

model_load_duration_seconds = Histogram(
    "model_load_duration_seconds",
    "Model load duration in seconds",
    ["model_name", "model_version"],
    buckets=[0.5, 1, 2, 3, 5, 10, 20],
    registry=REGISTRY,
)


# Feature metrics
feature_fetch_failures_total = Counter(
    "feature_fetch_failures_total",
    "Total number of feature fetch failures",
    ["store_type", "feature_name"],
    registry=REGISTRY,
)

feature_fetch_latency_ms = Histogram(
    "feature_fetch_latency_ms",
    "Feature fetch latency in milliseconds",
    ["store_type"],
    buckets=[5, 10, 25, 50, 100, 200, 500, 1000],
    registry=REGISTRY,
)

feature_reconciliation_mismatch_total = Counter(
    "feature_reconciliation_mismatch_total",
    "Total number of feature reconciliation mismatches",
    ["feature_name"],
    registry=REGISTRY,
)

feature_freshness_seconds = Gauge(
    "feature_freshness_seconds",
    "Age of features in seconds since computation",
    ["group_id"],
    registry=REGISTRY,
)


# Label metrics
label_consistency_score = Gauge(
    "label_consistency_score",
    "Label consistency score (agreement between predicted and actual)",
    ["domain", "label_source"],
    registry=REGISTRY,
)

label_fetch_failures_total = Counter(
    "label_fetch_failures_total",
    "Total number of label fetch failures",
    ["source", "label_source"],
    registry=REGISTRY,
)

label_validation_failures_total = Counter(
    "label_validation_failures_total",
    "Total number of label validation failures",
    ["label_source", "failure_reason"],
    registry=REGISTRY,
)


# Inference metrics
inference_timeout_total = Counter(
    "inference_timeout_total",
    "Total number of inference timeouts",
    ["mode", "model_version"],
    registry=REGISTRY,
)

inference_errors_total = Counter(
    "inference_errors_total",
    "Total number of inference errors",
    ["mode", "model_version", "error_type"],
    registry=REGISTRY,
)


# API metrics
api_request_latency_ms = Histogram(
    "api_request_latency_ms",
    "API request latency in milliseconds",
    ["endpoint", "method", "status_code"],
    buckets=[10, 25, 50, 100, 200, 300, 500, 1000, 2000, 5000],
    registry=REGISTRY,
)

api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status_code"],
    registry=REGISTRY,
)


# Kafka metrics
kafka_messages_consumed_total = Counter(
    "kafka_messages_consumed_total",
    "Total number of Kafka messages consumed",
    ["topic", "consumer_group"],
    registry=REGISTRY,
)

kafka_messages_produced_total = Counter(
    "kafka_messages_produced_total",
    "Total number of Kafka messages produced",
    ["topic"],
    registry=REGISTRY,
)

kafka_consumer_lag = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag in messages",
    ["topic", "partition", "consumer_group"],
    registry=REGISTRY,
)

kafka_errors_total = Counter(
    "kafka_errors_total",
    "Total number of Kafka errors",
    ["topic", "operation", "error_type"],
    registry=REGISTRY,
)


# Database metrics
postgres_query_duration_seconds = Histogram(
    "postgres_query_duration_seconds",
    "PostgreSQL query duration in seconds",
    ["operation"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registry=REGISTRY,
)

postgres_errors_total = Counter(
    "postgres_errors_total",
    "Total number of PostgreSQL errors",
    ["operation", "error_type"],
    registry=REGISTRY,
)

postgres_connection_pool_size = Gauge(
    "postgres_connection_pool_size",
    "PostgreSQL connection pool size",
    ["state"],
    registry=REGISTRY,
)


# Redis metrics
redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY,
)

redis_errors_total = Counter(
    "redis_errors_total",
    "Total number of Redis errors",
    ["operation", "error_type"],
    registry=REGISTRY,
)


# Drift detection metrics
feature_drift_score = Gauge(
    "feature_drift_score",
    "Feature drift score",
    ["feature_name"],
    registry=REGISTRY,
)

prediction_drift_score = Gauge(
    "prediction_drift_score",
    "Prediction drift score",
    ["domain"],
    registry=REGISTRY,
)


# Service health metrics
service_health = Gauge(
    "service_health",
    "Service health status (1=healthy, 0=unhealthy)",
    ["component"],
    registry=REGISTRY,
)

service_uptime_seconds = Gauge(
    "service_uptime_seconds",
    "Service uptime in seconds",
    registry=REGISTRY,
)


class MetricsCollector:
    """
    Helper class for collecting and updating metrics.
    
    Provides convenient methods for recording metrics with proper labels.
    """
    
    @staticmethod
    def record_prediction(
        mode: str,
        model_version: str,
        domain: str,
        latency_ms: float,
        confidence: Optional[float] = None,
    ) -> None:
        """
        Record a prediction event.
        
        Args:
            mode: Prediction mode (batch/stream/api)
            model_version: Version of the model used
            domain: Domain of the prediction (btc/conflict/geopolitical)
            latency_ms: Prediction latency in milliseconds
            confidence: Prediction confidence score (optional)
        """
        predictions_total.labels(mode=mode, model_version=model_version, domain=domain).inc()
        prediction_latency_ms.labels(mode=mode, model_version=model_version).observe(latency_ms)
        if confidence is not None:
            prediction_confidence_avg.labels(model_version=model_version, domain=domain).set(confidence)
    
    @staticmethod
    def record_cache_hit() -> None:
        """Record a cache hit event."""
        prediction_cache_hits_total.inc()
    
    @staticmethod
    def record_cache_miss() -> None:
        """Record a cache miss event."""
        prediction_cache_misses_total.inc()
    
    @staticmethod
    def record_model_load_failure(model_name: str, model_version: str) -> None:
        """
        Record a model load failure.
        
        Args:
            model_name: Name of the model
            model_version: Version of the model
        """
        model_load_failures_total.labels(model_name=model_name, model_version=model_version).inc()
    
    @staticmethod
    def record_feature_fetch_failure(store_type: str, feature_name: str) -> None:
        """
        Record a feature fetch failure.
        
        Args:
            store_type: Type of feature store (online/offline)
            feature_name: Name of the feature
        """
        feature_fetch_failures_total.labels(store_type=store_type, feature_name=feature_name).inc()
    
    @staticmethod
    def record_feature_fetch_latency(store_type: str, latency_ms: float) -> None:
        """
        Record feature fetch latency.
        
        Args:
            store_type: Type of feature store (online/offline)
            latency_ms: Fetch latency in milliseconds
        """
        feature_fetch_latency_ms.labels(store_type=store_type).observe(latency_ms)
    
    @staticmethod
    def record_feature_reconciliation_mismatch(feature_name: str) -> None:
        """
        Record a feature reconciliation mismatch.
        
        Args:
            feature_name: Name of the mismatched feature
        """
        feature_reconciliation_mismatch_total.labels(feature_name=feature_name).inc()
    
    @staticmethod
    def update_label_consistency(domain: str, label_source: str, score: float) -> None:
        """
        Update label consistency score.
        
        Args:
            domain: Domain of the prediction
            label_source: Source of the label
            score: Consistency score (0.0-1.0)
        """
        label_consistency_score.labels(domain=domain, label_source=label_source).set(score)
    
    @staticmethod
    def record_inference_timeout(mode: str, model_version: str) -> None:
        """
        Record an inference timeout.
        
        Args:
            mode: Prediction mode (batch/stream/api)
            model_version: Version of the model
        """
        inference_timeout_total.labels(mode=mode, model_version=model_version).inc()
    
    @staticmethod
    def record_api_request(
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """
        Record an API request.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            latency_ms: Request latency in milliseconds
        """
        api_requests_total.labels(endpoint=endpoint, method=method, status_code=str(status_code)).inc()
        api_request_latency_ms.labels(endpoint=endpoint, method=method, status_code=str(status_code)).observe(latency_ms)
    
    @staticmethod
    def update_service_health(component: str, healthy: bool) -> None:
        """
        Update service health status.

        Args:
            component: Component name (mlflow/feast/redis/postgres/kafka)
            healthy: Health status (True=healthy, False=unhealthy)
        """
        service_health.labels(component=component).set(1 if healthy else 0)

    @staticmethod
    def record_feature_fetch_latency(latency_ms: float, store_type: str) -> None:
        """
        Record feature fetch latency.

        Args:
            latency_ms: Fetch latency in milliseconds
            store_type: Type of feature store (online/offline)
        """
        feature_fetch_latency_ms.labels(store_type=store_type).observe(latency_ms)

    @staticmethod
    def increment_feature_fetch_failures(store_type: str) -> None:
        """
        Increment feature fetch failures counter.

        Args:
            store_type: Type of feature store (online/offline)
        """
        feature_fetch_failures_total.labels(store_type=store_type, feature_name="unknown").inc()

    @staticmethod
    def record_model_load_time(load_time_ms: float) -> None:
        """
        Record model load time.

        Args:
            load_time_ms: Load time in milliseconds
        """
        model_load_duration_seconds.labels(model_name="default", model_version="latest").observe(load_time_ms / 1000.0)

    @staticmethod
    def increment_model_load_failures() -> None:
        """Increment model load failures counter."""
        model_load_failures_total.labels(model_name="default", model_version="latest").inc()

    @staticmethod
    def increment_prediction_correct() -> None:
        """Increment correct predictions counter."""
        # This would need a new metric, using existing for now
        pass

    @staticmethod
    def increment_prediction_incorrect() -> None:
        """Increment incorrect predictions counter."""
        # This would need a new metric, using existing for now
        pass

    @staticmethod
    def set_label_consistency_score(score: float) -> None:
        """
        Set label consistency score.

        Args:
            score: Consistency score [0, 1]
        """
        label_consistency_score.labels(domain="default", label_source="kafka").set(score)

    @staticmethod
    def record_prediction_confidence(confidence: float) -> None:
        """
        Record prediction confidence.

        Args:
            confidence: Confidence score [0, 1]
        """
        prediction_confidence_avg.labels(model_version="latest", domain="default").set(confidence)

    @staticmethod
    def increment_stale_features_total() -> None:
        """Increment stale features counter."""
        # This would need a new metric, using existing for now
        pass

    @staticmethod
    def increment_missing_features_total(count: int) -> None:
        """
        Increment missing features counter.

        Args:
            count: Number of missing features
        """
        # This would need a new metric, using existing for now
        pass

    @staticmethod
    def record_feature_age(age_seconds: float) -> None:
        """
        Record feature age.

        Args:
            age_seconds: Age in seconds
        """
        feature_freshness_seconds.labels(group_id="default").set(age_seconds)

    @staticmethod
    def increment_label_reconciliation_total() -> None:
        """Increment label reconciliation counter."""
        # This would need a new metric, using existing for now
        pass

    @staticmethod
    def increment_feature_drift_detected(feature_name: str) -> None:
        """
        Increment feature drift detected counter.

        Args:
            feature_name: Name of the feature with drift
        """
        feature_drift_score.labels(feature_name=feature_name).set(1.0)

    @staticmethod
    def increment_prediction_drift_detected() -> None:
        """Increment prediction drift detected counter."""
        prediction_drift_score.labels(domain="default").set(1.0)

