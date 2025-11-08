"""
Unit tests for FeastClient.

Tests feature fetching from online and offline stores, error handling,
and metrics recording.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from src.clients.feast_client import FeastClient
from src.config import FeastConfig
from src.exceptions import FeatureFetchError


@pytest.fixture
def feast_config():
    """Create a test Feast configuration."""
    return FeastConfig(
        repo_path="/path/to/feast/repo",
        online_store_type="redis",
        offline_store_type="delta",
        redis_host="localhost",
        redis_port=6379,
        delta_path="s3://bucket/delta",
    )


@pytest.fixture
def feast_client(feast_config):
    """Create a FeastClient instance."""
    return FeastClient(config=feast_config)


@pytest.fixture
def mock_feature_store():
    """Create a mock FeatureStore."""
    store = MagicMock()
    return store


@pytest.fixture
def metrics_mock():
    """Mock MetricsCollector."""
    with patch("src.clients.feast_client.MetricsCollector") as mock:
        yield mock


class TestFeastClientInitialization:
    """Test FeastClient initialization."""

    def test_init(self, feast_client, feast_config):
        """Test client initialization."""
        assert feast_client.config == feast_config
        assert feast_client._store is None

    @pytest.mark.asyncio
    async def test_connect_success(self, feast_client, mock_feature_store):
        """Test successful connection to Feast."""
        with patch("src.clients.feast_client.FeatureStore", return_value=mock_feature_store):
            await feast_client.connect()
            assert feast_client._store is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self, feast_client):
        """Test connection failure."""
        with patch("src.clients.feast_client.FeatureStore", side_effect=Exception("Connection failed")):
            with pytest.raises(FeatureFetchError) as exc_info:
                await feast_client.connect()
            assert "Failed to connect to Feast feature store" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect(self, feast_client, mock_feature_store):
        """Test disconnection from Feast."""
        feast_client._store = mock_feature_store
        await feast_client.disconnect()
        assert feast_client._store is None

    def test_ensure_connected_not_connected(self, feast_client):
        """Test _ensure_connected when not connected."""
        with pytest.raises(FeatureFetchError) as exc_info:
            feast_client._ensure_connected()
        assert "not connected" in str(exc_info.value)

    def test_ensure_connected_success(self, feast_client, mock_feature_store):
        """Test _ensure_connected when connected."""
        feast_client._store = mock_feature_store
        store = feast_client._ensure_connected()
        assert store == mock_feature_store


class TestGetOnlineFeatures:
    """Test get_online_features method."""

    @pytest.mark.asyncio
    async def test_get_online_features_success(self, feast_client, mock_feature_store, metrics_mock):
        """Test successful online feature fetch."""
        feast_client._store = mock_feature_store
        
        # Mock feature vector response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature_num_sources": [5],
            "feature_sentiment_mean": [0.75],
        }
        mock_feature_store.get_online_features.return_value = mock_response
        
        feature_names = ["feature_num_sources", "feature_sentiment_mean"]
        entity_rows = [{"group_id": "123"}]
        
        result = await feast_client.get_online_features(
            feature_names=feature_names,
            entity_rows=entity_rows,
        )
        
        assert len(result) == 1
        assert result[0]["feature_num_sources"] == 5
        assert result[0]["feature_sentiment_mean"] == 0.75
        
        # Verify metrics recorded
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        assert metrics_mock.record_feature_fetch_latency.call_args[0][0] == "online"

    @pytest.mark.asyncio
    async def test_get_online_features_multiple_entities(self, feast_client, mock_feature_store, metrics_mock):
        """Test online feature fetch with multiple entities."""
        feast_client._store = mock_feature_store
        
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature_num_sources": [5, 10],
            "feature_sentiment_mean": [0.75, 0.85],
        }
        mock_feature_store.get_online_features.return_value = mock_response
        
        feature_names = ["feature_num_sources", "feature_sentiment_mean"]
        entity_rows = [{"group_id": "123"}, {"group_id": "456"}]
        
        result = await feast_client.get_online_features(
            feature_names=feature_names,
            entity_rows=entity_rows,
        )
        
        assert len(result) == 2
        assert result[0]["feature_num_sources"] == 5
        assert result[1]["feature_num_sources"] == 10

    @pytest.mark.asyncio
    async def test_get_online_features_not_connected(self, feast_client):
        """Test online feature fetch when not connected."""
        with pytest.raises(FeatureFetchError) as exc_info:
            await feast_client.get_online_features(
                feature_names=["feature1"],
                entity_rows=[{"group_id": "123"}],
            )
        assert "not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_online_features_fetch_failure(self, feast_client, mock_feature_store, metrics_mock):
        """Test online feature fetch failure."""
        feast_client._store = mock_feature_store
        mock_feature_store.get_online_features.side_effect = Exception("Fetch failed")
        
        feature_names = ["feature1", "feature2"]
        entity_rows = [{"group_id": "123"}]
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feast_client.get_online_features(
                feature_names=feature_names,
                entity_rows=entity_rows,
            )
        
        assert "Failed to fetch online features" in str(exc_info.value)
        
        # Verify failure metrics recorded for each feature
        assert metrics_mock.record_feature_fetch_failure.call_count == 2

    @pytest.mark.asyncio
    async def test_get_online_features_with_trace_id(self, feast_client, mock_feature_store, metrics_mock):
        """Test online feature fetch with trace ID."""
        feast_client._store = mock_feature_store
        
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"feature1": [1.0]}
        mock_feature_store.get_online_features.return_value = mock_response
        
        trace_id = "trace-123"
        result = await feast_client.get_online_features(
            feature_names=["feature1"],
            entity_rows=[{"group_id": "123"}],
            trace_id=trace_id,
        )
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_online_features_missing_feature(self, feast_client, mock_feature_store, metrics_mock):
        """Test online feature fetch with missing feature in response."""
        feast_client._store = mock_feature_store
        
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature1": [1.0],
            # feature2 is missing
        }
        mock_feature_store.get_online_features.return_value = mock_response
        
        result = await feast_client.get_online_features(
            feature_names=["feature1", "feature2"],
            entity_rows=[{"group_id": "123"}],
        )
        
        assert len(result) == 1
        assert result[0]["feature1"] == 1.0
        assert "feature2" not in result[0]

    @pytest.mark.asyncio
    async def test_get_online_features_empty_entity_rows(self, feast_client, mock_feature_store, metrics_mock):
        """Test online feature fetch with empty entity rows."""
        feast_client._store = mock_feature_store
        
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {}
        mock_feature_store.get_online_features.return_value = mock_response
        
        result = await feast_client.get_online_features(
            feature_names=["feature1"],
            entity_rows=[],
        )
        
        assert len(result) == 0


class TestGetHistoricalFeatures:
    """Test get_historical_features method."""

    @pytest.mark.asyncio
    async def test_get_historical_features_success(self, feast_client, mock_feature_store, metrics_mock):
        """Test successful historical feature fetch."""
        feast_client._store = mock_feature_store
        
        # Mock historical features response
        mock_df = MagicMock()
        mock_df.to_dict.return_value = {
            "group_id": ["123", "456"],
            "feature1": [1.0, 2.0],
            "feature2": [0.5, 0.6],
        }
        mock_feature_store.get_historical_features.return_value.to_df.return_value = mock_df
        
        feature_names = ["feature1", "feature2"]
        entity_df_dict = {
            "group_id": ["123", "456"],
            "event_timestamp": [datetime.now(), datetime.now()],
        }
        
        result = await feast_client.get_historical_features(
            feature_names=feature_names,
            entity_df_dict=entity_df_dict,
        )
        
        assert len(result) == 2
        assert result[0]["feature1"] == 1.0
        assert result[1]["feature1"] == 2.0
        
        # Verify metrics recorded
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        assert metrics_mock.record_feature_fetch_latency.call_args[0][0] == "offline"

    @pytest.mark.asyncio
    async def test_get_historical_features_not_connected(self, feast_client):
        """Test historical feature fetch when not connected."""
        with pytest.raises(FeatureFetchError) as exc_info:
            await feast_client.get_historical_features(
                feature_names=["feature1"],
                entity_df_dict={"group_id": ["123"]},
            )
        assert "not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_historical_features_fetch_failure(self, feast_client, mock_feature_store, metrics_mock):
        """Test historical feature fetch failure."""
        feast_client._store = mock_feature_store
        mock_feature_store.get_historical_features.side_effect = Exception("Fetch failed")
        
        feature_names = ["feature1", "feature2"]
        entity_df_dict = {"group_id": ["123"]}
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feast_client.get_historical_features(
                feature_names=feature_names,
                entity_df_dict=entity_df_dict,
            )
        
        assert "Failed to fetch historical features" in str(exc_info.value)
        
        # Verify failure metrics recorded
        assert metrics_mock.record_feature_fetch_failure.call_count == 2

