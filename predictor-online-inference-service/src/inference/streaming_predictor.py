"""
Streaming predictor for real-time predictions from Kafka.

Consumes computed features from Kafka (features_computed topic) and produces predictions.
This ensures features are ready before predictions are made, avoiding race conditions.
Implements low-latency streaming inference with <200ms p95 latency.
"""

import logging
import time
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
from ..utils.trace import TracingContext, trace_span, generate_trace_id

logger = logging.getLogger(__name__)


class StreamingPredictor:
    """
    Predictor for streaming inference from Kafka.

    Consumes computed features (features_computed topic) and produces predictions with low latency.
    Features are already computed by feature-engineering-service, avoiding race conditions.
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

        # Subscribe to features_computed topic (after feature engineering completes)
        await self.kafka_consumer.subscribe(["features_computed"])

        # Start consuming messages
        await self.kafka_consumer.consume_messages(self._handle_message)

    async def stop(self) -> None:
        """
        Stop streaming prediction consumer.
        """
        logger.info("Stopping streaming predictor")

        self._running = False

        # Close Kafka consumer
        await self.kafka_consumer.disconnect()

    async def _handle_message(self, message: dict[str, Any], topic: str) -> None:
        """
        Handle incoming Kafka message from features_computed topic.

        Args:
            message: Kafka message containing computed features
            topic: Kafka topic name
        """
        # Use trace_id from message or generate new one
        trace_id = message.get("trace_id") or generate_trace_id()

        with trace_span(
            "handle_streaming_message",
            attributes={"trace_id": trace_id},
        ):
            start_time = time.time()  # Use time.time() for consistent float timestamps

            try:
                # Extract group data from features_computed message
                group_id = message.get("group_id")
                features = message.get("features", {})
                validation_status = message.get("validation_status", "UNKNOWN")

                if not group_id:
                    logger.warning(
                        "Invalid message: missing group_id",
                        extra={"trace_id": trace_id},
                    )
                    return

                # Skip if features are invalid
                if validation_status == "INVALID":
                    logger.warning(
                        f"Skipping prediction for group {group_id}: features validation failed",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )
                    return

                # Determine domains from features
                # Features come from feature-engineering WITHOUT prefixes
                # Check if this is a BTC prediction (has btc_ prefixed features)
                # and/or conflict prediction (has semantic features)
                has_btc_features = any(k.startswith("btc_") for k in features.keys())
                has_semantic_features = any(k in ["sentiment_mean", "entity_count", "source_credibility_avg"] for k in features.keys())

                # Determine which domains to predict for
                domains_to_predict = []
                if has_btc_features:
                    domains_to_predict.append("btc")
                if has_semantic_features:
                    domains_to_predict.append("conflict")

                if not domains_to_predict:
                    logger.warning(
                        f"No recognizable features found, skipping prediction",
                        extra={"trace_id": trace_id, "group_id": group_id, "feature_keys": list(features.keys())[:10]},
                    )
                    return

                logger.info(
                    f"Processing features_computed message: group_id={group_id}, domains={domains_to_predict}, feature_count={len(features)}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )

                # Make predictions for each domain
                for domain in domains_to_predict:
                    logger.info(
                        f"Making {domain} prediction for group_id={group_id}",
                        extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                    )

                    # Check cache first
                    cached_prediction = await self.prediction_cache.get_cached_prediction(
                        group_id,
                        trace_id,
                    )

                    if cached_prediction and cached_prediction.get("domain") == domain:
                        logger.debug(
                            f"Using cached {domain} prediction: group_id={group_id}",
                            extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                        )
                        MetricsCollector.record_cache_hit()

                        # Still log to Kafka for downstream consumers
                        await self.prediction_logger._publish_to_kafka(
                            cached_prediction,
                            trace_id,
                        )
                        continue

                    MetricsCollector.record_cache_miss()

                    # Prepare features for this domain
                    # Features are already in the message and validated by feature-engineering-service
                    # But they come WITHOUT prefixes - we need to add prefixes for the model
                    logger.debug(
                        f"Using pre-computed features from feature-engineering-service (validation_status={validation_status})",
                        extra={"trace_id": trace_id, "group_id": group_id, "domain": domain},
                    )

                    # Add prefixes to features based on domain
                    # Models expect features WITH prefixes:
                    # - BTC model: btc_ prefix + reads from btc_features.parquet
                    # - Conflict model: semantic_group_features: prefix (needs to be added)
                    domain_features = features.copy()

                    if domain == "btc":
                        # For BTC predictions, read features from btc_features.parquet
                        # The parquet file has the correct feature names that the model was trained on
                        logger.info(
                            f"BTC prediction detected - will read features from btc_features.parquet",
                            extra={"trace_id": trace_id, "group_id": group_id},
                        )
                        # Features will be read from parquet in the model_manager.predict_btc() method
                        # Keep the features dict as-is for now
                    elif domain == "conflict":
                        # Add semantic_group_features: prefix to non-btc features
                        prefixed_features = {}
                        for key, value in domain_features.items():
                            if key.startswith("btc_") or key in ["group_id", "timestamp", "countries", "btc_timestamp"]:
                                # Keep BTC features and metadata as-is
                                prefixed_features[key] = value
                            elif not key.startswith("semantic_group_features:"):
                                # Add prefix to semantic features
                                prefixed_features[f"semantic_group_features:{key}"] = value
                            else:
                                # Already has prefix
                                prefixed_features[key] = value
                        domain_features = prefixed_features
                        logger.debug(
                            f"Added semantic_group_features: prefix to {len(domain_features)} features",
                            extra={"trace_id": trace_id, "group_id": group_id},
                        )

                    # Get model for group with specified domain
                    model, model_version = await self.model_manager.get_model_for_group(
                        group_id,
                        trace_id,
                        domain=domain,
                    )

                    # Make prediction
                    prediction_result = await self.model_manager.predict(
                        model,
                        domain_features,
                        model_version,
                        trace_id,
                        domain=domain,
                    )

                    # Calculate latency
                    domain_end_time = time.time()
                    domain_latency_ms = (domain_end_time - start_time) * 1000

                    # Build prediction dictionary with all required fields
                    # Note: Kafka schema requires prediction_probability and features fields
                    prediction = {
                        "group_id": group_id,
                        "domain": domain,
                        "model_version": model_version,
                        "predicted_at": datetime.utcnow().isoformat(),
                        "trace_id": trace_id,
                        "prediction_confidence": prediction_result.get("prediction_confidence", 0.0),
                        "features": {},  # Required by Kafka schema
                    }

                    # Add domain-specific fields
                    if domain == "btc":
                        # BTC predictions: use confidence (R² score) as prediction_probability since it's regression, not classification
                        prediction.update({
                            "prediction_probability": prediction_result.get("prediction_confidence", 0.5),
                            "prediction_value": prediction_result.get("prediction_value"),
                            "prediction_direction": prediction_result.get("prediction_direction"),
                            "prediction_magnitude": prediction_result.get("prediction_magnitude"),
                            "prediction_strength": prediction_result.get("prediction_strength"),
                            "prediction_description": prediction_result.get("prediction_description"),
                        })
                    else:
                        # Conflict predictions
                        prediction.update({
                            "prediction_probability": prediction_result.get("prediction_probability", 0.5),
                        })

                    # Record metrics
                    MetricsCollector.record_prediction(
                        mode="streaming",
                        model_version=model_version,
                        domain=domain,
                        latency_ms=domain_latency_ms,
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
                        f"{domain.upper()} prediction completed: group_id={group_id}, "
                        f"latency_ms={domain_latency_ms:.2f}",
                        extra={
                            "trace_id": trace_id,
                            "group_id": group_id,
                            "domain": domain,
                            "latency_ms": domain_latency_ms,
                        },
                    )

                # Overall completion log
                end_time = time.time()
                total_latency_ms = (end_time - start_time) * 1000
                logger.info(
                    f"Streaming prediction completed: group_id={group_id}, "
                    f"domains={domains_to_predict}, total_latency_ms={total_latency_ms:.2f}",
                    extra={
                        "trace_id": trace_id,
                        "group_id": group_id,
                        "latency_ms": total_latency_ms,
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
