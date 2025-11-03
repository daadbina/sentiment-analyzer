"""Tests for real-time analytics engine."""

import pytest
from datetime import datetime, timezone
from src.analytics.analytics_engine import (
    RealTimeAnalytics,
    AnalyticsSnapshot,
    TimeSeriesMetric,
)


class TestTimeSeriesMetric:
    """Test time series metric."""

    def test_metric_creation(self):
        """Test creating metric."""
        now = datetime.now(timezone.utc)
        metric = TimeSeriesMetric(timestamp=now, value=42.5)
        assert metric.timestamp == now
        assert metric.value == 42.5
        assert metric.label is None

    def test_metric_with_label(self):
        """Test metric with label."""
        now = datetime.now(timezone.utc)
        metric = TimeSeriesMetric(timestamp=now, value=42.5, label="test")
        assert metric.label == "test"


class TestAnalyticsSnapshot:
    """Test analytics snapshot."""

    def test_snapshot_creation(self):
        """Test creating snapshot."""
        now = datetime.now(timezone.utc)
        snapshot = AnalyticsSnapshot(timestamp=now)
        assert snapshot.timestamp == now
        assert snapshot.total_messages_processed == 0
        assert snapshot.total_messages_accepted == 0
        assert snapshot.total_messages_rejected == 0
        assert snapshot.total_messages_review == 0

    def test_snapshot_with_values(self):
        """Test snapshot with values."""
        now = datetime.now(timezone.utc)
        snapshot = AnalyticsSnapshot(
            timestamp=now,
            total_messages_processed=100,
            total_messages_accepted=80,
            total_messages_rejected=20,
            average_processing_time_ms=50.0,
            error_rate=0.05,
            throughput_msg_per_sec=10.0,
        )
        assert snapshot.total_messages_processed == 100
        assert snapshot.total_messages_accepted == 80
        assert snapshot.total_messages_rejected == 20
        assert snapshot.average_processing_time_ms == 50.0
        assert snapshot.error_rate == 0.05
        assert snapshot.throughput_msg_per_sec == 10.0


