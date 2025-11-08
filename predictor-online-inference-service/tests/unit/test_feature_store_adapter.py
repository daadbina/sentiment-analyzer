"""
Unit tests for FeatureStoreAdapter.

Tests online/offline feature fetching, version tracking, and error handling.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from src.features.feature_store_adapter import FeatureStoreAdapter
from src.exceptions import FeatureFetchError
from src.config import FeastConfig


@pytest.fixture
def feast_config():
    """Create Feast configuration for testing."""
    return FeastConfig(
        repo_path="/tmp/feast_repo",
        online_store_type="redis",
        offline_store_type="delta",
        feature_service_name="event_features"
    )


@pytest.fixture
def feast_client_mock():
    """Create Feast client mock."""
    client = Mock()
    client.get_online_features = AsyncMock()
    client.get_offline_features = AsyncMock()
    return client


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.record_feature_fetch_latency = Mock()
    metrics.increment_feature_fetch_failures = Mock()
    return metrics


@pytest.fixture
def feature_store_adapter(feast_config, feast_client_mock, metrics_mock):
    """Create FeatureStoreAdapter instance for testing."""
    return FeatureStoreAdapter(
        config=feast_config,
        feast_client=feast_client_mock,
        metrics=metrics_mock
    )


class TestFeatureStoreAdapter:
    """Test suite for FeatureStoreAdapter."""
    
    @pytest.mark.asyncio
    async def test_get_online_features_success(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test successful online feature fetch."""
        entity_rows = [{"event_id": "evt_123"}]
        feature_refs = ["event_features:feature1", "event_features:feature2"]
        
        # Mock Feast response
        feast_client_mock.get_online_features.return_value = {
            "event_features:feature1": [0.5],
            "event_features:feature2": [0.8]
        }
        
        features = await feature_store_adapter.get_online_features(
            entity_rows=entity_rows,
            feature_refs=feature_refs
        )
        
        assert features == {
            "event_features:feature1": [0.5],
            "event_features:feature2": [0.8]
        }
        feast_client_mock.get_online_features.assert_called_once()
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        assert metrics_mock.record_feature_fetch_latency.call_args[1]["store_type"] == "online"
    
    @pytest.mark.asyncio
    async def test_get_online_features_failure(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test online feature fetch failure."""
        entity_rows = [{"event_id": "evt_123"}]
        feature_refs = ["event_features:feature1"]
        
        # Mock Feast to raise exception
        feast_client_mock.get_online_features.side_effect = Exception("Feast error")
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_store_adapter.get_online_features(
                entity_rows=entity_rows,
                feature_refs=feature_refs
            )
        
        assert "Failed to fetch online features" in str(exc_info.value)
        metrics_mock.increment_feature_fetch_failures.assert_called_once_with(store_type="online")
    
    @pytest.mark.asyncio
    async def test_get_offline_features_success(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test successful offline feature fetch."""
        entity_df = pd.DataFrame({
            "event_id": ["evt_123", "evt_456"],
            "event_timestamp": [datetime.now(), datetime.now()]
        })
        feature_refs = ["event_features:feature1", "event_features:feature2"]
        
        # Mock Feast response
        result_df = pd.DataFrame({
            "event_id": ["evt_123", "evt_456"],
            "event_features:feature1": [0.5, 0.6],
            "event_features:feature2": [0.8, 0.9]
        })
        feast_client_mock.get_offline_features.return_value = result_df
        
        features = await feature_store_adapter.get_offline_features(
            entity_df=entity_df,
            feature_refs=feature_refs
        )
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) == 2
        assert "event_features:feature1" in features.columns
        feast_client_mock.get_offline_features.assert_called_once()
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        assert metrics_mock.record_feature_fetch_latency.call_args[1]["store_type"] == "offline"
    
    @pytest.mark.asyncio
    async def test_get_offline_features_failure(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test offline feature fetch failure."""
        entity_df = pd.DataFrame({
            "event_id": ["evt_123"],
            "event_timestamp": [datetime.now()]
        })
        feature_refs = ["event_features:feature1"]
        
        # Mock Feast to raise exception
        feast_client_mock.get_offline_features.side_effect = Exception("Feast error")
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_store_adapter.get_offline_features(
                entity_df=entity_df,
                feature_refs=feature_refs
            )
        
        assert "Failed to fetch offline features" in str(exc_info.value)
        metrics_mock.increment_feature_fetch_failures.assert_called_once_with(store_type="offline")
    
    @pytest.mark.asyncio
    async def test_track_feature_version(self, feature_store_adapter):
        """Test feature version tracking."""
        feature_name = "event_features:feature1"
        version = "v2.0"
        
        await feature_store_adapter.track_feature_version(
            feature_name=feature_name,
            version=version
        )
        
        # Verify version is tracked
        tracked_version = feature_store_adapter._feature_versions.get(feature_name)
        assert tracked_version == version
    
    @pytest.mark.asyncio
    async def test_get_feature_version(self, feature_store_adapter):
        """Test getting tracked feature version."""
        feature_name = "event_features:feature1"
        version = "v2.0"
        
        # Track version first
        await feature_store_adapter.track_feature_version(feature_name, version)
        
        # Get version
        retrieved_version = feature_store_adapter.get_feature_version(feature_name)
        assert retrieved_version == version
    
    @pytest.mark.asyncio
    async def test_get_feature_version_not_tracked(self, feature_store_adapter):
        """Test getting version for untracked feature."""
        feature_name = "event_features:unknown_feature"
        
        version = feature_store_adapter.get_feature_version(feature_name)
        assert version is None
    
    @pytest.mark.asyncio
    async def test_get_online_features_empty_entity_rows(
        self, feature_store_adapter, feast_client_mock
    ):
        """Test online feature fetch with empty entity rows."""
        entity_rows = []
        feature_refs = ["event_features:feature1"]
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_store_adapter.get_online_features(
                entity_rows=entity_rows,
                feature_refs=feature_refs
            )
        
        assert "Empty entity rows" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_online_features_empty_feature_refs(
        self, feature_store_adapter, feast_client_mock
    ):
        """Test online feature fetch with empty feature refs."""
        entity_rows = [{"event_id": "evt_123"}]
        feature_refs = []
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_store_adapter.get_online_features(
                entity_rows=entity_rows,
                feature_refs=feature_refs
            )
        
        assert "Empty feature refs" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_offline_features_empty_dataframe(
        self, feature_store_adapter, feast_client_mock
    ):
        """Test offline feature fetch with empty dataframe."""
        entity_df = pd.DataFrame()
        feature_refs = ["event_features:feature1"]
        
        with pytest.raises(FeatureFetchError) as exc_info:
            await feature_store_adapter.get_offline_features(
                entity_df=entity_df,
                feature_refs=feature_refs
            )
        
        assert "Empty entity dataframe" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_online_features_partial_results(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test online feature fetch with partial results (some features missing)."""
        entity_rows = [{"event_id": "evt_123"}]
        feature_refs = ["event_features:feature1", "event_features:feature2"]
        
        # Mock Feast to return only one feature
        feast_client_mock.get_online_features.return_value = {
            "event_features:feature1": [0.5]
            # feature2 is missing
        }
        
        features = await feature_store_adapter.get_online_features(
            entity_rows=entity_rows,
            feature_refs=feature_refs
        )
        
        # Should still return partial results
        assert "event_features:feature1" in features
        assert "event_features:feature2" not in features
    
    @pytest.mark.asyncio
    async def test_get_online_features_latency_tracking(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test that latency is properly tracked for online features."""
        entity_rows = [{"event_id": "evt_123"}]
        feature_refs = ["event_features:feature1"]
        
        feast_client_mock.get_online_features.return_value = {
            "event_features:feature1": [0.5]
        }
        
        await feature_store_adapter.get_online_features(
            entity_rows=entity_rows,
            feature_refs=feature_refs
        )
        
        # Verify latency was recorded
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        call_args = metrics_mock.record_feature_fetch_latency.call_args
        latency = call_args[0][0]
        assert latency >= 0  # Latency should be non-negative
        assert call_args[1]["store_type"] == "online"
    
    @pytest.mark.asyncio
    async def test_get_offline_features_latency_tracking(
        self, feature_store_adapter, feast_client_mock, metrics_mock
    ):
        """Test that latency is properly tracked for offline features."""
        entity_df = pd.DataFrame({
            "event_id": ["evt_123"],
            "event_timestamp": [datetime.now()]
        })
        feature_refs = ["event_features:feature1"]
        
        result_df = pd.DataFrame({
            "event_id": ["evt_123"],
            "event_features:feature1": [0.5]
        })
        feast_client_mock.get_offline_features.return_value = result_df
        
        await feature_store_adapter.get_offline_features(
            entity_df=entity_df,
            feature_refs=feature_refs
        )
        
        # Verify latency was recorded
        metrics_mock.record_feature_fetch_latency.assert_called_once()
        call_args = metrics_mock.record_feature_fetch_latency.call_args
        latency = call_args[0][0]
        assert latency >= 0  # Latency should be non-negative
        assert call_args[1]["store_type"] == "offline"
    
    @pytest.mark.asyncio
    async def test_close(self, feature_store_adapter, feast_client_mock):
        """Test closing the adapter."""
        feast_client_mock.disconnect = AsyncMock()
        
        await feature_store_adapter.close()
        
        feast_client_mock.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_version_tracking(self, feature_store_adapter):
        """Test tracking multiple feature versions."""
        features = {
            "event_features:feature1": "v1.0",
            "event_features:feature2": "v2.0",
            "event_features:feature3": "v1.5"
        }
        
        for feature_name, version in features.items():
            await feature_store_adapter.track_feature_version(feature_name, version)
        
        # Verify all versions are tracked
        for feature_name, expected_version in features.items():
            actual_version = feature_store_adapter.get_feature_version(feature_name)
            assert actual_version == expected_version

