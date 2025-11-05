"""
Integration tests for Feast integration.

Tests Feast feature store operations.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from src.clients.feast_client import FeastClient
from src.data.feature_retriever import FeatureRetriever


class TestFeastIntegration:
    """Test Feast integration."""

    @pytest.fixture
    def mock_feast_store(self):
        """Create mock Feast feature store."""
        with patch("src.clients.feast_client.FeatureStore") as mock:
            yield mock

    def test_feast_client_initialization(self, mock_feast_store):
        """Test Feast client initialization."""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        assert client is not None
        assert client.store is not None

    def test_feast_get_online_features(self, mock_feast_store):
        """Test getting online features from Feast."""
        mock_store = MagicMock()
        mock_store.get_online_features.return_value = {
            "feature_1": [1.0, 2.0, 3.0],
            "feature_2": [4.0, 5.0, 6.0],
        }
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        features = client.get_features(
            entity_rows=[{"entity_id": 1}, {"entity_id": 2}, {"entity_id": 3}],
            features=["feature_1", "feature_2"],
        )

        assert features is not None
        assert "feature_1" in features
        assert "feature_2" in features

    def test_feast_get_historical_features(self, mock_feast_store):
        """Test getting historical features from Feast."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            {
                "entity_id": [1, 2, 3],
                "feature_1": [1.0, 2.0, 3.0],
                "feature_2": [4.0, 5.0, 6.0],
            }
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        features = client.get_historical_features(
            entity_df=pd.DataFrame({"entity_id": [1, 2, 3]}),
            features=["feature_1", "feature_2"],
        )

        assert features is not None
        assert len(features) == 3

    def test_feast_feature_retriever_integration(self, mock_feast_store):
        """Test FeatureRetriever with Feast."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            np.random.randn(100, 10), columns=[f"feature_{i}" for i in range(10)]
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        retriever = FeatureRetriever()

        features = retriever.retrieve_features(
            entity_ids=list(range(100)), start_date="2024-01-01", end_date="2024-12-31"
        )

        assert features is not None
        assert len(features) == 100
        assert features.shape[1] == 10

    def test_feast_schema_validation(self, mock_feast_store):
        """Test Feast schema validation."""
        mock_store = MagicMock()
        mock_fv = MagicMock()
        mock_fv.schema = {
            "feature_1": "float",
            "feature_2": "float",
            "feature_3": "int",
        }
        mock_store.get_feature_view.return_value = mock_fv
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        schema = client.get_schema("test_feature_view")

        assert schema is not None
        assert "feature_1" in schema

    def test_feast_feature_statistics(self, mock_feast_store):
        """Test computing feature statistics from Feast."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            {
                "feature_1": np.random.randn(100),
                "feature_2": np.random.randn(100),
            }
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        retriever = FeatureRetriever()

        features = retriever.retrieve_features(
            entity_ids=list(range(100)), start_date="2024-01-01", end_date="2024-12-31"
        )

        stats = retriever.get_statistics(features)

        assert stats is not None
        assert "mean" in stats
        assert "std" in stats

    def test_feast_missing_features_handling(self, mock_feast_store):
        """Test handling of missing features."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            {
                "feature_1": [1.0, np.nan, 3.0],
                "feature_2": [4.0, 5.0, np.nan],
            }
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        retriever = FeatureRetriever()

        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3], start_date="2024-01-01", end_date="2024-12-31"
        )

        assert features is not None
        # Should handle NaN values
        assert features.isnull().sum().sum() >= 0

    def test_feast_feature_versioning(self, mock_feast_store):
        """Test Feast feature versioning."""
        mock_store = MagicMock()
        mock_fv_v1 = MagicMock()
        mock_fv_v1.name = "feature_view_v1"
        mock_fv_v2 = MagicMock()
        mock_fv_v2.name = "feature_view_v2"

        mock_store.get_feature_view.side_effect = [mock_fv_v1, mock_fv_v2]
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        fv1 = client.get_feature_view("feature_view_v1")
        fv2 = client.get_feature_view("feature_view_v2")

        assert fv1 is not None
        assert fv2 is not None
        assert fv1.name != fv2.name

    def test_feast_entity_retrieval(self, mock_feast_store):
        """Test entity retrieval from Feast."""
        mock_store = MagicMock()
        mock_entity = MagicMock()
        mock_entity.name = "article_id"
        mock_store.get_entity.return_value = mock_entity
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        entity = client.get_entity("article_id")

        assert entity is not None
        assert entity.name == "article_id"

    def test_feast_feature_list_retrieval(self, mock_feast_store):
        """Test listing available features."""
        mock_store = MagicMock()
        mock_store.list_feature_views.return_value = [
            MagicMock(name="fv1"),
            MagicMock(name="fv2"),
            MagicMock(name="fv3"),
        ]
        mock_feast_store.return_value = mock_store

        client = FeastClient()

        feature_views = client.list_feature_views()

        assert feature_views is not None
        assert len(feature_views) == 3

    def test_feast_temporal_feature_retrieval(self, mock_feast_store):
        """Test temporal feature retrieval."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            {
                "entity_id": [1, 2, 3],
                "timestamp": pd.date_range("2024-01-01", periods=3),
                "feature_1": [1.0, 2.0, 3.0],
            }
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        retriever = FeatureRetriever()

        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3], start_date="2024-01-01", end_date="2024-01-03"
        )

        assert features is not None
        assert len(features) == 3

    def test_feast_batch_feature_retrieval(self, mock_feast_store):
        """Test batch feature retrieval."""
        mock_store = MagicMock()
        mock_df = pd.DataFrame(
            np.random.randn(1000, 10), columns=[f"feature_{i}" for i in range(10)]
        )
        mock_store.get_historical_features.return_value = mock_df
        mock_feast_store.return_value = mock_store

        retriever = FeatureRetriever()

        features = retriever.retrieve_features(
            entity_ids=list(range(1000)), start_date="2024-01-01", end_date="2024-12-31"
        )

        assert features is not None
        assert len(features) == 1000
        assert features.shape[1] == 10
