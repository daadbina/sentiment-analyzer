"""
Unit tests for FeatureFetcher.

Tests feature fetching from online and offline stores.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.features.feature_fetcher import FeatureFetcher, REQUIRED_FEATURES
from src.exceptions import FeatureFetchError


@pytest.fixture
def feast_client_mock():
    """Create a mock FeastClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def feature_fetcher(feast_client_mock):
    """Create a FeatureFetcher instance."""
    return FeatureFetcher(feast_client=feast_client_mock)


class TestFeatureFetcherInitialization:
    """Test FeatureFetcher initialization."""

    def test_init(self, feature_fetcher, feast_client_mock):
        """Test fetcher initialization."""
        assert feature_fetcher.feast_client == feast_client_mock


class TestFetchOnlineFeatures:
    """Test fetch_online_features method."""

    @pytest.mark.asyncio
    async def test_fetch_online_features_success(self, feature_fetcher, feast_client_mock):
        """Test successful online feature fetch."""
        feast_client_mock.get_online_features.return_value = [
            {
                "feature_num_sources": 5,
                "feature_sentiment_mean": 0.75,
                "feature_credibility_mean": 0.85,
                "feature_entities": ["entity1", "entity2"],
                "feature_time_density": 0.5,
                "feature_timestamp": datetime.utcnow().isoformat(),
            }
        ]
        
        features = await feature_fetcher.fetch_online_features("group123")
        
        assert features["feature_num_sources"] == 5
        assert features["feature_sentiment_mean"] == 0.75
        feast_client_mock.get_online_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_online_features_with_trace_id(self, feature_fetcher, feast_client_mock):
        """Test online feature fetch with trace ID."""
        feast_client_mock.get_online_features.return_value = [
            {
                "feature_num_sources": 5,
                "feature_sentiment_mean": 0.75,
            }
        ]
        
        features = await feature_fetcher.fetch_online_features("group123", trace_id="trace-123")
        
        call_args = feast_client_mock.get_online_features.call_args
        assert call_args[1]["trace_id"] == "trace-123"

    @pytest.mark.asyncio
    async def test_fetch_online_features_no_results(self, feature_fetcher, feast_client_mock):
        """Test online feature fetch with no results."""
        feast_client_mock.get_online_features.return_value = []
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_fetcher.fetch_online_features("group123")
        
        assert "No features returned" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_online_features_with_freshness(self, feature_fetcher, feast_client_mock):
        """Test online feature fetch with freshness tracking."""
        timestamp = datetime.utcnow() - timedelta(minutes=5)
        feast_client_mock.get_online_features.return_value = [
            {
                "feature_num_sources": 5,
                "feature_timestamp": timestamp.isoformat(),
            }
        ]
        
        with patch("src.features.feature_fetcher.feature_freshness_seconds") as metrics_mock:
            features = await feature_fetcher.fetch_online_features("group123")
            
            # Verify freshness metric was set
            metrics_mock.labels.assert_called_once_with(group_id="group123")

    @pytest.mark.asyncio
    async def test_fetch_online_features_exception(self, feature_fetcher, feast_client_mock):
        """Test online feature fetch with exception."""
        feast_client_mock.get_online_features.side_effect = Exception("Fetch failed")
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_fetcher.fetch_online_features("group123")
        
        assert "Failed to fetch online features" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_online_features_missing_required_features(self, feature_fetcher, feast_client_mock):
        """Test online feature fetch with missing required features."""
        feast_client_mock.get_online_features.return_value = [
            {
                "feature_num_sources": 5,
                # Missing other required features
            }
        ]
        
        features = await feature_fetcher.fetch_online_features("group123")
        
        # Should still return the features (validation happens elsewhere)
        assert features["feature_num_sources"] == 5


