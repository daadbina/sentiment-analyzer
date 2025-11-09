"""
Batch predictor for making predictions on multiple semantic groups.

Provides efficient batch prediction with feature fetching and caching.
Implements throughput optimization for batch workloads.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from ..exceptions import FeatureValidationError, InferenceError
from ..features.feature_fetcher import FeatureFetcher
from ..features.feature_validator import FeatureValidator
from ..metrics import MetricsCollector
from ..models.model_manager import ModelManager
from ..storage.prediction_cache import PredictionCache
from ..storage.prediction_logger import PredictionLogger
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class BatchPredictor:
    """
    Predictor for batch inference on multiple semantic groups.

    Optimizes throughput by batching feature fetches and predictions.
    """

    def __init__(
        self,
        model_manager: ModelManager,
        feature_fetcher: FeatureFetcher,
        feature_validator: FeatureValidator,
        prediction_cache: PredictionCache,
        prediction_logger: PredictionLogger,
        batch_size: int = 100,
    ):
        """
        Initialize batch predictor.

        Args:
            model_manager: Model manager instance
            feature_fetcher: Feature fetcher instance
            feature_validator: Feature validator instance
            prediction_cache: Prediction cache instance
            prediction_logger: Prediction logger instance
            batch_size: Maximum batch size for processing
        """
        self.model_manager = model_manager
        self.feature_fetcher = feature_fetcher
        self.feature_validator = feature_validator
        self.prediction_cache = prediction_cache
        self.prediction_logger = prediction_logger
        self.batch_size = batch_size

        logger.info(f"Initialized batch predictor: batch_size={batch_size}")

    async def predict_batch(
        self,
        group_ids: list[str],
        domain: str,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Make predictions for a batch of semantic groups.

        Args:
            group_ids: List of semantic group IDs
            domain: Domain of predictions (btc/conflict/geopolitical)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of prediction dictionaries

        Raises:
            InferenceError: If batch prediction fails
        """
        with trace_span(
            "predict_batch",
            attributes={
                "batch_size": len(group_ids),
                "domain": domain,
                "trace_id": trace_id,
            },
        ):
            start_time = datetime.now()

            try:
                logger.info(
                    f"Starting batch prediction: batch_size={len(group_ids)}, domain={domain}",
                    extra={"trace_id": trace_id},
                )

                # Split into smaller batches if needed
                predictions = []
                for i in range(0, len(group_ids), self.batch_size):
                    batch = group_ids[i : i + self.batch_size]
                    batch_predictions = await self._predict_batch_chunk(
                        batch,
                        domain,
                        trace_id,
                    )
                    predictions.extend(batch_predictions)

                # Calculate total latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                logger.info(
                    f"Batch prediction completed: batch_size={len(group_ids)}, "
                    f"latency_ms={latency_ms:.2f}",
                    extra={"trace_id": trace_id, "latency_ms": latency_ms},
                )

                return predictions

            except Exception as e:
                logger.error(
                    f"Batch prediction failed: batch_size={len(group_ids)}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise InferenceError(
                    f"Batch prediction failed: {e}",
                    trace_id=trace_id,
                )

    async def _predict_batch_chunk(
        self,
        group_ids: list[str],
        domain: str,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Make predictions for a chunk of semantic groups.

        Args:
            group_ids: List of semantic group IDs (≤ batch_size)
            domain: Domain of predictions
            trace_id: Optional trace ID for distributed tracing

        Returns:
            List of prediction dictionaries
        """
        # Check cache for existing predictions
        cached_predictions = await self._get_cached_predictions(group_ids, domain, trace_id)

        # Identify groups needing prediction
        groups_to_predict = [gid for gid in group_ids if gid not in cached_predictions]

        if not groups_to_predict:
            logger.debug(
                f"All predictions cached: batch_size={len(group_ids)}",
                extra={"trace_id": trace_id},
            )
            return list(cached_predictions.values())

        logger.debug(
            f"Predicting batch chunk: total={len(group_ids)}, "
            f"cached={len(cached_predictions)}, to_predict={len(groups_to_predict)}",
            extra={"trace_id": trace_id},
        )

        # Fetch features for groups needing prediction
        features_list = await self.feature_fetcher.fetch_batch_online_features(
            groups_to_predict,
            trace_id,
        )

        # Make predictions
        new_predictions = []
        for group_id, features in zip(groups_to_predict, features_list, strict=False):
            try:
                prediction = await self._predict_single(
                    group_id,
                    domain,
                    features,
                    trace_id,
                )
                new_predictions.append(prediction)
            except (FeatureValidationError, InferenceError) as e:
                logger.warning(
                    f"Failed to predict for group: group_id={group_id}, error={e}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                # Continue with other groups
                continue

        # Combine cached and new predictions
        return list(cached_predictions.values()) + new_predictions

    async def _predict_single(
        self,
        group_id: str,
        domain: str,
        features: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Make prediction for a single semantic group.

        Args:
            group_id: Semantic group ID
            domain: Domain of prediction
            features: Feature dictionary
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Prediction dictionary
        """
        start_time = datetime.now()

        # Validate features
        await self.feature_validator.validate_features(features, group_id, trace_id)

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
            mode="batch",
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

        # Log prediction to database
        await self.prediction_logger.log_prediction(
            prediction,
            trace_id,
        )

        return prediction

    async def _get_cached_predictions(
        self,
        group_ids: list[str],
        domain: str,
        trace_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Get cached predictions for group IDs and domain.

        Args:
            group_ids: List of semantic group IDs
            domain: Domain of predictions (btc/conflict/geopolitical)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary mapping group_id to cached prediction
        """
        cached: dict[str, dict[str, Any]] = {}

        # Fetch cached predictions concurrently
        tasks = [self.prediction_cache.get_cached_prediction(gid, domain, trace_id) for gid in group_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for group_id, result in zip(group_ids, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    f"Failed to get cached prediction: group_id={group_id}, error={result}",
                    extra={"trace_id": trace_id},
                )
                continue

            if result is not None:
                cached[group_id] = result  # type: ignore[assignment]
                MetricsCollector.record_cache_hit()
            else:
                MetricsCollector.record_cache_miss()

        return cached
