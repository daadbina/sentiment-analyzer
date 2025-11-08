"""
Unit tests for DriftDetector.

Tests feature drift detection, prediction drift detection, and baseline management.
"""

import pytest
import numpy as np
from unittest.mock import Mock
from scipy import stats

from src.validation.drift_detector import DriftDetector
from src.config import ValidationConfig


@pytest.fixture
def validation_config():
    """Create validation configuration for testing."""
    return ValidationConfig(
        label_consistency_threshold=0.85,
        drift_detection_window_hours=24,
        min_samples_for_drift=30
    )


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.increment_feature_drift_detected = Mock()
    metrics.increment_prediction_drift_detected = Mock()
    return metrics


@pytest.fixture
def drift_detector(validation_config, metrics_mock):
    """Create DriftDetector instance for testing."""
    return DriftDetector(config=validation_config, metrics=metrics_mock)


class TestDriftDetector:
    """Test suite for DriftDetector."""
    
    def test_track_features_single_sample(self, drift_detector):
        """Test tracking features for a single sample."""
        features = {"feature1": 0.5, "feature2": 0.8}
        
        drift_detector.track_features(features, is_baseline=True)
        
        assert "feature1" in drift_detector._baseline_features
        assert len(drift_detector._baseline_features["feature1"]) == 1
        assert drift_detector._baseline_features["feature1"][0] == 0.5
    
    def test_track_features_multiple_samples(self, drift_detector):
        """Test tracking features for multiple samples."""
        samples = [
            {"feature1": 0.5, "feature2": 0.8},
            {"feature1": 0.6, "feature2": 0.7},
            {"feature1": 0.4, "feature2": 0.9}
        ]
        
        for sample in samples:
            drift_detector.track_features(sample, is_baseline=True)
        
        assert len(drift_detector._baseline_features["feature1"]) == 3
        assert len(drift_detector._baseline_features["feature2"]) == 3
    
    def test_track_features_baseline_and_current(self, drift_detector):
        """Test tracking both baseline and current features."""
        baseline_features = {"feature1": 0.5}
        current_features = {"feature1": 0.8}
        
        drift_detector.track_features(baseline_features, is_baseline=True)
        drift_detector.track_features(current_features, is_baseline=False)
        
        assert len(drift_detector._baseline_features["feature1"]) == 1
        assert len(drift_detector._current_features["feature1"]) == 1
        assert drift_detector._baseline_features["feature1"][0] == 0.5
        assert drift_detector._current_features["feature1"][0] == 0.8
    
    def test_detect_feature_drift_no_drift(self, drift_detector, metrics_mock):
        """Test drift detection when there is no drift."""
        # Create baseline and current data from same distribution
        np.random.seed(42)
        for _ in range(50):
            value = np.random.normal(0.5, 0.1)
            drift_detector.track_features({"feature1": value}, is_baseline=True)
        
        for _ in range(50):
            value = np.random.normal(0.5, 0.1)
            drift_detector.track_features({"feature1": value}, is_baseline=False)
        
        drift_results = drift_detector.detect_feature_drift()
        
        assert "feature1" in drift_results
        assert drift_results["feature1"]["drift_detected"] is False
        assert drift_results["feature1"]["p_value"] > 0.05
        metrics_mock.increment_feature_drift_detected.assert_not_called()
    
    def test_detect_feature_drift_with_drift(self, drift_detector, metrics_mock):
        """Test drift detection when there is significant drift."""
        # Create baseline and current data from different distributions
        np.random.seed(42)
        for _ in range(50):
            value = np.random.normal(0.3, 0.1)
            drift_detector.track_features({"feature1": value}, is_baseline=True)
        
        for _ in range(50):
            value = np.random.normal(0.7, 0.1)
            drift_detector.track_features({"feature1": value}, is_baseline=False)
        
        drift_results = drift_detector.detect_feature_drift()
        
        assert "feature1" in drift_results
        assert drift_results["feature1"]["drift_detected"] is True
        assert drift_results["feature1"]["p_value"] < 0.05
        metrics_mock.increment_feature_drift_detected.assert_called_once_with(feature_name="feature1")
    
    def test_detect_feature_drift_insufficient_samples(self, drift_detector):
        """Test drift detection with insufficient samples."""
        # Add only a few samples (less than min_samples_for_drift)
        for _ in range(10):
            drift_detector.track_features({"feature1": 0.5}, is_baseline=True)
            drift_detector.track_features({"feature1": 0.8}, is_baseline=False)
        
        drift_results = drift_detector.detect_feature_drift()
        
        assert "feature1" in drift_results
        assert drift_results["feature1"]["drift_detected"] is False
        assert "insufficient_samples" in drift_results["feature1"]["reason"]
    
    def test_detect_feature_drift_no_baseline(self, drift_detector):
        """Test drift detection when no baseline exists."""
        # Only track current features
        for _ in range(50):
            drift_detector.track_features({"feature1": 0.5}, is_baseline=False)
        
        drift_results = drift_detector.detect_feature_drift()
        
        assert "feature1" in drift_results
        assert drift_results["feature1"]["drift_detected"] is False
        assert "no_baseline" in drift_results["feature1"]["reason"]
    
    def test_detect_feature_drift_multiple_features(self, drift_detector, metrics_mock):
        """Test drift detection for multiple features."""
        np.random.seed(42)
        
        # feature1: no drift
        for _ in range(50):
            value = np.random.normal(0.5, 0.1)
            drift_detector.track_features({"feature1": value, "feature2": 0.0}, is_baseline=True)
        
        for _ in range(50):
            value = np.random.normal(0.5, 0.1)
            drift_detector.track_features({"feature1": value, "feature2": 0.0}, is_baseline=False)
        
        # feature2: drift
        for i in range(50):
            drift_detector._baseline_features["feature2"][i] = np.random.normal(0.3, 0.1)
            drift_detector._current_features["feature2"][i] = np.random.normal(0.7, 0.1)
        
        drift_results = drift_detector.detect_feature_drift()
        
        assert drift_results["feature1"]["drift_detected"] is False
        assert drift_results["feature2"]["drift_detected"] is True
        metrics_mock.increment_feature_drift_detected.assert_called_once_with(feature_name="feature2")
    
    def test_detect_prediction_drift_no_drift(self, drift_detector, metrics_mock):
        """Test prediction drift detection when there is no drift."""
        np.random.seed(42)
        
        # Create baseline and current predictions from same distribution
        baseline_predictions = [np.random.normal(0.5, 0.1) for _ in range(50)]
        current_predictions = [np.random.normal(0.5, 0.1) for _ in range(50)]
        
        drift_result = drift_detector.detect_prediction_drift(
            baseline_predictions=baseline_predictions,
            current_predictions=current_predictions
        )
        
        assert drift_result["drift_detected"] is False
        assert drift_result["p_value"] > 0.05
        metrics_mock.increment_prediction_drift_detected.assert_not_called()
    
    def test_detect_prediction_drift_with_drift(self, drift_detector, metrics_mock):
        """Test prediction drift detection when there is significant drift."""
        np.random.seed(42)
        
        # Create baseline and current predictions from different distributions
        baseline_predictions = [np.random.normal(0.3, 0.1) for _ in range(50)]
        current_predictions = [np.random.normal(0.7, 0.1) for _ in range(50)]
        
        drift_result = drift_detector.detect_prediction_drift(
            baseline_predictions=baseline_predictions,
            current_predictions=current_predictions
        )
        
        assert drift_result["drift_detected"] is True
        assert drift_result["p_value"] < 0.05
        metrics_mock.increment_prediction_drift_detected.assert_called_once()
    
    def test_detect_prediction_drift_insufficient_samples(self, drift_detector):
        """Test prediction drift detection with insufficient samples."""
        baseline_predictions = [0.5] * 10
        current_predictions = [0.8] * 10
        
        drift_result = drift_detector.detect_prediction_drift(
            baseline_predictions=baseline_predictions,
            current_predictions=current_predictions
        )
        
        assert drift_result["drift_detected"] is False
        assert "insufficient_samples" in drift_result["reason"]
    
    def test_detect_prediction_drift_empty_lists(self, drift_detector):
        """Test prediction drift detection with empty lists."""
        baseline_predictions = []
        current_predictions = []
        
        drift_result = drift_detector.detect_prediction_drift(
            baseline_predictions=baseline_predictions,
            current_predictions=current_predictions
        )
        
        assert drift_result["drift_detected"] is False
        assert "insufficient_samples" in drift_result["reason"]
    
    def test_set_baseline(self, drift_detector):
        """Test setting current data as new baseline."""
        # Track some current features
        for _ in range(30):
            drift_detector.track_features({"feature1": 0.8}, is_baseline=False)
        
        # Set as baseline
        drift_detector.set_baseline()
        
        # Current features should be moved to baseline
        assert len(drift_detector._baseline_features["feature1"]) == 30
        assert len(drift_detector._current_features["feature1"]) == 0
        assert drift_detector._baseline_features["feature1"][0] == 0.8
    
    def test_set_baseline_clears_current(self, drift_detector):
        """Test that setting baseline clears current features."""
        # Track baseline and current features
        drift_detector.track_features({"feature1": 0.5}, is_baseline=True)
        drift_detector.track_features({"feature1": 0.8}, is_baseline=False)
        
        # Set as baseline
        drift_detector.set_baseline()
        
        # Current should be cleared
        assert len(drift_detector._current_features["feature1"]) == 0
    
    def test_track_features_with_none_values(self, drift_detector):
        """Test tracking features with None values."""
        features = {"feature1": 0.5, "feature2": None}
        
        drift_detector.track_features(features, is_baseline=True)
        
        # Should only track non-None values
        assert "feature1" in drift_detector._baseline_features
        assert len(drift_detector._baseline_features["feature1"]) == 1
        # feature2 should either not be tracked or be empty
        if "feature2" in drift_detector._baseline_features:
            assert len(drift_detector._baseline_features["feature2"]) == 0
    
    def test_detect_feature_drift_custom_threshold(self, drift_detector):
        """Test drift detection with custom p-value threshold."""
        np.random.seed(42)
        
        # Create data with moderate difference
        for _ in range(50):
            drift_detector.track_features({"feature1": np.random.normal(0.5, 0.1)}, is_baseline=True)
        
        for _ in range(50):
            drift_detector.track_features({"feature1": np.random.normal(0.55, 0.1)}, is_baseline=False)
        
        # With default threshold (0.05), might not detect drift
        drift_results_default = drift_detector.detect_feature_drift(p_value_threshold=0.05)
        
        # With higher threshold (0.1), more likely to detect drift
        drift_results_relaxed = drift_detector.detect_feature_drift(p_value_threshold=0.1)
        
        # At least one should have a result
        assert "feature1" in drift_results_default
        assert "feature1" in drift_results_relaxed
    
    def test_kolmogorov_smirnov_test_calculation(self, drift_detector):
        """Test that KS test is calculated correctly."""
        np.random.seed(42)
        
        # Create two clearly different distributions
        baseline = [0.1, 0.2, 0.15, 0.18, 0.12] * 10
        current = [0.8, 0.9, 0.85, 0.88, 0.82] * 10
        
        for val in baseline:
            drift_detector.track_features({"feature1": val}, is_baseline=True)
        
        for val in current:
            drift_detector.track_features({"feature1": val}, is_baseline=False)
        
        drift_results = drift_detector.detect_feature_drift()
        
        # Manually calculate KS statistic
        ks_stat, p_value = stats.ks_2samp(baseline, current)
        
        # Results should match
        assert drift_results["feature1"]["drift_detected"] is True
        assert drift_results["feature1"]["p_value"] < 0.001
        assert abs(drift_results["feature1"]["ks_statistic"] - ks_stat) < 0.01

