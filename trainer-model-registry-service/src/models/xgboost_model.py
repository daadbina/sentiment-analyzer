"""
XGBoost model implementation.

Primary production model for sentiment analysis.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import xgboost as xgb

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class XGBoostModel(BaseModel):
    """XGBoost model implementation."""

    def __init__(self):
        """Initialize XGBoost model."""
        model_config = {
            "max_depth": config.xgboost.max_depth,
            "learning_rate": config.xgboost.learning_rate,
            "n_estimators": config.xgboost.n_estimators,
            "subsample": config.xgboost.subsample,
            "colsample_bytree": config.xgboost.colsample_bytree,
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "random_state": config.training.random_seed,
            "verbosity": 1,
            "scale_pos_weight": 1.0,  # Will be computed based on class distribution
        }

        super().__init__(
            model_name="xgboost_sentiment",
            model_type="xgboost",
            config=model_config,
        )

        self.model = xgb.XGBClassifier(**model_config)
        logger.info("XGBoost model initialized with config: %s", model_config)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train XGBoost model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Dictionary with training metrics

        Raises:
            TrainingError: If training fails
        """
        with tracer.start_as_current_span("train_xgboost") as span:
            span.set_attribute("num_train_samples", len(X_train))
            if X_val is not None:
                span.set_attribute("num_val_samples", len(X_val))

            try:
                self.validate_input(X_train, y_train)

                logger.info(f"Training XGBoost model with {len(X_train)} samples")
                logger.info(f"Training data shape: {X_train.shape}")

                # Compute class weights to handle imbalance
                y_train_series = pd.Series(y_train)
                class_distribution = y_train_series.value_counts().to_dict()
                logger.info(f"Training labels distribution: {class_distribution}")

                # Compute scale_pos_weight: ratio of negative to positive samples
                # This helps XGBoost handle class imbalance
                n_negative = class_distribution.get(0, 1)
                n_positive = class_distribution.get(1, 1)
                scale_pos_weight = n_negative / n_positive
                logger.info(f"Class imbalance ratio (negative/positive): {scale_pos_weight:.4f}")
                logger.info(f"Applying scale_pos_weight={scale_pos_weight:.4f} to XGBoost")

                # Update model with computed scale_pos_weight
                self.model.set_params(scale_pos_weight=scale_pos_weight)

                logger.debug(f"Training features: {list(X_train.columns)}")
                logger.debug(f"Training data null values: {X_train.isnull().sum().sum()}")

                # Prepare evaluation set
                eval_set = None
                if X_val is not None and y_val is not None:
                    self.validate_input(X_val, y_val)
                    logger.info(f"Validation data shape: {X_val.shape}")
                    logger.info(f"Validation labels distribution: {pd.Series(y_val).value_counts().to_dict()}")
                    eval_set = [(X_val, y_val)]

                # Train model
                logger.info("Starting XGBoost model fitting...")

                # Suppress XGBoost warnings about empty datasets or single-class samples
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*Dataset is empty.*")
                    warnings.filterwarnings("ignore", message=".*only positive or negative samples.*")

                    self.model.fit(
                        X_train,
                        y_train,
                        eval_set=eval_set,
                        verbose=False,
                    )

                self.is_trained = True

                # Get training metrics
                metrics = {
                    "model_type": "xgboost",
                    "num_train_samples": len(X_train),
                    "num_features": X_train.shape[1],
                    "n_estimators": self.model.n_estimators,
                }

                if eval_set:
                    # Get best score
                    results = self.model.evals_result()
                    if "validation_0" in results:
                        metrics["best_auc"] = max(results["validation_0"]["auc"])
                        logger.info(f"Best validation AUC: {metrics['best_auc']}")

                logger.info(f"XGBoost training complete: {metrics}")
                return metrics

            except Exception as e:
                logger.error(f"XGBoost training failed: {e}")
                raise TrainingError(
                    f"XGBoost training failed: {e}",
                    model_name=self.model_name,
                )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Features for prediction

        Returns:
            Binary predictions (0 or 1)

        Raises:
            TrainingError: If prediction fails
        """
        with tracer.start_as_current_span("predict_xgboost"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                predictions = self.model.predict(X)
                logger.debug(f"Made predictions for {len(X)} samples")
                return predictions

            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                raise TrainingError(
                    f"Prediction failed: {e}",
                    model_name=self.model_name,
                )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities.

        Args:
            X: Features for prediction

        Returns:
            Prediction probabilities

        Raises:
            TrainingError: If prediction fails
        """
        with tracer.start_as_current_span("predict_proba_xgboost"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                probabilities = self.model.predict_proba(X)
                logger.debug(f"Got probabilities for {len(X)} samples")
                return probabilities

            except Exception as e:
                logger.error(f"Probability prediction failed: {e}")
                raise TrainingError(
                    f"Probability prediction failed: {e}",
                    model_name=self.model_name,
                )

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If model not trained
        """
        with tracer.start_as_current_span("get_feature_importance"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                # Get feature importance
                importance = self.model.feature_importances_
                feature_names = self.model.get_booster().feature_names

                # Create dictionary
                importance_dict = dict(zip(feature_names, importance))

                # Sort by importance
                importance_dict = dict(
                    sorted(
                        importance_dict.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                )

                logger.debug(f"Top 5 features: {list(importance_dict.items())[:5]}")
                return importance_dict

            except Exception as e:
                logger.error(f"Failed to get feature importance: {e}")
                raise TrainingError(
                    f"Failed to get feature importance: {e}",
                    model_name=self.model_name,
                )

    def get_model_params(self) -> Dict[str, Any]:
        """
        Get model parameters.

        Returns:
            Dictionary with model parameters
        """
        return self.model.get_params()

    def set_model_params(self, params: Dict[str, Any]) -> None:
        """
        Set model parameters.

        Args:
            params: Dictionary with parameters to set
        """
        self.model.set_params(**params)
        logger.info(f"Updated model parameters: {params}")
