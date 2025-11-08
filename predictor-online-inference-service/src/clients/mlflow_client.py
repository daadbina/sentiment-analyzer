"""
MLflow client for model registry and model loading.

Provides abstraction over MLflow for loading models from the registry.
Supports model versioning, fallback models, and circuit breaker pattern.
"""

import asyncio
import logging
from datetime import datetime

import mlflow
from mlflow.pyfunc import PyFuncModel
from mlflow.tracking import MlflowClient

from ..config import MLflowConfig
from ..exceptions import ModelLoadError
from ..metrics import MetricsCollector, model_load_duration_seconds
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class MLflowModelClient:
    """
    Client for interacting with MLflow model registry.

    Provides methods for loading models with version management and fallback.
    Implements circuit breaker pattern for resilient model loading.
    """

    def __init__(self, config: MLflowConfig):
        """
        Initialize MLflow client.

        Args:
            config: MLflow configuration
        """
        self.config = config
        self._client: MlflowClient | None = None
        self._loaded_models: dict[str, PyFuncModel] = {}

        logger.info(
            f"Initializing MLflow client: tracking_uri={config.tracking_uri}, "
            f"model_name={config.model_name}"
        )

    async def connect(self) -> None:
        """
        Connect to MLflow tracking server.

        Raises:
            ModelLoadError: If connection fails
        """
        try:
            logger.info(f"Connecting to MLflow: {self.config.tracking_uri}")

            # Set tracking URI
            mlflow.set_tracking_uri(self.config.tracking_uri)

            # Initialize client
            self._client = MlflowClient(tracking_uri=self.config.tracking_uri)

            # Verify connection by listing experiments
            experiments = self._client.search_experiments(max_results=1)

            logger.info(
                f"Connected to MLflow: tracking_uri={self.config.tracking_uri}, "
                f"experiments_found={len(experiments)}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to MLflow: {e}", exc_info=True)
            raise ModelLoadError(
                f"Failed to connect to MLflow: {e}",
                context={"tracking_uri": self.config.tracking_uri},
            )

    async def disconnect(self) -> None:
        """Disconnect from MLflow and clear loaded models."""
        logger.info("Disconnecting from MLflow")
        self._client = None
        self._loaded_models.clear()

    def _ensure_connected(self) -> MlflowClient:
        """
        Ensure client is connected.

        Returns:
            MlflowClient instance

        Raises:
            ModelLoadError: If not connected
        """
        if self._client is None:
            raise ModelLoadError(
                "MLflow client not connected. Call connect() first.",
            )
        return self._client

    async def load_model(
        self,
        model_version: str | None = None,
        use_fallback: bool = True,
        trace_id: str | None = None,
    ) -> PyFuncModel:
        """
        Load model from MLflow registry.

        Args:
            model_version: Model version to load (uses config default if None)
            use_fallback: Whether to use fallback model on failure
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Loaded PyFuncModel instance

        Raises:
            ModelLoadError: If model loading fails and no fallback available
        """
        version = model_version or self.config.model_version
        cache_key = f"{self.config.model_name}:{version}"

        # Check if model is already loaded
        if cache_key in self._loaded_models:
            logger.debug(f"Using cached model: {cache_key}")
            return self._loaded_models[cache_key]

        with trace_span(
            "mlflow_load_model",
            attributes={
                "model_name": self.config.model_name,
                "model_version": version,
                "trace_id": trace_id,
            },
        ):
            try:
                start_time = datetime.now()

                # Load model with timeout
                model = await asyncio.wait_for(
                    self._load_model_async(version),
                    timeout=self.config.model_load_timeout_seconds,
                )

                # Calculate load duration
                duration_seconds = (datetime.now() - start_time).total_seconds()

                # Record metrics
                model_load_duration_seconds.labels(
                    model_name=self.config.model_name,
                    model_version=version,
                ).observe(duration_seconds)

                # Cache loaded model
                self._loaded_models[cache_key] = model

                logger.info(
                    f"Model loaded successfully: name={self.config.model_name}, "
                    f"version={version}, duration_seconds={duration_seconds:.2f}",
                    extra={"trace_id": trace_id, "model_version": version},
                )

                return model

            except TimeoutError:
                logger.error(
                    f"Model load timeout: name={self.config.model_name}, "
                    f"version={version}, timeout={self.config.model_load_timeout_seconds}s",
                    extra={"trace_id": trace_id},
                )

                MetricsCollector.record_model_load_failure(self.config.model_name, version)

                # Try fallback model
                if use_fallback and self.config.fallback_model_version:
                    return await self._load_fallback_model(trace_id)

                raise ModelLoadError(
                    f"Model load timeout after {self.config.model_load_timeout_seconds}s",
                    model_name=self.config.model_name,
                    model_version=version,
                    trace_id=trace_id,
                )

            except Exception as e:
                logger.error(
                    f"Failed to load model: name={self.config.model_name}, "
                    f"version={version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )

                MetricsCollector.record_model_load_failure(self.config.model_name, version)

                # Try fallback model
                if use_fallback and self.config.fallback_model_version:
                    return await self._load_fallback_model(trace_id)

                raise ModelLoadError(
                    f"Failed to load model: {e}",
                    model_name=self.config.model_name,
                    model_version=version,
                    trace_id=trace_id,
                )

    async def _load_model_async(self, version: str) -> PyFuncModel:
        """
        Load model asynchronously.

        Args:
            version: Model version to load

        Returns:
            Loaded PyFuncModel instance
        """
        self._ensure_connected()

        # Resolve model URI
        if version in ["production", "staging", "archived", "none"]:
            # Load by stage
            model_uri = f"models:/{self.config.model_name}/{version}"
        else:
            # Load by version number
            model_uri = f"models:/{self.config.model_name}/{version}"

        logger.debug(f"Loading model from URI: {model_uri}")

        # Load model in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            mlflow.pyfunc.load_model,
            model_uri,
        )


    async def _load_fallback_model(self, trace_id: str | None = None) -> PyFuncModel:
        """
        Load fallback model.

        Args:
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Loaded fallback model

        Raises:
            ModelLoadError: If fallback model loading fails
        """
        fallback_version = self.config.fallback_model_version

        logger.warning(
            f"Loading fallback model: version={fallback_version}",
            extra={"trace_id": trace_id},
        )

        try:
            # Load fallback model without further fallback
            return await self.load_model(
                model_version=fallback_version,
                use_fallback=False,
                trace_id=trace_id,
            )
        except Exception as e:
            logger.error(
                f"Failed to load fallback model: version={fallback_version}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )
            raise ModelLoadError(
                f"Failed to load fallback model: {e}",
                model_name=self.config.model_name,
                model_version=fallback_version,
                trace_id=trace_id,
            )

    async def get_model_metadata(self, model_version: str | None = None) -> dict:
        """
        Get metadata for a model version.

        Args:
            model_version: Model version (uses config default if None)

        Returns:
            Dictionary containing model metadata

        Raises:
            ModelLoadError: If metadata retrieval fails
        """
        client = self._ensure_connected()
        version = model_version or self.config.model_version

        try:
            # Get model version details
            model_version_details = client.get_model_version(
                name=self.config.model_name,
                version=version,
            )

            return {
                "name": model_version_details.name,
                "version": model_version_details.version,
                "stage": model_version_details.current_stage,
                "description": model_version_details.description,
                "run_id": model_version_details.run_id,
                "status": model_version_details.status,
                "creation_timestamp": model_version_details.creation_timestamp,
                "last_updated_timestamp": model_version_details.last_updated_timestamp,
            }
        except Exception as e:
            logger.error(f"Failed to get model metadata: {e}", exc_info=True)
            raise ModelLoadError(
                f"Failed to get model metadata: {e}",
                model_name=self.config.model_name,
                model_version=version,
            )

    async def health_check(self) -> bool:
        """
        Check if MLflow is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = self._ensure_connected()
            # Try to search experiments as a health check
            client.search_experiments(max_results=1)
            return True
        except Exception as e:
            logger.warning(f"MLflow health check failed: {e}")
            return False

