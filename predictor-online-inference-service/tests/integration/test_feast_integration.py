"""
Integration tests for Feast integration.

Tests feature retrieval from online and offline stores, and end-to-end workflows.
Requires Feast feature store to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd

from src.clients.feast_client import FeastClient
from src.config import FeastConfig
from src.exceptions import FeatureFetchError


@pytest.fixture
def feast_config():
    """Create Feast configuration for testing."""
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
    """Create FeastClient instance."""
    return FeastClient(config=feast_config)


class TestFeastConnection:
    """Test Feast connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, feast_client):
        """Test successful connection to Feast."""
        with patch("src.clients.feast_client.FeatureStore") as mock_store:
            mock_store.return_value = MagicMock()
            await feast_client.connect()
            assert feast_client._store is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, feast_client):
        """Test connection failure handling."""
        with patch("src.clients.feast_client.FeatureStore", side_effect=Exception("Connection failed")):
            with pytest.raises(FeatureFetchError):
                await feast_client.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_disconnect(self, feast_client):
        """Test disconnection from Feast."""
        feast_client._store = MagicMock()
        await feast_client.disconnect()
        assert feast_client._store is None


class TestOnlineFeatureRetrieval:
    """Test online feature retrieval."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_online_features_single_entity(self, feast_client):
        """Test fetching online features for single entity."""
        mock_store = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature_num_sources": [5],
            "feature_sentiment_mean": [0.75],
        }
        mock_store.get_online_features.return_value = mock_response
        feast_client._store = mock_store
        
        features = await feast_client.get_online_features(
            feature_names=["feature_num_sources", "feature_sentiment_mean"],
            entity_rows=[{"group_id": "123"}],
        )
        
        assert len(features) == 1
        assert features[0]["feature_num_sources"] == 5
        assert features[0]["feature_sentiment_mean"] == 0.75

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_online_features_multiple_entities(self, feast_client):
        """Test fetching online features for multiple entities."""
        mock_store = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature_num_sources": [5, 10, 15],
            "feature_sentiment_mean": [0.75, 0.85, 0.65],
        }
        mock_store.get_online_features.return_value = mock_response
        feast_client._store = mock_store
        
        features = await feast_client.get_online_features(
            feature_names=["feature_num_sources", "feature_sentiment_mean"],
            entity_rows=[
                {"group_id": "123"},
                {"group_id": "456"},
                {"group_id": "789"},
            ],
        )
        
        assert len(features) == 3
        assert features[0]["feature_num_sources"] == 5
        assert features[1]["feature_num_sources"] == 10
        assert features[2]["feature_num_sources"] == 15

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_online_features_with_null_values(self, feast_client):
        """Test fetching online features with null values."""
        mock_store = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "feature_num_sources": [5, None, 15],
            "feature_sentiment_mean": [0.75, 0.85, None],
        }
        mock_store.get_online_features.return_value = mock_response
        feast_client._store = mock_store
        
        features = await feast_client.get_online_features(
            feature_names=["feature_num_sources", "feature_sentiment_mean"],
            entity_rows=[
                {"group_id": "123"},
                {"group_id": "456"},
                {"group_id": "789"},
            ],
        )
        
        assert len(features) == 3
        assert features[1]["feature_num_sources"] is None
        assert features[2]["feature_sentiment_mean"] is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_online_features_latency_tracking(self, feast_client):
        """Test that online feature fetch tracks latency."""
        mock_store = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"feature1": [1.0]}
        mock_store.get_online_features.return_value = mock_response
        feast_client._store = mock_store
        
        with patch("src.clients.feast_client.MetricsCollector") as metrics_mock:
            await feast_client.get_online_features(
                feature_names=["feature1"],
                entity_rows=[{"group_id": "123"}],
            )
            
            # Verify latency was recorded
            metrics_mock.record_feature_fetch_latency.assert_called_once()
            assert metrics_mock.record_feature_fetch_latency.call_args[0][0] == "online"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_online_features_failure(self, feast_client):
        """Test online feature fetch failure."""
        mock_store = MagicMock()
        mock_store.get_online_features.side_effect = Exception("Fetch failed")
        feast_client._store = mock_store
        
        with pytest.raises(FeatureFetchError):
            await feast_client.get_online_features(
                feature_names=["feature1"],
                entity_rows=[{"group_id": "123"}],
            )


class TestOfflineFeatureRetrieval:
    """Test offline feature retrieval."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_historical_features_success(self, feast_client):
        """Test fetching historical features."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame({
            "group_id": ["123", "456"],
            "feature1": [1.0, 2.0],
            "feature2": [0.5, 0.6],
        })
        mock_store.get_historical_features.return_value.to_df.return_value = mock_df
        feast_client._store = mock_store
        
        features = await feast_client.get_historical_features(
            feature_names=["feature1", "feature2"],
            entity_df_dict={
                "group_id": ["123", "456"],
                "event_timestamp": [datetime.now(), datetime.now()],
            },
        )
        
        assert len(features) == 2
        assert features[0]["feature1"] == 1.0
        assert features[1]["feature1"] == 2.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_historical_features_with_time_range(self, feast_client):
        """Test fetching historical features with time range."""
        mock_store = MagicMock()
        
        # Create timestamps for last 7 days
        timestamps = [datetime.now() - timedelta(days=i) for i in range(7)]
        
        mock_df = pd.DataFrame({
            "group_id": [f"group{i}" for i in range(7)],
            "event_timestamp": timestamps,
            "feature1": [float(i) for i in range(7)],
        })
        mock_store.get_historical_features.return_value.to_df.return_value = mock_df
        feast_client._store = mock_store
        
        features = await feast_client.get_historical_features(
            feature_names=["feature1"],
            entity_df_dict={
                "group_id": [f"group{i}" for i in range(7)],
                "event_timestamp": timestamps,
            },
        )
        
        assert len(features) == 7

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_historical_features_latency_tracking(self, feast_client):
        """Test that historical feature fetch tracks latency."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame({"group_id": ["123"], "feature1": [1.0]})
        mock_store.get_historical_features.return_value.to_df.return_value = mock_df
        feast_client._store = mock_store
        
        with patch("src.clients.feast_client.MetricsCollector") as metrics_mock:
            await feast_client.get_historical_features(
                feature_names=["feature1"],
                entity_df_dict={"group_id": ["123"]},
            )
            
            # Verify latency was recorded
            metrics_mock.record_feature_fetch_latency.assert_called_once()
            assert metrics_mock.record_feature_fetch_latency.call_args[0][0] == "offline"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_historical_features_failure(self, feast_client):
        """Test historical feature fetch failure."""
        mock_store = MagicMock()
        mock_store.get_historical_features.side_effect = Exception("Fetch failed")
        feast_client._store = mock_store
        
        with pytest.raises(FeatureFetchError):
            await feast_client.get_historical_features(
                feature_names=["feature1"],
                entity_df_dict={"group_id": ["123"]},
            )


