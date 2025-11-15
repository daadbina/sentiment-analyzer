"""
MLflow client for model registry and model loading.

Provides abstraction over MLflow for loading models from the registry.
Supports model versioning, fallback models, automatic model selection, and S3-based loading.
"""

import asyncio
import logging
import pickle
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import joblib
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

    Provides methods for loading models with version management, fallback,
    automatic model selection, and S3-based loading.
    Implements circuit breaker pattern for resilient model loading.
    """

    def __init__(self, config: MLflowConfig, s3_client=None):
        """
        Initialize MLflow client.

        Args:
            config: MLflow configuration
            s3_client: Optional S3 client for model artifact retrieval
        """
        self.config = config
        self.s3_client = s3_client
        self._client: MlflowClient | None = None
        self._loaded_models: dict[str, Any] = {}
        self._selected_model_info: Dict[str, Any] | None = None

        logger.info(
            f"Initializing MLflow client: tracking_uri={config.tracking_uri}, "
            f"auto_select={config.auto_select_best_model}"
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

    async def find_best_model(self, domain: str | None = None) -> Tuple[str, str, str]:
        """
        Find the best performing model from MLflow registry.

        Args:
            domain: Optional domain filter (btc/conflict/geopolitical)

        Returns:
            Tuple of (model_name, model_version, run_id)

        Raises:
            ModelLoadError: If no models found or selection fails
        """
        self._ensure_connected()

        try:
            # Determine metric based on domain
            # BTC models are regression (use RMSE, lower is better)
            # Conflict models are classification (use F1, higher is better)
            if domain == "btc":
                selection_metric = "rmse"
                maximize_metric = False  # Lower RMSE is better
            else:
                selection_metric = self.config.model_selection_metric
                maximize_metric = True  # Higher F1 is better

            logger.info(f"Searching for best model using metric: {selection_metric}, domain: {domain}, maximize: {maximize_metric}")

            # Search for models based on domain
            if domain == "btc":
                filter_string = "name LIKE 'btc_prediction%'"
            elif domain == "conflict":
                filter_string = "name LIKE 'conflict_prediction%'"
            elif domain == "geopolitical":
                filter_string = "name LIKE 'geopolitical_prediction%'"
            else:
                # Fallback: search for all prediction models
                filter_string = "name LIKE '%prediction%'"

            all_models = self._client.search_registered_models(filter_string=filter_string)

            if not all_models:
                raise ModelLoadError(f"No models found in MLflow registry with filter: {filter_string}")

            logger.info(f"Found {len(all_models)} registered models for domain: {domain}")

            best_model_name = None
            best_model_version = None
            best_run_id = None
            # Initialize based on whether we're maximizing or minimizing
            best_metric_value = -float('inf') if maximize_metric else float('inf')

            # Iterate through all models and their versions
            for model in all_models:
                model_name = model.name
                logger.debug(f"Evaluating model: {model_name}")

                # Get latest version
                versions = self._client.search_model_versions(f"name='{model_name}'")
                if not versions:
                    logger.debug(f"No versions found for model: {model_name}")
                    continue

                # Sort by version number (descending) and get the latest
                latest_version = sorted(versions, key=lambda v: int(v.version), reverse=True)[0]
                version_number = latest_version.version
                run_id = latest_version.run_id

                # If run_id is empty, try to extract from source
                if not run_id or run_id.strip() == "":
                    source = latest_version.source
                    if source and source.startswith("runs://"):
                        # Extract run_id from source: runs://{run_id}/model
                        run_id = source.split("/")[2]
                        logger.info(f"Extracted run_id from source for {model_name}: {run_id}")

                logger.info(
                    f"Latest version for {model_name}: {version_number}, run_id: '{run_id}', "
                    f"source: {latest_version.source}, status: {latest_version.status}"
                )

                # Get run metrics
                try:
                    if not run_id or run_id.strip() == "":
                        logger.info(f"Skipping {model_name} v{version_number}: empty run_id")
                        continue

                    run = self._client.get_run(run_id)
                    metrics = run.data.metrics

                    # Look for evaluation metric (with eval_ prefix)
                    metric_key = f"eval_{selection_metric}"
                    if metric_key not in metrics:
                        # Try without prefix
                        metric_key = selection_metric
                        if metric_key not in metrics:
                            logger.debug(f"Metric {selection_metric} not found for {model_name}")
                            continue

                    metric_value = metrics[metric_key]
                    logger.info(
                        f"Model {model_name} v{version_number}: {metric_key}={metric_value:.4f}"
                    )

                    # Update best model if this one is better
                    is_better = (metric_value > best_metric_value) if maximize_metric else (metric_value < best_metric_value)
                    if is_better:
                        best_metric_value = metric_value
                        best_model_name = model_name
                        best_model_version = version_number
                        best_run_id = run_id

                except Exception as e:
                    logger.warning(f"Failed to get metrics for {model_name} v{version_number}: {e}")
                    continue

            if best_model_name is None:
                raise ModelLoadError(
                    f"No models found with metric: {selection_metric}"
                )

            logger.info(
                f"Selected best model: {best_model_name} v{best_model_version} "
                f"with {selection_metric}={best_metric_value:.4f}"
            )

            # Store selected model info
            self._selected_model_info = {
                "model_name": best_model_name,
                "model_version": best_model_version,
                "run_id": best_run_id,
                "metric": self.config.model_selection_metric,
                "metric_value": best_metric_value,
            }

            return best_model_name, best_model_version, best_run_id

        except Exception as e:
            logger.error(f"Failed to find best model: {e}", exc_info=True)
            raise ModelLoadError(f"Failed to find best model: {e}")

    async def load_model(
        self,
        model_version: str | None = None,
        use_fallback: bool = True,
        trace_id: str | None = None,
        domain: str | None = None,
    ) -> tuple[Any, str]:
        """
        Load model from S3 via MLflow registry.

        If auto_select_best_model is enabled, automatically selects the best model.
        Otherwise, uses the configured model name and version.

        Args:
            model_version: Model version to load (uses config default if None)
            use_fallback: Whether to use fallback model on failure
            trace_id: Optional trace ID for distributed tracing
            domain: Optional domain filter (btc/conflict/geopolitical) for auto-selection

        Returns:
            Tuple of (loaded model instance, actual version string)

        Raises:
            ModelLoadError: If model loading fails and no fallback available
        """
        try:
            start_time = datetime.now()

            # Determine which model to load
            if self.config.auto_select_best_model:
                logger.info(f"Auto-selecting best model from MLflow registry for domain: {domain}")
                model_name, version, run_id = await self.find_best_model(domain=domain)
            else:
                # Select model name and version based on domain
                if domain == "btc":
                    if not self.config.btc_model_name:
                        raise ModelLoadError("MLFLOW_BTC_MODEL_NAME must be set when auto_select is disabled")
                    model_name = self.config.btc_model_name
                    # Use domain-specific version if available, otherwise fall back to general version
                    logger.info(f"DEBUG mlflow_client.load_model: domain=btc, model_version={model_version}, btc_model_version={self.config.btc_model_version}, model_version_config={self.config.model_version}")
                    version = model_version or self.config.btc_model_version or self.config.model_version
                elif domain == "conflict":
                    if not self.config.conflict_model_name:
                        raise ModelLoadError("MLFLOW_CONFLICT_MODEL_NAME must be set when auto_select is disabled")
                    model_name = self.config.conflict_model_name
                    # Use domain-specific version if available, otherwise fall back to general version
                    logger.info(f"DEBUG mlflow_client.load_model: domain=conflict, model_version={model_version}, conflict_model_version={self.config.conflict_model_version}, model_version_config={self.config.model_version}")
                    version = model_version or self.config.conflict_model_version or self.config.model_version
                else:
                    raise ModelLoadError(f"Unknown domain: {domain}. Must be 'btc' or 'conflict'")

                logger.info(f"Using configured model for domain {domain}: {model_name} version {version}")

                if not version:
                    raise ModelLoadError("Model version must be set (MLFLOW_MODEL_VERSION or domain-specific version) when auto_select is disabled")

                # Get run_id for this model version
                self._ensure_connected()
                versions = self._client.search_model_versions(f"name='{model_name}'")
                matching_version = next((v for v in versions if v.version == version), None)
                if not matching_version:
                    raise ModelLoadError(f"Model version not found: {model_name} v{version}")
                run_id = matching_version.run_id

            cache_key = f"{model_name}:{version}"

            # Check if model is already loaded
            if cache_key in self._loaded_models:
                logger.debug(f"Using cached model: {cache_key}")
                return self._loaded_models[cache_key], version

            with trace_span(
                "mlflow_load_model",
                attributes={
                    "model_name": model_name,
                    "model_version": version,
                    "run_id": run_id,
                    "trace_id": trace_id,
                },
            ):
                # Load model with timeout
                model = await asyncio.wait_for(
                    self._load_model_from_s3(model_name, version, run_id),
                    timeout=self.config.model_load_timeout_seconds,
                )

                # Calculate load duration
                duration_seconds = (datetime.now() - start_time).total_seconds()

                # Record metrics
                model_load_duration_seconds.labels(
                    model_name=model_name,
                    model_version=version,
                ).observe(duration_seconds)

                # Cache loaded model
                self._loaded_models[cache_key] = model

                logger.info(
                    f"Model loaded successfully: name={model_name}, "
                    f"version={version}, duration_seconds={duration_seconds:.2f}",
                    extra={"trace_id": trace_id, "model_version": version, "run_id": run_id},
                )

                return model, version

        except TimeoutError:
            logger.error(
                f"Model load timeout: timeout={self.config.model_load_timeout_seconds}s",
                extra={"trace_id": trace_id},
            )

            MetricsCollector.record_model_load_failure("unknown", "unknown")

            raise ModelLoadError(
                f"Model load timeout after {self.config.model_load_timeout_seconds}s",
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(
                f"Failed to load model: error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )

            MetricsCollector.record_model_load_failure("unknown", "unknown")

            raise ModelLoadError(
                f"Failed to load model: {e}",
                trace_id=trace_id,
            )

    async def _load_model_from_s3(self, model_name: str, version: str, run_id: str) -> Any:
        """
        Load model from MLflow registry using pyfunc.

        Args:
            model_name: Model name
            version: Model version
            run_id: MLflow run ID

        Returns:
            Loaded model instance

        Raises:
            ModelLoadError: If loading fails
        """
        try:
            # Use MLflow's pyfunc.load_model() to load models properly
            # This handles all model flavors (sklearn, xgboost, etc.) correctly
            model_uri = f"models:/{model_name}/{version}"
            logger.info(f"Loading model from MLflow registry: {model_uri}")

            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None,
                mlflow.pyfunc.load_model,
                model_uri,
            )

            logger.info(f"Model loaded successfully from MLflow: {model_name} v{version}")
            return model

        except Exception as e:
            logger.error(f"Failed to load model from MLflow: {e}", exc_info=True)
            raise ModelLoadError(f"Failed to load model from MLflow: {e}")

    def _load_pickle_model(self, file_path: str) -> Any:
        """
        Load model from pickle file using joblib for better numpy compatibility.

        Args:
            file_path: Path to pickle file

        Returns:
            Loaded model instance
        """
        try:
            # Try joblib first (better for sklearn models and numpy objects)
            model = joblib.load(file_path)
            logger.debug(f"Model loaded successfully using joblib from {file_path}")
            return model
        except Exception as e:
            logger.warning(f"Failed to load with joblib, trying pickle: {e}")
            # Fallback to pickle
            with open(file_path, 'rb') as f:
                model = pickle.load(f)
            logger.debug(f"Model loaded successfully using pickle from {file_path}")
            return model

    async def get_model_metadata(self) -> dict:
        """
        Get metadata for the currently selected/loaded model.

        Returns:
            Dictionary containing model metadata

        Raises:
            ModelLoadError: If metadata retrieval fails
        """
        if self._selected_model_info:
            return self._selected_model_info

        raise ModelLoadError("No model has been loaded yet")

    def download_artifact(
        self,
        model_version: str | None = None,
        artifact_path: str = "preprocessor",
        trace_id: str | None = None,
    ) -> str:
        """
        Download artifact from MLflow for a specific model version.

        Args:
            model_version: Model version identifier (if None, uses production model)
            artifact_path: Path to artifact within the run (e.g., "preprocessor")
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Local path to downloaded artifact file

        Raises:
            ModelLoadError: If artifact download fails
        """
        try:
            client = self._ensure_connected()

            # Get the run_id for this model version
            if model_version:
                # Get run_id for specific model version
                model_name = self.config.model_name
                versions = client.search_model_versions(f"name='{model_name}'")
                matching_version = next((v for v in versions if v.version == model_version), None)
                if not matching_version:
                    raise ModelLoadError(f"Model version not found: {model_name} v{model_version}")
                run_id = matching_version.run_id
                logger.info(f"Found run_id for {model_name} v{model_version}: {run_id}")
            elif self._selected_model_info and "run_id" in self._selected_model_info:
                # Use selected model's run_id
                run_id = self._selected_model_info["run_id"]
            else:
                # Try to get production model
                try:
                    model_name = self.config.model_name
                    versions = client.get_latest_versions(model_name, stages=["Production"])
                    if not versions:
                        versions = client.get_latest_versions(model_name, stages=["None"])

                    if versions:
                        run_id = versions[0].run_id
                    else:
                        raise ModelLoadError(f"No model versions found for {model_name}")
                except Exception as e:
                    raise ModelLoadError(f"Failed to get model run_id: {e}")

            logger.info(f"Downloading artifact from run {run_id}: {artifact_path}")

            # List artifacts in the preprocessor directory to find the .pkl file
            artifacts = client.list_artifacts(run_id, path=artifact_path)
            if not artifacts:
                raise ModelLoadError(f"No artifacts found in {artifact_path}")

            # Find the .pkl file
            preprocessor_artifact = None
            for artifact in artifacts:
                if artifact.path.endswith(".pkl"):
                    preprocessor_artifact = artifact
                    break

            if not preprocessor_artifact:
                raise ModelLoadError(f"No .pkl file found in {artifact_path}")

            logger.info(f"Found preprocessor artifact: {preprocessor_artifact.path}")

            # Download the specific artifact
            artifact_uri = client.download_artifacts(run_id, preprocessor_artifact.path)

            logger.info(f"Artifact downloaded to: {artifact_uri}")
            return artifact_uri

        except Exception as e:
            logger.error(f"Failed to download artifact: {e}", exc_info=True)
            raise ModelLoadError(f"Failed to download artifact: {e}")

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
