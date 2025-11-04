"""Non-Functional Requirements metrics collection."""

import logging
import time
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, REGISTRY

logger = logging.getLogger(__name__)

# Performance Metrics
try:
    extraction_latency = Histogram(
        "ner_extraction_latency_seconds",
        "Entity extraction latency in seconds",
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    )
except ValueError:
    extraction_latency = REGISTRY._names_to_collectors.get("ner_extraction_latency_seconds")

try:
    linking_latency = Histogram(
        "ner_linking_latency_seconds",
        "Entity linking latency in seconds",
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    )
except ValueError:
    linking_latency = REGISTRY._names_to_collectors.get("ner_linking_latency_seconds")

try:
    total_latency = Histogram(
        "ner_total_latency_seconds",
        "Total processing latency in seconds",
        buckets=(1.0, 2.0, 5.0, 8.0, 12.0, 20.0),
    )
except ValueError:
    total_latency = REGISTRY._names_to_collectors.get("ner_total_latency_seconds")

# Throughput Metrics
try:
    articles_processed = Counter(
        "ner_articles_processed_total",
        "Total articles processed",
    )
except ValueError:
    articles_processed = REGISTRY._names_to_collectors.get("ner_articles_processed_total")

try:
    entities_extracted = Counter(
        "ner_entities_extracted_total",
        "Total entities extracted",
    )
except ValueError:
    entities_extracted = REGISTRY._names_to_collectors.get("ner_entities_extracted_total")

try:
    entities_linked = Counter(
        "ner_entities_linked_total",
        "Total entities successfully linked",
    )
except ValueError:
    entities_linked = REGISTRY._names_to_collectors.get("ner_entities_linked_total")

try:
    messages_consumed = Counter(
        "ner_messages_consumed_total",
        "Total messages consumed from Kafka",
    )
except ValueError:
    messages_consumed = REGISTRY._names_to_collectors.get("ner_messages_consumed_total")

try:
    actors_created = Counter(
        "ner_actors_created_total",
        "Total actors created",
    )
except ValueError:
    actors_created = REGISTRY._names_to_collectors.get("ner_actors_created_total")

try:
    actors_updated = Counter(
        "ner_actors_updated_total",
        "Total actors updated",
    )
except ValueError:
    actors_updated = REGISTRY._names_to_collectors.get("ner_actors_updated_total")

try:
    repository_errors = Counter(
        "ner_repository_errors_total",
        "Total repository errors",
    )
except ValueError:
    repository_errors = REGISTRY._names_to_collectors.get("ner_repository_errors_total")

# Reliability Metrics
try:
    extraction_errors = Counter(
        "ner_extraction_errors_total",
        "Total extraction errors",
        ["error_type"],
    )
except ValueError:
    extraction_errors = REGISTRY._names_to_collectors.get("ner_extraction_errors_total")

try:
    linking_errors = Counter(
        "ner_linking_errors_total",
        "Total linking errors",
        ["error_type"],
    )
except ValueError:
    linking_errors = REGISTRY._names_to_collectors.get("ner_linking_errors_total")

try:
    circuit_breaker_state = Gauge(
        "ner_circuit_breaker_state",
        "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
        ["service"],
    )
except ValueError:
    circuit_breaker_state = REGISTRY._names_to_collectors.get("ner_circuit_breaker_state")

# Resource Metrics
try:
    cache_hit_rate = Gauge(
        "ner_cache_hit_rate",
        "Cache hit rate (0-1)",
    )
except ValueError:
    cache_hit_rate = REGISTRY._names_to_collectors.get("ner_cache_hit_rate")

try:
    db_connection_pool_size = Gauge(
        "ner_db_connection_pool_size",
        "Database connection pool size",
    )
except ValueError:
    db_connection_pool_size = REGISTRY._names_to_collectors.get("ner_db_connection_pool_size")

try:
    kafka_consumer_lag = Gauge(
        "ner_kafka_consumer_lag",
        "Kafka consumer lag in messages",
    )
except ValueError:
    kafka_consumer_lag = REGISTRY._names_to_collectors.get("ner_kafka_consumer_lag")

# Quality Metrics
try:
    extraction_confidence = Histogram(
        "ner_extraction_confidence",
        "Entity extraction confidence scores",
        buckets=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
    )
except ValueError:
    extraction_confidence = REGISTRY._names_to_collectors.get("ner_extraction_confidence")

try:
    linking_success_rate = Gauge(
        "ner_linking_success_rate",
        "Entity linking success rate (0-1)",
    )
except ValueError:
    linking_success_rate = REGISTRY._names_to_collectors.get("ner_linking_success_rate")

