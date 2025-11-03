"""Prometheus metrics for NER Entity Linking Service."""

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict

# Counters
ner_messages_consumed_total = Counter(
    "ner_messages_consumed_total",
    "Total messages consumed from news_canonical",
)

ner_entities_extracted_total = Counter(
    "ner_entities_extracted_total",
    "Total entities extracted by type and language",
    ["entity_type", "language"],
)

ner_entities_linked_total = Counter(
    "ner_entities_linked_total",
    "Total entities successfully linked by source",
    ["source"],
)

ner_entities_unlinked_total = Counter(
    "ner_entities_unlinked_total",
    "Total entities without knowledge base links",
)

ner_actors_created_total = Counter(
    "ner_actors_created_total",
    "New actor records created",
)

ner_actors_updated_total = Counter(
    "ner_actors_updated_total",
    "Existing actor records updated",
)

ner_actor_repository_errors_total = Counter(
    "ner_actor_repository_errors_total",
    "Failed actor repository operations",
)

# Histograms
ner_extraction_duration_seconds = Histogram(
    "ner_extraction_duration_seconds",
    "NER extraction latency by language and model",
    ["language", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

ner_linking_duration_seconds = Histogram(
    "ner_linking_duration_seconds",
    "Entity linking latency by source",
    ["source"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

ner_coverage_score = Histogram(
    "ner_coverage_score",
    "Distribution of coverage scores by language",
    ["language"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

ner_model_load_duration_seconds = Histogram(
    "ner_model_load_duration_seconds",
    "Model loading time by language",
    ["language"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0),
)

# Gauges
ner_linking_success_rate = Gauge(
    "ner_linking_success_rate",
    "Ratio of successfully linked entities",
)

ner_consumer_lag = Gauge(
    "ner_consumer_lag",
    "Kafka consumer lag by partition",
    ["partition"],
)

ner_circuit_breaker_state = Gauge(
    "ner_circuit_breaker_state",
    "Circuit breaker state by dependency (0=closed, 1=open, 2=half-open)",
    ["dependency"],
)

ner_cache_hit_rate = Gauge(
    "ner_cache_hit_rate",
    "Redis cache hit ratio by operation",
    ["operation"],
)


class MetricsCollector:
    """Centralized metrics collection."""

    @staticmethod
    def record_message_consumed() -> None:
        """Record consumed message."""
        ner_messages_consumed_total.inc()

    @staticmethod
    def record_entity_extracted(entity_type: str, language: str) -> None:
        """Record extracted entity."""
        ner_entities_extracted_total.labels(entity_type=entity_type, language=language).inc()

    @staticmethod
    def record_entity_linked(source: str) -> None:
        """Record linked entity."""
        ner_entities_linked_total.labels(source=source).inc()

    @staticmethod
    def record_entity_unlinked() -> None:
        """Record unlinked entity."""
        ner_entities_unlinked_total.inc()

    @staticmethod
    def record_actor_created() -> None:
        """Record created actor."""
        ner_actors_created_total.inc()

    @staticmethod
    def record_actor_updated() -> None:
        """Record updated actor."""
        ner_actors_updated_total.inc()

    @staticmethod
    def record_extraction_duration(duration_seconds: float, language: str, model: str) -> None:
        """Record extraction duration."""
        ner_extraction_duration_seconds.labels(language=language, model=model).observe(
            duration_seconds
        )

    @staticmethod
    def record_linking_duration(duration_seconds: float, source: str) -> None:
        """Record linking duration."""
        ner_linking_duration_seconds.labels(source=source).observe(duration_seconds)

    @staticmethod
    def record_coverage_score(score: float, language: str) -> None:
        """Record coverage score."""
        ner_coverage_score.labels(language=language).observe(score)

    @staticmethod
    def record_model_load_duration(duration_seconds: float, language: str) -> None:
        """Record model load duration."""
        ner_model_load_duration_seconds.labels(language=language).observe(duration_seconds)

    @staticmethod
    def set_linking_success_rate(rate: float) -> None:
        """Set linking success rate."""
        ner_linking_success_rate.set(rate)

    @staticmethod
    def set_consumer_lag(partition: int, lag: int) -> None:
        """Set consumer lag."""
        ner_consumer_lag.labels(partition=str(partition)).set(lag)

    @staticmethod
    def set_circuit_breaker_state(dependency: str, state: int) -> None:
        """Set circuit breaker state."""
        ner_circuit_breaker_state.labels(dependency=dependency).set(state)

    @staticmethod
    def set_cache_hit_rate(operation: str, rate: float) -> None:
        """Set cache hit rate."""
        ner_cache_hit_rate.labels(operation=operation).set(rate)

    @staticmethod
    def record_repository_error() -> None:
        """Record repository error."""
        ner_actor_repository_errors_total.inc()

