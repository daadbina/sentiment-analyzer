"""Resilience tests for labeler service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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


class TestResilience:
    """Resilience tests."""

    def test_deduplication_with_malformed_labels(self, dedup_engine):
        """Test deduplication with malformed labels."""
        labels = [
            {"event_id": "evt_001", "confidence": 0.85},  # Missing fields
            {"event_date": "2025-11-05", "confidence": 0.85},  # Missing event_id
            None,  # Null label
            {},  # Empty label
        ]
        
        # Should handle gracefully
        try:
            unique, duplicates = dedup_engine.deduplicate_batch(labels)
            # Should process without crashing
            assert True
        except Exception as e:
            pytest.fail(f"Deduplication failed with malformed labels: {str(e)}")

    def test_deduplication_with_missing_confidence(self, dedup_engine):
        """Test deduplication with missing confidence."""
        labels = [
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                # Missing confidence
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        unique, duplicates = dedup_engine.deduplicate_batch(labels)
        # Should handle gracefully
        assert len(unique) + len(duplicates) == 1

    def test_drift_detection_with_invalid_confidence(self, drift_detector):
        """Test drift detection with invalid confidence values."""
        labels = [
            {"event_id": "evt_001", "confidence": "invalid"},  # String instead of float
            {"event_id": "evt_002", "confidence": None},  # Null confidence
            {"event_id": "evt_003", "confidence": 0.85},  # Valid
        ]
        
        # Should handle gracefully
        try:
            drift_detected, drift_info = drift_detector.detect_confidence_drift("GDELT", labels)
            # Should process without crashing
            assert True
        except Exception as e:
            pytest.fail(f"Drift detection failed with invalid confidence: {str(e)}")

    def test_drift_detection_with_extreme_values(self, drift_detector):
        """Test drift detection with extreme confidence values."""
        labels = [
            {"event_id": "evt_001", "confidence": 0.0},
            {"event_id": "evt_002", "confidence": 1.0},
            {"event_id": "evt_003", "confidence": 0.5},
        ]
        
        # Should handle gracefully
        drift_detected, drift_info = drift_detector.detect_confidence_drift("GDELT", labels)
        # Should process without crashing
        assert isinstance(drift_detected, bool)

    @pytest.mark.asyncio
    async def test_validation_with_missing_fields(self, label_validator):
        """Test validation with missing required fields."""
        labels = [
            {
                "event_id": "evt_001",
                # Missing confidence
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        valid, invalid = await label_validator.validate_batch(labels, "GDELT")
        
        # Should mark as invalid
        assert len(valid) == 0
        assert len(invalid) == 1

    @pytest.mark.asyncio
    async def test_validation_with_invalid_confidence(self, label_validator):
        """Test validation with invalid confidence."""
        labels = [
            {
                "event_id": "evt_001",
                "confidence": 1.5,  # Out of range
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        valid, invalid = await label_validator.validate_batch(labels, "GDELT")
        
        # Should mark as invalid
        assert len(valid) == 0
        assert len(invalid) == 1

    @pytest.mark.asyncio
    async def test_validation_with_low_confidence(self, label_validator):
        """Test validation with confidence below threshold."""
        labels = [
            {
                "event_id": "evt_001",
                "confidence": 0.5,  # Below default threshold of 0.7
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        valid, invalid = await label_validator.validate_batch(labels, "GDELT")
        
        # Should mark as invalid
        assert len(valid) == 0
        assert len(invalid) == 1

    def test_deduplication_recovery_from_error(self, dedup_engine):
        """Test deduplication recovery from error."""
        # First batch - normal
        batch1 = [
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        unique1, _ = dedup_engine.deduplicate_batch(batch1)
        assert len(unique1) == 1
        
        # Second batch - with error
        batch2 = [None, {}, {"event_id": None}]
        unique2, _ = dedup_engine.deduplicate_batch(batch2)
        
        # Third batch - normal again
        batch3 = [
            {
                "event_id": "evt_002",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_002"
            }
        ]
        
        unique3, _ = dedup_engine.deduplicate_batch(batch3)
        assert len(unique3) == 1
        
        # Should recover and process normally
        assert True

    def test_drift_detector_recovery_from_error(self, drift_detector):
        """Test drift detector recovery from error."""
        # First batch - normal
        batch1 = [
            {"event_id": "evt_001", "confidence": 0.85, "fetched_at": "2025-11-05T10:00:00Z"}
        ]
        
        drift_detector.detect_confidence_drift("GDELT", batch1)
        
        # Second batch - with error
        batch2 = [{"event_id": "evt_002", "confidence": "invalid"}]
        drift_detector.detect_confidence_drift("GDELT", batch2)
        
        # Third batch - normal again
        batch3 = [
            {"event_id": "evt_003", "confidence": 0.85, "fetched_at": "2025-11-05T10:00:00Z"}
        ]
        
        drift_detector.detect_confidence_drift("GDELT", batch3)
        
        # Should recover and process normally
        assert True

    def test_deduplication_with_large_batch(self, dedup_engine):
        """Test deduplication with very large batch."""
        # Create large batch
        batch = [
            {
                "event_id": f"evt_{i:06d}",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": f"trace_{i:06d}"
            }
            for i in range(10000)
        ]
        
        # Should handle without memory issues
        unique, duplicates = dedup_engine.deduplicate_batch(batch)
        assert len(unique) == 10000
        assert len(duplicates) == 0

    def test_drift_detector_with_many_sources(self, drift_detector):
        """Test drift detector with many sources."""
        # Process many sources
        for source_id in range(100):
            batch = [
                {
                    "event_id": f"evt_{source_id}_{i:04d}",
                    "confidence": 0.85,
                    "fetched_at": "2025-11-05T10:00:00Z"
                }
                for i in range(10)
            ]
            
            drift_detector.detect_confidence_drift(f"SOURCE_{source_id}", batch)
        
        # Should handle many sources
        assert len(drift_detector.confidence_history) == 100

    def test_deduplication_cache_clear_recovery(self, dedup_engine):
        """Test deduplication recovery after cache clear."""
        # Add labels
        batch1 = [
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        dedup_engine.deduplicate_batch(batch1)
        assert len(dedup_engine.seen_hashes) == 1
        
        # Clear cache
        dedup_engine.clear_cache()
        assert len(dedup_engine.seen_hashes) == 0
        
        # Process again
        batch2 = [
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]
        
        unique, duplicates = dedup_engine.deduplicate_batch(batch2)
        # After cache clear, same label is not a duplicate
        assert len(unique) == 1
        assert len(duplicates) == 0

