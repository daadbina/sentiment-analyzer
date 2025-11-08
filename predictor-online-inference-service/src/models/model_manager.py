"""
Model manager for loading and managing ML models.

Provides high-level interface for model loading with version management.
Implements circuit breaker pattern and fallback model support.
"""

import logging
from typing import Any

import numpy as np
from mlflow.pyfunc import PyFuncModel

from ..clients import MLflowModelClient
from ..exceptions import InferenceError, ModelLoadError
from ..utils.ab_testing import ABTestingStrategy
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manager for ML model loading and inference.

    Handles model versioning, A/B testing, and fallback models.
    """

    def __init__(
        self,
        mlflow_client: MLflowModelClient,
        ab_testing_strategy: ABTestingStrategy | None = None,
    ):
        """
        Initialize model manager.

        Args:
            mlflow_client: MLflow client instance
            ab_testing_strategy: Optional A/B testing strategy
        """
        self.mlflow_client = mlflow_client
        self.ab_testing_strategy = ab_testing_strategy
        self._models: dict[str, PyFuncModel] = {}

        logger.info("Initialized model manager")

    async def load_model(
        self,
        model_version: str | None = None,
        trace_id: str | None = None,
    ) -> PyFuncModel:
        """
        Load model from MLflow registry.

        Args:
            model_version: Model version to load (uses default if None)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Loaded model instance

        Raises:
            ModelLoadError: If model loading fails
        """
        with trace_span(
            "load_model",
            attributes={"model_version": model_version, "trace_id": trace_id},
        ):
            try:
                # Load model from MLflow
                model = await self.mlflow_client.load_model(
                    model_version=model_version,
                    use_fallback=True,
                    trace_id=trace_id,
                )

                # Cache model
                version = model_version or self.mlflow_client.config.model_version
                self._models[version] = model

                logger.info(
                    f"Model loaded: version={version}",
                    extra={"trace_id": trace_id, "model_version": version},
                )

                return model

            except ModelLoadError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to load model: version={model_version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise ModelLoadError(
                    f"Failed to load model: {e}",
                    model_version=model_version,
                    trace_id=trace_id,
                )

    async def get_model_for_group(
        self,
        group_id: str,
        trace_id: str | None = None,
    ) -> tuple[PyFuncModel, str]:
        """
        Get model for a semantic group using A/B testing strategy.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Tuple of (model, model_version)

        Raises:
            ModelLoadError: If model loading fails
        """
        # Select model version using A/B testing
        if self.ab_testing_strategy:
            model_version = self.ab_testing_strategy.select_variant(group_id)
        else:
            model_version = self.mlflow_client.config.model_version

        # Check if model is already loaded
        if model_version in self._models:
            return self._models[model_version], model_version

        # Load model
        model = await self.load_model(model_version, trace_id)
        return model, model_version

    async def predict(
        self,
        model: PyFuncModel,
        features: dict[str, Any],
        model_version: str,
        trace_id: str | None = None,
    ) -> dict[str, float]:
        """
        Make prediction using model.

        Args:
            model: Loaded model instance
            features: Feature dictionary
            model_version: Model version identifier
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary containing:
                - prediction_probability: float (0.0-1.0)
                - prediction_confidence: float (0.0-1.0)

        Raises:
            InferenceError: If prediction fails
        """
        with trace_span(
            "model_predict",
            attributes={"model_version": model_version, "trace_id": trace_id},
        ):
            try:
                # Prepare input data
                input_data = self._prepare_input(features)

                # Make prediction
                prediction = model.predict(input_data)

                # Extract probability and confidence
                if isinstance(prediction, np.ndarray):
                    if prediction.ndim == 2:
                        # Binary classification: [[prob_class_0, prob_class_1]]
                        probability = float(prediction[0][1])
                    else:
                        # Single value
                        probability = float(prediction[0])
                else:
                    probability = float(prediction)

                # Calculate confidence (distance from 0.5)
                confidence = abs(probability - 0.5) * 2.0

                result = {
                    "prediction_probability": probability,
                    "prediction_confidence": confidence,
                }

                logger.debug(
                    f"Prediction made: model_version={model_version}, "
                    f"probability={probability:.4f}, confidence={confidence:.4f}",
                    extra={"trace_id": trace_id, "model_version": model_version},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Prediction failed: model_version={model_version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise InferenceError(
                    f"Prediction failed: {e}",
                    model_version=model_version,
                    trace_id=trace_id,
                )

    def _prepare_input(self, features: dict[str, Any]) -> np.ndarray:
        """
        Prepare input data for model prediction.

        Args:
            features: Feature dictionary

        Returns:
            NumPy array ready for model input
        """
        # Extract feature values in expected order
        feature_values = [
            float(features.get("feature_num_sources", 0)),
            float(features.get("feature_sentiment_mean", 0)),
            float(features.get("feature_credibility_mean", 0)),
            float(
                len(features.get("feature_entities", []))
                if isinstance(features.get("feature_entities"), list)
                else 0
            ),
            float(features.get("feature_time_density", 0)),
        ]

        # Convert to 2D array (single sample)
        return np.array([feature_values])

    async def get_model_metadata(
        self,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        """
        Get metadata for a model version.

        Args:
            model_version: Model version (uses default if None)

        Returns:
            Dictionary containing model metadata
        """
        return await self.mlflow_client.get_model_metadata(model_version)

    def get_loaded_models(self) -> list[str]:
        """
        Get list of loaded model versions.

        Returns:
            List of model version identifiers
        """
        return list(self._models.keys())
