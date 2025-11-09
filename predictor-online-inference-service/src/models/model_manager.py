"""
Model manager for loading and managing ML models.

Provides high-level interface for model loading with version management.
Implements circuit breaker pattern and fallback model support.
"""

import logging
import pickle
from typing import Any

import numpy as np
import pandas as pd
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
        self._preprocessors: dict[str, Any] = {}  # Cache preprocessors by model version

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
                # Log raw features before preprocessing
                logger.info(
                    f"Raw features before preprocessing: count={len(features)}",
                    extra={
                        "trace_id": trace_id,
                        "model_version": model_version,
                        "feature_names": list(features.keys()),
                        "feature_sample": {k: features[k] for k in list(features.keys())[:5]},
                    },
                )

                # Load preprocessor for this model version
                preprocessor = await self._load_preprocessor(model_version, trace_id)

                # Prepare input data with preprocessing
                input_data = self._prepare_input(features, preprocessor)

                # Log prepared input shape
                logger.info(
                    f"Prepared input for model: shape={input_data.shape}",
                    extra={
                        "trace_id": trace_id,
                        "model_version": model_version,
                        "input_shape": input_data.shape,
                        "preprocessor_used": preprocessor is not None,
                    },
                )

                # Make prediction
                prediction = model.predict(input_data)

                # Extract probability and confidence
                if isinstance(prediction, np.ndarray):
                    if prediction.ndim == 2:  # type: ignore[attr-defined]
                        # Binary classification: [[prob_class_0, prob_class_1]]
                        probability = float(prediction[0][1])  # type: ignore[index]
                    else:
                        # Single value
                        probability = float(prediction[0])  # type: ignore[index]
                else:
                    # Handle PyFuncOutput or other types - convert to numpy first
                    pred_array = np.asarray(prediction)
                    if pred_array.ndim == 2:
                        probability = float(pred_array[0][1])
                    else:
                        probability = float(pred_array[0]) if pred_array.size > 0 else float(prediction)  # type: ignore[arg-type]

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

    async def _load_preprocessor(
        self,
        model_version: str,
        trace_id: str | None = None,
    ) -> Any:
        """
        Load preprocessor from MLflow for a specific model version.

        Args:
            model_version: Model version identifier
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Loaded preprocessor instance

        Raises:
            ModelLoadError: If preprocessor loading fails
        """
        # Check cache first
        if model_version in self._preprocessors:
            logger.debug(f"Using cached preprocessor for version {model_version}")
            return self._preprocessors[model_version]

        try:
            logger.info(f"Loading preprocessor for model version {model_version}")

            # Download preprocessor artifact from MLflow
            preprocessor_path = self.mlflow_client.download_artifact(
                model_version=model_version,
                artifact_path="preprocessor",
                trace_id=trace_id,
            )

            # Load preprocessor
            with open(preprocessor_path, "rb") as f:
                preprocessor = pickle.load(f)

            # Cache it
            self._preprocessors[model_version] = preprocessor

            logger.info(f"Preprocessor loaded successfully for version {model_version}")
            return preprocessor

        except Exception as e:
            logger.warning(
                f"Failed to load preprocessor for version {model_version}: {e}. "
                "Will use raw features without preprocessing."
            )
            # Return None to indicate no preprocessing available
            return None

    def _prepare_input(
        self,
        features: dict[str, Any],
        preprocessor: Any = None,
    ) -> np.ndarray:
        """
        Prepare input data for model prediction.

        Args:
            features: Feature dictionary (24 raw features)
            preprocessor: Optional preprocessor instance from training

        Returns:
            NumPy array ready for model input (preprocessed features)
        """
        # Convert features dict to DataFrame with single row
        # Ensure features are in the correct order as expected by the preprocessor
        feature_df = pd.DataFrame([features])

        logger.debug(
            f"Input features shape before preprocessing: {feature_df.shape}",
            extra={"feature_columns": list(feature_df.columns)},
        )

        # Apply preprocessing if available
        if preprocessor is not None:
            try:
                # Apply the same preprocessing pipeline as training:
                # 1. Handle missing values (imputation)
                # 2. Feature engineering (interaction + polynomial features)
                # 3. Scaling
                # 4. Remove constant features
                preprocessed_df, _ = preprocessor.preprocess(feature_df, y=None, fit=False)

                logger.debug(
                    f"Features after preprocessing: shape={preprocessed_df.shape}",
                    extra={"preprocessed_shape": preprocessed_df.shape},
                )

                # Convert to numpy array
                return preprocessed_df.values

            except Exception as e:
                logger.error(f"Preprocessing failed: {e}. Using raw features.", exc_info=True)
                # Fall back to raw features
                return feature_df.values
        else:
            # No preprocessor available, use raw features
            logger.warning("No preprocessor available, using raw features")
            return feature_df.values

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
