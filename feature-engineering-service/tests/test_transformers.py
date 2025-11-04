"""Unit tests for feature transformers."""

import pytest
from src.transformers import FeatureAggregator, FeatureNormalizer


@pytest.fixture
def sample_features():
    """Create sample features."""
    return {
        "num_sources": 2,
        "sentiment_mean": 0.5,
        "sentiment_std": 0.1,
        "entity_count": 5,
        "avg_word_count": 150.5,
    }


def test_feature_aggregator(sample_features):
    """Test feature aggregator."""
    aggregator = FeatureAggregator()
    result = aggregator.transform(sample_features)

    # Check that all original features are present
    for key in sample_features:
        assert key in result

    # Check aggregate statistics
    assert "feature_count" in result
    assert "feature_sum" in result
    assert "feature_mean" in result
    assert "feature_min" in result
    assert "feature_max" in result
    assert "feature_range" in result

    assert result["feature_count"] == 5
    assert result["feature_min"] == 0.1
    assert result["feature_max"] == 150.5


def test_feature_normalizer(sample_features):
    """Test feature normalizer."""
    normalizer = FeatureNormalizer()
    result = normalizer.transform(sample_features)

    # Check that all features are present
    for key in sample_features:
        assert key in result

    # Check that sentiment features are normalized to [0, 1]
    assert 0 <= result["sentiment_mean"] <= 1
    assert 0 <= result["sentiment_std"] <= 1


def test_feature_normalizer_with_out_of_range():
    """Test normalizer with out-of-range values."""
    features = {
        "sentiment_mean": 2.0,  # Out of range [-1, 1]
        "sentiment_std": -0.5,  # Out of range [0, 1]
    }

    normalizer = FeatureNormalizer()
    result = normalizer.transform(features)

    # Should clamp to valid range
    assert 0 <= result["sentiment_mean"] <= 1
    assert 0 <= result["sentiment_std"] <= 1


def test_aggregator_with_empty_features():
    """Test aggregator with empty features."""
    aggregator = FeatureAggregator()
    result = aggregator.transform({})

    assert result == {}


def test_normalizer_with_non_numeric():
    """Test normalizer with non-numeric features."""
    features = {
        "topic": "politics",
        "sentiment_mean": 0.5,
    }

    normalizer = FeatureNormalizer()
    result = normalizer.transform(features)

    # Non-numeric features should be preserved
    assert result["topic"] == "politics"
    assert "sentiment_mean" in result