class TestFetchHistoricalFeatures:
    """Test fetch_historical_features method."""

    @pytest.mark.asyncio
    async def test_fetch_historical_features_success(self, feature_fetcher, feast_client_mock):
        """Test successful historical feature fetch."""
        group_ids = ["group1", "group2", "group3"]
        timestamps = [datetime.utcnow() for _ in range(3)]
        
        feast_client_mock.get_historical_features.return_value = [
            {
                "group_id": "group1",
                "feature_num_sources": 5,
                "feature_sentiment_mean": 0.75,
            },
            {
                "group_id": "group2",
                "feature_num_sources": 10,
                "feature_sentiment_mean": 0.85,
            },
            {
                "group_id": "group3",
                "feature_num_sources": 15,
                "feature_sentiment_mean": 0.65,
            },
        ]
        
        features = await feature_fetcher.fetch_historical_features(group_ids, timestamps)
        
        assert len(features) == 3
        assert features[0]["group_id"] == "group1"
        assert features[1]["feature_num_sources"] == 10
        feast_client_mock.get_historical_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_historical_features_with_trace_id(self, feature_fetcher, feast_client_mock):
        """Test historical feature fetch with trace ID."""
        group_ids = ["group1"]
        timestamps = [datetime.utcnow()]
        
        feast_client_mock.get_historical_features.return_value = [
            {"group_id": "group1", "feature_num_sources": 5}
        ]
        
        features = await feature_fetcher.fetch_historical_features(
            group_ids, timestamps, trace_id="trace-123"
        )
        
        call_args = feast_client_mock.get_historical_features.call_args
        assert call_args[1]["trace_id"] == "trace-123"

    @pytest.mark.asyncio
    async def test_fetch_historical_features_empty_list(self, feature_fetcher, feast_client_mock):
        """Test historical feature fetch with empty list."""
        feast_client_mock.get_historical_features.return_value = []
        
        features = await feature_fetcher.fetch_historical_features([], [])
        
        assert len(features) == 0

    @pytest.mark.asyncio
    async def test_fetch_historical_features_exception(self, feature_fetcher, feast_client_mock):
        """Test historical feature fetch with exception."""
        feast_client_mock.get_historical_features.side_effect = Exception("Fetch failed")
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_fetcher.fetch_historical_features(["group1"], [datetime.utcnow()])
        
        assert "Failed to fetch historical features" in str(exc_info.value)


class TestFetchBatchOnlineFeatures:
    """Test fetch_batch_online_features method."""

    @pytest.mark.asyncio
    async def test_fetch_batch_online_features_success(self, feature_fetcher, feast_client_mock):
        """Test successful batch online feature fetch."""
        group_ids = ["group1", "group2", "group3"]
        
        feast_client_mock.get_online_features.return_value = [
            {"group_id": "group1", "feature_num_sources": 5},
            {"group_id": "group2", "feature_num_sources": 10},
            {"group_id": "group3", "feature_num_sources": 15},
        ]
        
        features = await feature_fetcher.fetch_batch_online_features(group_ids)
        
        assert len(features) == 3
        assert features[0]["group_id"] == "group1"
        assert features[1]["feature_num_sources"] == 10

    @pytest.mark.asyncio
    async def test_fetch_batch_online_features_with_trace_id(self, feature_fetcher, feast_client_mock):
        """Test batch online feature fetch with trace ID."""
        group_ids = ["group1", "group2"]
        
        feast_client_mock.get_online_features.return_value = [
            {"group_id": "group1", "feature_num_sources": 5},
            {"group_id": "group2", "feature_num_sources": 10},
        ]
        
        features = await feature_fetcher.fetch_batch_online_features(
            group_ids, trace_id="trace-123"
        )
        
        call_args = feast_client_mock.get_online_features.call_args
        assert call_args[1]["trace_id"] == "trace-123"

    @pytest.mark.asyncio
    async def test_fetch_batch_online_features_empty_list(self, feature_fetcher, feast_client_mock):
        """Test batch online feature fetch with empty list."""
        feast_client_mock.get_online_features.return_value = []
        
        features = await feature_fetcher.fetch_batch_online_features([])
        
        assert len(features) == 0

    @pytest.mark.asyncio
    async def test_fetch_batch_online_features_partial_results(self, feature_fetcher, feast_client_mock):
        """Test batch online feature fetch with partial results."""
        group_ids = ["group1", "group2", "group3"]
        
        # Only 2 results returned (group2 missing)
        feast_client_mock.get_online_features.return_value = [
            {"group_id": "group1", "feature_num_sources": 5},
            {"group_id": "group3", "feature_num_sources": 15},
        ]
        
        features = await feature_fetcher.fetch_batch_online_features(group_ids)
        
        assert len(features) == 2

    @pytest.mark.asyncio
    async def test_fetch_batch_online_features_exception(self, feature_fetcher, feast_client_mock):
        """Test batch online feature fetch with exception."""
        feast_client_mock.get_online_features.side_effect = Exception("Fetch failed")
        
        with pytest.raises(FeatureFetchError):
            await feature_fetcher.fetch_batch_online_features(["group1", "group2"])


class TestRequiredFeatures:
    """Test REQUIRED_FEATURES constant."""

    def test_required_features_defined(self):
        """Test that required features are defined."""
        assert len(REQUIRED_FEATURES) > 0
        assert "semantic_group_features:num_sources" in REQUIRED_FEATURES
        assert "semantic_group_features:sentiment_mean" in REQUIRED_FEATURES
        assert "semantic_group_features:source_credibility_avg" in REQUIRED_FEATURES
        assert "semantic_group_features:entity_count" in REQUIRED_FEATURES
        assert "semantic_group_features:temporal_concentration" in REQUIRED_FEATURES

