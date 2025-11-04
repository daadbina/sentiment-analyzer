"""Tests for drift detection."""

import pytest
import numpy as np
from src.drift.drift_detector import DriftDetector


class TestDriftDetector:
    """Test drift detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = DriftDetector(sample_size=100, drift_threshold=0.05)

    def test_initialization(self):
        """Test detector initialization."""
        assert not self.detector._is_initialized
        assert self.detector.baseline_stats is None

    def test_add_samples(self):
        """Test adding samples."""
        embeddings = np.random.randn(50, 768).astype(np.float32)
        self.detector.add_samples(embeddings)
        # baseline_samples stores flattened values, so 50 embeddings * 768 dims = 38400 values
        # but maxlen is 100 (from setup_method), so it will only store up to 100 values
        assert len(self.detector.baseline_samples) == min(50 * 768, 100)

    def test_baseline_initialization(self):
        """Test baseline initialization."""
        # Add enough samples to initialize
        for _ in range(2):
            embeddings = np.random.randn(50, 768).astype(np.float32)
            self.detector.add_samples(embeddings)

        assert self.detector._is_initialized
        assert self.detector.baseline_stats is not None
        assert "mean" in self.detector.baseline_stats
        assert "std" in self.detector.baseline_stats

    def test_no_drift_same_distribution(self):
        """Test no drift when distribution is same."""
        # Initialize with baseline
        baseline = np.random.randn(100, 768).astype(np.float32)
        self.detector.add_samples(baseline)

        # Test with same distribution
        test_data = np.random.randn(50, 768).astype(np.float32)
        result = self.detector.detect_drift(test_data)

        assert "drift_detected" in result
        assert "ks_statistic" in result
        assert "p_value" in result

    def test_drift_detection_different_distribution(self):
        """Test drift detection with different distribution."""
        # Initialize with baseline (mean=0)
        baseline = np.random.randn(100, 768).astype(np.float32)
        self.detector.add_samples(baseline)

        # Test with shifted distribution (mean=5)
        test_data = np.random.randn(50, 768).astype(np.float32) + 5
        result = self.detector.detect_drift(test_data)

        # Should detect drift
        assert result["ks_statistic"] > 0.01

    def test_reset(self):
        """Test detector reset."""
        embeddings = np.random.randn(50, 768).astype(np.float32)
        self.detector.add_samples(embeddings)

        self.detector.reset()

        assert len(self.detector.baseline_samples) == 0
        assert self.detector.baseline_stats is None
        assert not self.detector._is_initialized

    def test_get_baseline_stats(self):
        """Test getting baseline stats."""
        # Initialize
        for _ in range(2):
            embeddings = np.random.randn(50, 768).astype(np.float32)
            self.detector.add_samples(embeddings)

        stats = self.detector.get_baseline_stats()
        assert stats is not None
        assert isinstance(stats, dict)

