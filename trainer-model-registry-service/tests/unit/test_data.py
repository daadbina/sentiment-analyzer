"""
Unit tests for data retrieval and preprocessing.

Tests feature retriever, label retriever, and preprocessor.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.data.feature_retriever import FeatureRetriever
from src.data.label_retriever import LabelRetriever
from src.data.preprocessor import DataPreprocessor


class TestFeatureRetriever:
    """Test feature retrieval from Feast."""

    @pytest.fixture
    def mock_feast_client(self):
        """Create mock Feast client."""
        with patch('src.data.feature_retriever.FeastClient') as mock:
            yield mock

    def test_feature_retriever_initialization(self, mock_feast_client):
        """Test feature retriever initialization."""
        retriever = FeatureRetriever()
        assert retriever is not None

    def test_feature_retriever_retrieve_features(self, mock_feast_client):
        """Test feature retrieval."""
        mock_client = MagicMock()
        mock_client.get_features.return_value = pd.DataFrame(
            np.random.randn(100, 10),
            columns=[f'feature_{i}' for i in range(10)]
        )
        mock_feast_client.return_value = mock_client
        
        retriever = FeatureRetriever()
        
        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3],
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        assert features is not None
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0

    def test_feature_retriever_schema_validation(self, mock_feast_client):
        """Test feature schema validation."""
        mock_client = MagicMock()
        mock_client.get_features.return_value = pd.DataFrame(
            np.random.randn(100, 10),
            columns=[f'feature_{i}' for i in range(10)]
        )
        mock_feast_client.return_value = mock_client
        
        retriever = FeatureRetriever()
        
        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3],
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        # Validate schema
        assert all(isinstance(col, str) for col in features.columns)
        assert all(isinstance(val, (int, float, np.number)) for val in features.values.flatten())

    def test_feature_retriever_temporal_alignment(self, mock_feast_client):
        """Test temporal alignment of features."""
        mock_client = MagicMock()
        mock_client.get_features.return_value = pd.DataFrame(
            np.random.randn(100, 10),
            columns=[f'feature_{i}' for i in range(10)],
            index=pd.date_range('2025-01-01', periods=100)
        )
        mock_feast_client.return_value = mock_client
        
        retriever = FeatureRetriever()
        
        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3],
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        assert features is not None
        assert len(features) > 0

    def test_feature_retriever_statistics(self, mock_feast_client):
        """Test feature statistics computation."""
        mock_client = MagicMock()
        mock_client.get_features.return_value = pd.DataFrame(
            np.random.randn(100, 10),
            columns=[f'feature_{i}' for i in range(10)]
        )
        mock_feast_client.return_value = mock_client
        
        retriever = FeatureRetriever()
        
        features = retriever.retrieve_features(
            entity_ids=[1, 2, 3],
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        stats = retriever.get_statistics(features)
        
        assert stats is not None
        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats


class TestLabelRetriever:
    """Test label retrieval from PostgreSQL."""

    @pytest.fixture
    def mock_postgres_client(self):
        """Create mock PostgreSQL client."""
        with patch('src.data.label_retriever.PostgreSQLClient') as mock:
            yield mock

    def test_label_retriever_initialization(self, mock_postgres_client):
        """Test label retriever initialization."""
        retriever = LabelRetriever()
        assert retriever is not None

    @pytest.mark.asyncio
    async def test_label_retriever_retrieve_labels(self, mock_postgres_client):
        """Test label retrieval."""
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {'entity_id': 1, 'label': 1, 'timestamp': '2025-01-01'},
            {'entity_id': 2, 'label': 0, 'timestamp': '2025-01-02'},
            {'entity_id': 3, 'label': 1, 'timestamp': '2025-01-03'},
        ]
        mock_postgres_client.return_value = mock_client
        
        retriever = LabelRetriever()
        
        labels = await retriever.retrieve_labels(
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        assert labels is not None
        assert len(labels) > 0

    def test_label_retriever_temporal_filtering(self, mock_postgres_client):
        """Test temporal filtering of labels."""
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {'entity_id': 1, 'label': 1, 'timestamp': '2025-06-01'},
            {'entity_id': 2, 'label': 0, 'timestamp': '2025-06-02'},
        ]
        mock_postgres_client.return_value = mock_client
        
        retriever = LabelRetriever()
        
        labels = retriever.retrieve_labels(
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        
        assert labels is not None

    def test_label_retriever_validation(self, mock_postgres_client):
        """Test label validation."""
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {'entity_id': 1, 'label': 1},
            {'entity_id': 2, 'label': 0},
            {'entity_id': 3, 'label': 1},
        ]
        mock_postgres_client.return_value = mock_client
        
        retriever = LabelRetriever()
        
        labels = retriever.retrieve_labels()
        
        # Validate labels are binary
        assert all(label in [0, 1] for label in labels)

    def test_label_retriever_statistics(self, mock_postgres_client):
        """Test label statistics."""
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {'entity_id': i, 'label': i % 2} for i in range(100)
        ]
        mock_postgres_client.return_value = mock_client
        
        retriever = LabelRetriever()
        
        labels = retriever.retrieve_labels()
        stats = retriever.get_statistics(labels)
        
        assert stats is not None
        assert 'class_distribution' in stats
        assert 'total_samples' in stats


class TestDataPreprocessor:
    """Test data preprocessing."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data with missing values."""
        X = np.random.randn(100, 10)
        X[0, 0] = np.nan  # Add missing value
        X[1, 1] = np.nan
        return X

    def test_preprocessor_initialization(self):
        """Test preprocessor initialization."""
        preprocessor = DataPreprocessor()
        assert preprocessor is not None

    def test_preprocessor_handle_missing_values(self, sample_data):
        """Test missing value handling."""
        preprocessor = DataPreprocessor()
        
        X_clean = preprocessor.handle_missing_values(sample_data)
        
        assert X_clean is not None
        assert not np.isnan(X_clean).any()

    def test_preprocessor_feature_scaling(self, sample_data):
        """Test feature scaling."""
        preprocessor = DataPreprocessor()
        
        X_scaled = preprocessor.scale_features(sample_data)
        
        assert X_scaled is not None
        # Check that features are scaled
        assert np.abs(X_scaled.mean(axis=0)).max() < 0.1
        assert np.abs(X_scaled.std(axis=0) - 1.0).max() < 0.1

    def test_preprocessor_feature_selection(self, sample_data):
        """Test feature selection."""
        y = np.random.randint(0, 2, len(sample_data))
        preprocessor = DataPreprocessor()
        
        X_selected = preprocessor.select_features(sample_data, y, k=5)
        
        assert X_selected is not None
        assert X_selected.shape[1] <= 5

    def test_preprocessor_remove_constant_features(self):
        """Test removal of constant features."""
        X = np.random.randn(100, 10)
        X[:, 0] = 5.0  # Constant feature
        
        preprocessor = DataPreprocessor()
        
        X_clean = preprocessor.remove_constant_features(X)
        
        assert X_clean is not None
        assert X_clean.shape[1] < X.shape[1]

    def test_preprocessor_fit_transform(self, sample_data):
        """Test fit-transform pattern."""
        preprocessor = DataPreprocessor()
        
        X_train_processed = preprocessor.fit_transform(sample_data)
        
        assert X_train_processed is not None
        assert X_train_processed.shape[0] == sample_data.shape[0]

    def test_preprocessor_transform(self, sample_data):
        """Test transform after fit."""
        preprocessor = DataPreprocessor()
        
        # Fit on training data
        preprocessor.fit_transform(sample_data)
        
        # Transform test data
        X_test = np.random.randn(20, 10)
        X_test_processed = preprocessor.transform(X_test)
        
        assert X_test_processed is not None
        assert X_test_processed.shape[0] == X_test.shape[0]

    def test_preprocessor_immutability(self, sample_data):
        """Test that preprocessing doesn't modify original data."""
        X_original = sample_data.copy()
        preprocessor = DataPreprocessor()
        
        X_processed = preprocessor.fit_transform(sample_data)
        
        # Original data should not be modified
        assert np.array_equal(sample_data, X_original, equal_nan=True)

    def test_preprocessor_statistics(self, sample_data):
        """Test preprocessing statistics."""
        preprocessor = DataPreprocessor()
        
        X_processed = preprocessor.fit_transform(sample_data)
        stats = preprocessor.get_statistics()
        
        assert stats is not None
        assert 'missing_values' in stats
        assert 'constant_features' in stats

