"""Prometheus metrics for Ingest Validator Service."""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from typing import Optional


class MetricsCollector:
    """Centralized metrics collection."""

    def __init__(self, registry=None):
        """Initialize metrics collector.

        Args:
            registry: Prometheus registry (uses default if None)
        """
        self.registry = registry or REGISTRY

        # Counters
        self.messages_consumed_total = Counter(
            "validator_messages_consumed_total",
            "Total messages consumed from news_raw",
            registry=self.registry,
        )

        self.messages_validated_total = Counter(
            "validator_messages_validated_total",
            "Messages published to news_validated",
            registry=self.registry,
        )

        self.messages_rejected_total = Counter(
            "validator_messages_rejected_total",
            "Messages published to news_rejected",
            registry=self.registry,
        )

        self.audit_log_write_errors_total = Counter(
            "validator_audit_log_write_errors_total",
            "Failed TimescaleDB writes",
            registry=self.registry,
        )

        self.replay_initiated = Counter(
            "validator_replay_initiated_total",
            "Total replay operations initiated",
            registry=self.registry,
        )

        self.replay_failed = Counter(
            "validator_replay_failed_total",
            "Total replay operations failed",
            registry=self.registry,
        )

        # Histograms
        self.validation_duration_seconds = Histogram(
            "validator_validation_duration_seconds",
            "End-to-end validation latency per stage",
            ["stage"],
            registry=self.registry,
        )

        self.validation_score = Histogram(
            "validator_validation_score",
            "Distribution of validation scores",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )

        self.language_detection_duration_seconds = Histogram(
            "validator_language_detection_duration_seconds",
            "Language detection latency by method",
            ["method"],
            registry=self.registry,
        )

        # Gauges
        self.language_confidence = Gauge(
            "validator_language_confidence",
            "Average language detection confidence",
            registry=self.registry,
        )

        self.duplicate_rate = Gauge(
            "validator_duplicate_rate",
            "Ratio of duplicate articles detected",
            registry=self.registry,
        )

        self.consumer_lag = Gauge(
            "validator_consumer_lag",
            "Kafka consumer lag by partition",
            ["partition"],
            registry=self.registry,
        )

        self.circuit_breaker_state = Gauge(
            "validator_circuit_breaker_state",
            "Circuit breaker state by dependency (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
            ["dependency"],
            registry=self.registry,
        )

        self.cache_hit_rate = Gauge(
            "validator_cache_hit_rate",
            "Redis cache hit ratio",
            registry=self.registry,
        )


# Global metrics instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics instance (singleton)."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


def initialize_metrics(registry=None) -> MetricsCollector:
    """Initialize metrics with optional custom registry."""
    global _metrics_instance
    _metrics_instance = MetricsCollector(registry)
    return _metrics_instance
