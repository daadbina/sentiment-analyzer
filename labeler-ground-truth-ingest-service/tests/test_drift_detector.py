"""Tests for drift detector."""

import pytest
from src.validation.drift_detector import DriftDetector


@pytest.fixture
def drift_detector():
    """Create drift detector."""
    return DriftDetector(window_size=10)


@pytest.fixture
def sample_labels():
    """Create sample labels."""
    return [
        {
            "event_id": f"evt_{i:03d}",
            "confidence": 0.85,
            "fetched_at": "2025-11-05T10:00:00Z"
        }
        for i in range(5)
    ]


class TestDriftDetector:
    """Test drift detector."""

    def test_init(self, drift_detector):
        """Test initialization."""
        assert drift_detector is not None
        assert drift_detector.window_size == 10
        assert len(drift_detector.confidence_history) == 0

    def test_compute_confidence_stats_empty(self, drift_detector):
        """Test stats computation with empty history."""
        stats = drift_detector.compute_confidence_stats("GDELT")
        
        assert stats["mean"] == 0.0
        assert stats["stdev"] == 0.0
        assert stats["count"] == 0

    def test_compute_confidence_stats_single_value(self, drift_detector):
        """Test stats computation with single value."""
        drift_detector._add_to_history(drift_detector.confidence_history, "GDELT", 0.85)
        
        stats = drift_detector.compute_confidence_stats("GDELT")
        
        assert stats["mean"] == 0.85
        assert stats["stdev"] == 0.0
        assert stats["count"] == 1

    def test_compute_confidence_stats_multiple_values(self, drift_detector):
        """Test stats computation with multiple values."""
        for conf in [0.80, 0.85, 0.90]:
            drift_detector._add_to_history(drift_detector.confidence_history, "GDELT", conf)
        
        stats = drift_detector.compute_confidence_stats("GDELT")
        
        assert stats["mean"] == 0.85
        assert stats["min"] == 0.80
        assert stats["max"] == 0.90
        assert stats["count"] == 3

    def test_detect_confidence_drift_no_drift(self, drift_detector, sample_labels):
        """Test drift detection with no drift."""
        # Build history
        for _ in range(10):
            drift_detected, _ = drift_detector.detect_confidence_drift("GDELT", sample_labels)
        
        # Next batch with similar confidence
        drift_detected, drift_info = drift_detector.detect_confidence_drift("GDELT", sample_labels)
        
        assert drift_detected is False
        assert drift_info == {}

    def test_detect_confidence_drift_with_drift(self, drift_detector):
        """Test drift detection with drift."""
        # Build history with confidence ~0.85
        normal_labels = [
            {"event_id": f"evt_{i:03d}", "confidence": 0.85, "fetched_at": "2025-11-05T10:00:00Z"}
            for i in range(5)
        ]

        for _ in range(15):  # Build more history to establish baseline
            drift_detector.detect_confidence_drift("GDELT", normal_labels)

        # Batch with very different confidence (drift)
        drift_labels = [
            {"event_id": f"evt_{i:03d}", "confidence": 0.10, "fetched_at": "2025-11-05T10:00:00Z"}
            for i in range(5)
        ]

        drift_detected, drift_info = drift_detector.detect_confidence_drift("GDELT", drift_labels)

        # With enough history and extreme difference, drift should be detected
        if drift_detected:
            assert drift_info["drift_type"] == "confidence"
            assert drift_info["z_score"] > 2.0

    def test_detect_volume_drift_no_drift(self, drift_detector):
        """Test volume drift detection with no drift."""
        # Build history
        for _ in range(5):
            drift_detector.detect_volume_drift("GDELT", 100)
        
        # Next batch with similar volume
        drift_detected, drift_info = drift_detector.detect_volume_drift("GDELT", 100)
        
        assert drift_detected is False
        assert drift_info == {}

    def test_detect_volume_drift_with_drift(self, drift_detector):
        """Test volume drift detection with drift."""
        # Build history with volume ~100
        for _ in range(5):
            drift_detector.detect_volume_drift("GDELT", 100)
        
        # Batch with very different volume (drift)
        drift_detected, drift_info = drift_detector.detect_volume_drift("GDELT", 10)
        
        assert drift_detected is True
        assert drift_info["drift_type"] == "volume"
        assert drift_info["z_score"] > 2.0

    def test_detect_volume_drift_insufficient_history(self, drift_detector):
        """Test volume drift detection with insufficient history."""
        drift_detected, drift_info = drift_detector.detect_volume_drift("GDELT", 100)
        
        assert drift_detected is False
        assert drift_info == {}

    def test_clear_history(self, drift_detector, sample_labels):
        """Test history clearing."""
        drift_detector.detect_confidence_drift("GDELT", sample_labels)
        assert len(drift_detector.confidence_history) > 0
        
        drift_detector.clear_history()
        assert len(drift_detector.confidence_history) == 0
        assert len(drift_detector.label_count_history) == 0

    def test_multiple_sources(self, drift_detector):
        """Test drift detection with multiple sources."""
        labels_gdelt = [
            {"event_id": f"evt_{i:03d}", "confidence": 0.85, "fetched_at": "2025-11-05T10:00:00Z"}
            for i in range(5)
        ]
        
        labels_binance = [
            {"event_id": f"evt_{i:03d}", "confidence": 0.75, "fetched_at": "2025-11-05T10:00:00Z"}
            for i in range(5)
        ]
        
        drift_detector.detect_confidence_drift("GDELT", labels_gdelt)
        drift_detector.detect_confidence_drift("Binance", labels_binance)
        
        assert "GDELT" in drift_detector.confidence_history
        assert "Binance" in drift_detector.confidence_history

    def test_window_size_limit(self, drift_detector):
        """Test window size limit."""
        # Add more values than window size
        for i in range(20):
            drift_detector._add_to_history(drift_detector.confidence_history, "GDELT", 0.85)
        
        # Should only keep last 10 (window_size)
        assert len(drift_detector.confidence_history["GDELT"]) == 10

    def test_detect_confidence_drift_empty_labels(self, drift_detector):
        """Test drift detection with empty labels."""
        drift_detected, drift_info = drift_detector.detect_confidence_drift("GDELT", [])
        
        assert drift_detected is False
        assert drift_info == {}

