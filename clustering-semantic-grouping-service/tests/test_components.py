"""Unit tests for clustering components."""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from src.time_window_manager import TimeWindowManager
from src.clustering_engine import ClusteringEngine
from src.cluster_validator import ClusterValidator
from src.centroid_calculator import CentroidCalculator
from src.metadata_aggregator import MetadataAggregator
from src.topic_labeler import TopicLabeler
from src.temporal_tracker import TemporalTracker


class TestTimeWindowManager:
    """Tests for TimeWindowManager."""

    def test_initialization(self):
        """Test initialization."""
        manager = TimeWindowManager(window_size_hours=24, overlap_hours=6)
        assert manager.window_size_hours == 24
        assert manager.overlap_hours == 6

    def test_calculate_window_first_run(self):
        """Test window calculation for first run."""
        manager = TimeWindowManager(window_size_hours=24)
        start, end = manager.calculate_window(last_run_time=None)

        assert start < end
        duration = (end - start).total_seconds() / 3600
        assert duration == 24

    def test_calculate_window_subsequent_run(self):
        """Test window calculation for subsequent run."""
        manager = TimeWindowManager(window_size_hours=24, overlap_hours=6)
        last_run = datetime.now(timezone.utc) - timedelta(hours=4)
        start, end = manager.calculate_window(last_run_time=last_run)

        assert start < end
        assert start < last_run  # Should include overlap

    def test_validate_window(self):
        """Test window validation."""
        manager = TimeWindowManager()
        now = datetime.now(timezone.utc)

        # Valid window
        assert manager.validate_window(now - timedelta(hours=24), now)

        # Invalid: start >= end
        assert not manager.validate_window(now, now - timedelta(hours=1))

        # Invalid: too large
        assert not manager.validate_window(now - timedelta(days=10), now)


class TestClusteringEngine:
    """Tests for ClusteringEngine."""

    def test_initialization(self):
        """Test initialization."""
        engine = ClusteringEngine(algorithm="hdbscan", min_cluster_size=3)
        assert engine.algorithm == "hdbscan"
        assert engine.min_cluster_size == 3

    def test_cluster_hdbscan(self):
        """Test HDBSCAN clustering."""
        engine = ClusteringEngine(algorithm="hdbscan")

        # Create synthetic data
        np.random.seed(42)
        embeddings = np.random.randn(100, 768).astype(np.float32)

        labels = engine.cluster(embeddings)

        assert len(labels) == 100
        assert len(set(labels)) > 1  # Should have multiple clusters

    def test_cluster_dbscan(self):
        """Test DBSCAN clustering."""
        engine = ClusteringEngine(algorithm="dbscan")

        np.random.seed(42)
        embeddings = np.random.randn(100, 768).astype(np.float32)

        labels = engine.cluster(embeddings)

        assert len(labels) == 100

    def test_cluster_empty_embeddings(self):
        """Test clustering with empty embeddings."""
        engine = ClusteringEngine()
        embeddings = np.array([])

        labels = engine.cluster(embeddings)

        assert len(labels) == 0


class TestClusterValidator:
    """Tests for ClusterValidator."""

    def test_initialization(self):
        """Test initialization."""
        validator = ClusterValidator(min_cluster_purity=0.85)
        assert validator.min_cluster_purity == 0.85

    def test_validate_cluster_valid(self):
        """Test validation of valid cluster."""
        validator = ClusterValidator(min_cluster_size=3)

        # Create similar embeddings
        np.random.seed(42)
        base = np.random.randn(768).astype(np.float32)
        embeddings = np.array([base + np.random.randn(768) * 0.1 for _ in range(5)])

        articles = [
            {
                "article_id": f"art_{i}",
                "published_at": datetime.now(timezone.utc),
                "source": f"source_{i % 2}",
                "language": "en",
                "domain": "example.com",
            }
            for i in range(5)
        ]

        is_valid, report = validator.validate_cluster(
            embeddings, articles, datetime.now(timezone.utc)
        )

        assert isinstance(is_valid, bool)
        assert "metrics" in report
        assert "issues" in report

    def test_validate_cluster_too_small(self):
        """Test validation of too-small cluster."""
        validator = ClusterValidator(min_cluster_size=5)

        embeddings = np.random.randn(2, 768).astype(np.float32)
        articles = [{"article_id": f"art_{i}"} for i in range(2)]

        is_valid, report = validator.validate_cluster(
            embeddings, articles, datetime.now(timezone.utc)
        )

        assert not is_valid
        assert any("small" in issue.lower() for issue in report["issues"])


