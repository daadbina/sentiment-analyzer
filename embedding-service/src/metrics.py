"""Prometheus metrics for Embedding Service."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create registry
registry = CollectorRegistry()

# Counters
embedding_messages_consumed_total = Counter(
    "embedding_messages_consumed_total",
    "Total messages consumed from news_canonical",
    registry=registry,
)

embedding_computed_total = Counter(
    "embedding_computed_total",
    "Total embeddings computed",
    ["model_name", "language"],
    registry=registry,
)

embedding_qdrant_writes_total = Counter(
    "embedding_qdrant_writes_total",
    "Total successful Qdrant writes",
    registry=registry,
)

embedding_qdrant_write_failures_total = Counter(
    "embedding_qdrant_write_failures_total",
    "Failed Qdrant writes",
    registry=registry,
)

embedding_validation_failures_total = Counter(
    "embedding_validation_failures_total",
    "Failed validation checks",
    ["check_type"],
    registry=registry,
)

embedding_model_load_total = Counter(
    "embedding_model_load_total",
    "Total model load attempts",
    ["model_name", "status"],
    registry=registry,
)

# Histograms
embedding_computation_duration_seconds = Histogram(
    "embedding_computation_duration_seconds",
    "Embedding computation latency",
    ["model_name", "device"],
    registry=registry,
)

embedding_batch_size = Histogram(
    "embedding_batch_size",
    "Distribution of batch sizes processed",
    registry=registry,
)

embedding_preprocessing_duration_seconds = Histogram(
    "embedding_preprocessing_duration_seconds",
    "Text preprocessing latency",
    registry=registry,
)

embedding_model_load_duration_seconds = Histogram(
    "embedding_model_load_duration_seconds",
    "Model loading time",
    ["model_name"],
    registry=registry,
)

# Gauges
embedding_gpu_memory_used_bytes = Gauge(
    "embedding_gpu_memory_used_bytes",
    "Current GPU memory usage",
    registry=registry,
)

embedding_gpu_utilization_percent = Gauge(
    "embedding_gpu_utilization_percent",
    "GPU utilization percentage",
    registry=registry,
)

embedding_consumer_lag = Gauge(
    "embedding_consumer_lag",
    "Kafka consumer lag",
    ["partition"],
    registry=registry,
)

embedding_circuit_breaker_state = Gauge(
    "embedding_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["dependency"],
    registry=registry,
)

embedding_drift_score = Gauge(
    "embedding_drift_score",
    "Drift detection score (KS statistic)",
    registry=registry,
)

embedding_cache_hit_rate = Gauge(
    "embedding_cache_hit_rate",
    "Model pool cache hit ratio",
    registry=registry,
)

embedding_truncation_rate = Gauge(
    "embedding_truncation_rate",
    "Ratio of truncated texts",
    registry=registry,
)

embedding_models_loaded = Gauge(
    "embedding_models_loaded",
    "Number of models currently loaded in cache",
    registry=registry,
)

