"""Unit tests for feature validators."""

import pytest
import math
from src.validation import FeatureValidator, QualityChecker


@pytest.fixture
def valid_features():
    """Create valid features."""
    return {
        "num_sources": 2,
        "sentiment_mean": 0.5,
        "sentiment_std": 0.1,
        "entity_count": 5,
    }


@pytest.fixture
def invalid_features():
    """Create invalid features."""
    return {
        "num_sources": -1,  # Negative count
        "sentiment_mean": math.nan,  # NaN
        "sentiment_std": math.inf,  # Inf
        "entity_count": 5,
    }


def test_feature_validator_valid(valid_features):
    """Test validator with valid features."""
    validator = FeatureValidator()
    is_valid, errors = validator.validate(valid_features)

    assert is_valid is True
    assert len(errors) == 0


def test_feature_validator_invalid(invalid_features):
    """Test validator with invalid features."""
    validator = FeatureValidator()
    is_valid, errors = validator.validate(invalid_features)

    assert is_valid is False
    assert len(errors) > 0


def test_feature_validator_nan():
    """Test validator detects NaN."""
    features = {"sentiment_mean": math.nan}
    validator = FeatureValidator()
    is_valid, errors = validator.validate(features)

    assert is_valid is False
    assert any("NaN" in error for error in errors)


def test_feature_validator_inf():
    """Test validator detects Inf."""
    features = {"sentiment_std": math.inf}
    validator = FeatureValidator()
    is_valid, errors = validator.validate(features)

    assert is_valid is False
    assert any("Inf" in error for error in errors)


def test_feature_validator_negative_count():
    """Test validator detects negative counts."""
    features = {"num_sources": -5}
    validator = FeatureValidator()
    is_valid, errors = validator.validate(features)

    assert is_valid is False
    assert any("negative" in error.lower() for error in errors)


def test_feature_validator_out_of_range():
    """Test validator detects out-of-range values."""
    features = {"sentiment_mean": 2.0}  # Out of range [-1, 1]
    validator = FeatureValidator()
    is_valid, errors = validator.validate(features)

    assert is_valid is False
    assert any("out of range" in error.lower() for error in errors)


def test_quality_checker_normality():
    """Test quality checker normality test."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    checker = QualityChecker()
    result = checker.check_distribution("test_feature", values)

    assert result["test"] == "normality"
    assert "p_value" in result
    assert "is_normal" in result


def test_quality_checker_outliers():
    """Test quality checker outlier detection."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]  # 100.0 is outlier
    checker = QualityChecker()
    result = checker.check_distribution("test_feature", values)

    assert result["test"] == "normality"


def test_quality_checker_insufficient_data():
    """Test quality checker with insufficient data."""
    values = [1.0]
    checker = QualityChecker()
    result = checker.check_distribution("test_feature", values)

    assert result["result"] == "insufficient_data"


def test_quality_checker_correlation():
    """Test quality checker correlation analysis."""
    features = {
        "feature1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "feature2": [2.0, 4.0, 6.0, 8.0, 10.0],  # Perfectly correlated
    }
    checker = QualityChecker()
    result = checker.check_correlation(features)

    assert result["test"] == "correlation"
    assert "correlations" in result

