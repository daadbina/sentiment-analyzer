"""Metrics collection for monitoring."""

import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Single metric value."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricStats:
    """Statistics for a metric."""

    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    avg: float = 0.0

    def update(self, value: float) -> None:
        """Update statistics with new value.

        Args:
            value: New value
        """
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.avg = self.sum / self.count


class MetricsCollector:
    """Collect and aggregate metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, list[MetricValue]] = {}
        self.stats: Dict[str, MetricStats] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels
        """
        if name not in self.metrics:
            self.metrics[name] = []
            self.stats[name] = MetricStats()

        metric = MetricValue(name=name, value=value, labels=labels or {})
        self.metrics[name].append(metric)
        self.stats[name].update(value)

    def get_metric_stats(self, name: str) -> Optional[MetricStats]:
        """Get statistics for a metric.

        Args:
            name: Metric name

        Returns:
            Metric statistics or None
        """
        return self.stats.get(name)

    def get_all_metrics(self) -> Dict[str, list[MetricValue]]:
        """Get all recorded metrics.

        Returns:
            Dictionary of metrics
        """
        return self.metrics

    def get_all_stats(self) -> Dict[str, MetricStats]:
        """Get statistics for all metrics.

        Returns:
            Dictionary of statistics
        """
        return self.stats

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.stats.clear()

    def clear_metric(self, name: str) -> None:
        """Clear metrics for a specific name.

        Args:
            name: Metric name
        """
        if name in self.metrics:
            del self.metrics[name]
        if name in self.stats:
            del self.stats[name]


class DomainMetrics:
    """Metrics for domain classification."""

    def __init__(self, collector: MetricsCollector):
        """Initialize domain metrics.

        Args:
            collector: Metrics collector
        """
        self.collector = collector

    def record_classification(self, domain: str, confidence: float) -> None:
        """Record domain classification.

        Args:
            domain: Domain name
            confidence: Classification confidence
        """
        self.collector.record_metric(
            'domain_classification_confidence',
            confidence,
            labels={'domain': domain},
        )

    def record_classification_time(self, duration_ms: float) -> None:
        """Record classification duration.

        Args:
            duration_ms: Duration in milliseconds
        """
        self.collector.record_metric('domain_classification_duration_ms', duration_ms)


class DeduplicationMetrics:
    """Metrics for deduplication."""

    def __init__(self, collector: MetricsCollector):
        """Initialize deduplication metrics.

        Args:
            collector: Metrics collector
        """
        self.collector = collector

    def record_duplicate_found(self, similarity: float) -> None:
        """Record duplicate found.

        Args:
            similarity: Similarity score
        """
        self.collector.record_metric('duplicate_similarity_score', similarity)

    def record_deduplication_time(self, duration_ms: float) -> None:
        """Record deduplication duration.

        Args:
            duration_ms: Duration in milliseconds
        """
        self.collector.record_metric('deduplication_duration_ms', duration_ms)


class NormalizationMetrics:
    """Metrics for normalization."""

    def __init__(self, collector: MetricsCollector):
        """Initialize normalization metrics.

        Args:
            collector: Metrics collector
        """
        self.collector = collector

    def record_normalization_score(self, score: float) -> None:
        """Record normalization score.

        Args:
            score: Normalization score
        """
        self.collector.record_metric('normalization_score', score)

    def record_normalization_time(self, duration_ms: float) -> None:
        """Record normalization duration.

        Args:
            duration_ms: Duration in milliseconds
        """
        self.collector.record_metric('normalization_duration_ms', duration_ms)

    def record_content_length(self, length: int) -> None:
        """Record content length.

        Args:
            length: Content length in characters
        """
        self.collector.record_metric('content_length', float(length))


class CacheMetrics:
    """Metrics for caching."""

    def __init__(self, collector: MetricsCollector):
        """Initialize cache metrics.

        Args:
            collector: Metrics collector
        """
        self.collector = collector

    def record_cache_hit(self, cache_type: str) -> None:
        """Record cache hit.

        Args:
            cache_type: Type of cache
        """
        self.collector.record_metric(
            'cache_hits',
            1.0,
            labels={'cache_type': cache_type},
        )

    def record_cache_miss(self, cache_type: str) -> None:
        """Record cache miss.

        Args:
            cache_type: Type of cache
        """
        self.collector.record_metric(
            'cache_misses',
            1.0,
            labels={'cache_type': cache_type},
        )

