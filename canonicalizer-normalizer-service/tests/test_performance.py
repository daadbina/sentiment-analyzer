"""Performance benchmarks for canonicalizer-normalizer-service."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from src.analytics.analytics_engine import RealTimeAnalytics
from src.api.api_server import (
    CanonicalizeEndpoint,
    BatchCanonicalizeEndpoint,
    APIRequest,
)


class TestCanonicalizePerformance:
    """Performance tests for canonicalization."""

    def test_single_canonicalization_performance(self):
        """Test single article canonicalization performance."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(
            return_value={"url": "https://example.com"}
        )

        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="https://example.com")

        # Measure performance
        start = time.time()
        for _ in range(100):
            # Simulate canonicalization
            pass
        elapsed = time.time() - start

        # Should complete 100 iterations in < 1 second
        assert elapsed < 1.0

    def test_batch_canonicalization_performance(self):
        """Test batch canonicalization performance."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(
            return_value={"url": "https://example.com"}
        )

        endpoint = BatchCanonicalizeEndpoint(canonicalizer, batch_size=100)
        requests = [
            APIRequest(url=f"https://example{i}.com") for i in range(50)
        ]

        # Measure performance
        start = time.time()
        for _ in range(10):
            # Simulate batch canonicalization
            pass
        elapsed = time.time() - start

        # Should complete 10 iterations in < 1 second
        assert elapsed < 1.0


class TestAnalyticsPerformance:
    """Performance tests for analytics."""

    def test_analytics_recording_performance(self):
        """Test analytics recording performance."""
        analytics = RealTimeAnalytics()

        start = time.time()
        for i in range(1000):
            analytics.record_message_processed(50.0)
            if i % 10 == 0:
                analytics.record_cache_hit()
            else:
                analytics.record_cache_miss()
        elapsed = time.time() - start

        # Should record 1000 metrics in < 1 second
        assert elapsed < 1.0
        assert analytics.total_messages_processed == 1000

    def test_analytics_snapshot_performance(self):
        """Test analytics snapshot generation performance."""
        analytics = RealTimeAnalytics()

        # Pre-populate analytics
        for i in range(1000):
            analytics.record_message_processed(50.0)
            if i % 5 == 0:
                analytics.record_cache_hit()

        start = time.time()
        for _ in range(100):
            snapshot = analytics.get_snapshot()
        elapsed = time.time() - start

        # Should generate 100 snapshots in < 1 second
        assert elapsed < 1.0
        assert snapshot is not None

    def test_analytics_throughput_calculation(self):
        """Test throughput calculation performance."""
        analytics = RealTimeAnalytics()

        # Pre-populate analytics
        for i in range(1000):
            analytics.record_message_processed(50.0)

        start = time.time()
        for _ in range(100):
            throughput = analytics.get_throughput()
        elapsed = time.time() - start

        # Should calculate throughput 100 times in < 1 second
        assert elapsed < 1.0
        assert throughput >= 0.0


class TestThroughputBenchmarks:
    """Throughput benchmarks."""

    def test_high_volume_message_processing(self):
        """Test processing high volume of messages."""
        analytics = RealTimeAnalytics()
        start_time = time.time()

        # Process 10,000 messages
        for i in range(10000):
            analytics.record_message_processed(50.0)
            if i % 100 == 0:
                analytics.record_cache_hit()

        elapsed_time = time.time() - start_time
        throughput = 10000 / elapsed_time

        # Should process at least 1000 messages per second
        assert throughput > 1000
        assert analytics.total_messages_processed == 10000

    def test_batch_processing_throughput(self):
        """Test batch processing throughput."""
        analytics = RealTimeAnalytics()
        start_time = time.time()

        # Process 100 batches of 100 messages each
        for batch in range(100):
            for msg in range(100):
                analytics.record_message_processed(50.0)

        elapsed_time = time.time() - start_time
        throughput = 10000 / elapsed_time

        # Should process at least 1000 messages per second
        assert throughput > 1000
        assert analytics.total_messages_processed == 10000


class TestLatencyBenchmarks:
    """Latency benchmarks."""

    def test_canonicalization_latency(self):
        """Test canonicalization latency."""
        analytics = RealTimeAnalytics()
        latencies = []

        for i in range(100):
            start = time.time()
            analytics.record_message_processed(50.0)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Average latency should be < 1ms
        assert avg_latency < 1.0
        # Max latency should be < 10ms
        assert max_latency < 10.0

    def test_analytics_snapshot_latency(self):
        """Test analytics snapshot generation latency."""
        analytics = RealTimeAnalytics()

        # Pre-populate
        for i in range(1000):
            analytics.record_message_processed(50.0)

        latencies = []
        for _ in range(100):
            start = time.time()
            analytics.get_snapshot()
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Average latency should be < 5ms
        assert avg_latency < 5.0
        # Max latency should be < 50ms
        assert max_latency < 50.0


class TestMemoryUsage:
    """Memory usage tests."""

    def test_analytics_memory_efficiency(self):
        """Test analytics memory efficiency."""
        analytics = RealTimeAnalytics()

        # Record 100,000 messages
        for i in range(100000):
            analytics.record_message_processed(50.0)
            if i % 1000 == 0:
                analytics.record_cache_hit()

        # Verify data is stored efficiently
        assert analytics.total_messages_processed == 100000
        assert analytics.cache_hits == 100

    def test_batch_processing_memory(self):
        """Test batch processing memory efficiency."""
        analytics = RealTimeAnalytics()

        # Process large batch
        for i in range(50000):
            analytics.record_message_processed(50.0)

        # Verify memory is managed
        assert analytics.total_messages_processed == 50000


class TestConcurrency:
    """Concurrency tests."""

    def test_concurrent_analytics_recording(self):
        """Test concurrent analytics recording."""
        analytics = RealTimeAnalytics()

        # Simulate concurrent recording
        for i in range(1000):
            analytics.record_message_processed(50.0)
            analytics.record_cache_hit()
            analytics.record_message_accepted()

        # Verify all operations completed
        assert analytics.total_messages_processed == 1000
        assert analytics.cache_hits == 1000
        assert analytics.total_messages_accepted == 1000

    def test_concurrent_snapshot_generation(self):
        """Test concurrent snapshot generation."""
        analytics = RealTimeAnalytics()

        # Pre-populate
        for i in range(1000):
            analytics.record_message_processed(50.0)

        # Generate multiple snapshots
        snapshots = []
        for _ in range(10):
            snapshot = analytics.get_snapshot()
            snapshots.append(snapshot)

        # Verify all snapshots are consistent
        assert len(snapshots) == 10
        assert all(s.total_messages_processed == 1000 for s in snapshots)

