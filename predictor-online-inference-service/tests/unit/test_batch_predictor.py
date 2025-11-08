"""
Unit tests for BatchPredictor.

Tests batch inference, feature integration, caching, and error handling.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from src.inference.batch_predictor import BatchPredictor
from src.exceptions import InferenceError, FeatureValidationError


@pytest.fixture
def model_manager_mock():
    """Create a mock ModelManager."""
    manager = AsyncMock()
    manager.get_model.return_value = MagicMock()
    return manager


@pytest.fixture
def feature_fetcher_mock():
    """Create a mock FeatureFetcher."""
    fetcher = AsyncMock()
    return fetcher


@pytest.fixture
def feature_validator_mock():
    """Create a mock FeatureValidator."""
    validator = AsyncMock()
    validator.validate_features.return_value = True
    return validator


@pytest.fixture
def prediction_cache_mock():
    """Create a mock PredictionCache."""
    cache = AsyncMock()
    return cache


@pytest.fixture
def prediction_logger_mock():
    """Create a mock PredictionLogger."""
    logger = AsyncMock()
    return logger


@pytest.fixture
def batch_predictor(
    model_manager_mock,
    feature_fetcher_mock,
    feature_validator_mock,
    prediction_cache_mock,
    prediction_logger_mock,
):
    """Create a BatchPredictor instance."""
    return BatchPredictor(
        model_manager=model_manager_mock,
        feature_fetcher=feature_fetcher_mock,
        feature_validator=feature_validator_mock,
        prediction_cache=prediction_cache_mock,
        prediction_logger=prediction_logger_mock,
        batch_size=100,
    )


class TestBatchPredictorInitialization:
    """Test BatchPredictor initialization."""

    def test_init(self, batch_predictor):
        """Test predictor initialization."""
        assert batch_predictor.batch_size == 100
        assert batch_predictor.model_manager is not None
        assert batch_predictor.feature_fetcher is not None


class TestPredictBatch:
    """Test predict_batch method."""

    @pytest.mark.asyncio
    async def test_predict_batch_success(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        model_manager_mock,
    ):
        """Test successful batch prediction."""
        group_ids = ["group1", "group2", "group3"]
        domain = "btc"
        
        # Mock cache returns no cached predictions
        prediction_cache_mock.get_batch.return_value = {}
        
        # Mock feature fetching
        feature_fetcher_mock.fetch_batch_online_features.return_value = [
            {"feature1": 0.5, "feature2": 0.8},
            {"feature1": 0.6, "feature2": 0.7},
            {"feature1": 0.4, "feature2": 0.9},
        ]
        
        # Mock model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75, 0.85, 0.65]
        model_manager_mock.get_model.return_value = mock_model
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        assert len(result) == 3
        assert all("group_id" in pred for pred in result)

    @pytest.mark.asyncio
    async def test_predict_batch_with_cache_hits(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        model_manager_mock,
    ):
        """Test batch prediction with some cached predictions."""
        group_ids = ["group1", "group2", "group3"]
        domain = "btc"
        
        # Mock cache returns one cached prediction
        prediction_cache_mock.get_batch.return_value = {
            "group1": {
                "group_id": "group1",
                "prediction": 0.75,
                "confidence": 0.9,
                "cached": True,
            }
        }
        
        # Mock feature fetching for remaining groups
        feature_fetcher_mock.fetch_batch_online_features.return_value = [
            {"feature1": 0.6, "feature2": 0.7},
            {"feature1": 0.4, "feature2": 0.9},
        ]
        
        # Mock model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.85, 0.65]
        model_manager_mock.get_model.return_value = mock_model
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        # Should have 3 predictions (1 cached + 2 new)
        assert len(result) == 3
        
        # Verify only 2 groups were fetched for features
        feature_fetcher_mock.fetch_batch_online_features.assert_called_once()
        call_args = feature_fetcher_mock.fetch_batch_online_features.call_args[0][0]
        assert len(call_args) == 2
        assert "group1" not in call_args

    @pytest.mark.asyncio
    async def test_predict_batch_all_cached(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
    ):
        """Test batch prediction with all predictions cached."""
        group_ids = ["group1", "group2"]
        domain = "btc"
        
        # Mock cache returns all predictions
        prediction_cache_mock.get_batch.return_value = {
            "group1": {"group_id": "group1", "prediction": 0.75},
            "group2": {"group_id": "group2", "prediction": 0.85},
        }
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        assert len(result) == 2
        
        # Verify no feature fetching occurred
        feature_fetcher_mock.fetch_batch_online_features.assert_not_called()

    @pytest.mark.asyncio
    async def test_predict_batch_large_batch(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        model_manager_mock,
    ):
        """Test batch prediction with batch size exceeding limit."""
        # Create 250 group IDs (exceeds batch_size of 100)
        group_ids = [f"group{i}" for i in range(250)]
        domain = "btc"
        
        # Mock cache returns no cached predictions
        prediction_cache_mock.get_batch.return_value = {}
        
        # Mock feature fetching
        feature_fetcher_mock.fetch_batch_online_features.return_value = [
            {"feature1": 0.5} for _ in range(100)
        ]
        
        # Mock model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75] * 100
        model_manager_mock.get_model.return_value = mock_model
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        # Should process all groups in chunks
        assert len(result) <= 250
        
        # Verify feature fetching was called multiple times (3 chunks: 100, 100, 50)
        assert feature_fetcher_mock.fetch_batch_online_features.call_count >= 3

    @pytest.mark.asyncio
    async def test_predict_batch_empty_group_ids(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
    ):
        """Test batch prediction with empty group IDs."""
        group_ids = []
        domain = "btc"
        
        prediction_cache_mock.get_batch.return_value = {}
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        assert len(result) == 0
        feature_fetcher_mock.fetch_batch_online_features.assert_not_called()

    @pytest.mark.asyncio
    async def test_predict_batch_feature_fetch_failure(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
    ):
        """Test batch prediction with feature fetch failure."""
        group_ids = ["group1", "group2"]
        domain = "btc"
        
        prediction_cache_mock.get_batch.return_value = {}
        feature_fetcher_mock.fetch_batch_online_features.side_effect = Exception("Fetch failed")
        
        with pytest.raises(InferenceError) as exc_info:
            await batch_predictor.predict_batch(
                group_ids=group_ids,
                domain=domain,
            )
        
        assert "Batch prediction failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_batch_partial_failure(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        model_manager_mock,
        feature_validator_mock,
    ):
        """Test batch prediction with partial failures."""
        group_ids = ["group1", "group2", "group3"]
        domain = "btc"
        
        prediction_cache_mock.get_batch.return_value = {}
        
        # Mock feature fetching
        feature_fetcher_mock.fetch_batch_online_features.return_value = [
            {"feature1": 0.5},
            {"feature1": 0.6},
            {"feature1": 0.4},
        ]
        
        # Mock validation to fail for second group
        async def validate_side_effect(features):
            if features.get("feature1") == 0.6:
                raise FeatureValidationError("Validation failed")
            return True
        
        feature_validator_mock.validate_features.side_effect = validate_side_effect
        
        # Mock model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75, 0.65]
        model_manager_mock.get_model.return_value = mock_model
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
        )
        
        # Should have 2 successful predictions (group2 failed validation)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_predict_batch_with_trace_id(
        self,
        batch_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        model_manager_mock,
    ):
        """Test batch prediction with trace ID."""
        group_ids = ["group1"]
        domain = "btc"
        trace_id = "trace-123"
        
        prediction_cache_mock.get_batch.return_value = {}
        feature_fetcher_mock.fetch_batch_online_features.return_value = [
            {"feature1": 0.5}
        ]
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75]
        model_manager_mock.get_model.return_value = mock_model
        
        result = await batch_predictor.predict_batch(
            group_ids=group_ids,
            domain=domain,
            trace_id=trace_id,
        )
        
        assert len(result) == 1
        
        # Verify trace_id was passed to feature fetcher
        feature_fetcher_mock.fetch_batch_online_features.assert_called_once()
        call_kwargs = feature_fetcher_mock.fetch_batch_online_features.call_args[1]
        assert call_kwargs.get("trace_id") == trace_id or \
               feature_fetcher_mock.fetch_batch_online_features.call_args[0][1] == trace_id

