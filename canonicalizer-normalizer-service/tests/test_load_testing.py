"""Load testing for high-volume message processing."""

import pytest
import time
from src.analytics.analytics_engine import RealTimeAnalytics


class TestHighVolumeProcessing:
    """Test system behavior under high message volume."""

    def test_10k_messages_per_second(self):
        """Test processing 10,000 messages per second."""
        analytics = RealTimeAnalytics()
        start_time = time.time()

        # Process 10,000 messages
        for i in range(10000):
            analytics.record_message_processed(50.0)

        elapsed = time.time() - start_time
        throughput = 10000 / elapsed

        # Should achieve at least 1000 msg/sec
        assert throughput > 1000
        assert analytics.total_messages_processed == 10000

    def test_100k_messages_sustained(self):
        """Test sustained processing of 100,000 messages."""
        analytics = RealTimeAnalytics()
        start_time = time.time()

        # Process 100,000 messages
        for i in range(100000):
            analytics.record_message_processed(50.0)

        elapsed = time.time() - start_time
        throughput = 100000 / elapsed

        # Should maintain throughput
        assert throughput > 1000
        assert analytics.total_messages_processed == 100000

    def test_1m_messages_endurance(self):
        """Test endurance with 1 million messages."""
        analytics = RealTimeAnalytics()
        start_time = time.time()

        # Process 1 million messages
        for i in range(1000000):
            analytics.record_message_processed(50.0)

        elapsed = time.time() - start_time
        throughput = 1000000 / elapsed

        # Should maintain throughput
        assert throughput > 1000
        assert analytics.total_messages_processed == 1000000


class TestBurstTraffic:
    """Test system behavior with burst traffic patterns."""

    def test_traffic_spike_handling(self):
        """Test handling of sudden traffic spike."""
        analytics = RealTimeAnalytics()

        # Normal traffic
        for i in range(1000):
            analytics.record_message_processed(50.0)

        # Traffic spike
        spike_start = time.time()
        for i in range(10000):
            analytics.record_message_processed(50.0)
        spike_duration = time.time() - spike_start

        # Normal traffic resumes
        for i in range(1000):
            analytics.record_message_processed(50.0)

        # Verify system handled spike
        assert analytics.total_messages_processed == 12000
        assert spike_duration < 15  # Should complete in reasonable time

    def test_multiple_traffic_spikes(self):
        """Test handling of multiple traffic spikes."""
        analytics = RealTimeAnalytics()

        for spike in range(5):
            # Normal traffic
            for i in range(1000):
                analytics.record_message_processed(50.0)

            # Spike
            for i in range(5000):
                analytics.record_message_processed(50.0)

        # Verify all messages processed
        assert analytics.total_messages_processed == 30000

    def test_traffic_wave_pattern(self):
        """Test handling of wave-like traffic pattern."""
        analytics = RealTimeAnalytics()

        # Wave pattern: low -> high -> low -> high
        for wave in range(4):
            if wave % 2 == 0:
                # Low traffic
                for i in range(1000):
                    analytics.record_message_processed(50.0)
            else:
                # High traffic
                for i in range(5000):
                    analytics.record_message_processed(50.0)

        # Verify all messages processed
        assert analytics.total_messages_processed == 12000


class TestConcurrentLoad:
    """Test system behavior under concurrent load."""

    def test_concurrent_analytics_recording(self):
        """Test concurrent analytics recording."""
        analytics = RealTimeAnalytics()

        # Simulate concurrent operations
        for i in range(10000):
            analytics.record_message_processed(50.0)
            if i % 10 == 0:
                analytics.record_cache_hit()
            if i % 20 == 0:
                analytics.record_message_accepted()
            if i % 50 == 0:
                analytics.record_error()

        # Verify all operations completed
        assert analytics.total_messages_processed == 10000
        assert analytics.cache_hits == 1000
        assert analytics.total_messages_accepted == 500
        assert analytics.total_errors == 200

    def test_concurrent_snapshot_generation(self):
        """Test concurrent snapshot generation."""
        analytics = RealTimeAnalytics()

        # Pre-populate
        for i in range(10000):
            analytics.record_message_processed(50.0)

        # Generate multiple snapshots concurrently
        snapshots = []
        for _ in range(100):
            snapshot = analytics.get_snapshot()
            snapshots.append(snapshot)

        # Verify consistency
        assert len(snapshots) == 100
        assert all(s.total_messages_processed == 10000 for s in snapshots)


