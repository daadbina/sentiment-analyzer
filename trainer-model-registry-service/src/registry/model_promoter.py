"""
Model promotion to production.

Manages model stage transitions with gating and validation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.clients.mlflow_client import MLflowClient
from src.config import config
from src.exceptions import PromotionError
from src.utils.trace import get_tracer
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class ModelPromoter:
    """Manages model promotion to production."""

    def __init__(self, mlflow_client: MLflowClient):
        """
        Initialize model promoter.

        Args:
            mlflow_client: MLflow client instance
        """
        self.mlflow_client = mlflow_client
        self.promotion_history: Dict[str, Dict[str, Any]] = {}
        logger.info("Model promoter initialized")

    def promote_model(
        self,
        model_name: str,
        model_version: int,
        metrics_dict: Dict[str, float],
        stage: str = "Staging",
    ) -> bool:
        """
        Promote model to specified stage.

        Args:
            model_name: Name of model in MLflow
            model_version: Version number
            metrics_dict: Model evaluation metrics
            stage: Target stage (Staging or Production)

        Returns:
            True if promotion successful, False otherwise

        Raises:
            PromotionError: If promotion fails
        """
        with tracer.start_as_current_span("promote_model") as span:
            span.set_attribute("model_name", model_name)
            span.set_attribute("model_version", model_version)
            span.set_attribute("target_stage", stage)

            try:
                logger.info(
                    f"Promoting {model_name} v{model_version} to {stage}"
                )

                # Validate metrics
                if not self._validate_metrics(metrics_dict, stage):
                    logger.warning(
                        f"Model {model_name} v{model_version} failed validation"
                    )
                    metrics.record_promotion_failure()
                    return False

                # Transition stage
                self.mlflow_client.transition_model_stage(
                    model_name=model_name,
                    version=model_version,
                    stage=stage,
                )

                # Record promotion
                self.promotion_history[f"{model_name}_v{model_version}"] = {
                    "timestamp": datetime.now().isoformat(),
                    "stage": stage,
                    "metrics": metrics_dict,
                }

                # Record metric
                metrics.record_model_promoted()

                logger.info(
                    f"Successfully promoted {model_name} v{model_version} to {stage}"
                )
                return True

            except Exception as e:
                logger.error(f"Promotion failed: {e}")
                metrics.record_promotion_failure()
                raise PromotionError(
                    f"Promotion failed: {e}",
                    model_name=model_name,
                    version=model_version,
                )

    def promote_to_staging(
        self,
        model_name: str,
        model_version: int,
        metrics_dict: Dict[str, float],
    ) -> bool:
        """
        Promote model to Staging.

        Args:
            model_name: Name of model
            model_version: Version number
            metrics_dict: Evaluation metrics

        Returns:
            True if successful
        """
        return self.promote_model(
            model_name, model_version, metrics_dict, stage="Staging"
        )

    def promote_to_production(
        self,
        model_name: str,
        model_version: int,
        metrics_dict: Dict[str, float],
    ) -> bool:
        """
        Promote model to Production.

        Args:
            model_name: Name of model
            model_version: Version number
            metrics_dict: Evaluation metrics

        Returns:
            True if successful
        """
        return self.promote_model(
            model_name, model_version, metrics_dict, stage="Production"
        )

    def _validate_metrics(
        self,
        metrics_dict: Dict[str, float],
        stage: str,
    ) -> bool:
        """
        Validate metrics against thresholds.

        Args:
            metrics_dict: Evaluation metrics
            stage: Target stage

        Returns:
            True if metrics pass validation

        Raises:
            PromotionError: If validation fails
        """
        with tracer.start_as_current_span("validate_metrics"):
            try:
                # Check required metrics
                required_metrics = ["auc", "precision", "recall", "f1"]
                for metric in required_metrics:
                    if metric not in metrics_dict:
                        raise PromotionError(
                            f"Missing required metric: {metric}",
                            model_name="unknown",
                        )

                # Get thresholds
                auc_threshold = config.model_promotion.threshold_auc
                precision_threshold = config.model_promotion.threshold_precision
                recall_threshold = config.model_promotion.threshold_recall

                # Validate thresholds
                auc = metrics_dict.get("auc", 0)
                precision = metrics_dict.get("precision", 0)
                recall = metrics_dict.get("recall", 0)

                if auc < auc_threshold:
                    logger.warning(
                        f"AUC {auc} below threshold {auc_threshold}"
                    )
                    return False

                if precision < precision_threshold:
                    logger.warning(
                        f"Precision {precision} below threshold {precision_threshold}"
                    )
                    return False

                if recall < recall_threshold:
                    logger.warning(
                        f"Recall {recall} below threshold {recall_threshold}"
                    )
                    return False

                logger.info("Metrics validation passed")
                return True

            except Exception as e:
                logger.error(f"Metrics validation failed: {e}")
                raise PromotionError(
                    f"Metrics validation failed: {e}",
                    model_name="unknown",
                )

    def get_promotion_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Get promotion history.

        Returns:
            Dictionary with promotion history
        """
        return self.promotion_history

    def get_current_production_model(
        self,
        model_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current production model.

        Args:
            model_name: Name of model

        Returns:
            Model version info or None

        Raises:
            PromotionError: If retrieval fails
        """
        with tracer.start_as_current_span("get_current_production_model"):
            try:
                model_version = self.mlflow_client.get_model_version(
                    model_name=model_name,
                    stage="Production",
                )

                logger.info(f"Current production model: {model_version}")
                return model_version

            except Exception as e:
                logger.error(f"Failed to get production model: {e}")
                raise PromotionError(
                    f"Failed to get production model: {e}",
                    model_name=model_name,
                )

