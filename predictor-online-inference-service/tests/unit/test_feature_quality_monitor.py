"""
Unit tests for FeatureQualityMonitor.

Tests feature freshness tracking, completeness monitoring, and quality reporting.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.features.feature_quality_monitor import FeatureQualityMonitor
from src.config import FeastConfig


@pytest.fixture
def feast_config():
    """Create Feast configuration for testing."""
    return FeastConfig(
        repo_path="/tmp/feast_repo",
        online_store_type="redis",
        offline_store_type="delta",
        feature_service_name="event_features",
        feature_freshness_threshold_seconds=3600  # 1 hour
    )


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.record_feature_age = Mock()
    return metrics


@pytest.fixture
def feature_quality_monitor(feast_config, metrics_mock):
    """Create FeatureQualityMonitor instance for testing."""
    return FeatureQualityMonitor(config=feast_config, metrics=metrics_mock)


class TestFeatureQualityMonitor:
    """Test suite for FeatureQualityMonitor."""
    
    def test_track_feature_fetch_fresh_features(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch with fresh features."""
        features = {
            "feature1": 0.5,
            "feature2": 0.8
        }
        feature_timestamps = {
            "feature1": datetime.now(),
            "feature2": datetime.now()
        }
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        assert result["freshness_rate"] == 1.0
        assert result["completeness_rate"] == 1.0
        assert result["quality_score"] == 1.0
        assert len(result["missing_features"]) == 0
        assert len(result["stale_features"]) == 0
    
    def test_track_feature_fetch_stale_features(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch with stale features."""
        features = {
            "feature1": 0.5,
            "feature2": 0.8
        }
        # feature1 is stale (older than 1 hour)
        feature_timestamps = {
            "feature1": datetime.now() - timedelta(hours=2),
            "feature2": datetime.now()
        }
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        assert result["freshness_rate"] == 0.5  # 1 out of 2 fresh
        assert result["completeness_rate"] == 1.0  # All present
        assert result["quality_score"] == 0.75  # (0.5 + 1.0) / 2
        assert len(result["stale_features"]) == 1
        assert "feature1" in result["stale_features"]
    
    def test_track_feature_fetch_missing_features(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch with missing features."""
        features = {
            "feature1": 0.5
            # feature2 is missing
        }
        feature_timestamps = {
            "feature1": datetime.now()
        }
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        assert result["freshness_rate"] == 1.0  # All present features are fresh
        assert result["completeness_rate"] == 0.5  # 1 out of 2 present
        assert result["quality_score"] == 0.75  # (1.0 + 0.5) / 2
        assert len(result["missing_features"]) == 1
        assert "feature2" in result["missing_features"]
    
    def test_track_feature_fetch_missing_and_stale(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch with both missing and stale features."""
        features = {
            "feature1": 0.5
            # feature2 is missing
        }
        feature_timestamps = {
            "feature1": datetime.now() - timedelta(hours=2)  # stale
        }
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        assert result["freshness_rate"] == 0.0  # No fresh features
        assert result["completeness_rate"] == 0.5  # 1 out of 2 present
        assert result["quality_score"] == 0.25  # (0.0 + 0.5) / 2
        assert len(result["missing_features"]) == 1
        assert len(result["stale_features"]) == 1
    
    def test_track_feature_fetch_no_timestamps(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch without timestamps."""
        features = {
            "feature1": 0.5,
            "feature2": 0.8
        }
        feature_timestamps = {}
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        # Without timestamps, assume all features are stale
        assert result["freshness_rate"] == 0.0
        assert result["completeness_rate"] == 1.0
        assert len(result["stale_features"]) == 2
    
    def test_track_feature_fetch_empty_features(self, feature_quality_monitor, metrics_mock):
        """Test tracking feature fetch with empty features."""
        features = {}
        feature_timestamps = {}
        expected_features = ["feature1", "feature2"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        assert result["freshness_rate"] == 0.0
        assert result["completeness_rate"] == 0.0
        assert result["quality_score"] == 0.0
        assert len(result["missing_features"]) == 2
    
    def test_get_feature_freshness_rate_all_fresh(self, feature_quality_monitor):
        """Test getting freshness rate when all features are fresh."""
        # Track multiple fresh feature fetches
        for _ in range(10):
            features = {"feature1": 0.5, "feature2": 0.8}
            timestamps = {
                "feature1": datetime.now(),
                "feature2": datetime.now()
            }
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1", "feature2"]
            )
        
        freshness_rate = feature_quality_monitor.get_feature_freshness_rate(
            time_window_hours=1
        )
        
        assert freshness_rate == 1.0
    
    def test_get_feature_freshness_rate_mixed(self, feature_quality_monitor):
        """Test getting freshness rate with mixed fresh/stale features."""
        # Track 5 fresh and 5 stale feature fetches
        for _ in range(5):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now()}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1"]
            )
        
        for _ in range(5):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now() - timedelta(hours=2)}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1"]
            )
        
        freshness_rate = feature_quality_monitor.get_feature_freshness_rate(
            time_window_hours=1
        )
        
        assert 0.4 <= freshness_rate <= 0.6  # Should be around 0.5
    
    def test_get_feature_freshness_rate_no_data(self, feature_quality_monitor):
        """Test getting freshness rate with no tracked data."""
        freshness_rate = feature_quality_monitor.get_feature_freshness_rate(
            time_window_hours=1
        )
        
        assert freshness_rate == 0.0
    
    def test_get_feature_freshness_rate_time_window(self, feature_quality_monitor):
        """Test getting freshness rate respects time window."""
        # Track old data (outside time window)
        old_time = datetime.now() - timedelta(hours=25)
        feature_quality_monitor._fetch_history.append({
            "timestamp": old_time,
            "freshness_rate": 0.0
        })
        
        # Track recent data (inside time window)
        for _ in range(5):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now()}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1"]
            )
        
        freshness_rate = feature_quality_monitor.get_feature_freshness_rate(
            time_window_hours=24
        )
        
        # Should only consider recent data
        assert freshness_rate == 1.0
    
    def test_generate_quality_report_comprehensive(self, feature_quality_monitor):
        """Test generating comprehensive quality report."""
        # Track various feature fetches
        features1 = {"feature1": 0.5, "feature2": 0.8}
        timestamps1 = {
            "feature1": datetime.now(),
            "feature2": datetime.now() - timedelta(hours=2)
        }
        feature_quality_monitor.track_feature_fetch(
            features=features1,
            feature_timestamps=timestamps1,
            expected_features=["feature1", "feature2", "feature3"]
        )
        
        report = feature_quality_monitor.generate_quality_report(
            time_window_hours=1
        )
        
        assert "overall_freshness_rate" in report
        assert "overall_completeness_rate" in report
        assert "overall_quality_score" in report
        assert "total_fetches" in report
        assert "missing_features_summary" in report
        assert "stale_features_summary" in report
        assert report["total_fetches"] == 1
    
    def test_generate_quality_report_missing_features_summary(self, feature_quality_monitor):
        """Test quality report includes missing features summary."""
        # Track fetches with missing features
        for _ in range(3):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now()}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1", "feature2"]
            )
        
        for _ in range(2):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now()}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1", "feature3"]
            )
        
        report = feature_quality_monitor.generate_quality_report(
            time_window_hours=1
        )
        
        # feature2 missing 3 times, feature3 missing 2 times
        assert "feature2" in report["missing_features_summary"]
        assert "feature3" in report["missing_features_summary"]
        assert report["missing_features_summary"]["feature2"] == 3
        assert report["missing_features_summary"]["feature3"] == 2
    
    def test_generate_quality_report_stale_features_summary(self, feature_quality_monitor):
        """Test quality report includes stale features summary."""
        # Track fetches with stale features
        for _ in range(4):
            features = {"feature1": 0.5}
            timestamps = {"feature1": datetime.now() - timedelta(hours=2)}
            feature_quality_monitor.track_feature_fetch(
                features=features,
                feature_timestamps=timestamps,
                expected_features=["feature1"]
            )
        
        report = feature_quality_monitor.generate_quality_report(
            time_window_hours=1
        )
        
        # feature1 stale 4 times
        assert "feature1" in report["stale_features_summary"]
        assert report["stale_features_summary"]["feature1"] == 4
    
    def test_generate_quality_report_no_data(self, feature_quality_monitor):
        """Test generating quality report with no data."""
        report = feature_quality_monitor.generate_quality_report(
            time_window_hours=1
        )
        
        assert report["overall_freshness_rate"] == 0.0
        assert report["overall_completeness_rate"] == 0.0
        assert report["overall_quality_score"] == 0.0
        assert report["total_fetches"] == 0
        assert len(report["missing_features_summary"]) == 0
        assert len(report["stale_features_summary"]) == 0
    
    def test_metrics_recording(self, feature_quality_monitor, metrics_mock):
        """Test that metrics are properly recorded."""
        features = {"feature1": 0.5}
        feature_timestamps = {"feature1": datetime.now() - timedelta(seconds=300)}
        expected_features = ["feature1"]
        
        feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=feature_timestamps,
            expected_features=expected_features
        )
        
        # Verify feature age was recorded
        metrics_mock.record_feature_age.assert_called_once()
        call_args = metrics_mock.record_feature_age.call_args
        age_seconds = call_args[0][0]
        assert age_seconds >= 300  # At least 5 minutes old
    
    def test_quality_score_calculation(self, feature_quality_monitor):
        """Test quality score is calculated correctly."""
        # 50% fresh, 75% complete
        features = {"feature1": 0.5, "feature2": 0.8, "feature3": 0.9}
        timestamps = {
            "feature1": datetime.now(),  # fresh
            "feature2": datetime.now() - timedelta(hours=2),  # stale
            "feature3": datetime.now()  # fresh
        }
        expected_features = ["feature1", "feature2", "feature3", "feature4"]
        
        result = feature_quality_monitor.track_feature_fetch(
            features=features,
            feature_timestamps=timestamps,
            expected_features=expected_features
        )
        
        # Freshness: 2/3 = 0.667
        # Completeness: 3/4 = 0.75
        # Quality: (0.667 + 0.75) / 2 = 0.708
        assert abs(result["freshness_rate"] - 0.667) < 0.01
        assert abs(result["completeness_rate"] - 0.75) < 0.01
        assert abs(result["quality_score"] - 0.708) < 0.01

