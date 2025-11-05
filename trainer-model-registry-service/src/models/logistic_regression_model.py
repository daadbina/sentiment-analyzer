"""
Logistic Regression model implementation.

Baseline model for comparison with advanced models.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import TrainingError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class LogisticRegressionModel(BaseModel):
    """Logistic Regression model implementation."""

    def __init__(self):
        """Initialize Logistic Regression model."""
        model_config = {
            "C": config.logistic_regression.C,
            "penalty": config.logistic_regression.penalty,
            "solver": config.logistic_regression.solver,
            "max_iter": config.logistic_regression.max_iter,
            "random_state": config.training.random_seed,
            "n_jobs": -1,
        }

        super().__init__(
            model_name="logistic_regression_sentiment",
            model_type="logistic_regression",
            config=model_config,
        )

        self.model = LogisticRegression(**model_config)
        logger.info(
            "Logistic Regression model initialized with config: %s", model_config
        )

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train Logistic Regression model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features (not used for LR)
            y_val: Optional validation labels (not used for LR)

        Returns:
            Dictionary with training metrics

        Raises:
            TrainingError: If training fails
        """
        with tracer.start_as_current_span("train_logistic_regression") as span:
            span.set_attribute("num_train_samples", len(X_train))

            try:
                self.validate_input(X_train, y_train)

                logger.info(
                    f"Training Logistic Regression model with {len(X_train)} samples"
                )

                # Train model
                self.model.fit(X_train, y_train)

                self.is_trained = True

                # Get training metrics
                train_score = self.model.score(X_train, y_train)
                metrics = {
                    "model_type": "logistic_regression",
                    "num_train_samples": len(X_train),
                    "num_features": X_train.shape[1],
                    "train_accuracy": train_score,
                }

                if X_val is not None and y_val is not None:
                    val_score = self.model.score(X_val, y_val)
                    metrics["val_accuracy"] = val_score

                logger.info(f"Logistic Regression training complete: {metrics}")
                return metrics

            except Exception as e:
                logger.error(f"Logistic Regression training failed: {e}")
                raise TrainingError(
                    f"Logistic Regression training failed: {e}",
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
        with tracer.start_as_current_span("predict_logistic_regression"):
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
        with tracer.start_as_current_span("predict_proba_logistic_regression"):
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
        Get feature importance scores (coefficients).

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

                # Get coefficients as importance
                coefficients = self.model.coef_[0]

                # Create dictionary (assuming feature names are available)
                importance_dict = {
                    f"feature_{i}": coef for i, coef in enumerate(coefficients)
                }

                # Sort by absolute importance
                importance_dict = dict(
                    sorted(
                        importance_dict.items(),
                        key=lambda x: abs(x[1]),
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
