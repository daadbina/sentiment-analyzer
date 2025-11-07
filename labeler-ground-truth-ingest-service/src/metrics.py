"""Prometheus metrics for labeler-ground-truth-ingest-service."""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Optional


class Metrics:
    """Prometheus metrics collector."""

    def __init__(self, port: int = 9107):
        """Initialize metrics."""
        self.port = port

        # Counters
        self.label_fetched_total = Counter(
            "label_fetched_total",
            "Total labels fetched by source",
            ["source"]
        )
        self.label_reconciled_total = Counter(
            "label_reconciled_total",
            "Successfully reconciled labels"
        )
        self.label_reconciliation_failures_total = Counter(
            "label_reconciliation_failures_total",
            "Failed reconciliations"
        )
        self.label_validation_failures_total = Counter(
            "label_validation_failures_total",
            "Failed label validations"
        )
        self.label_license_violations_total = Counter(
            "label_license_violations_total",
            "License compliance violations"
        )
        self.label_duplicates_detected_total = Counter(
            "label_duplicates_detected_total",
            "Duplicate labels detected"
        )

        # Histograms
        self.label_fetch_duration_seconds = Histogram(
            "label_fetch_duration_seconds",
            "API fetch latency by source",
            ["source"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        self.label_reconciliation_duration_seconds = Histogram(
            "label_reconciliation_duration_seconds",
            "Reconciliation latency",
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        self.label_validation_duration_seconds = Histogram(
            "label_validation_duration_seconds",
            "Validation latency",
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        self.label_storage_duration_seconds = Histogram(
            "label_storage_duration_seconds",
            "Storage operation latency",
            ["storage_type"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )

        # Gauges
        self.label_freshness_hours = Gauge(
            "label_freshness_hours",
            "Age of latest label by source",
            ["source"]
        )
        self.label_confidence_avg = Gauge(
            "label_confidence_avg",
            "Average label confidence score",
            ["source"]
        )
        self.label_queue_size = Gauge(
            "label_queue_size",
            "Number of labels in processing queue"
        )
        self.label_batch_size = Gauge(
            "label_batch_size",
            "Size of current processing batch"
        )

        # Kafka consumer metrics
        self.kafka_consumer_lag = Gauge(
            "kafka_consumer_lag",
            "Kafka consumer lag in messages",
            ["topic", "partition"]
        )
        self.kafka_messages_consumed_total = Counter(
            "kafka_messages_consumed_total",
            "Total messages consumed from Kafka",
            ["topic"]
        )
        self.kafka_deserialization_errors_total = Counter(
            "kafka_deserialization_errors_total",
            "Total deserialization errors",
            ["topic"]
        )
        self.kafka_offset_commit_duration_seconds = Histogram(
            "kafka_offset_commit_duration_seconds",
            "Kafka offset commit latency",
            ["topic"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
        )
        self.kafka_consumer_poll_duration_seconds = Histogram(
            "kafka_consumer_poll_duration_seconds",
            "Kafka consumer poll latency",
            ["topic"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
        )

        # Kafka producer metrics
        self.kafka_messages_produced_total = Counter(
            "kafka_messages_produced_total",
            "Total messages produced to Kafka",
            ["topic"]
        )
        self.kafka_production_errors_total = Counter(
            "kafka_production_errors_total",
            "Total production errors",
            ["topic"]
        )
        self.kafka_production_duration_seconds = Histogram(
            "kafka_production_duration_seconds",
            "Kafka production latency",
            ["topic"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
        )

    def start_server(self):
        """Start Prometheus metrics server."""
        start_http_server(self.port)

    def record_fetch(self, source: str, count: int, duration_seconds: float):
        """Record label fetch."""
        self.label_fetched_total.labels(source=source).inc(count)
        self.label_fetch_duration_seconds.labels(source=source).observe(duration_seconds)

    def record_reconciliation_success(self, duration_seconds: float):
        """Record successful reconciliation."""
        self.label_reconciled_total.inc()
        self.label_reconciliation_duration_seconds.observe(duration_seconds)

    def record_reconciliation_failure(self):
        """Record failed reconciliation."""
        self.label_reconciliation_failures_total.inc()

    def record_validation_failure(self):
        """Record failed validation."""
        self.label_validation_failures_total.inc()

    def record_validation_success(self, duration_seconds: float):
        """Record successful validation."""
        self.label_validation_duration_seconds.observe(duration_seconds)

    def record_license_violation(self):
        """Record license violation."""
        self.label_license_violations_total.inc()

    def record_duplicate_detected(self):
        """Record duplicate detection."""
        self.label_duplicates_detected_total.inc()

    def record_storage(self, storage_type: str, duration_seconds: float):
        """Record storage operation."""
        self.label_storage_duration_seconds.labels(storage_type=storage_type).observe(duration_seconds)

    def set_freshness(self, source: str, hours: float):
        """Set label freshness."""
        self.label_freshness_hours.labels(source=source).set(hours)

    def set_confidence_avg(self, source: str, confidence: float):
        """Set average confidence."""
        self.label_confidence_avg.labels(source=source).set(confidence)

    def set_queue_size(self, size: int):
        """Set queue size."""
        self.label_queue_size.set(size)

    def set_batch_size(self, size: int):
        """Set batch size."""
        self.label_batch_size.set(size)

    def record_kafka_consumer_message(self, topic: str):
        """Record consumed Kafka message."""
        self.kafka_messages_consumed_total.labels(topic=topic).inc()

    def record_kafka_consumer_lag(self, topic: str, partition: int, lag: int):
        """Record Kafka consumer lag."""
        self.kafka_consumer_lag.labels(topic=topic, partition=partition).set(lag)

    def record_kafka_deserialization_error(self, topic: str):
        """Record Kafka deserialization error."""
        self.kafka_deserialization_errors_total.labels(topic=topic).inc()

    def record_kafka_offset_commit(self, topic: str, duration_seconds: float):
        """Record Kafka offset commit."""
        self.kafka_offset_commit_duration_seconds.labels(topic=topic).observe(duration_seconds)

    def record_kafka_consumer_poll(self, topic: str, duration_seconds: float):
        """Record Kafka consumer poll."""
        self.kafka_consumer_poll_duration_seconds.labels(topic=topic).observe(duration_seconds)

    def record_kafka_producer_message(self, topic: str):
        """Record produced Kafka message."""
        self.kafka_messages_produced_total.labels(topic=topic).inc()

    def record_kafka_production_error(self, topic: str):
        """Record Kafka production error."""
        self.kafka_production_errors_total.labels(topic=topic).inc()

    def record_kafka_production(self, topic: str, duration_seconds: float):
        """Record Kafka production."""
        self.kafka_production_duration_seconds.labels(topic=topic).observe(duration_seconds)


# Global metrics instance
metrics: Optional[Metrics] = None


def get_metrics(port: int = 9107) -> Metrics:
    """Get or create metrics instance."""
    global metrics
    if metrics is None:
        metrics = Metrics(port)
    return metrics

