"""
Model training orchestration.

Coordinates training pipeline with strategy pattern for pluggable trainers.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.models.base_model import BaseModel
from src.models.xgboost_model import XGBoostModel
from src.models.logistic_regression_model import LogisticRegressionModel
from src.models.llm_baseline_model import LLMBaselineModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer
from src.metrics import metrics

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class Trainer:
    """Orchestrates model training pipeline."""

    def __init__(self):
        """Initialize trainer."""
        self.models: Dict[str, BaseModel] = {}
        self.training_history: Dict[str, Dict[str, Any]] = {}
        logger.info("Trainer initialized")

    def train_model(
        self,
        model_type: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Train a model of specified type.

        Args:
            model_type: Type of model (xgboost, logistic_regression, llm)
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Tuple of (trained model, training metrics)

        Raises:
            TrainingError: If training fails
        """
        with tracer.start_as_current_span("train_model") as span:
            span.set_attribute("model_type", model_type)
            span.set_attribute("num_train_samples", len(X_train))

            try:
                logger.info(f"Starting training for {model_type}")

                # Create model instance
                model = self._create_model(model_type)

                # Train model
                metrics_dict = model.train(X_train, y_train, X_val, y_val)

                # Store model and history
                self.models[model_type] = model
                self.training_history[model_type] = {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics_dict,
                }

                # Record metrics
                metrics.record_training_run(model_type)

                logger.info(f"Training complete for {model_type}: {metrics_dict}")
                return model, metrics_dict

            except Exception as e:
                logger.error(f"Training failed for {model_type}: {e}")
                raise TrainingError(
                    f"Training failed for {model_type}: {e}",
                    model_name=model_type,
                )

    def train_all_models(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Tuple[BaseModel, Dict[str, Any]]]:
        """
        Train all model types.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Dictionary mapping model types to (model, metrics) tuples

        Raises:
            TrainingError: If any training fails
        """
        with tracer.start_as_current_span("train_all_models"):
            try:
                logger.info("Starting training for all models")

                results = {}
                model_types = ["xgboost", "logistic_regression", "llm"]

                for model_type in model_types:
                    try:
                        model, metrics_dict = self.train_model(
                            model_type, X_train, y_train, X_val, y_val
                        )
                        results[model_type] = (model, metrics_dict)
                    except Exception as e:
                        logger.error(f"Failed to train {model_type}: {e}")
                        # Continue with other models

                if not results:
                    raise TrainingError(
                        "Failed to train any models",
                        model_name="all",
                    )

                logger.info(f"Training complete for {len(results)} models")
                return results

            except Exception as e:
                logger.error(f"Training all models failed: {e}")
                raise TrainingError(
                    f"Training all models failed: {e}",
                    model_name="all",
                )

    def _create_model(self, model_type: str) -> BaseModel:
        """
        Create model instance.

        Args:
            model_type: Type of model

        Returns:
            Model instance

        Raises:
            TrainingError: If model type unknown
        """
        if model_type == "xgboost":
            return XGBoostModel()
        elif model_type == "logistic_regression":
            return LogisticRegressionModel()
        elif model_type == "llm":
            return LLMBaselineModel()
        else:
            raise TrainingError(
                f"Unknown model type: {model_type}",
                model_name=model_type,
            )

    def get_model(self, model_type: str) -> Optional[BaseModel]:
        """
        Get trained model.

        Args:
            model_type: Type of model

        Returns:
            Model instance or None if not trained
        """
        return self.models.get(model_type)

    def get_training_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Get training history.

        Returns:
            Dictionary with training history
        """
        return self.training_history

    def compare_models(self) -> Dict[str, Any]:
        """
        Compare trained models.

        Returns:
            Dictionary with model comparison

        Raises:
            TrainingError: If no models trained
        """
        with tracer.start_as_current_span("compare_models"):
            try:
                if not self.models:
                    raise TrainingError(
                        "No models trained",
                        model_name="all",
                    )

                comparison = {}
                for model_type, model in self.models.items():
                    comparison[model_type] = {
                        "model_name": model.model_name,
                        "is_trained": model.is_trained,
                        "config": model.config,
                    }

                logger.info(f"Model comparison: {comparison}")
                return comparison

            except Exception as e:
                logger.error(f"Model comparison failed: {e}")
                raise TrainingError(
                    f"Model comparison failed: {e}",
                    model_name="all",
                )
