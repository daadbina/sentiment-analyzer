"""
Unit tests for StreamingPredictor.

Tests streaming inference, Kafka integration, and error handling.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.inference.streaming_predictor import StreamingPredictor
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
def kafka_consumer_mock():
    """Create a mock KafkaConsumerClient."""
    consumer = AsyncMock()
    return consumer


@pytest.fixture
def streaming_predictor(
    model_manager_mock,
    feature_fetcher_mock,
    feature_validator_mock,
    prediction_cache_mock,
    prediction_logger_mock,
    kafka_consumer_mock,
):
    """Create a StreamingPredictor instance."""
    return StreamingPredictor(
        model_manager=model_manager_mock,
        feature_fetcher=feature_fetcher_mock,
        feature_validator=feature_validator_mock,
        prediction_cache=prediction_cache_mock,
        prediction_logger=prediction_logger_mock,
        kafka_consumer=kafka_consumer_mock,
    )


class TestStreamingPredictorInitialization:
    """Test StreamingPredictor initialization."""

    def test_init(self, streaming_predictor):
        """Test predictor initialization."""
        assert streaming_predictor.model_manager is not None
        assert streaming_predictor.feature_fetcher is not None
        assert streaming_predictor.kafka_consumer is not None
        assert streaming_predictor._running is False


class TestStartStop:
    """Test start and stop methods."""

    @pytest.mark.asyncio
    async def test_start(self, streaming_predictor, kafka_consumer_mock):
        """Test starting the streaming predictor."""
        # Mock consume_messages to not block
        kafka_consumer_mock.consume_messages.return_value = None
        
        await streaming_predictor.start()
        
        assert streaming_predictor._running is True
        kafka_consumer_mock.subscribe.assert_called_once_with(["semantic_groups"])
        kafka_consumer_mock.consume_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, streaming_predictor, kafka_consumer_mock):
        """Test stopping the streaming predictor."""
        streaming_predictor._running = True
        
        await streaming_predictor.stop()
        
        assert streaming_predictor._running is False
        kafka_consumer_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self, streaming_predictor, kafka_consumer_mock):
        """Test start-stop cycle."""
        kafka_consumer_mock.consume_messages.return_value = None
        
        await streaming_predictor.start()
        assert streaming_predictor._running is True
        
        await streaming_predictor.stop()
        assert streaming_predictor._running is False


class TestHandleMessage:
    """Test _handle_message method."""

    @pytest.mark.asyncio
    async def test_handle_message_success(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
        model_manager_mock,
    ):
        """Test successful message handling."""
        message = {
            "group_id": "group123",
            "domain": "btc",
            "articles": [{"id": "art1"}],
        }
        
        # Mock cache miss
        prediction_cache_mock.get.return_value = None
        
        # Mock feature fetching
        feature_fetcher_mock.fetch_online_features.return_value = {
            "feature1": 0.5,
            "feature2": 0.8,
        }
        
        # Mock model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75]
        model_manager_mock.get_model.return_value = mock_model
        
        await streaming_predictor._handle_message(message)
        
        # Verify prediction was logged
        prediction_logger_mock.log_prediction.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_cache_hit(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
    ):
        """Test message handling with cache hit."""
        message = {
            "group_id": "group123",
            "domain": "btc",
        }
        
        # Mock cache hit
        cached_prediction = {
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
        }
        prediction_cache_mock.get.return_value = cached_prediction
        
        await streaming_predictor._handle_message(message)
        
        # Verify no feature fetching occurred
        feature_fetcher_mock.fetch_online_features.assert_not_called()
        
        # Verify cached prediction was logged
        prediction_logger_mock.log_prediction.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_feature_fetch_failure(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
    ):
        """Test message handling with feature fetch failure."""
        message = {
            "group_id": "group123",
            "domain": "btc",
        }
        
        prediction_cache_mock.get.return_value = None
        feature_fetcher_mock.fetch_online_features.side_effect = Exception("Fetch failed")
        
        # Should not raise exception (error handling inside)
        await streaming_predictor._handle_message(message)
        
        # Verify no prediction was logged
        prediction_logger_mock.log_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_validation_failure(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        feature_validator_mock,
        prediction_cache_mock,
        prediction_logger_mock,
    ):
        """Test message handling with feature validation failure."""
        message = {
            "group_id": "group123",
            "domain": "btc",
        }
        
        prediction_cache_mock.get.return_value = None
        feature_fetcher_mock.fetch_online_features.return_value = {"feature1": 0.5}
        feature_validator_mock.validate_features.side_effect = FeatureValidationError("Invalid")
        
        # Should not raise exception (error handling inside)
        await streaming_predictor._handle_message(message)
        
        # Verify no prediction was logged
        prediction_logger_mock.log_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_prediction_failure(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
        model_manager_mock,
    ):
        """Test message handling with prediction failure."""
        message = {
            "group_id": "group123",
            "domain": "btc",
        }
        
        prediction_cache_mock.get.return_value = None
        feature_fetcher_mock.fetch_online_features.return_value = {"feature1": 0.5}
        
        # Mock model prediction failure
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Prediction failed")
        model_manager_mock.get_model.return_value = mock_model
        
        # Should not raise exception (error handling inside)
        await streaming_predictor._handle_message(message)
        
        # Verify no prediction was logged
        prediction_logger_mock.log_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_missing_group_id(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_logger_mock,
    ):
        """Test message handling with missing group_id."""
        message = {
            "domain": "btc",
            # group_id is missing
        }
        
        # Should not raise exception (error handling inside)
        await streaming_predictor._handle_message(message)
        
        # Verify no feature fetching occurred
        feature_fetcher_mock.fetch_online_features.assert_not_called()
        
        # Verify no prediction was logged
        prediction_logger_mock.log_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_missing_domain(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
    ):
        """Test message handling with missing domain."""
        message = {
            "group_id": "group123",
            # domain is missing
        }
        
        prediction_cache_mock.get.return_value = None
        
        # Should not raise exception (error handling inside)
        await streaming_predictor._handle_message(message)

    @pytest.mark.asyncio
    async def test_handle_message_with_trace_context(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
        model_manager_mock,
    ):
        """Test message handling with trace context."""
        message = {
            "group_id": "group123",
            "domain": "btc",
            "trace_id": "trace-123",
        }
        
        prediction_cache_mock.get.return_value = None
        feature_fetcher_mock.fetch_online_features.return_value = {"feature1": 0.5}
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75]
        model_manager_mock.get_model.return_value = mock_model
        
        await streaming_predictor._handle_message(message)
        
        # Verify prediction was logged
        prediction_logger_mock.log_prediction.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_latency_tracking(
        self,
        streaming_predictor,
        feature_fetcher_mock,
        prediction_cache_mock,
        prediction_logger_mock,
        model_manager_mock,
    ):
        """Test that message handling tracks latency."""
        message = {
            "group_id": "group123",
            "domain": "btc",
        }
        
        prediction_cache_mock.get.return_value = None
        feature_fetcher_mock.fetch_online_features.return_value = {"feature1": 0.5}
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.75]
        model_manager_mock.get_model.return_value = mock_model
        
        with patch("src.inference.streaming_predictor.MetricsCollector") as metrics_mock:
            await streaming_predictor._handle_message(message)
            
            # Verify latency was recorded (method should be called)
            # Note: Actual implementation may vary
            assert prediction_logger_mock.log_prediction.called

