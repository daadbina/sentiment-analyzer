"""
Model Loader for Predictor Online Inference Service.

Handles lazy loading, validation, and fallback to baseline models.
Includes model warmup and health checks.
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from ..config import MLflowConfig
from ..exceptions import ModelLoadError
from ..metrics import MetricsCollector
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loader for ML models with lazy loading and fallback support.

    Handles model validation, warmup, and health checks with
    automatic fallback to baseline model on failures.
    """

    def __init__(self, config: MLflowConfig, metrics: MetricsCollector):
        """
        Initialize model loader.

        Args:
            config: MLflow configuration
            metrics: Metrics collector
        """
        self.config = config
        self.metrics = metrics
        self._model: Any | None = None
        self._model_version: str | None = None
        self._model_metadata: dict[str, Any] = {}
        self._baseline_model: Any | None = None
        self._is_using_baseline = False

        logger.info(
            "Initialized ModelLoader",
            extra={
                "tracking_uri": config.tracking_uri,
                "model_name": config.model_name
            }
        )

    @trace_span("model_loader.lazy_load_model")
    async def lazy_load_model(
        self,
        model_version: str | None = None,
        trace_id: str | None = None
    ) -> Any:
        """
        Lazy load model from MLflow.

        Loads model only if not already loaded or if version changed.

        Args:
            model_version: Specific model version to load (None = latest)
            trace_id: Trace ID for correlation

        Returns:
            Loaded model

        Raises:
            ModelLoadError: If model loading fails
        """
        try:
            # Check if model already loaded with same version
            if self._model and self._model_version == model_version:
                logger.debug(
                    "Model already loaded",
                    extra={
                        "model_version": model_version,
                        "trace_id": trace_id
                    }
                )
                return self._model

            start_time = datetime.now()

            logger.info(
                "Loading model from MLflow",
                extra={
                    "model_name": self.config.model_name,
                    "model_version": model_version,
                    "trace_id": trace_id
                }
            )

            # Set MLflow tracking URI
            mlflow.set_tracking_uri(self.config.tracking_uri)

            # Load model
            if model_version:
                model_uri = f"models:/{self.config.model_name}/{model_version}"
            else:
                model_uri = f"models:/{self.config.model_name}/latest"

            self._model = mlflow.pyfunc.load_model(model_uri)
            self._model_version = model_version or "latest"

            # Load model metadata
            client = MlflowClient(tracking_uri=self.config.tracking_uri)
            if model_version:
                model_metadata = client.get_model_version(
                    name=self.config.model_name,
                    version=model_version
                )
                self._model_metadata = {
                    "version": model_metadata.version,
                    "run_id": model_metadata.run_id,
                    "status": model_metadata.status,
                    "creation_timestamp": model_metadata.creation_timestamp
                }

            # Calculate load time
            load_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record metrics
            self.metrics.record_model_load_time(load_time_ms)

            # Validate model
            await self.validate_model(trace_id=trace_id)

            # Warmup model
            await self.warmup_model(trace_id=trace_id)

            self._is_using_baseline = False

            logger.info(
                "Model loaded successfully",
                extra={
                    "model_version": self._model_version,
                    "load_time_ms": load_time_ms,
                    "metadata": self._model_metadata,
                    "trace_id": trace_id
                }
            )

            return self._model

        except Exception as e:
            logger.error(
                "Failed to load model",
                extra={
                    "model_name": self.config.model_name,
                    "model_version": model_version,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )

            self.metrics.increment_model_load_failures()

            # Try fallback to baseline
            return await self.fallback_to_baseline_model(trace_id=trace_id)

    @trace_span("model_loader.validate_model")
    async def validate_model(
        self,
        trace_id: str | None = None
    ) -> bool:
        """
        Validate loaded model.

        Args:
            trace_id: Trace ID for correlation

        Returns:
            True if model is valid

        Raises:
            ModelLoadError: If validation fails
        """
        if not self._model:
            raise ModelLoadError(
                message="No model loaded to validate",
                details={"operation": "validate_model"}
            )

        try:
            logger.debug(
                "Validating model",
                extra={
                    "model_version": self._model_version,
                    "trace_id": trace_id
                }
            )

            # Check if model has predict method
            if not hasattr(self._model, 'predict'):
                raise ModelLoadError(
                    message="Model does not have predict method",
                    details={"model_version": self._model_version}
                )

            logger.info(
                "Model validation successful",
                extra={
                    "model_version": self._model_version,
                    "trace_id": trace_id
                }
            )

            return True

        except Exception as e:
            logger.error(
                "Model validation failed",
                extra={
                    "model_version": self._model_version,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise ModelLoadError(
                message=f"Model validation failed: {str(e)}",
                details={"model_version": self._model_version}
            ) from e

    @trace_span("model_loader.warmup_model")
    async def warmup_model(
        self,
        trace_id: str | None = None
    ) -> None:
        """
        Warmup model with dummy prediction.

        Args:
            trace_id: Trace ID for correlation
        """
        if not self._model:
            logger.warning(
                "No model loaded to warmup",
                extra={"trace_id": trace_id}
            )
            return

        try:
            import pandas as pd

            logger.debug(
                "Warming up model",
                extra={
                    "model_version": self._model_version,
                    "trace_id": trace_id
                }
            )

            # Create dummy input with expected features
            dummy_input = pd.DataFrame({
                "feature_num_sources": [5],
                "feature_sentiment_mean": [0.5],
                "feature_credibility_mean": [0.7],
                "feature_time_density": [0.3],
                "feature_entities_count": [3]
            })

            # Make dummy prediction
            _ = self._model.predict(dummy_input)

            logger.info(
                "Model warmup successful",
                extra={
                    "model_version": self._model_version,
                    "trace_id": trace_id
                }
            )

        except Exception as e:
            logger.warning(
                "Model warmup failed (non-critical)",
                extra={
                    "model_version": self._model_version,
                    "error": str(e),
                    "trace_id": trace_id
                }
            )

    @trace_span("model_loader.fallback_to_baseline_model")
    async def fallback_to_baseline_model(
        self,
        trace_id: str | None = None
    ) -> Any:
        """
        Fallback to baseline model.

        Args:
            trace_id: Trace ID for correlation

        Returns:
            Baseline model

        Raises:
            ModelLoadError: If baseline model loading fails
        """
        try:
            logger.warning(
                "Falling back to baseline model",
                extra={"trace_id": trace_id}
            )

            # Check if baseline already loaded
            if self._baseline_model:
                self._model = self._baseline_model
                self._is_using_baseline = True
                logger.info("Using cached baseline model")
                return self._baseline_model

            # Load baseline model
            baseline_path = os.getenv("BASELINE_MODEL_PATH", "/models/baseline_model.pkl")

            if not os.path.exists(baseline_path):
                raise ModelLoadError(
                    message=f"Baseline model not found: {baseline_path}",
                    details={"baseline_path": baseline_path}
                )

            with open(baseline_path, 'rb') as f:
                self._baseline_model = pickle.load(f)

            self._model = self._baseline_model
            self._model_version = "baseline"
            self._is_using_baseline = True

            logger.info(
                "Baseline model loaded",
                extra={
                    "baseline_path": baseline_path,
                    "trace_id": trace_id
                }
            )

            return self._baseline_model

        except Exception as e:
            logger.error(
                "Failed to load baseline model",
                extra={
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise ModelLoadError(
                message=f"Failed to load baseline model: {str(e)}",
                details={}
            ) from e

    def get_model(self) -> Any | None:
        """Get currently loaded model."""
        return self._model

    def get_model_version(self) -> str | None:
        """Get currently loaded model version."""
        return self._model_version

    def get_model_metadata(self) -> dict[str, Any]:
        """Get model metadata."""
        return self._model_metadata

    def is_using_baseline(self) -> bool:
        """Check if using baseline model."""
        return self._is_using_baseline

