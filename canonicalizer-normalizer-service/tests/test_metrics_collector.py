"""Tests for metrics collector."""

import pytest
from src.monitoring.metrics_collector import (
    MetricsCollector,
    MetricValue,
    MetricStats,
    DomainMetrics,
    DeduplicationMetrics,
    NormalizationMetrics,
    CacheMetrics,
)


class TestMetricValue:
    """Test metric value."""

    def test_metric_value_creation(self):
        """Test creating metric value."""
        value = MetricValue(name="test_metric", value=42.0)
        assert value.name == "test_metric"
        assert value.value == 42.0
        assert value.timestamp is not None

    def test_metric_value_with_labels(self):
        """Test metric value with labels."""
        value = MetricValue(
            name="test_metric",
            value=42.0,
            labels={"domain": "politics"}
        )
        assert value.labels == {"domain": "politics"}


class TestMetricStats:
    """Test metric statistics."""

    def test_metric_stats_initialization(self):
        """Test metric stats initialization."""
        stats = MetricStats()
        assert stats.count == 0
        assert stats.sum == 0.0
        assert stats.min == float('inf')
        assert stats.max == float('-inf')
        assert stats.avg == 0.0

    def test_metric_stats_update_single(self):
        """Test updating stats with single value."""
        stats = MetricStats()
        stats.update(10.0)
        assert stats.count == 1
        assert stats.sum == 10.0
        assert stats.min == 10.0
        assert stats.max == 10.0
        assert stats.avg == 10.0

    def test_metric_stats_update_multiple(self):
        """Test updating stats with multiple values."""
        stats = MetricStats()
        stats.update(10.0)
        stats.update(20.0)
        stats.update(30.0)
        assert stats.count == 3
        assert stats.sum == 60.0
        assert stats.min == 10.0
        assert stats.max == 30.0
        assert stats.avg == 20.0


class TestMetricsCollector:
    """Test metrics collector."""

    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector()
        assert collector is not None
        assert len(collector.metrics) == 0
        assert len(collector.stats) == 0

    def test_collector_record_metric(self):
        """Test recording metric."""
        collector = MetricsCollector()
        collector.record_metric("test_metric", 42.0)
        assert "test_metric" in collector.metrics
        assert len(collector.metrics["test_metric"]) == 1

    def test_collector_record_metric_with_labels(self):
        """Test recording metric with labels."""
        collector = MetricsCollector()
        collector.record_metric("test_metric", 42.0, labels={"domain": "politics"})
        metric = collector.metrics["test_metric"][0]
        assert metric.labels == {"domain": "politics"}

    def test_collector_get_metric_stats(self):
        """Test getting metric stats."""
        collector = MetricsCollector()
        collector.record_metric("test_metric", 10.0)
        collector.record_metric("test_metric", 20.0)
        stats = collector.get_metric_stats("test_metric")
        assert stats is not None
        assert stats.count == 2
        assert stats.avg == 15.0

    def test_collector_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()
        collector.record_metric("metric1", 10.0)
        collector.record_metric("metric2", 20.0)
        metrics = collector.get_all_metrics()
        assert len(metrics) == 2

    def test_collector_get_all_stats(self):
        """Test getting all stats."""
        collector = MetricsCollector()
        collector.record_metric("metric1", 10.0)
        collector.record_metric("metric2", 20.0)
        stats = collector.get_all_stats()
        assert len(stats) == 2

    def test_collector_clear(self):
        """Test clearing collector."""
        collector = MetricsCollector()
        collector.record_metric("metric1", 10.0)
        collector.clear()
        assert len(collector.metrics) == 0
        assert len(collector.stats) == 0

    def test_collector_clear_metric(self):
        """Test clearing specific metric."""
        collector = MetricsCollector()
        collector.record_metric("metric1", 10.0)
        collector.record_metric("metric2", 20.0)
        collector.clear_metric("metric1")
        assert "metric1" not in collector.metrics
        assert "metric2" in collector.metrics


class TestDomainMetrics:
    """Test domain metrics."""

    def test_domain_metrics_initialization(self):
        """Test domain metrics initialization."""
        collector = MetricsCollector()
        metrics = DomainMetrics(collector)
        assert metrics is not None

    def test_domain_metrics_record_classification(self):
        """Test recording classification."""
        collector = MetricsCollector()
        metrics = DomainMetrics(collector)
        metrics.record_classification("politics", 0.95)
        assert "domain_classification_confidence" in collector.metrics

    def test_domain_metrics_record_classification_time(self):
        """Test recording classification time."""
        collector = MetricsCollector()
        metrics = DomainMetrics(collector)
        metrics.record_classification_time(50.0)
        assert "domain_classification_duration_ms" in collector.metrics


class TestDeduplicationMetrics:
    """Test deduplication metrics."""

    def test_dedup_metrics_initialization(self):
        """Test deduplication metrics initialization."""
        collector = MetricsCollector()
        metrics = DeduplicationMetrics(collector)
        assert metrics is not None

    def test_dedup_metrics_record_duplicate(self):
        """Test recording duplicate."""
        collector = MetricsCollector()
        metrics = DeduplicationMetrics(collector)
        metrics.record_duplicate_found(0.92)
        assert "duplicate_similarity_score" in collector.metrics

    def test_dedup_metrics_record_time(self):
        """Test recording deduplication time."""
        collector = MetricsCollector()
        metrics = DeduplicationMetrics(collector)
        metrics.record_deduplication_time(75.0)
        assert "deduplication_duration_ms" in collector.metrics


class TestNormalizationMetrics:
    """Test normalization metrics."""

    def test_norm_metrics_initialization(self):
        """Test normalization metrics initialization."""
        collector = MetricsCollector()
        metrics = NormalizationMetrics(collector)
        assert metrics is not None

    def test_norm_metrics_record_score(self):
        """Test recording normalization score."""
        collector = MetricsCollector()
        metrics = NormalizationMetrics(collector)
        metrics.record_normalization_score(0.87)
        assert "normalization_score" in collector.metrics

    def test_norm_metrics_record_time(self):
        """Test recording normalization time."""
        collector = MetricsCollector()
        metrics = NormalizationMetrics(collector)
        metrics.record_normalization_time(100.0)
        assert "normalization_duration_ms" in collector.metrics

    def test_norm_metrics_record_content_length(self):
        """Test recording content length."""
        collector = MetricsCollector()
        metrics = NormalizationMetrics(collector)
        metrics.record_content_length(1500)
        assert "content_length" in collector.metrics


class TestCacheMetrics:
    """Test cache metrics."""

    def test_cache_metrics_initialization(self):
        """Test cache metrics initialization."""
        collector = MetricsCollector()
        metrics = CacheMetrics(collector)
        assert metrics is not None

    def test_cache_metrics_record_hit(self):
        """Test recording cache hit."""
        collector = MetricsCollector()
        metrics = CacheMetrics(collector)
        metrics.record_cache_hit("redis")
        assert "cache_hits" in collector.metrics

    def test_cache_metrics_record_miss(self):
        """Test recording cache miss."""
        collector = MetricsCollector()
        metrics = CacheMetrics(collector)
        metrics.record_cache_miss("redis")
        assert "cache_misses" in collector.metrics