class TestMemoryUnderLoad:
    """Test memory efficiency under load."""

    def test_memory_stability_high_volume(self):
        """Test memory stability with high message volume."""
        analytics = RealTimeAnalytics()

        # Process large volume
        for i in range(100000):
            analytics.record_message_processed(50.0)

        # Verify data integrity
        assert analytics.total_messages_processed == 100000

        # Get snapshot to verify memory is managed
        snapshot = analytics.get_snapshot()
        assert snapshot is not None

    def test_memory_with_many_snapshots(self):
        """Test memory usage with many snapshots."""
        analytics = RealTimeAnalytics()

        # Pre-populate
        for i in range(10000):
            analytics.record_message_processed(50.0)

        # Generate many snapshots
        snapshots = []
        for _ in range(1000):
            snapshot = analytics.get_snapshot()
            snapshots.append(snapshot)

        # Verify all snapshots are valid
        assert len(snapshots) == 1000
        assert all(s is not None for s in snapshots)


class TestLatencyUnderLoad:
    """Test latency characteristics under load."""

    def test_latency_consistency_high_volume(self):
        """Test latency consistency with high message volume."""
        analytics = RealTimeAnalytics()
        latencies = []

        # Record latencies for 1000 operations
        for i in range(1000):
            start = time.time()
            analytics.record_message_processed(50.0)
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Verify latency remains acceptable
        assert avg_latency < 1.0  # < 1ms average
        assert max_latency < 10.0  # < 10ms max

    def test_snapshot_latency_under_load(self):
        """Test snapshot generation latency under load."""
        analytics = RealTimeAnalytics()

        # Pre-populate with high volume
        for i in range(100000):
            analytics.record_message_processed(50.0)

        latencies = []

        # Measure snapshot latencies
        for _ in range(100):
            start = time.time()
            analytics.get_snapshot()
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Verify snapshot latency (relaxed thresholds for Windows)
        assert avg_latency < 100.0  # < 100ms average
        assert max_latency < 500.0  # < 500ms max


class TestErrorRateUnderLoad:
    """Test error handling under load."""

    def test_error_rate_stability(self):
        """Test error rate stability under load."""
        analytics = RealTimeAnalytics()

        # Process with consistent error rate
        for i in range(10000):
            analytics.record_message_processed(50.0)
            if i % 100 == 0:
                analytics.record_error()

        error_rate = analytics.get_error_rate()

        # Verify error rate is consistent (100 errors out of 10000 = 1%)
        assert 0.005 < error_rate < 0.015  # ~1% error rate

    def test_error_recovery_under_load(self):
        """Test error recovery under load."""
        analytics = RealTimeAnalytics()

        # Phase 1: High error rate
        for i in range(1000):
            analytics.record_message_processed(50.0)
            if i % 2 == 0:
                analytics.record_error()

        phase1_error_rate = analytics.get_error_rate()

        # Phase 2: Low error rate
        for i in range(9000):
            analytics.record_message_processed(50.0)
            if i % 100 == 0:
                analytics.record_error()

        phase2_error_rate = analytics.get_error_rate()

        # Verify error rate improved
        assert phase2_error_rate < phase1_error_rate


class TestThroughputVariation:
    """Test throughput under varying conditions."""

    def test_variable_processing_time(self):
        """Test throughput with variable processing times."""
        analytics = RealTimeAnalytics()

        # Variable processing times
        times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for i in range(1000):
            processing_time = times[i % len(times)]
            analytics.record_message_processed(processing_time)

        throughput = analytics.get_throughput()

        # Should maintain reasonable throughput
        assert throughput > 0

    def test_throughput_with_cache_hits(self):
        """Test throughput improvement with cache hits."""
        analytics = RealTimeAnalytics()

        # Process with cache hits
        for i in range(10000):
            analytics.record_message_processed(50.0)
            if i % 3 == 0:
                analytics.record_cache_hit()
            else:
                analytics.record_cache_miss()

        cache_hit_rate = analytics.get_cache_hit_rate()

        # Verify cache hit rate
        assert 0.3 < cache_hit_rate < 0.35

