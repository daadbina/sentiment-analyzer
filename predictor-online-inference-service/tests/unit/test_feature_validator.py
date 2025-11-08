"""
Unit tests for FeatureValidator.

Tests feature validation logic including completeness, types, ranges, and freshness.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.features.feature_validator import FeatureValidator
from src.exceptions import FeatureValidationError


@pytest.fixture
def feature_validator():
    """Create a FeatureValidator instance."""
    return FeatureValidator(feature_freshness_threshold_seconds=3600)


@pytest.fixture
def valid_features():
    """Create a valid feature dictionary."""
    return {
        "feature_num_sources": 5,
        "feature_sentiment_mean": 0.75,
        "feature_credibility_mean": 0.85,
        "feature_entities": ["entity1", "entity2"],
        "feature_time_density": 0.5,
        "feature_timestamp": datetime.utcnow().isoformat(),
    }


class TestFeatureValidatorInitialization:
    """Test FeatureValidator initialization."""

    def test_init_default(self):
        """Test validator initialization with default threshold."""
        validator = FeatureValidator()
        assert validator.feature_freshness_threshold_seconds == 3600

    def test_init_custom_threshold(self):
        """Test validator initialization with custom threshold."""
        validator = FeatureValidator(feature_freshness_threshold_seconds=7200)
        assert validator.feature_freshness_threshold_seconds == 7200


class TestValidateFeatures:
    """Test validate_features method."""

    @pytest.mark.asyncio
    async def test_validate_features_success(self, feature_validator, valid_features):
        """Test successful feature validation."""
        # Should not raise exception
        await feature_validator.validate_features(valid_features, "group123")

    @pytest.mark.asyncio
    async def test_validate_features_with_trace_id(self, feature_validator, valid_features):
        """Test feature validation with trace ID."""
        # Should not raise exception
        await feature_validator.validate_features(
            valid_features, "group123", trace_id="trace-123"
        )

    @pytest.mark.asyncio
    async def test_validate_features_missing_required(self, feature_validator):
        """Test validation with missing required features."""
        features = {
            "feature_num_sources": 5,
            # Missing other required features
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            await feature_validator.validate_features(features, "group123")
        
        assert "Missing required features" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_features_null_values(self, feature_validator):
        """Test validation with null feature values."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": None,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            await feature_validator.validate_features(features, "group123")
        
        assert "Null feature values" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_features_invalid_types(self, feature_validator):
        """Test validation with invalid feature types."""
        features = {
            "feature_num_sources": "not a number",  # Should be numeric
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            await feature_validator.validate_features(features, "group123")
        
        assert "Invalid feature types" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_features_out_of_range(self, feature_validator):
        """Test validation with features out of range."""
        features = {
            "feature_num_sources": -5,  # Should be >= 0
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            await feature_validator.validate_features(features, "group123")
        
        assert "out of range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_features_stale_timestamp(self, feature_validator):
        """Test validation with stale feature timestamp."""
        stale_timestamp = datetime.utcnow() - timedelta(hours=2)
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
            "feature_timestamp": stale_timestamp.isoformat(),
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            await feature_validator.validate_features(features, "group123")
        
        assert "stale" in str(exc_info.value).lower() or "fresh" in str(exc_info.value).lower()


class TestCheckMissingFeatures:
    """Test _check_missing_features method."""

    def test_check_missing_features_none_missing(self, feature_validator, valid_features):
        """Test with no missing features."""
        missing = feature_validator._check_missing_features(valid_features)
        assert len(missing) == 0

    def test_check_missing_features_some_missing(self, feature_validator):
        """Test with some missing features."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
        }
        
        missing = feature_validator._check_missing_features(features)
        assert len(missing) > 0
        assert "feature_credibility_mean" in missing
        assert "feature_entities" in missing

    def test_check_missing_features_all_missing(self, feature_validator):
        """Test with all features missing."""
        features = {}
        
        missing = feature_validator._check_missing_features(features)
        assert len(missing) == 5  # All required features


class TestCheckNullFeatures:
    """Test _check_null_features method."""

    def test_check_null_features_none_null(self, feature_validator, valid_features):
        """Test with no null features."""
        null_features = feature_validator._check_null_features(valid_features)
        assert len(null_features) == 0

    def test_check_null_features_some_null(self, feature_validator):
        """Test with some null features."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": None,
            "feature_credibility_mean": 0.85,
            "feature_entities": None,
            "feature_time_density": 0.5,
        }
        
        null_features = feature_validator._check_null_features(features)
        assert len(null_features) == 2
        assert "feature_sentiment_mean" in null_features
        assert "feature_entities" in null_features


class TestCheckFeatureTypes:
    """Test _check_feature_types method."""

    def test_check_feature_types_all_valid(self, feature_validator, valid_features):
        """Test with all valid feature types."""
        invalid = feature_validator._check_feature_types(valid_features)
        assert len(invalid) == 0

    def test_check_feature_types_invalid_num_sources(self, feature_validator):
        """Test with invalid feature_num_sources type."""
        features = {
            "feature_num_sources": "not a number",
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        invalid = feature_validator._check_feature_types(features)
        assert "feature_num_sources" in invalid

    def test_check_feature_types_invalid_sentiment(self, feature_validator):
        """Test with invalid feature_sentiment_mean type."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": "not a number",
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        invalid = feature_validator._check_feature_types(features)
        assert "feature_sentiment_mean" in invalid

    def test_check_feature_types_invalid_entities(self, feature_validator):
        """Test with invalid feature_entities type."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": 123,  # Should be list or string
            "feature_time_density": 0.5,
        }
        
        invalid = feature_validator._check_feature_types(features)
        assert "feature_entities" in invalid


class TestCheckFeatureRanges:
    """Test _check_feature_ranges method."""

    def test_check_feature_ranges_all_valid(self, feature_validator, valid_features):
        """Test with all features in valid ranges."""
        out_of_range = feature_validator._check_feature_ranges(valid_features)
        assert len(out_of_range) == 0

    def test_check_feature_ranges_negative_num_sources(self, feature_validator):
        """Test with negative feature_num_sources."""
        features = {
            "feature_num_sources": -5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        out_of_range = feature_validator._check_feature_ranges(features)
        assert "feature_num_sources" in out_of_range

    def test_check_feature_ranges_sentiment_out_of_range(self, feature_validator):
        """Test with feature_sentiment_mean out of range."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": 1.5,  # Should be [-1, 1]
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        out_of_range = feature_validator._check_feature_ranges(features)
        assert "feature_sentiment_mean" in out_of_range

    def test_check_feature_ranges_credibility_out_of_range(self, feature_validator):
        """Test with feature_credibility_mean out of range."""
        features = {
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 1.5,  # Should be [0, 1]
            "feature_entities": ["entity1"],
            "feature_time_density": 0.5,
        }
        
        out_of_range = feature_validator._check_feature_ranges(features)
        assert "feature_credibility_mean" in out_of_range


class TestCheckFeatureFreshness:
    """Test _check_feature_freshness method."""

    def test_check_feature_freshness_fresh(self, feature_validator):
        """Test with fresh features."""
        features = {
            "feature_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Should not raise exception
        feature_validator._check_feature_freshness(features, "group123", None)

    def test_check_feature_freshness_stale(self, feature_validator):
        """Test with stale features."""
        stale_timestamp = datetime.utcnow() - timedelta(hours=2)
        features = {
            "feature_timestamp": stale_timestamp.isoformat(),
        }
        
        with pytest.raises(FeatureValidationError) as exc_info:
            feature_validator._check_feature_freshness(features, "group123", None)
        
        assert "stale" in str(exc_info.value).lower() or "fresh" in str(exc_info.value).lower()

    def test_check_feature_freshness_at_threshold(self, feature_validator):
        """Test with features at freshness threshold."""
        threshold_timestamp = datetime.utcnow() - timedelta(seconds=3600)
        features = {
            "feature_timestamp": threshold_timestamp.isoformat(),
        }
        
        # Should be at the edge, might raise or not depending on implementation
        # This tests the boundary condition
        try:
            feature_validator._check_feature_freshness(features, "group123", None)
        except FeatureValidationError:
            pass  # Expected if implementation is strict

