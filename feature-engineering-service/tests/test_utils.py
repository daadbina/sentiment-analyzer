"""Unit tests for utilities."""

import pytest
from datetime import datetime
from src.utils import (
    compute_checksum,
    compute_feature_checksum,
    FeatureVersion,
    FeatureLineage,
)


def test_compute_checksum_dict():
    """Test checksum computation for dict."""
    data = {"a": 1, "b": 2}
    checksum = compute_checksum(data)

    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA256 hex is 64 chars


def test_compute_checksum_consistency():
    """Test checksum consistency."""
    data = {"a": 1, "b": 2}
    checksum1 = compute_checksum(data)
    checksum2 = compute_checksum(data)

    assert checksum1 == checksum2


def test_compute_checksum_order_independent():
    """Test checksum is order-independent for dicts."""
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}

    checksum1 = compute_checksum(data1)
    checksum2 = compute_checksum(data2)

    assert checksum1 == checksum2


def test_compute_feature_checksum():
    """Test feature checksum computation."""
    features = {
        "sentiment_mean": 0.5,
        "num_sources": 2,
        "entity_count": 5,
    }
    checksum = compute_feature_checksum(features)

    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_feature_version():
    """Test feature version."""
    version = FeatureVersion(
        version="v1.0",
        feature_names=["sentiment_mean", "num_sources"],
        computation_timestamp=datetime.utcnow(),
    )

    assert version.version == "v1.0"
    assert len(version.feature_names) == 2
    assert version.checksum is not None


def test_feature_version_equality():
    """Test feature version equality."""
    now = datetime.utcnow()
    version1 = FeatureVersion(
        version="v1.0",
        feature_names=["sentiment_mean", "num_sources"],
        computation_timestamp=now,
    )
    version2 = FeatureVersion(
        version="v1.0",
        feature_names=["sentiment_mean", "num_sources"],
        computation_timestamp=now,
    )

    assert version1 == version2


def test_feature_lineage():
    """Test feature lineage tracking."""
    lineage = FeatureLineage(
        group_id="group_001",
        trace_id="trace_001",
    )

    lineage.add_extractor("source_extractor")
    lineage.add_transformation("aggregator")
    lineage.add_validation("feature_validator")
    lineage.add_feature_checksum("sentiment_mean", "abc123")

    assert len(lineage.extractors_used) == 1
    assert len(lineage.transformations_applied) == 1
    assert len(lineage.validations_passed) == 1
    assert "sentiment_mean" in lineage.feature_checksums


def test_feature_lineage_to_dict():
    """Test feature lineage serialization."""
    lineage = FeatureLineage(
        group_id="group_001",
        trace_id="trace_001",
    )

    lineage.add_extractor("source_extractor")

    data = lineage.to_dict()

    assert data["group_id"] == "group_001"
    assert data["trace_id"] == "trace_001"
    assert "extractors_used" in data
    assert len(data["extractors_used"]) == 1