class TestCentroidCalculator:
    """Tests for CentroidCalculator."""

    def test_compute_unweighted_centroid(self):
        """Test unweighted centroid computation."""
        np.random.seed(42)
        embeddings = np.random.randn(10, 768).astype(np.float32)

        centroid = CentroidCalculator.compute_unweighted_centroid(embeddings)

        assert centroid.shape == (768,)
        assert np.isclose(np.linalg.norm(centroid), 1.0)  # Should be normalized

    def test_compute_weighted_centroid(self):
        """Test weighted centroid computation."""
        np.random.seed(42)
        embeddings = np.random.randn(10, 768).astype(np.float32)
        weights = np.array([1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

        centroid = CentroidCalculator.compute_weighted_centroid(embeddings, weights)

        assert centroid.shape == (768,)
        assert np.isclose(np.linalg.norm(centroid), 1.0)

    def test_select_representative_article(self):
        """Test representative article selection."""
        np.random.seed(42)
        embeddings = np.random.randn(10, 768).astype(np.float32)
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        article_ids = [f"art_{i}" for i in range(10)]

        rep_id = CentroidCalculator.select_representative_article(
            embeddings, centroid, article_ids
        )

        assert rep_id in article_ids


class TestMetadataAggregator:
    """Tests for MetadataAggregator."""

    def test_aggregate_cluster_metadata(self):
        """Test metadata aggregation."""
        articles = [
            {
                "article_id": f"art_{i}",
                "language": "en",
                "domain": "example.com",
                "source": f"source_{i % 2}",
                "publisher_credibility": 0.8,
                "published_at": datetime.now(timezone.utc),
            }
            for i in range(5)
        ]

        metadata = MetadataAggregator.aggregate_cluster_metadata(articles)

        assert metadata["article_count"] == 5
        assert len(metadata["article_ids"]) == 5
        assert "publisher_credibility_avg" in metadata


class TestTopicLabeler:
    """Tests for TopicLabeler."""

    def test_generate_label_extractive(self):
        """Test extractive label generation."""
        labeler = TopicLabeler()

        articles = [
            {
                "title": "Breaking News: Major Event Occurs",
                "body": "Details about the major event happening today",
            }
            for _ in range(3)
        ]

        label = labeler.generate_label(articles, method="extractive")

        assert isinstance(label, str)
        assert len(label) > 0


class TestTemporalTracker:
    """Tests for TemporalTracker."""

    def test_initialization(self):
        """Test initialization."""
        tracker = TemporalTracker(similarity_threshold=0.85)
        assert tracker.similarity_threshold == 0.85

    def test_track_cluster_evolution(self):
        """Test cluster evolution tracking."""
        tracker = TemporalTracker()

        np.random.seed(42)
        centroid = np.random.randn(768).astype(np.float32)
        articles = [{"article_id": f"art_{i}"} for i in range(5)]

        evolution = tracker.track_cluster_evolution(
            "cluster_1",
            articles,
            centroid,
            datetime.now(timezone.utc),
        )

        assert evolution["cluster_id"] == "cluster_1"
        assert evolution["article_count"] == 5

    def test_get_cluster_lineage(self):
        """Test cluster lineage retrieval."""
        tracker = TemporalTracker()

        np.random.seed(42)
        centroid = np.random.randn(768).astype(np.float32)
        articles = [{"article_id": f"art_{i}"} for i in range(5)]

        tracker.track_cluster_evolution(
            "cluster_1", articles, centroid, datetime.now(timezone.utc)
        )

        lineage = tracker.get_cluster_lineage("cluster_1")

        assert len(lineage) == 1
        assert lineage[0]["cluster_id"] == "cluster_1"

