"""Quality tests for embedding service."""

import pytest
import numpy as np
from src.validation.quality_checks import QualityChecker
from src.validation.anomaly_detector import AnomalyDetector
from src.embedding.normalization import normalize_l2

pytestmark = pytest.mark.quality


@pytest.fixture
def quality_checker():
    """Create quality checker."""
    return QualityChecker()


@pytest.fixture
def anomaly_detector():
    """Create anomaly detector."""
    return AnomalyDetector()


def test_embedding_dimension_check(quality_checker):
    """Test embedding dimension check."""
    # Valid embedding
    valid = np.random.randn(768)
    assert quality_checker.check_dimension(valid, 768)

    # Invalid embedding
    invalid = np.random.randn(512)
    assert not quality_checker.check_dimension(invalid, 768)


def test_embedding_normalization_check(quality_checker):
    """Test embedding normalization check."""
    # Normalized embedding
    normalized = normalize_l2(np.random.randn(768))
    assert quality_checker.check_normalization(normalized)

    # Non-normalized embedding
    non_normalized = np.random.randn(768)
    assert not quality_checker.check_normalization(non_normalized)


def test_embedding_nan_check(quality_checker):
    """Test NaN check."""
    # Valid embedding
    valid = np.random.randn(768)
    assert quality_checker.check_no_nan(valid)

    # Embedding with NaN
    with_nan = np.full(768, np.nan)
    assert not quality_checker.check_no_nan(with_nan)


def test_embedding_inf_check(quality_checker):
    """Test Inf check."""
    # Valid embedding
    valid = np.random.randn(768)
    assert quality_checker.check_no_inf(valid)

    # Embedding with Inf
    with_inf = np.full(768, np.inf)
    assert not quality_checker.check_no_inf(with_inf)


def test_embedding_diversity_check(quality_checker):
    """Test embedding diversity check."""
    # Diverse embeddings
    diverse = np.random.randn(100, 768)
    diversity = quality_checker.check_diversity(diverse)
    assert diversity > 0.5

    # Identical embeddings
    identical = np.ones((100, 768))
    diversity = quality_checker.check_diversity(identical)
    assert diversity < 0.1


def test_embedding_statistics_check(quality_checker):
    """Test embedding statistics check."""
    embeddings = np.random.randn(100, 768)

    stats = quality_checker.get_statistics(embeddings)

    assert "mean" in stats
    assert "std" in stats
    assert "min" in stats
    assert "max" in stats
    assert stats["mean"] is not None
    assert stats["std"] is not None


def test_embedding_sparsity_check(quality_checker):
    """Test embedding sparsity check."""
    # Dense embedding
    dense = np.random.randn(768)
    sparsity = quality_checker.check_sparsity(dense)
    assert sparsity < 0.1

    # Sparse embedding
    sparse = np.zeros(768)
    sparse[:10] = np.random.randn(10)
    sparsity = quality_checker.check_sparsity(sparse)
    assert sparsity > 0.9


def test_anomaly_detection_z_score(anomaly_detector):
    """Test Z-score anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    anomalies, scores = anomaly_detector.detect_z_score_anomalies(embeddings)

    assert np.sum(anomalies) > 0
    assert anomalies[0]


def test_anomaly_detection_magnitude(anomaly_detector):
    """Test magnitude-based anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    anomalies, scores = anomaly_detector.detect_magnitude_anomalies(embeddings)

    assert np.sum(anomalies) > 0
    assert anomalies[0]


def test_anomaly_detection_cosine_distance(anomaly_detector):
    """Test cosine distance anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings = normalize_l2(embeddings)
    embeddings[0] = np.full(768, 1.0 / np.sqrt(768))  # Different direction

    anomalies, scores = anomaly_detector.detect_cosine_distance_anomalies(embeddings)

    assert np.sum(anomalies) > 0


def test_anomaly_detection_isolation_forest(anomaly_detector):
    """Test Isolation Forest anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    anomalies, scores = anomaly_detector.detect_isolation_forest_anomalies(embeddings)

    assert np.sum(anomalies) > 0


def test_anomaly_detection_lof(anomaly_detector):
    """Test Local Outlier Factor anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    anomalies, scores = anomaly_detector.detect_local_outlier_factor_anomalies(embeddings)

    assert np.sum(anomalies) > 0


def test_ensemble_anomaly_detection(anomaly_detector):
    """Test ensemble anomaly detection."""
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    anomalies, scores = anomaly_detector.detect_ensemble_anomalies(embeddings)

    assert np.sum(anomalies) > 0
    assert anomalies[0]


def test_quality_report(quality_checker):
    """Test quality report generation."""
    embeddings = np.random.randn(100, 768)
    embeddings = normalize_l2(embeddings)

    report = quality_checker.generate_report(embeddings)

    assert "dimension" in report
    assert "normalization" in report
    assert "nan_check" in report
    assert "inf_check" in report
    assert "diversity" in report
    assert "statistics" in report
    assert "sparsity" in report


def test_quality_threshold_validation(quality_checker):
    """Test quality threshold validation."""
    embeddings = np.random.randn(100, 768)
    embeddings = normalize_l2(embeddings)

    # Should pass quality checks
    assert quality_checker.check_dimension(embeddings[0], 768)
    assert quality_checker.check_normalization(embeddings[0])
    assert quality_checker.check_no_nan(embeddings[0])
    assert quality_checker.check_no_inf(embeddings[0])


def test_batch_quality_check(quality_checker):
    """Test batch quality check."""
    embeddings = np.random.randn(100, 768)
    embeddings = normalize_l2(embeddings)

    # Check all embeddings
    for embedding in embeddings:
        assert quality_checker.check_dimension(embedding, 768)
        assert quality_checker.check_normalization(embedding)
        assert quality_checker.check_no_nan(embedding)
        assert quality_checker.check_no_inf(embedding)


def test_quality_metrics_consistency(quality_checker):
    """Test consistency of quality metrics."""
    embeddings = np.random.randn(100, 768)
    embeddings = normalize_l2(embeddings)

    # Generate report twice
    report1 = quality_checker.generate_report(embeddings)
    report2 = quality_checker.generate_report(embeddings)

    # Should be consistent
    assert report1["dimension"] == report2["dimension"]
    assert report1["normalization"] == report2["normalization"]

