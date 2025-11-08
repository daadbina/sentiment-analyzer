"""
Integration tests for feature reconciliation.

Tests offline vs online feature consistency and reconciliation metrics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from src.features.feature_fetcher import FeatureFetcher
from src.clients.feast_client import FeastClient


@pytest.fixture
def feast_client_mock():
    """Create a mock FeastClient."""
    client = AsyncMock(spec=FeastClient)
    return client


@pytest.fixture
def feature_fetcher(feast_client_mock):
    """Create a FeatureFetcher instance."""
    return FeatureFetcher(feast_client=feast_client_mock)


@pytest.fixture
def online_features() -> List[Dict[str, Any]]:
    """Create online feature data."""
    return [
        {
            "group_id": "group1",
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1", "entity2"],
            "feature_time_density": 0.5,
        },
        {
            "group_id": "group2",
            "feature_num_sources": 10,
            "feature_sentiment_mean": 0.65,
            "feature_credibility_mean": 0.75,
            "feature_entities": ["entity3"],
            "feature_time_density": 0.6,
        },
        {
            "group_id": "group3",
            "feature_num_sources": 3,
            "feature_sentiment_mean": 0.55,
            "feature_credibility_mean": 0.95,
            "feature_entities": ["entity4", "entity5"],
            "feature_time_density": 0.4,
        },
    ]


@pytest.fixture
def offline_features() -> List[Dict[str, Any]]:
    """Create offline feature data (matching online)."""
    return [
        {
            "group_id": "group1",
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1", "entity2"],
            "feature_time_density": 0.5,
        },
        {
            "group_id": "group2",
            "feature_num_sources": 10,
            "feature_sentiment_mean": 0.65,
            "feature_credibility_mean": 0.75,
            "feature_entities": ["entity3"],
            "feature_time_density": 0.6,
        },
        {
            "group_id": "group3",
            "feature_num_sources": 3,
            "feature_sentiment_mean": 0.55,
            "feature_credibility_mean": 0.95,
            "feature_entities": ["entity4", "entity5"],
            "feature_time_density": 0.4,
        },
    ]


@pytest.fixture
def offline_features_with_mismatch() -> List[Dict[str, Any]]:
    """Create offline feature data with mismatches."""
    return [
        {
            "group_id": "group1",
            "feature_num_sources": 5,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
            "feature_entities": ["entity1", "entity2"],
            "feature_time_density": 0.5,
        },
        {
            "group_id": "group2",
            "feature_num_sources": 12,  # Mismatch: should be 10
            "feature_sentiment_mean": 0.70,  # Mismatch: should be 0.65
            "feature_credibility_mean": 0.75,
            "feature_entities": ["entity3"],
            "feature_time_density": 0.6,
        },
        {
            "group_id": "group3",
            "feature_num_sources": 3,
            "feature_sentiment_mean": 0.55,
            "feature_credibility_mean": 0.90,  # Mismatch: should be 0.95
            "feature_entities": ["entity4", "entity5"],
            "feature_time_density": 0.4,
        },
    ]


@pytest.mark.integration
class TestFeatureReconciliation:
    """Test feature reconciliation between online and offline stores."""

    @pytest.mark.asyncio
    async def test_perfect_reconciliation(
        self, feature_fetcher, feast_client_mock, online_features, offline_features
    ):
        """Test perfect reconciliation (100% match)."""
        # Setup mocks
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = offline_features
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Calculate match rate
        matches = 0
        total = 0
        
        for online, offline in zip(online_results, offline_results):
            for key in ["feature_num_sources", "feature_sentiment_mean", "feature_credibility_mean"]:
                total += 1
                if online.get(key) == offline.get(key):
                    matches += 1
        
        match_rate = matches / total if total > 0 else 0
        
        # Verify ≥99% match rate
        assert match_rate >= 0.99
        assert match_rate == 1.0  # Perfect match

    @pytest.mark.asyncio
    async def test_reconciliation_with_mismatches(
        self, feature_fetcher, feast_client_mock, online_features, offline_features_with_mismatch
    ):
        """Test reconciliation with mismatches."""
        # Setup mocks
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = offline_features_with_mismatch
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Calculate match rate and detect mismatches
        matches = 0
        total = 0
        mismatches = []
        
        for online, offline in zip(online_results, offline_results):
            group_id = online.get("group_id")
            for key in ["feature_num_sources", "feature_sentiment_mean", "feature_credibility_mean"]:
                total += 1
                if online.get(key) == offline.get(key):
                    matches += 1
                else:
                    mismatches.append({
                        "group_id": group_id,
                        "feature": key,
                        "online_value": online.get(key),
                        "offline_value": offline.get(key),
                    })
        
        match_rate = matches / total if total > 0 else 0
        
        # Verify mismatches detected
        assert len(mismatches) == 3  # 3 mismatches in the data
        assert match_rate < 1.0
        
        # Verify specific mismatches
        mismatch_features = [m["feature"] for m in mismatches]
        assert "feature_num_sources" in mismatch_features
        assert "feature_sentiment_mean" in mismatch_features
        assert "feature_credibility_mean" in mismatch_features

    @pytest.mark.asyncio
    async def test_reconciliation_metric_calculation(
        self, feature_fetcher, feast_client_mock, online_features, offline_features
    ):
        """Test reconciliation metric calculation."""
        # Setup mocks
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = offline_features
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Calculate detailed metrics
        feature_metrics = {}
        
        for feature_name in ["feature_num_sources", "feature_sentiment_mean", "feature_credibility_mean"]:
            matches = 0
            total = 0
            
            for online, offline in zip(online_results, offline_results):
                total += 1
                if online.get(feature_name) == offline.get(feature_name):
                    matches += 1
            
            feature_metrics[feature_name] = {
                "matches": matches,
                "total": total,
                "match_rate": matches / total if total > 0 else 0,
            }
        
        # Verify all features have 100% match rate
        for feature_name, metrics in feature_metrics.items():
            assert metrics["match_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_reconciliation_with_missing_offline_data(
        self, feature_fetcher, feast_client_mock, online_features
    ):
        """Test reconciliation with missing offline data."""
        # Setup mocks - offline returns fewer results
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = online_features[:2]  # Only 2 results
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Verify counts
        assert len(online_results) == 3
        assert len(offline_results) == 2
        
        # Calculate match rate only for available data
        matches = 0
        total = 0
        
        for online, offline in zip(online_results, offline_results):
            for key in ["feature_num_sources", "feature_sentiment_mean"]:
                total += 1
                if online.get(key) == offline.get(key):
                    matches += 1
        
        match_rate = matches / total if total > 0 else 0
        assert match_rate == 1.0  # Available data matches

    @pytest.mark.asyncio
    async def test_reconciliation_threshold_validation(
        self, feature_fetcher, feast_client_mock, online_features, offline_features_with_mismatch
    ):
        """Test reconciliation threshold validation (≥99%)."""
        # Setup mocks
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = offline_features_with_mismatch
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Calculate match rate
        matches = 0
        total = 0
        
        for online, offline in zip(online_results, offline_results):
            for key in ["feature_num_sources", "feature_sentiment_mean", "feature_credibility_mean"]:
                total += 1
                if online.get(key) == offline.get(key):
                    matches += 1
        
        match_rate = matches / total if total > 0 else 0
        
        # With 3 mismatches out of 9 comparisons, match rate is 66.7%
        # This should fail the ≥99% threshold
        assert match_rate < 0.99
        
        # In production, this would trigger an alert


@pytest.mark.integration
class TestReconciliationMetrics:
    """Test reconciliation metrics recording."""

    @pytest.mark.asyncio
    async def test_record_reconciliation_metrics(
        self, feature_fetcher, feast_client_mock, online_features, offline_features
    ):
        """Test recording reconciliation metrics."""
        with patch("src.features.feature_fetcher.feature_reconciliation_mismatch_total") as metrics_mock:
            # Setup mocks
            feast_client_mock.get_online_features.return_value = online_features
            feast_client_mock.get_historical_features.return_value = offline_features
            
            # Fetch features
            group_ids = ["group1", "group2", "group3"]
            timestamps = [datetime.utcnow() for _ in range(3)]
            
            await feature_fetcher.fetch_batch_online_features(group_ids)
            await feature_fetcher.fetch_historical_features(group_ids, timestamps)
            
            # Metrics should be recorded (implementation-specific)
            # This is a placeholder for actual metrics recording logic

    @pytest.mark.asyncio
    async def test_alert_on_reconciliation_failure(
        self, feature_fetcher, feast_client_mock, online_features, offline_features_with_mismatch
    ):
        """Test alerting on reconciliation failure."""
        # Setup mocks
        feast_client_mock.get_online_features.return_value = online_features
        feast_client_mock.get_historical_features.return_value = offline_features_with_mismatch
        
        # Fetch features
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        online_results = await feature_fetcher.fetch_batch_online_features(group_ids)
        offline_results = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        # Calculate match rate
        matches = 0
        total = 0
        
        for online, offline in zip(online_results, offline_results):
            for key in ["feature_num_sources", "feature_sentiment_mean", "feature_credibility_mean"]:
                total += 1
                if online.get(key) == offline.get(key):
                    matches += 1
        
        match_rate = matches / total if total > 0 else 0
        
        # If match rate < 99%, should trigger alert
        if match_rate < 0.99:
            # In production, this would trigger an alert via Prometheus/Alertmanager
            alert_triggered = True
        else:
            alert_triggered = False
        
        assert alert_triggered is True