class TestFeatureReconciliation:
    """Test feature reconciliation between online and offline stores."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_online_offline_consistency(self, feast_client):
        """Test consistency between online and offline features."""
        mock_store = MagicMock()
        feast_client._store = mock_store
        
        # Mock online features
        mock_online_response = MagicMock()
        mock_online_response.to_dict.return_value = {
            "feature1": [1.0],
            "feature2": [0.5],
        }
        mock_store.get_online_features.return_value = mock_online_response
        
        # Mock offline features
        mock_df = pd.DataFrame({
            "group_id": ["123"],
            "feature1": [1.0],
            "feature2": [0.5],
        })
        mock_store.get_historical_features.return_value.to_df.return_value = mock_df
        
        # Fetch both
        online_features = await feast_client.get_online_features(
            feature_names=["feature1", "feature2"],
            entity_rows=[{"group_id": "123"}],
        )
        
        offline_features = await feast_client.get_historical_features(
            feature_names=["feature1", "feature2"],
            entity_df_dict={"group_id": ["123"]},
        )
        
        # Verify consistency
        assert online_features[0]["feature1"] == offline_features[0]["feature1"]
        assert online_features[0]["feature2"] == offline_features[0]["feature2"]


class TestEndToEndWorkflow:
    """Test end-to-end Feast workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_fetch_workflow(self, feast_client):
        """Test complete workflow: connect -> fetch online -> fetch offline."""
        with patch("src.clients.feast_client.FeatureStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store_class.return_value = mock_store
            
            # Connect
            await feast_client.connect()
            
            # Fetch online features
            mock_online_response = MagicMock()
            mock_online_response.to_dict.return_value = {"feature1": [1.0]}
            mock_store.get_online_features.return_value = mock_online_response
            
            online_features = await feast_client.get_online_features(
                feature_names=["feature1"],
                entity_rows=[{"group_id": "123"}],
            )
            
            # Fetch offline features
            mock_df = pd.DataFrame({"group_id": ["123"], "feature1": [1.0]})
            mock_store.get_historical_features.return_value.to_df.return_value = mock_df
            
            offline_features = await feast_client.get_historical_features(
                feature_names=["feature1"],
                entity_df_dict={"group_id": ["123"]},
            )
            
            assert len(online_features) == 1
            assert len(offline_features) == 1


class TestErrorHandling:
    """Test error handling in Feast integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_network_timeout(self, feast_client):
        """Test handling of network timeout."""
        mock_store = MagicMock()
        mock_store.get_online_features.side_effect = TimeoutError("Timeout")
        feast_client._store = mock_store
        
        with pytest.raises(FeatureFetchError):
            await feast_client.get_online_features(
                feature_names=["feature1"],
                entity_rows=[{"group_id": "123"}],
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_feature_name(self, feast_client):
        """Test handling of invalid feature name."""
        mock_store = MagicMock()
        mock_store.get_online_features.side_effect = Exception("Feature not found")
        feast_client._store = mock_store
        
        with pytest.raises(FeatureFetchError):
            await feast_client.get_online_features(
                feature_names=["invalid_feature"],
                entity_rows=[{"group_id": "123"}],
            )