class TestRealTimeAnalytics:
    """Test real-time analytics."""

    def test_analytics_initialization(self):
        """Test analytics initialization."""
        analytics = RealTimeAnalytics()
        assert analytics.total_messages_processed == 0
        assert analytics.total_messages_accepted == 0
        assert analytics.total_messages_rejected == 0
        assert analytics.total_errors == 0

    def test_analytics_record_message_processed(self):
        """Test recording processed message."""
        analytics = RealTimeAnalytics()
        analytics.record_message_processed(50.0, domain="politics", publisher="BBC")
        assert analytics.total_messages_processed == 1
        assert analytics.domain_distribution["politics"] == 1
        assert analytics.publisher_distribution["BBC"] == 1

    def test_analytics_record_message_accepted(self):
        """Test recording accepted message."""
        analytics = RealTimeAnalytics()
        analytics.record_message_accepted()
        assert analytics.total_messages_accepted == 1

    def test_analytics_record_message_rejected(self):
        """Test recording rejected message."""
        analytics = RealTimeAnalytics()
        analytics.record_message_rejected()
        assert analytics.total_messages_rejected == 1

    def test_analytics_record_message_review(self):
        """Test recording message for review."""
        analytics = RealTimeAnalytics()
        analytics.record_message_review()
        assert analytics.total_messages_review == 1

    def test_analytics_record_error(self):
        """Test recording error."""
        analytics = RealTimeAnalytics()
        analytics.record_error()
        assert analytics.total_errors == 1

    def test_analytics_cache_metrics(self):
        """Test cache metrics."""
        analytics = RealTimeAnalytics()
        analytics.record_cache_hit()
        analytics.record_cache_hit()
        analytics.record_cache_miss()
        assert analytics.cache_hits == 2
        assert analytics.cache_misses == 1
        assert analytics.get_cache_hit_rate() == 2.0 / 3.0

    def test_analytics_cache_hit_rate_empty(self):
        """Test cache hit rate with no data."""
        analytics = RealTimeAnalytics()
        assert analytics.get_cache_hit_rate() == 0.0

    def test_analytics_error_rate(self):
        """Test error rate calculation."""
        analytics = RealTimeAnalytics()
        for _ in range(100):
            analytics.record_message_processed(50.0)
        for _ in range(5):
            analytics.record_error()
        assert analytics.get_error_rate() == 0.05

    def test_analytics_error_rate_empty(self):
        """Test error rate with no data."""
        analytics = RealTimeAnalytics()
        assert analytics.get_error_rate() == 0.0

    def test_analytics_deduplication_rate(self):
        """Test deduplication rate."""
        analytics = RealTimeAnalytics()
        for _ in range(100):
            analytics.record_message_processed(50.0)
        for _ in range(10):
            analytics.record_deduplication_hit()
        assert analytics.get_deduplication_rate() == 0.1

    def test_analytics_deduplication_rate_empty(self):
        """Test deduplication rate with no data."""
        analytics = RealTimeAnalytics()
        assert analytics.get_deduplication_rate() == 0.0

    def test_analytics_average_processing_time(self):
        """Test average processing time."""
        analytics = RealTimeAnalytics()
        analytics.record_message_processed(50.0)
        analytics.record_message_processed(100.0)
        analytics.record_message_processed(150.0)
        assert analytics.get_average_processing_time() == 100.0

    def test_analytics_average_processing_time_empty(self):
        """Test average processing time with no data."""
        analytics = RealTimeAnalytics()
        assert analytics.get_average_processing_time() == 0.0

    def test_analytics_throughput(self):
        """Test throughput calculation."""
        analytics = RealTimeAnalytics()
        analytics.record_message_processed(50.0)
        analytics.record_message_processed(50.0)
        throughput = analytics.get_throughput()
        assert throughput >= 0.0

    def test_analytics_throughput_empty(self):
        """Test throughput with no data."""
        analytics = RealTimeAnalytics()
        assert analytics.get_throughput() == 0.0

    def test_analytics_get_snapshot(self):
        """Test getting snapshot."""
        analytics = RealTimeAnalytics()
        analytics.record_message_processed(50.0, domain="politics")
        analytics.record_message_accepted()
        snapshot = analytics.get_snapshot()
        assert isinstance(snapshot, AnalyticsSnapshot)
        assert snapshot.total_messages_processed == 1
        assert snapshot.total_messages_accepted == 1

    def test_analytics_get_recent_snapshots(self):
        """Test getting recent snapshots."""
        analytics = RealTimeAnalytics()
        for i in range(5):
            analytics.record_message_processed(50.0)
            analytics.get_snapshot()
        snapshots = analytics.get_recent_snapshots(3)
        assert len(snapshots) == 3

    def test_analytics_reset(self):
        """Test resetting analytics."""
        analytics = RealTimeAnalytics()
        analytics.record_message_processed(50.0)
        analytics.record_message_accepted()
        analytics.record_error()
        analytics.reset()
        assert analytics.total_messages_processed == 0
        assert analytics.total_messages_accepted == 0
        assert analytics.total_errors == 0
        assert len(analytics.processing_times) == 0


class TestRealTimeAnalyticsIntegration:
    """Integration tests for real-time analytics."""

    def test_analytics_full_workflow(self):
        """Test full analytics workflow."""
        analytics = RealTimeAnalytics()

        # Simulate processing messages
        for i in range(100):
            analytics.record_message_processed(50.0 + i, domain="politics", publisher="BBC")
            if i % 10 == 0:
                analytics.record_error()
            if i % 5 == 0:
                analytics.record_cache_hit()
            else:
                analytics.record_cache_miss()
            if i % 20 == 0:
                analytics.record_deduplication_hit()

        # Get snapshot
        snapshot = analytics.get_snapshot()
        assert snapshot.total_messages_processed == 100
        assert snapshot.error_rate > 0.0
        assert snapshot.cache_hit_rate > 0.0
        assert snapshot.deduplication_rate > 0.0

    def test_analytics_multiple_domains(self):
        """Test analytics with multiple domains."""
        analytics = RealTimeAnalytics()

        domains = ["politics", "economy", "technology", "health"]
        for domain in domains:
            for _ in range(25):
                analytics.record_message_processed(50.0, domain=domain)

        snapshot = analytics.get_snapshot()
        assert snapshot.total_messages_processed == 100
        assert len(snapshot.domain_distribution) == 4
        assert all(count == 25 for count in snapshot.domain_distribution.values())

    def test_analytics_snapshot_history(self):
        """Test snapshot history."""
        analytics = RealTimeAnalytics(window_size_seconds=1, max_history=10)

        for i in range(5):
            analytics.record_message_processed(50.0)
            analytics.get_snapshot()

        snapshots = analytics.get_recent_snapshots(10)
        assert len(snapshots) == 5

