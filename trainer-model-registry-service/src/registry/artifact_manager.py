"""
Model artifact management.

Handles model artifact storage and retrieval.
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pickle

from src.clients.s3_client import S3Client
from src.clients.mlflow_client import MLflowClientWrapper
from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import RegistrationError
from src.utils.trace import get_tracer
from src.utils.checksum import compute_file_checksum, generate_model_metadata

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class ArtifactManager:
    """Manages model artifacts."""

    def __init__(self, s3_client: S3Client, mlflow_client: MLflowClientWrapper):
        """
        Initialize artifact manager.

        Args:
            s3_client: S3 client instance
            mlflow_client: MLflow client instance
        """
        self.s3_client = s3_client
        self.mlflow_client = mlflow_client
        self.artifact_registry: Dict[str, Dict[str, Any]] = {}
        logger.info("Artifact manager initialized")

    def save_model_artifact(
        self,
        model: BaseModel,
        model_name: str,
        version: str,
        local_path: str = "/tmp",
    ) -> Dict[str, Any]:
        """
        Save model artifact to S3 and MLflow.

        Args:
            model: Trained model instance
            model_name: Name of model
            version: Version string
            local_path: Local path for temporary storage

        Returns:
            Dictionary with artifact metadata

        Raises:
            RegistrationError: If save fails
        """
        with tracer.start_as_current_span("save_model_artifact") as span:
            span.set_attribute("model_name", model_name)
            span.set_attribute("version", version)

            try:
                logger.info(f"Saving model artifact: {model_name} v{version}")

                # Create local file
                local_file = os.path.join(local_path, f"{model_name}_{version}.pkl")
                model.save_model(local_file)

                # Compute checksum
                checksum = compute_file_checksum(local_file)

                # Upload to S3
                s3_key = f"models/{model_name}/{version}/model.pkl"
                self.s3_client.upload_file(local_file, s3_key)

                # Generate metadata
                metadata = generate_model_metadata(
                    model_name=model_name,
                    version=version,
                    model_type=model.model_type,
                    checksum=checksum,
                )

                # Store in registry
                self.artifact_registry[f"{model_name}_{version}"] = {
                    "timestamp": datetime.now().isoformat(),
                    "s3_key": s3_key,
                    "checksum": checksum,
                    "metadata": metadata,
                }

                # Clean up local file
                if os.path.exists(local_file):
                    os.remove(local_file)

                logger.info(f"Model artifact saved: {s3_key}")
                return metadata

            except Exception as e:
                logger.error(f"Failed to save model artifact: {e}")
                raise RegistrationError(
                    f"Failed to save model artifact: {e}",
                    model_name=model_name,
                )

    def load_model_artifact(
        self,
        model_name: str,
        version: str,
        local_path: str = "/tmp",
    ) -> BaseModel:
        """
        Load model artifact from S3.

        Args:
            model_name: Name of model
            version: Version string
            local_path: Local path for temporary storage

        Returns:
            Loaded model instance

        Raises:
            RegistrationError: If load fails
        """
        with tracer.start_as_current_span("load_model_artifact"):
            try:
                logger.info(f"Loading model artifact: {model_name} v{version}")

                # Get S3 key
                s3_key = f"models/{model_name}/{version}/model.pkl"

                # Download from S3
                local_file = os.path.join(local_path, f"{model_name}_{version}.pkl")
                self.s3_client.download_file(s3_key, local_file)

                # Load model
                with open(local_file, "rb") as f:
                    model = pickle.load(f)

                # Verify checksum
                checksum = compute_file_checksum(local_file)
                stored_checksum = self.artifact_registry.get(
                    f"{model_name}_{version}", {}
                ).get("checksum")

                if stored_checksum and checksum != stored_checksum:
                    logger.warning("Checksum mismatch for loaded model")

                # Clean up local file
                if os.path.exists(local_file):
                    os.remove(local_file)

                logger.info(f"Model artifact loaded: {s3_key}")
                return model

            except Exception as e:
                logger.error(f"Failed to load model artifact: {e}")
                raise RegistrationError(
                    f"Failed to load model artifact: {e}",
                    model_name=model_name,
                )

    def register_model_version(
        self,
        model_name: str,
        version: str,
        metrics: Dict[str, float],
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Register model version in MLflow.

        Args:
            model_name: Name of model
            version: Version string
            metrics: Model metrics
            description: Model description

        Returns:
            Registration metadata

        Raises:
            RegistrationError: If registration fails
        """
        with tracer.start_as_current_span("register_model_version"):
            try:
                logger.info(f"Registering model version: {model_name} v{version}")

                # Register in MLflow
                self.mlflow_client.register_model(
                    model_name=model_name,
                    version=version,
                    metrics=metrics,
                    description=description,
                )

                logger.info(f"Model version registered: {model_name} v{version}")

                return {
                    "model_name": model_name,
                    "version": version,
                    "metrics": metrics,
                    "registered_at": datetime.now().isoformat(),
                }

            except Exception as e:
                logger.error(f"Failed to register model version: {e}")
                raise RegistrationError(
                    f"Failed to register model version: {e}",
                    model_name=model_name,
                )

    def get_artifact_metadata(
        self,
        model_name: str,
        version: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get artifact metadata.

        Args:
            model_name: Name of model
            version: Version string

        Returns:
            Metadata dictionary or None
        """
        return self.artifact_registry.get(f"{model_name}_{version}")

    def list_artifacts(self) -> Dict[str, Dict[str, Any]]:
        """
        List all artifacts.

        Returns:
            Dictionary with all artifacts
        """
        return self.artifact_registry
