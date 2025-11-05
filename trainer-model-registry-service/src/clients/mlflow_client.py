"""
MLflow client for Trainer & Model Registry Service.

Provides integration with MLflow model registry and tracking.
"""

import logging
from typing import Optional, Dict, Any, List
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities.model_registry import ModelVersion

from src.config import MLflowConfig
from src.exceptions import ExternalServiceError, RegistrationError

logger = logging.getLogger(__name__)


class MLflowClientWrapper:
    """MLflow client wrapper for model tracking and registry."""

    def __init__(self, config: MLflowConfig):
        """
        Initialize MLflow client.

        Args:
            config: MLflow configuration
        """
        self.config = config
        self.client: Optional[MlflowClient] = None
        logger.info(f"MLflow client initialized with URI: {config.tracking_uri}")

    def connect(self) -> None:
        """
        Initialize MLflow client.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            mlflow.set_tracking_uri(self.config.tracking_uri)
            mlflow.set_registry_uri(self.config.registry_uri)
            self.client = MlflowClient(tracking_uri=self.config.tracking_uri)
            logger.info("MLflow client connected")
        except Exception as e:
            logger.error(f"Failed to connect to MLflow: {e}")
            raise ExternalServiceError(
                f"Failed to connect to MLflow: {e}",
                service_name="MLflow",
                details={"tracking_uri": self.config.tracking_uri},
            )

    def health_check(self) -> bool:
        """
        Check MLflow connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.client:
            logger.warning("MLflow client not initialized")
            return False

        try:
            # Try to list experiments
            _ = self.client.search_experiments()
            logger.debug("MLflow health check passed")
            return True
        except Exception as e:
            logger.error(f"MLflow health check failed: {e}")
            return False

    def create_experiment(self, name: str) -> str:
        """
        Create MLflow experiment.

        Args:
            name: Experiment name

        Returns:
            Experiment ID

        Raises:
            ExternalServiceError: If creation fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            experiment_id = self.client.create_experiment(name)
            logger.info(f"Created MLflow experiment: {name} (ID: {experiment_id})")
            return experiment_id
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            raise ExternalServiceError(
                f"Failed to create experiment: {e}",
                service_name="MLflow",
                details={"experiment_name": name},
            )

    def get_experiment_by_name(self, name: str) -> Optional[str]:
        """
        Get experiment ID by name.

        Args:
            name: Experiment name

        Returns:
            Experiment ID or None if not found

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            experiment = self.client.get_experiment_by_name(name)
            if experiment:
                logger.debug(
                    f"Found experiment: {name} (ID: {experiment.experiment_id})"
                )
                return experiment.experiment_id
            return None
        except Exception as e:
            logger.error(f"Failed to get experiment: {e}")
            raise ExternalServiceError(
                f"Failed to get experiment: {e}",
                service_name="MLflow",
                details={"experiment_name": name},
            )

    def log_model(
        self,
        run_id: str,
        model_path: str,
        artifact_path: str,
        model_type: str,
    ) -> None:
        """
        Log model artifact.

        Args:
            run_id: MLflow run ID
            model_path: Path to model file
            artifact_path: Artifact path in MLflow
            model_type: Type of model (xgboost, sklearn, etc.)

        Raises:
            ExternalServiceError: If logging fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            self.client.log_artifact(run_id, model_path, artifact_path)
            logger.info(f"Logged model artifact for run {run_id}")
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
            raise ExternalServiceError(
                f"Failed to log model: {e}",
                service_name="MLflow",
                details={"run_id": run_id, "model_type": model_type},
            )

    def log_metrics(self, run_id: str, metrics: Dict[str, float]) -> None:
        """
        Log metrics to MLflow.

        Args:
            run_id: MLflow run ID
            metrics: Dictionary of metric names and values

        Raises:
            ExternalServiceError: If logging fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            for key, value in metrics.items():
                self.client.log_metric(run_id, key, value)
            logger.debug(f"Logged {len(metrics)} metrics for run {run_id}")
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
            raise ExternalServiceError(
                f"Failed to log metrics: {e}",
                service_name="MLflow",
                details={"run_id": run_id, "num_metrics": len(metrics)},
            )

    def register_model(
        self,
        model_uri: str,
        model_name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Register model in MLflow registry.

        Args:
            model_uri: URI of model artifact
            model_name: Name for registered model
            tags: Optional tags for model

        Returns:
            Model version

        Raises:
            RegistrationError: If registration fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            model_version = mlflow.register_model(model_uri, model_name)
            logger.info(
                f"Registered model: {model_name} (version: {model_version.version})"
            )

            if tags:
                self.client.set_model_version_tag(
                    model_name, model_version.version, "tags", str(tags)
                )

            return str(model_version.version)
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise RegistrationError(
                f"Failed to register model: {e}",
                model_name=model_name,
                details={"model_uri": model_uri},
            )

    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
    ) -> None:
        """
        Transition model to new stage.

        Args:
            model_name: Name of registered model
            version: Model version
            stage: Target stage (Staging, Production, Archived)

        Raises:
            ExternalServiceError: If transition fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            self.client.transition_model_version_stage(model_name, version, stage)
            logger.info(f"Transitioned {model_name} v{version} to {stage}")
        except Exception as e:
            logger.error(f"Failed to transition model stage: {e}")
            raise ExternalServiceError(
                f"Failed to transition model stage: {e}",
                service_name="MLflow",
                details={"model_name": model_name, "version": version, "stage": stage},
            )

    def get_model_version(
        self, model_name: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get model version details.

        Args:
            model_name: Name of registered model
            version: Model version

        Returns:
            Model version details or None if not found

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            model_version = self.client.get_model_version(model_name, version)
            logger.debug(f"Retrieved model version: {model_name} v{version}")
            return {
                "name": model_version.name,
                "version": model_version.version,
                "stage": model_version.current_stage,
                "source": model_version.source,
                "status": model_version.status,
            }
        except Exception as e:
            logger.error(f"Failed to get model version: {e}")
            raise ExternalServiceError(
                f"Failed to get model version: {e}",
                service_name="MLflow",
                details={"model_name": model_name, "version": version},
            )

    def list_model_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of a model.

        Args:
            model_name: Name of registered model

        Returns:
            List of model version details

        Raises:
            ExternalServiceError: If listing fails
        """
        if not self.client:
            raise ExternalServiceError(
                "MLflow client not initialized",
                service_name="MLflow",
            )

        try:
            versions = self.client.search_model_versions(f"name='{model_name}'")
            logger.debug(f"Listed {len(versions)} versions for {model_name}")
            return [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "status": v.status,
                }
                for v in versions
            ]
        except Exception as e:
            logger.error(f"Failed to list model versions: {e}")
            raise ExternalServiceError(
                f"Failed to list model versions: {e}",
                service_name="MLflow",
                details={"model_name": model_name},
            )