try:
    coverage_score = Gauge(
        "ner_coverage_score",
        "Entity coverage score (0-1)",
    )
except ValueError:
    coverage_score = REGISTRY._names_to_collectors.get("ner_coverage_score")


class NFRMetricsCollector:
    """Collects Non-Functional Requirements metrics."""

    @staticmethod
    def record_extraction_latency(latency_seconds: float) -> None:
        """Record entity extraction latency.

        Args:
            latency_seconds: Latency in seconds
        """
        extraction_latency.observe(latency_seconds)
        logger.debug(f"Extraction latency: {latency_seconds:.3f}s")

    @staticmethod
    def record_linking_latency(latency_seconds: float) -> None:
        """Record entity linking latency.

        Args:
            latency_seconds: Latency in seconds
        """
        linking_latency.observe(latency_seconds)
        logger.debug(f"Linking latency: {latency_seconds:.3f}s")

    @staticmethod
    def record_total_latency(latency_seconds: float) -> None:
        """Record total processing latency.

        Args:
            latency_seconds: Latency in seconds
        """
        total_latency.observe(latency_seconds)
        logger.debug(f"Total latency: {latency_seconds:.3f}s")

    @staticmethod
    def record_article_processed() -> None:
        """Record article processed."""
        articles_processed.inc()

    @staticmethod
    def record_entities_extracted(count: int) -> None:
        """Record entities extracted.

        Args:
            count: Number of entities extracted
        """
        entities_extracted.inc(count)

    @staticmethod
    def record_entities_linked(count: int) -> None:
        """Record entities linked.

        Args:
            count: Number of entities linked
        """
        entities_linked.inc(count)

    @staticmethod
    def record_message_consumed() -> None:
        """Record message consumed from Kafka."""
        messages_consumed.inc()

    @staticmethod
    def record_actor_created() -> None:
        """Record actor created."""
        actors_created.inc()

    @staticmethod
    def record_actor_updated() -> None:
        """Record actor updated."""
        actors_updated.inc()

    @staticmethod
    def record_repository_error() -> None:
        """Record repository error."""
        repository_errors.inc()

    @staticmethod
    def record_extraction_error(error_type: str) -> None:
        """Record extraction error.

        Args:
            error_type: Type of error
        """
        extraction_errors.labels(error_type=error_type).inc()
        logger.warning(f"Extraction error: {error_type}")

    @staticmethod
    def record_linking_error(error_type: str) -> None:
        """Record linking error.

        Args:
            error_type: Type of error
        """
        linking_errors.labels(error_type=error_type).inc()
        logger.warning(f"Linking error: {error_type}")

    @staticmethod
    def set_circuit_breaker_state(service: str, state: int) -> None:
        """Set circuit breaker state.

        Args:
            service: Service name
            state: State (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
        """
        circuit_breaker_state.labels(service=service).set(state)

    @staticmethod
    def set_cache_hit_rate(rate: float) -> None:
        """Set cache hit rate.

        Args:
            rate: Hit rate (0-1)
        """
        cache_hit_rate.set(rate)

    @staticmethod
    def set_db_connection_pool_size(size: int) -> None:
        """Set database connection pool size.

        Args:
            size: Pool size
        """
        db_connection_pool_size.set(size)

    @staticmethod
    def set_kafka_consumer_lag(lag: int) -> None:
        """Set Kafka consumer lag.

        Args:
            lag: Lag in messages
        """
        kafka_consumer_lag.set(lag)

    @staticmethod
    def record_extraction_confidence(confidence: float) -> None:
        """Record extraction confidence.

        Args:
            confidence: Confidence score (0-1)
        """
        extraction_confidence.observe(confidence)

    @staticmethod
    def set_linking_success_rate(rate: float) -> None:
        """Set entity linking success rate.

        Args:
            rate: Success rate (0-1)
        """
        linking_success_rate.set(rate)

    @staticmethod
    def set_coverage_score(score: float) -> None:
        """Set entity coverage score.

        Args:
            score: Coverage score (0-1)
        """
        coverage_score.set(score)


class LatencyTracker:
    """Context manager for tracking latency."""

    def __init__(self, operation: str):
        """Initialize latency tracker.

        Args:
            operation: Operation name (extraction, linking, total)
        """
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record latency."""
        if self.start_time:
            latency = time.time() - self.start_time
            if self.operation == "extraction":
                NFRMetricsCollector.record_extraction_latency(latency)
            elif self.operation == "linking":
                NFRMetricsCollector.record_linking_latency(latency)
            elif self.operation == "total":
                NFRMetricsCollector.record_total_latency(latency)

