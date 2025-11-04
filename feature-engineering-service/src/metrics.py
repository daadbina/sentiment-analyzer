"""Prometheus metrics for feature-engineering-service."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create registry
registry = CollectorRegistry()

# Counters
feature_groups_consumed_total = Counter(
    "feature_groups_consumed_total",
    "Total semantic groups consumed",
    registry=registry,
)

feature_computed_total = Counter(
    "feature_computed_total",
    "Total features computed by type",
    ["feature_type"],
    registry=registry,
)

feature_validation_failures_total = Counter(
    "feature_validation_failures_total",
    "Failed feature validations",
    ["feature_type"],
    registry=registry,
)

feature_feast_writes_total = Counter(
    "feature_feast_writes_total",
    "Successful Feast writes",
    registry=registry,
)

feature_feast_write_failures_total = Counter(
    "feature_feast_write_failures_total",
    "Failed Feast writes",
    registry=registry,
)

feature_redis_writes_total = Counter(
    "feature_redis_writes_total",
    "Successful Redis writes",
    registry=registry,
)

feature_redis_write_failures_total = Counter(
    "feature_redis_write_failures_total",
    "Failed Redis writes",
    registry=registry,
)

feature_reconciliation_mismatches_total = Counter(
    "feature_reconciliation_mismatches_total",
    "Offline-online mismatches",
    registry=registry,
)

# Histograms
feature_computation_duration_seconds = Histogram(
    "feature_computation_duration_seconds",
    "Feature computation latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=registry,
)

feature_extraction_duration_seconds = Histogram(
    "feature_extraction_duration_seconds",
    "Feature extraction latency",
    ["extractor_type"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=registry,
)

# Gauges
feature_drift_score = Gauge(
    "feature_drift_score",
    "Drift detection score (KS statistic)",
    ["feature_name"],
    registry=registry,
)

feature_consumer_lag = Gauge(
    "feature_consumer_lag",
    "Kafka consumer lag",
    registry=registry,
)

feature_batch_size = Gauge(
    "feature_batch_size",
    "Current batch size",
    registry=registry,
)

feature_processing_queue_size = Gauge(
    "feature_processing_queue_size",
    "Size of processing queue",
    registry=registry,
)


def record_group_consumed():
    """Record a semantic group consumption."""
    feature_groups_consumed_total.inc()


def record_feature_computed(feature_type: str):
    """Record a computed feature."""
    feature_computed_total.labels(feature_type=feature_type).inc()


def record_validation_failure(feature_type: str):
    """Record a validation failure."""
    feature_validation_failures_total.labels(feature_type=feature_type).inc()


def record_feast_write_success():
    """Record successful Feast write."""
    feature_feast_writes_total.inc()


def record_feast_write_failure():
    """Record failed Feast write."""
    feature_feast_write_failures_total.inc()


def record_redis_write_success():
    """Record successful Redis write."""
    feature_redis_writes_total.inc()


def record_redis_write_failure():
    """Record failed Redis write."""
    feature_redis_write_failures_total.inc()


def record_reconciliation_mismatch():
    """Record reconciliation mismatch."""
    feature_reconciliation_mismatches_total.inc()

