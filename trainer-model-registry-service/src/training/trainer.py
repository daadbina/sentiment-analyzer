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
from src.models.random_forest_model import RandomForestModel
from src.models.gradient_boosting_model import GradientBoostingModel
from src.models.voting_ensemble_model import VotingEnsembleModel
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
                logger.info(f"=== TRAINER: Starting training for {model_type} ===")
                logger.info(f"Training data shape: {X_train.shape}")
                logger.info(f"Training labels shape: {y_train.shape}")
                logger.info(f"Training features ({len(X_train.columns)}): {list(X_train.columns)[:20]}")  # First 20

                # Log sample training data
                if len(X_train) > 0:
                    sample_row = X_train.iloc[0].to_dict()
                    sample_features = {k: sample_row[k] for k in list(sample_row.keys())[:10]}
                    logger.info(f"Sample training features (first row): {sample_features}")

                # Check training data quality
                logger.info(f"Training data null values: {X_train.isnull().sum().sum()}")
                logger.info(f"Training labels null values: {y_train.isnull().sum()}")
                logger.info(f"Training labels distribution:\n{y_train.value_counts()}")

                if X_val is not None:
                    logger.info(f"Validation data shape: {X_val.shape}")
                    logger.info(f"Validation data null values: {X_val.isnull().sum().sum()}")
                    logger.info(f"Validation labels distribution:\n{y_val.value_counts()}")

                # Create model instance
                model = self._create_model(model_type)
                logger.info(f"Model instance created: {type(model).__name__}")

                # Train model
                logger.info(f"=== TRAINER: Training {model_type} model ===")
                metrics_dict = model.train(X_train, y_train, X_val, y_val)

                # Store model and history
                self.models[model_type] = model
                self.training_history[model_type] = {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics_dict,
                }

                # Record metrics
                metrics.record_training_run(model_type)

                logger.info(f"=== TRAINER: Training complete for {model_type} ===")
                logger.info(f"Training metrics: {metrics_dict}")
                logger.info(f"Model accuracy: {metrics_dict.get('accuracy', 'N/A')}")
                logger.info(f"Model precision: {metrics_dict.get('precision', 'N/A')}")
                logger.info(f"Model recall: {metrics_dict.get('recall', 'N/A')}")
                logger.info(f"Model F1 score: {metrics_dict.get('f1', 'N/A')}")
                return model, metrics_dict

            except Exception as e:
                logger.error(f"Training failed for {model_type}: {e}", exc_info=True)
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
        Train all model types including ensemble models.

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
                base_model_types = ["xgboost", "logistic_regression", "llm"]
                ensemble_model_types = ["random_forest", "gradient_boosting"]

                # Train base models first
                logger.info("Training base models")
                for model_type in base_model_types:
                    try:
                        model, metrics_dict = self.train_model(
                            model_type, X_train, y_train, X_val, y_val
                        )
                        results[model_type] = (model, metrics_dict)
                    except Exception as e:
                        logger.error(f"Failed to train {model_type}: {e}")
                        # Continue with other models

                # Train ensemble models
                logger.info("Training ensemble models")
                for model_type in ensemble_model_types:
                    try:
                        model, metrics_dict = self.train_model(
                            model_type, X_train, y_train, X_val, y_val
                        )
                        results[model_type] = (model, metrics_dict)
                    except Exception as e:
                        logger.error(f"Failed to train {model_type}: {e}")
                        # Continue with other models

                # Train voting ensemble (requires base models)
                if len(results) >= 2:
                    try:
                        logger.info("Training voting ensemble")
                        model, metrics_dict = self.train_model(
                            "voting_ensemble", X_train, y_train, X_val, y_val
                        )
                        results["voting_ensemble"] = (model, metrics_dict)
                    except Exception as e:
                        logger.error(f"Failed to train voting_ensemble: {e}")
                else:
                    logger.warning("Not enough base models trained for voting ensemble")

                if not results:
                    raise TrainingError(
                        "Failed to train any models",
                        model_name="all",
                    )

                logger.info(f"Training complete for {len(results)} models: {list(results.keys())}")
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
        elif model_type == "random_forest":
            return RandomForestModel(config.random_forest.model_dump())
        elif model_type == "gradient_boosting":
            return GradientBoostingModel(config.gradient_boosting.model_dump())
        elif model_type == "voting_ensemble":
            # Create voting ensemble with trained base models
            base_models = []
            if "xgboost" in self.models:
                base_models.append(self.models["xgboost"])
            if "logistic_regression" in self.models:
                base_models.append(self.models["logistic_regression"])
            if "random_forest" in self.models:
                base_models.append(self.models["random_forest"])
            if "gradient_boosting" in self.models:
                base_models.append(self.models["gradient_boosting"])

            if not base_models:
                raise TrainingError(
                    "No base models available for voting ensemble",
                    model_name="voting_ensemble",
                )

            logger.info(f"Creating voting ensemble with {len(base_models)} base models")
            return VotingEnsembleModel(base_models, config.voting_ensemble.model_dump())
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
