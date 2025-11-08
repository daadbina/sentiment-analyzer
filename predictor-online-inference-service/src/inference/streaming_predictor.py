"""
Streaming predictor for real-time predictions from Kafka.

Consumes semantic groups from Kafka and produces predictions.
Implements low-latency streaming inference with <200ms p95 latency.
"""

import logging
from datetime import datetime
from typing import Any

from ..clients import KafkaConsumerClient
from ..exceptions import FeatureFetchError, FeatureValidationError, InferenceError
from ..features.feature_fetcher import FeatureFetcher
from ..features.feature_validator import FeatureValidator
from ..metrics import MetricsCollector
from ..models.model_manager import ModelManager
from ..storage.prediction_cache import PredictionCache
from ..storage.prediction_logger import PredictionLogger
from ..utils.trace import TracingContext, trace_span

logger = logging.getLogger(__name__)


class StreamingPredictor:
    """
    Predictor for streaming inference from Kafka.

    Consumes semantic groups and produces predictions with low latency.
    """

    def __init__(
        self,
        model_manager: ModelManager,
        feature_fetcher: FeatureFetcher,
        feature_validator: FeatureValidator,
        prediction_cache: PredictionCache,
        prediction_logger: PredictionLogger,
        kafka_consumer: KafkaConsumerClient,
    ):
        """
        Initialize streaming predictor.

        Args:
            model_manager: Model manager instance
            feature_fetcher: Feature fetcher instance
            feature_validator: Feature validator instance
            prediction_cache: Prediction cache instance
            prediction_logger: Prediction logger instance
            kafka_consumer: Kafka consumer instance
        """
        self.model_manager = model_manager
        self.feature_fetcher = feature_fetcher
        self.feature_validator = feature_validator
        self.prediction_cache = prediction_cache
        self.prediction_logger = prediction_logger
        self.kafka_consumer = kafka_consumer
        self._running = False

        logger.info("Initialized streaming predictor")

    async def start(self) -> None:
        """
        Start streaming prediction consumer.

        Subscribes to Kafka topic and processes messages.
        """
        logger.info("Starting streaming predictor")

        self._running = True

        # Subscribe to semantic_groups topic
        await self.kafka_consumer.subscribe(["semantic_groups"])

        # Start consuming messages
        await self.kafka_consumer.consume_messages(self._handle_message)

    async def stop(self) -> None:
        """
        Stop streaming prediction consumer.
        """
        logger.info("Stopping streaming predictor")

        self._running = False

        # Close Kafka consumer
        await self.kafka_consumer.close()

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """
        Handle incoming Kafka message.

        Args:
            message: Kafka message containing semantic group data
        """
        # Generate trace ID for this message
        trace_id = TracingContext.generate_trace_id()

        with trace_span(
            "handle_streaming_message",
            attributes={"trace_id": trace_id},
        ):
            start_time = datetime.now()

            try:
                # Extract group data
                group_id = message.get("group_id")
                domain = message.get("domain")

                if not group_id or not domain:
                    logger.warning(
                        "Invalid message: missing group_id or domain",
                        extra={"trace_id": trace_id},
                    )
                    return

                logger.debug(
                    f"Processing streaming message: group_id={group_id}, domain={domain}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Check cache first
                cached_prediction = await self.prediction_cache.get_cached_prediction(
                    group_id,
                    trace_id,
                )

                if cached_prediction:
                    logger.debug(
                        f"Using cached prediction: group_id={group_id}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )
                    MetricsCollector.record_cache_hit()

                    # Still log to Kafka for downstream consumers
                    await self.prediction_logger._publish_to_kafka(
                        cached_prediction,
                        trace_id,
                    )
                    return

                MetricsCollector.record_cache_miss()

                # Fetch features
                features = await self.feature_fetcher.fetch_online_features(
                    group_id,
                    trace_id,
                )

                # Validate features
                await self.feature_validator.validate_features(
                    features,
                    group_id,
                    trace_id,
                )

                # Get model for group (A/B testing)
                model, model_version = await self.model_manager.get_model_for_group(
                    group_id,
                    trace_id,
                )

                # Make prediction
                prediction_result = await self.model_manager.predict(
                    model,
                    features,
                    model_version,
                    trace_id,
                )

                # Calculate latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Build prediction dictionary
                prediction = {
                    "group_id": group_id,
                    "domain": domain,
                    "prediction_probability": prediction_result["prediction_probability"],
                    "prediction_confidence": prediction_result["prediction_confidence"],
                    "model_version": model_version,
                    "predicted_at": datetime.utcnow().isoformat(),
                    "trace_id": trace_id,
                    "features": features,
                }

                # Record metrics
                MetricsCollector.record_prediction(
                    mode="streaming",
                    model_version=model_version,
                    domain=domain,
                    latency_ms=latency_ms,
                    confidence=prediction_result["prediction_confidence"],
                )

                # Cache prediction
                await self.prediction_cache.cache_prediction(
                    group_id,
                    prediction,
                    trace_id,
                )

                # Log prediction to database and Kafka
                await self.prediction_logger.log_prediction(
                    prediction,
                    trace_id,
                )

                logger.info(
                    f"Streaming prediction completed: group_id={group_id}, "
                    f"latency_ms={latency_ms:.2f}",
                    extra={
                        "trace_id": trace_id,
                        "group_id": group_id,
                        "latency_ms": latency_ms,
                    },
                )

            except (FeatureFetchError, FeatureValidationError, InferenceError) as e:
                logger.error(
                    f"Streaming prediction failed: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                # Continue processing other messages
            except Exception as e:
                logger.error(
                    f"Unexpected error in streaming prediction: error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                # Continue processing other messages

    def is_running(self) -> bool:
        """
        Check if streaming predictor is running.

        Returns:
            True if running, False otherwise
        """
        return self._running
