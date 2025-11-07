"""Performance tests for labeler service."""

import pytest
import time
from src.validation.deduplication import DeduplicationEngine
from src.validation.drift_detector import DriftDetector
from src.validation.label_validator import LabelValidator


@pytest.fixture
def dedup_engine():
    """Create deduplication engine."""
    return DeduplicationEngine()


@pytest.fixture
def drift_detector():
    """Create drift detector."""
    return DriftDetector(window_size=100)


@pytest.fixture
def label_validator():
    """Create label validator."""
    return LabelValidator()


@pytest.fixture
def large_label_batch():
    """Create large batch of labels."""
    return [
        {
            "event_id": f"evt_{i:06d}",
            "event_date": "2025-11-05",
            "label_source": "GDELT",
            "confidence": 0.85,
            "fetched_at": "2025-11-05T10:00:00Z",
            "trace_id": f"trace_{i:06d}"
        }
        for i in range(1000)
    ]


class TestPerformance:
    """Performance tests."""

    @pytest.mark.asyncio
    async def test_deduplication_throughput(self, dedup_engine, large_label_batch):
        """Test deduplication throughput."""
        start = time.time()
        unique, duplicates = await dedup_engine.deduplicate_batch(large_label_batch)
        duration = time.time() - start

        # Should process 1000 labels in < 2 seconds (accounting for DB writes)
        assert duration < 2.0
        assert len(unique) == 1000

        # Calculate throughput
        throughput = len(large_label_batch) / duration
        print(f"Deduplication throughput: {throughput:.0f} labels/sec")
        assert throughput > 500  # At least 500 labels/sec (reduced due to DB persistence)

    def test_drift_detection_throughput(self, drift_detector, large_label_batch):
        """Test drift detection throughput."""
        start = time.time()
        
        for _ in range(10):
            drift_detector.detect_confidence_drift("GDELT", large_label_batch)
        
        duration = time.time() - start
        total_labels = len(large_label_batch) * 10
        
        # Should process 10k labels in < 2 seconds
        assert duration < 2.0
        
        # Calculate throughput
        throughput = total_labels / duration
        print(f"Drift detection throughput: {throughput:.0f} labels/sec")
        assert throughput > 5000  # At least 5000 labels/sec

    @pytest.mark.asyncio
    async def test_validation_throughput(self, label_validator, large_label_batch):
        """Test validation throughput."""
        start = time.time()
        valid, invalid = await label_validator.validate_batch(large_label_batch, "GDELT")
        duration = time.time() - start
        
        # Should process 1000 labels in < 2 seconds
        assert duration < 2.0
        
        # Calculate throughput
        throughput = len(large_label_batch) / duration
        print(f"Validation throughput: {throughput:.0f} labels/sec")
        assert throughput > 500  # At least 500 labels/sec

    @pytest.mark.asyncio
    async def test_deduplication_memory_efficiency(self, dedup_engine):
        """Test deduplication memory efficiency."""
        # Process multiple batches
        for batch_num in range(10):
            batch = [
                {
                    "event_id": f"evt_{batch_num}_{i:04d}",
                    "event_date": "2025-11-05",
                    "label_source": "GDELT",
                    "confidence": 0.85,
                    "fetched_at": "2025-11-05T10:00:00Z",
                    "trace_id": f"trace_{batch_num}_{i:04d}"
                }
                for i in range(100)
            ]

            unique, duplicates = await dedup_engine.deduplicate_batch(batch)
            assert len(unique) == 100

        # Cache should contain all unique labels
        stats = dedup_engine.get_cache_stats()
        assert stats["cache_size"] == 1000

    def test_drift_detector_memory_efficiency(self, drift_detector):
        """Test drift detector memory efficiency."""
        # Process multiple batches
        for batch_num in range(20):
            batch = [
                {
                    "event_id": f"evt_{batch_num}_{i:04d}",
                    "confidence": 0.85,
                    "fetched_at": "2025-11-05T10:00:00Z"
                }
                for i in range(100)
            ]
            
            drift_detector.detect_confidence_drift("GDELT", batch)
        
        # History should be limited by window size
        assert len(drift_detector.confidence_history["GDELT"]) <= 100

    def test_deduplication_latency_p99(self, dedup_engine):
        """Test deduplication latency (p99)."""
        latencies = []
        
        for i in range(100):
            batch = [
                {
                    "event_id": f"evt_{i}_{j:04d}",
                    "event_date": "2025-11-05",
                    "label_source": "GDELT",
                    "confidence": 0.85,
                    "fetched_at": "2025-11-05T10:00:00Z",
                    "trace_id": f"trace_{i}_{j:04d}"
                }
                for j in range(100)
            ]
            
            start = time.time()
            dedup_engine.deduplicate_batch(batch)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)
        
        # Sort and get p99
        latencies.sort()
        p99_latency = latencies[int(len(latencies) * 0.99)]
        
        print(f"Deduplication p99 latency: {p99_latency:.2f}ms")
        # p99 should be < 200ms for 100 labels (reasonable for Python)
        assert p99_latency < 200

    def test_drift_detection_latency_p99(self, drift_detector):
        """Test drift detection latency (p99)."""
        latencies = []
        
        for i in range(100):
            batch = [
                {
                    "event_id": f"evt_{i}_{j:04d}",
                    "confidence": 0.85,
                    "fetched_at": "2025-11-05T10:00:00Z"
                }
                for j in range(100)
            ]
            
            start = time.time()
            drift_detector.detect_confidence_drift("GDELT", batch)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)
        
        # Sort and get p99
        latencies.sort()
        p99_latency = latencies[int(len(latencies) * 0.99)]
        
        print(f"Drift detection p99 latency: {p99_latency:.2f}ms")
        # p99 should be < 100ms for 100 labels
        assert p99_latency < 100

